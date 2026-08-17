"""
Enterprise Warehouse Data Seeder for Whitfield Logistics.

Populates realistic, production-grade warehouse master data:
- 2 Bicoastal Facilities: RNO (Reno, NV) & CMH (Columbus, OH)
- 4 Enterprise Brand Tenants: Aura Electronics, Nordic Apparel, Vitality Nutrition, Apex Workspace
- 12 Real SKU Products with dimensions, weights, and barcodes
- Multi-State Inventory Balances: AVAILABLE, RESERVED, DAMAGED, QUARANTINED (>3,000 units)
- Audit-Grade Immutable Movement Ledgers
- Complete Order Pipeline (PENDING, RESERVED, ALLOCATED, PICKED, PACKED, SHIPPED)
- Inbound Dock Receipts (Active and Draft)
- Inter-Facility Stock Transfers (Bicoastal Rebalancing)
- Customer Returns & RMA Inspections
- Pick Tasks & Outbound Carrier Shipments
"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import uuid

from sqlalchemy import delete, select
from core.database.database import connect_to_database, transaction_session
from core.models.identity_model import User, Warehouse, Seller, UserSellerAssignment, UserWarehouseAssignment
from core.models.catalog_model import Product, ProductIdentifier, WarehouseLocation
from core.models.inventory_model import InventoryBalance, InventoryMovement
from core.models.order_model import Order, OrderLine, InventoryReservation
from core.models.receiving_model import Receipt, ReceiptLine
from core.models.fulfillment_model import PickTask, PickTaskLine, Shipment
from core.models.transfer_model import Transfer, TransferLine
from core.models.return_model import Return, ReturnLine
from core.constants import BusinessStatus, UserRole, UserStatus
from common.auth import hash_password


async def seed_enterprise_data():
    print("Connecting to PostgreSQL...")
    await connect_to_database()

    async with transaction_session() as session:
        print("Cleaning up old dummy / phase test records with TRUNCATE CASCADE...")
        from sqlalchemy import text
        await session.execute(text("""
            TRUNCATE TABLE 
                shipments, 
                pick_task_lines, pick_tasks, 
                inventory_reservations, order_lines, orders, 
                return_lines, returns, 
                transfer_lines, transfers, 
                receipt_lines, receipts, 
                inventory_movements, inventory_balances, 
                product_identifiers, products, warehouse_locations, 
                user_seller_assignments, sellers 
            CASCADE;
        """))

        print("1. Seeding Bicoastal Fulfillment Warehouses (RNO & CMH)...")
        warehouses_data = [
            {"code": "RNO", "name": "Reno West Coast Fulfillment Center", "city": "Reno", "state": "Nevada", "tz": "America/Los_Angeles"},
            {"code": "CMH", "name": "Columbus Midwest Fulfillment Center", "city": "Columbus", "state": "Ohio", "tz": "America/New_York"},
        ]
        wh_map = {}
        for wd in warehouses_data:
            wh_q = await session.execute(select(Warehouse).where(Warehouse.code == wd["code"]))
            wh = wh_q.scalar_one_or_none()
            if not wh:
                wh = Warehouse(
                    code=wd["code"],
                    name=wd["name"],
                    city=wd["city"],
                    state=wd["state"],
                    timezone=wd["tz"],
                    status=BusinessStatus.ACTIVE.value,
                )
                session.add(wh)
                await session.flush()
            else:
                wh.name = wd["name"]
                wh.city = wd["city"]
                wh.state = wd["state"]
            wh_map[wd["code"]] = wh

        # Seed Locations for each warehouse
        loc_map = {}
        for code, wh in wh_map.items():
            for loc_name in ["A-01-01", "A-01-02", "B-02-01", "B-02-02", "C-03-01", "DOCK-INTAKE"]:
                loc = WarehouseLocation(
                    warehouse_id=wh.id,
                    code=f"{code}-{loc_name}",
                    location_type="STORAGE" if "DOCK" not in loc_name else "DOCK",
                    status="ACTIVE",
                )
                session.add(loc)
                await session.flush()
                loc_map[f"{code}-{loc_name}"] = loc

        print("2. Seeding Canonical Enterprise Staff...")
        staff_data = [
            ("admin@whitfield.local", "Alex Whitfield (Platform Admin)", UserRole.ADMINISTRATOR.value, "WhitfieldAdmin123!"),
            ("manager@whitfield.local", "Marcus Vance (Operations Manager)", UserRole.WAREHOUSE_MANAGER.value, "Manager123!"),
            ("receiver@whitfield.local", "Elena Rostova (Inbound Dock Lead)", UserRole.RECEIVER.value, "Receiver123!"),
            ("picker@whitfield.local", "John Doe (Lead Picker/Packer)", UserRole.PICKER_PACKER.value, "Picker123!"),
            ("seller@whitfield.local", "David Chen (Aura Electronics Merchant)", UserRole.SELLER.value, "Seller123!"),
        ]
        user_map = {}
        for email, name, role, pwd in staff_data:
            uq = await session.execute(select(User).where(User.email == email))
            u = uq.scalar_one_or_none()
            if not u:
                u = User(
                    email=email,
                    name=name,
                    role=role,
                    hashed_password=hash_password(pwd),
                    status=UserStatus.ACTIVE.value,
                )
                session.add(u)
                await session.flush()
            else:
                u.name = name
                u.role = role
                u.hashed_password = hash_password(pwd)
                u.status = UserStatus.ACTIVE.value
            user_map[email] = u

            # Assign warehouse access to staff
            for wh in wh_map.values():
                uwa_q = await session.execute(
                    select(UserWarehouseAssignment).where(
                        UserWarehouseAssignment.user_id == u.id,
                        UserWarehouseAssignment.warehouse_id == wh.id
                    )
                )
                if not uwa_q.scalar_one_or_none():
                    session.add(UserWarehouseAssignment(user_id=u.id, warehouse_id=wh.id, assignment_role="PRIMARY"))

        print("3. Seeding Real Brand Sellers...")
        sellers_data = [
            ("SL-AURA", "Aura Electronics Corp"),
            ("SL-NORD", "Nordic Apparel Co"),
            ("SL-VITA", "Vitality Nutrition Labs"),
            ("SL-APEX", "Apex Workspace Innovations"),
        ]
        seller_map = {}
        for sc, sname in sellers_data:
            s = Seller(code=sc, name=sname, status=BusinessStatus.ACTIVE.value)
            session.add(s)
            await session.flush()
            seller_map[sc] = s

        # Assign seller user to Aura
        session.add(UserSellerAssignment(user_id=user_map["seller@whitfield.local"].id, seller_id=seller_map["SL-AURA"].id, assignment_role="SELLER_PRIMARY"))

        print("4. Seeding Real Products with Barcodes & Dimensions...")
        products_data = [
            # Aura Electronics
            ("SL-AURA", "SKU-AURA-ANC100", "Aura Pro Wireless Noise-Cancelling Headphones", "Active noise cancellation, 40h battery, spatial audio.", Decimal("0.45"), Decimal("20.0"), Decimal("18.0"), Decimal("8.0")),
            ("SL-AURA", "SKU-AURA-CHG45W", "Aura MagCharge 45W Fast Wireless Dock", "3-in-1 magnetic charging stand for phone, watch, earbuds.", Decimal("0.25"), Decimal("12.0"), Decimal("12.0"), Decimal("3.0")),
            ("SL-AURA", "SKU-AURA-SPK20", "Aura Sonic Waterproof Bluetooth Speaker", "IPX7 waterproof, 360-degree sound, bass boost.", Decimal("0.60"), Decimal("15.0"), Decimal("8.0"), Decimal("8.0")),
            # Nordic Apparel
            ("SL-NORD", "SKU-NORD-HDY01", "Nordic Heavyweight Oversized Hoodie (Navy / L)", "450 GSM organic French terry cotton, custom relaxed fit.", Decimal("0.80"), Decimal("35.0"), Decimal("25.0"), Decimal("5.0")),
            ("SL-NORD", "SKU-NORD-JCK02", "Nordic All-Weather Ripstop Anorak (Black / M)", "Waterproof membrane, taped seams, packable hood.", Decimal("0.65"), Decimal("38.0"), Decimal("28.0"), Decimal("4.0")),
            ("SL-NORD", "SKU-NORD-TEE01", "Nordic Supima Heavy Cotton Tee (White / M)", "220 GSM combed cotton, reinforced collar.", Decimal("0.25"), Decimal("30.0"), Decimal("22.0"), Decimal("2.0")),
            # Vitality Nutrition
            ("SL-VITA", "SKU-VITA-ELX30", "Vitality Electrolyte Hydration Sticks (Lemon 30pk)", "Zero sugar, potassium, magnesium, Himalayan pink salt.", Decimal("0.35"), Decimal("18.0"), Decimal("12.0"), Decimal("6.0")),
            ("SL-VITA", "SKU-VITA-WHEY2", "Vitality Grass-Fed Isolate Protein (Vanilla 2lb)", "27g pure protein per scoop, non-GMO, digestive enzymes.", Decimal("1.10"), Decimal("25.0"), Decimal("15.0"), Decimal("15.0")),
            ("SL-VITA", "SKU-VITA-MGN60", "Vitality Triple Magnesium Complex (60 Caps)", "Glycinate, Malate, and L-Threonate for sleep and recovery.", Decimal("0.15"), Decimal("10.0"), Decimal("6.0"), Decimal("6.0")),
            # Apex Workspace
            ("SL-APEX", "SKU-APEX-KBD75", "Apex Pro 75% Gasket Mechanical Keyboard", "Hot-swappable switches, wireless 2.4G/BT, CNC aluminum frame.", Decimal("0.95"), Decimal("32.0"), Decimal("14.0"), Decimal("4.0")),
            ("SL-APEX", "SKU-APEX-MATXL", "Apex DeskMat Pro Felt & Leather (90x40cm)", "Water-resistant vegan leather and merino wool felt backing.", Decimal("0.40"), Decimal("42.0"), Decimal("8.0"), Decimal("8.0")),
            ("SL-APEX", "SKU-APEX-MOU01", "Apex Ultralight Wireless Precision Mouse", "58g featherweight, 26,000 DPI optical sensor, optical switches.", Decimal("0.18"), Decimal("14.0"), Decimal("9.0"), Decimal("5.0")),
        ]

        prod_map = {}
        for sc, sku, pname, pdesc, wt, l, w, h in products_data:
            p = Product(
                seller_id=seller_map[sc].id,
                sku=sku,
                name=pname,
                description=pdesc,
                unit_of_measure="EA",
                weight=wt,
                length=l,
                width=w,
                height=h,
                status="ACTIVE",
            )
            session.add(p)
            await session.flush()
            prod_map[sku] = p

            # Add primary barcode identifier
            session.add(ProductIdentifier(
                product_id=p.id,
                identifier_type="UPC",
                identifier_value=f"8500{abs(hash(sku)) % 100000000:08d}",
                is_primary=True,
            ))

        print("5. Seeding Real Multi-State Inventory Balances & Ledgers...")
        # Populate balances across Reno and Columbus
        inventory_distribution = [
            ("SKU-AURA-ANC100", "RNO", "AVAILABLE", Decimal("350.00")),
            ("SKU-AURA-ANC100", "CMH", "AVAILABLE", Decimal("180.00")),
            ("SKU-AURA-ANC100", "RNO", "RESERVED", Decimal("25.00")),
            ("SKU-AURA-ANC100", "CMH", "DAMAGED", Decimal("4.00")),

            ("SKU-AURA-CHG45W", "RNO", "AVAILABLE", Decimal("420.00")),
            ("SKU-AURA-CHG45W", "CMH", "AVAILABLE", Decimal("290.00")),
            ("SKU-AURA-CHG45W", "CMH", "RESERVED", Decimal("15.00")),

            ("SKU-AURA-SPK20", "RNO", "AVAILABLE", Decimal("200.00")),
            ("SKU-AURA-SPK20", "CMH", "AVAILABLE", Decimal("150.00")),
            ("SKU-AURA-SPK20", "RNO", "QUARANTINED", Decimal("6.00")),

            ("SKU-NORD-HDY01", "RNO", "AVAILABLE", Decimal("180.00")),
            ("SKU-NORD-HDY01", "CMH", "AVAILABLE", Decimal("220.00")),
            ("SKU-NORD-HDY01", "CMH", "RESERVED", Decimal("12.00")),

            ("SKU-NORD-JCK02", "RNO", "AVAILABLE", Decimal("140.00")),
            ("SKU-NORD-JCK02", "CMH", "AVAILABLE", Decimal("95.00")),
            ("SKU-NORD-JCK02", "RNO", "DAMAGED", Decimal("2.00")),

            ("SKU-NORD-TEE01", "RNO", "AVAILABLE", Decimal("500.00")),
            ("SKU-NORD-TEE01", "CMH", "AVAILABLE", Decimal("450.00")),

            ("SKU-VITA-ELX30", "RNO", "AVAILABLE", Decimal("600.00")),
            ("SKU-VITA-ELX30", "CMH", "AVAILABLE", Decimal("550.00")),
            ("SKU-VITA-ELX30", "RNO", "RESERVED", Decimal("30.00")),

            ("SKU-VITA-WHEY2", "RNO", "AVAILABLE", Decimal("280.00")),
            ("SKU-VITA-WHEY2", "CMH", "AVAILABLE", Decimal("210.00")),

            ("SKU-VITA-MGN60", "RNO", "AVAILABLE", Decimal("400.00")),
            ("SKU-VITA-MGN60", "CMH", "AVAILABLE", Decimal("350.00")),

            ("SKU-APEX-KBD75", "RNO", "AVAILABLE", Decimal("160.00")),
            ("SKU-APEX-KBD75", "CMH", "AVAILABLE", Decimal("190.00")),
            ("SKU-APEX-KBD75", "CMH", "QUARANTINED", Decimal("5.00")),

            ("SKU-APEX-MATXL", "RNO", "AVAILABLE", Decimal("320.00")),
            ("SKU-APEX-MATXL", "CMH", "AVAILABLE", Decimal("280.00")),

            ("SKU-APEX-MOU01", "RNO", "AVAILABLE", Decimal("240.00")),
            ("SKU-APEX-MOU01", "CMH", "AVAILABLE", Decimal("210.00")),
        ]

        for sku, wh_code, state, qty in inventory_distribution:
            p = prod_map[sku]
            wh = wh_map[wh_code]
            loc = loc_map.get(f"{wh_code}-A-01-01")

            b = InventoryBalance(
                seller_id=p.seller_id,
                product_id=p.id,
                warehouse_id=wh.id,
                location_id=loc.id if loc else None,
                inventory_state=state,
                quantity=qty,
            )
            session.add(b)

            # Movement ledger record
            m = InventoryMovement(
                seller_id=p.seller_id,
                product_id=p.id,
                warehouse_id=wh.id,
                location_id=loc.id if loc else None,
                inventory_state=state,
                quantity_delta=qty,
                movement_type="INBOUND_RECEIPT" if state == "AVAILABLE" else "STATE_TRANSFER",
                source_type="INITIAL_SEED",
                source_id=uuid.uuid4(),
                idempotency_key=f"SEED-{sku}-{wh_code}-{state}",
                reason_code="WAREHOUSE_INITIALIZATION",
                reason_text=f"Initial seed balance of {qty} units in {wh.name}",
                actor_user_id=user_map["admin@whitfield.local"].id,
                occurred_at=datetime.now(UTC) - timedelta(days=2),
                recorded_at=datetime.now(UTC) - timedelta(days=2),
            )
            session.add(m)

        print("6. Seeding Real Customer Orders (All Pipeline States)...")
        orders_data = [
            {
                "num": "ORD-2026-1001",
                "seller": "SL-AURA",
                "wh": "RNO",
                "status": "RESERVED",
                "customer": "Jonathan Miller",
                "addr": "742 Evergreen Terrace",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94102",
                "lines": [("SKU-AURA-ANC100", Decimal("1.00")), ("SKU-AURA-CHG45W", Decimal("1.00"))],
            },
            {
                "num": "ORD-2026-1002",
                "seller": "SL-NORD",
                "wh": "CMH",
                "status": "ALLOCATED",
                "customer": "Sarah Jenkins",
                "addr": "1204 Elmwood Ave",
                "city": "Chicago",
                "state": "IL",
                "zip": "60601",
                "lines": [("SKU-NORD-JCK02", Decimal("1.00")), ("SKU-NORD-HDY01", Decimal("2.00"))],
            },
            {
                "num": "ORD-2026-1003",
                "seller": "SL-VITA",
                "wh": "RNO",
                "status": "PENDING",
                "customer": "Marcus Brody",
                "addr": "554 Pacific Blvd",
                "city": "Seattle",
                "state": "WA",
                "zip": "98101",
                "lines": [("SKU-VITA-ELX30", Decimal("3.00")), ("SKU-VITA-WHEY2", Decimal("1.00"))],
            },
            {
                "num": "ORD-2026-1004",
                "seller": "SL-APEX",
                "wh": "CMH",
                "status": "PICKED",
                "customer": "Emily Chen",
                "addr": "88 Riverside Drive",
                "city": "New York",
                "state": "NY",
                "zip": "10024",
                "lines": [("SKU-APEX-KBD75", Decimal("1.00")), ("SKU-APEX-MATXL", Decimal("1.00"))],
            },
            {
                "num": "ORD-2026-1005",
                "seller": "SL-AURA",
                "wh": "RNO",
                "status": "PACKED",
                "customer": "David Ross",
                "addr": "301 Ocean Avenue",
                "city": "Santa Monica",
                "state": "CA",
                "zip": "90401",
                "lines": [("SKU-AURA-SPK20", Decimal("2.00"))],
            },
            {
                "num": "ORD-2026-1006",
                "seller": "SL-NORD",
                "wh": "CMH",
                "status": "SHIPPED",
                "customer": "Rachel Adams",
                "addr": "410 Chestnut Street",
                "city": "Philadelphia",
                "state": "PA",
                "zip": "19106",
                "lines": [("SKU-NORD-TEE01", Decimal("3.00"))],
            },
        ]

        order_map = {}
        order_lines_map = {}
        for od in orders_data:
            ord_obj = Order(
                seller_id=seller_map[od["seller"]].id,
                seller_order_number=od["num"],
                warehouse_id=wh_map[od["wh"]].id,
                channel="SHOPIFY",
                status=od["status"],
                customer_name=od["customer"],
                shipping_address_line1=od["addr"],
                city=od["city"],
                state=od["state"],
                postal_code=od["zip"],
            )
            session.add(ord_obj)
            await session.flush()
            order_map[od["num"]] = ord_obj
            order_lines_map[od["num"]] = []

            for sku, qty in od["lines"]:
                p = prod_map[sku]
                ol = OrderLine(
                    order_id=ord_obj.id,
                    product_id=p.id,
                    ordered_quantity=qty,
                    reserved_quantity=qty if od["status"] in ["RESERVED", "ALLOCATED", "PICKED", "PACKED", "SHIPPED"] else Decimal("0.00"),
                    picked_quantity=qty if od["status"] in ["PICKED", "PACKED", "SHIPPED"] else Decimal("0.00"),
                    shipped_quantity=qty if od["status"] == "SHIPPED" else Decimal("0.00"),
                )
                session.add(ol)
                await session.flush()
                order_lines_map[od["num"]].append(ol)

                # Add reservation record if reserved
                if od["status"] in ["RESERVED", "ALLOCATED", "PICKED", "PACKED"]:
                    session.add(InventoryReservation(
                        order_line_id=ol.id,
                        warehouse_id=ord_obj.warehouse_id,
                        product_id=p.id,
                        quantity=qty,
                        status="ACTIVE",
                        expires_at=datetime.now(UTC) + timedelta(hours=24),
                    ))

        print("7. Seeding Real Inbound Dock Receipts...")
        # Receipt 1: Completed 40ft container intake at Reno
        rec1 = Receipt(
            receipt_number="REC-2026-001",
            seller_id=seller_map["SL-AURA"].id,
            warehouse_id=wh_map["RNO"].id,
            source_type="CARRIER_TRACKING",
            source_reference="1Z8942109823417621",
            status="COMPLETED",
            expected_arrival_at=datetime.now(UTC) - timedelta(days=1),
            actual_arrival_at=datetime.now(UTC) - timedelta(days=1),
            completed_at=datetime.now(UTC) - timedelta(hours=18),
            started_by_user_id=user_map["receiver@whitfield.local"].id,
            completed_by_user_id=user_map["receiver@whitfield.local"].id,
        )
        session.add(rec1)
        await session.flush()
        session.add(ReceiptLine(
            receipt_id=rec1.id,
            product_id=prod_map["SKU-AURA-ANC100"].id,
            expected_quantity=Decimal("350.00"),
            sellable_quantity=Decimal("350.00"),
            damaged_quantity=Decimal("0.00"),
            notes="Verified intact dock delivery",
        ))
        session.add(ReceiptLine(
            receipt_id=rec1.id,
            product_id=prod_map["SKU-AURA-CHG45W"].id,
            expected_quantity=Decimal("420.00"),
            sellable_quantity=Decimal("420.00"),
            damaged_quantity=Decimal("0.00"),
            notes="Verified intact dock delivery",
        ))

        # Receipt 2: Live Inbound Delivery Draft at Columbus Dock
        rec2 = Receipt(
            receipt_number="REC-2026-002",
            seller_id=seller_map["SL-VITA"].id,
            warehouse_id=wh_map["CMH"].id,
            source_type="SELLER_DROP_OFF",
            source_reference="BOL-2026-8812",
            status="DRAFT",
            expected_arrival_at=datetime.now(UTC),
            actual_arrival_at=datetime.now(UTC) - timedelta(hours=2),
            started_by_user_id=user_map["receiver@whitfield.local"].id,
        )
        session.add(rec2)
        await session.flush()
        session.add(ReceiptLine(
            receipt_id=rec2.id,
            product_id=prod_map["SKU-VITA-ELX30"].id,
            expected_quantity=Decimal("200.00"),
            sellable_quantity=Decimal("0.00"),
            damaged_quantity=Decimal("0.00"),
            notes="Awaiting dock unloading",
        ))

        print("8. Seeding Inter-Facility Transfers (Bicoastal Rebalance)...")
        trf1 = Transfer(
            transfer_number="TRF-2026-101",
            seller_id=seller_map["SL-AURA"].id,
            origin_warehouse_id=wh_map["RNO"].id,
            destination_warehouse_id=wh_map["CMH"].id,
            status="DISPATCHED",
            created_by_user_id=user_map["manager@whitfield.local"].id,
            approved_by_user_id=user_map["manager@whitfield.local"].id,
            dispatched_at=datetime.now(UTC) - timedelta(hours=6),
            notes="West-to-East coast inventory rebalance for high headphone demand",
        )
        session.add(trf1)
        await session.flush()
        session.add(TransferLine(
            transfer_id=trf1.id,
            product_id=prod_map["SKU-AURA-ANC100"].id,
            requested_quantity=Decimal("100.00"),
            approved_quantity=Decimal("100.00"),
            dispatched_quantity=Decimal("100.00"),
            received_good_quantity=Decimal("0.00"),
        ))

        trf2 = Transfer(
            transfer_number="TRF-2026-102",
            seller_id=seller_map["SL-NORD"].id,
            origin_warehouse_id=wh_map["CMH"].id,
            destination_warehouse_id=wh_map["RNO"].id,
            status="DRAFT",
            created_by_user_id=user_map["manager@whitfield.local"].id,
            notes="Draft transfer for seasonal winter outerwear",
        )
        session.add(trf2)
        await session.flush()
        session.add(TransferLine(
            transfer_id=trf2.id,
            product_id=prod_map["SKU-NORD-JCK02"].id,
            requested_quantity=Decimal("50.00"),
            approved_quantity=Decimal("0.00"),
            dispatched_quantity=Decimal("0.00"),
            received_good_quantity=Decimal("0.00"),
        ))

        print("9. Seeding Customer Returns (RMAs)...")
        ret1 = Return(
            return_number="RET-2026-001",
            rma_number="RMA-2026-501",
            seller_id=seller_map["SL-NORD"].id,
            warehouse_id=wh_map["CMH"].id,
            inbound_tracking_number="1Z999AA10987654321",
            status="COMPLETED",
        )
        session.add(ret1)
        await session.flush()
        session.add(ReturnLine(
            return_id=ret1.id,
            product_id=prod_map["SKU-NORD-HDY01"].id,
            expected_quantity=Decimal("1.00"),
            received_quantity=Decimal("1.00"),
            inspection_notes="Returned in original packaging, perfect condition. Restocked to available.",
        ))

        ret2 = Return(
            return_number="RET-2026-002",
            rma_number="RMA-2026-502",
            seller_id=seller_map["SL-APEX"].id,
            warehouse_id=wh_map["RNO"].id,
            inbound_tracking_number="9400111899562537482910",
            status="INSPECTED",
        )
        session.add(ret2)
        await session.flush()
        session.add(ReturnLine(
            return_id=ret2.id,
            product_id=prod_map["SKU-APEX-KBD75"].id,
            expected_quantity=Decimal("1.00"),
            received_quantity=Decimal("1.00"),
            inspection_notes="Outer box crushed during carrier transit. Switches intact, held in quarantine.",
        ))

        print("10. Seeding Pick Tasks & Shipments...")
        # Pick task for ORD-2026-1004
        ord_picked = order_map["ORD-2026-1004"]
        pt = PickTask(
            order_id=ord_picked.id,
            warehouse_id=ord_picked.warehouse_id,
            assigned_user_id=user_map["picker@whitfield.local"].id,
            status="COMPLETED",
            priority=1,
            completed_at=datetime.now(UTC) - timedelta(hours=2),
        )
        session.add(pt)
        await session.flush()
        for ol in order_lines_map["ORD-2026-1004"]:
            session.add(PickTaskLine(
                pick_task_id=pt.id,
                order_line_id=ol.id,
                product_id=ol.product_id,
                location_id=loc_map.get("CMH-B-02-01").id,
                requested_quantity=ol.ordered_quantity,
                picked_quantity=ol.ordered_quantity,
            ))

        # Shipment for ORD-2026-1006
        ord_shipped = order_map["ORD-2026-1006"]
        ship = Shipment(
            order_id=ord_shipped.id,
            warehouse_id=ord_shipped.warehouse_id,
            carrier="UPS",
            service_level="GROUND",
            tracking_number="1Z999AA10123456784",
            status="SHIPPED",
        )
        session.add(ship)

    print("SUCCESS: Enterprise Data Seeding Completed Successfully!")


if __name__ == "__main__":
    asyncio.run(seed_enterprise_data())

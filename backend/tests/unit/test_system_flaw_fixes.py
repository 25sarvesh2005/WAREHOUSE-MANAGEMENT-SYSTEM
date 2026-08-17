"""
Unit tests verifying fixes for core system flaws:
1. Scope assertion accepting UUIDs and strings.
2. Dynamic reservation idempotency allowing repeat reservation attempts.
3. Short-pick missing stock routing to QUARANTINED rather than AVAILABLE.
4. Transfer shrinkage tracking for lost transit goods.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from common.warehouse_scope import assert_seller_access, assert_warehouse_access
from core.constants import BusinessStatus, InventoryState, OrderStatus, PickTaskStatus, TransferStatus, UserRole
from core.controllers.fulfillment_controller import fulfillment_controller
from core.controllers.order_controller import order_controller
from core.controllers.transfer_controller import transfer_controller
from core.cruds import catalog_crud, identity_crud, inventory_crud, order_crud, transfer_crud
from core.database.database import close_database_connection, connect_to_database, transaction_session
from core.database.seed import initialize_schema_for_development, seed_initial_data
from core.models.catalog_model import Product
from core.models.identity_model import Seller, Warehouse




@pytest.mark.asyncio
async def test_scope_assertions_accept_uuids_and_strings():
    """Verify that assert_seller_access and assert_warehouse_access work with UUID objects."""
    seller_uuid = uuid4()
    warehouse_uuid = uuid4()

    scope = {
        "user_id": str(uuid4()),
        "role": UserRole.SELLER.value,
        "seller_ids": [str(seller_uuid)],
        "warehouse_ids": [str(warehouse_uuid)],
    }

    # Should succeed with UUID objects
    assert_seller_access(scope, seller_uuid)
    assert_warehouse_access(scope, warehouse_uuid)

    # Should succeed with string objects
    assert_seller_access(scope, str(seller_uuid))
    assert_warehouse_access(scope, str(warehouse_uuid))

    # Should fail for unauthorized UUID
    other_uuid = uuid4()
    with pytest.raises(HTTPException) as exc_info:
        assert_seller_access(scope, other_uuid)
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info:
        assert_warehouse_access(scope, other_uuid)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_order_re_reservation_succeeds_without_idempotency_collision():
    """Verify that an order with backorder can be reserved multiple times without unique constraint error."""
    async with transaction_session() as session:
        admin_user = await identity_crud.get_user_by_email(session, "admin@whitfield.local")
        assert admin_user is not None
        admin_id = admin_user.id

        # Create seller & warehouse
        seller = Seller(
            name=f"Seller {uuid4().hex[:6]}",
            code=f"S-{uuid4().hex[:4].upper()}",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(seller)
        warehouse = Warehouse(
            name=f"Warehouse {uuid4().hex[:6]}",
            code=f"W-{uuid4().hex[:4].upper()}",
            timezone="UTC",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(warehouse)
        await session.flush()

        # Create product
        product = Product(
            seller_id=seller.id,
            sku=f"SKU-RERES-{uuid4().hex[:6].upper()}",
            name="Re-res Test Product",
            unit_of_measure="EA",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(product)
        await session.flush()

        # Seed initial AVAILABLE inventory of 5 units
        await inventory_crud.update_balance_projection(
            session,
            seller_id=seller.id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            inventory_state=InventoryState.AVAILABLE.value,
            quantity_delta=Decimal("5.00"),
        )
        seller_id = seller.id
        warehouse_id = warehouse.id
        product_id = product.id

    scope = {
        "user_id": str(admin_id),
        "role": UserRole.ADMINISTRATOR.value,
        "seller_ids": [],
        "warehouse_ids": [],
    }

    # Create order for 10 units
    order_data = {
        "seller_id": str(seller_id),
        "warehouse_id": str(warehouse_id),
        "seller_order_number": f"ORD-RERES-{uuid4().hex[:6].upper()}",
        "lines": [{"product_id": str(product_id), "ordered_quantity": "10.00"}],
    }
    order = await order_controller.create_order(order_data, scope)

    # First reservation attempt: 5 reserved, 5 backordered
    res1 = await order_controller.reserve_order(order.id, scope)
    assert res1.status == OrderStatus.PARTIALLY_RESERVED.value
    assert res1.lines[0].reserved_quantity == Decimal("5.00")
    assert res1.lines[0].backordered_quantity == Decimal("5.00")

    # Inbound more stock (+10 available units)
    async with transaction_session() as session:
        await inventory_crud.update_balance_projection(
            session,
            seller_id=seller_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            inventory_state=InventoryState.AVAILABLE.value,
            quantity_delta=Decimal("10.00"),
        )

    # Second reservation attempt on the same order: should reserve the remaining 5 without constraint collision
    res2 = await order_controller.reserve_order(order.id, scope)
    assert res2.status == OrderStatus.RESERVED.value
    assert res2.lines[0].reserved_quantity == Decimal("10.00")
    assert res2.lines[0].backordered_quantity == Decimal("0.00")


@pytest.mark.asyncio
async def test_short_pick_moves_stock_to_quarantined_not_available():
    """Verify short-picked items move to QUARANTINED to avoid phantom inventory loops."""
    async with transaction_session() as session:
        admin_user = await identity_crud.get_user_by_email(session, "admin@whitfield.local")
        assert admin_user is not None
        admin_id = admin_user.id

        seller = Seller(
            name=f"Seller {uuid4().hex[:6]}",
            code=f"S-{uuid4().hex[:4].upper()}",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(seller)
        warehouse = Warehouse(
            name=f"Warehouse {uuid4().hex[:6]}",
            code=f"W-{uuid4().hex[:4].upper()}",
            timezone="UTC",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(warehouse)
        await session.flush()

        product = Product(
            seller_id=seller.id,
            sku=f"SKU-SHORT-{uuid4().hex[:6].upper()}",
            name="Short Pick Test Product",
            unit_of_measure="EA",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(product)
        await session.flush()

        await inventory_crud.update_balance_projection(
            session,
            seller_id=seller.id,
            product_id=product.id,
            warehouse_id=warehouse.id,
            inventory_state=InventoryState.AVAILABLE.value,
            quantity_delta=Decimal("10.00"),
        )
        seller_id = seller.id
        warehouse_id = warehouse.id
        product_id = product.id

    scope = {
        "user_id": str(admin_id),
        "role": UserRole.ADMINISTRATOR.value,
        "seller_ids": [],
        "warehouse_ids": [],
    }

    # Create and reserve order for 10 units
    order = await order_controller.create_order(
        {
            "seller_id": str(seller_id),
            "warehouse_id": str(warehouse_id),
            "seller_order_number": f"ORD-SP-{uuid4().hex[:6].upper()}",
            "lines": [{"product_id": str(product_id), "ordered_quantity": "10.00"}],
        },
        scope,
    )
    await order_controller.reserve_order(order.id, scope)

    # Create pick task
    pick_task = await fulfillment_controller.create_pick_task(
        {"order_id": str(order.id), "priority": 1},
        scope,
    )

    # Complete pick task with short pick: 7 picked, 3 short
    task_line_id = pick_task.lines[0].id
    completed_task = await fulfillment_controller.complete_pick_task(
        pick_task.id,
        {
            "lines": [
                {
                    "pick_task_line_id": str(task_line_id),
                    "picked_quantity": "7.00",
                    "short_quantity": "3.00",
                }
            ]
        },
        scope,
    )

    assert completed_task.status == PickTaskStatus.SHORT_PICK_EXCEPTION.value

    # Verify inventory balances:
    # AVAILABLE: 0.00 (not restored to 3.00)
    # RESERVED: 7.00 (down from 10.00 by 3.00 short)
    # QUARANTINED: 3.00 (shortage routed to quarantine)
    async with transaction_session() as session:
        bal_avail = await inventory_crud.get_balance_for_update(
            session, seller_id=seller_id, product_id=product_id, warehouse_id=warehouse_id,
            inventory_state=InventoryState.AVAILABLE.value,
        )
        bal_res = await inventory_crud.get_balance_for_update(
            session, seller_id=seller_id, product_id=product_id, warehouse_id=warehouse_id,
            inventory_state=InventoryState.RESERVED.value,
        )
        bal_quar = await inventory_crud.get_balance_for_update(
            session, seller_id=seller_id, product_id=product_id, warehouse_id=warehouse_id,
            inventory_state=InventoryState.QUARANTINED.value,
        )

        avail_qty = bal_avail.quantity if bal_avail else Decimal("0.00")
        res_qty = bal_res.quantity if bal_res else Decimal("0.00")
        quar_qty = bal_quar.quantity if bal_quar else Decimal("0.00")

        assert avail_qty == Decimal("0.00")
        assert res_qty == Decimal("7.00")
        assert quar_qty == Decimal("3.00")


@pytest.mark.asyncio
async def test_transfer_shrinkage_discrepancy_recorded_on_short_receipt():
    """Verify inter-warehouse transfer with transit shortage records discrepancy review status."""
    async with transaction_session() as session:
        admin_user = await identity_crud.get_user_by_email(session, "admin@whitfield.local")
        assert admin_user is not None
        admin_id = admin_user.id

        seller = Seller(
            name=f"Seller {uuid4().hex[:6]}",
            code=f"S-{uuid4().hex[:4].upper()}",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(seller)
        wh_origin = Warehouse(
            name=f"Origin WH {uuid4().hex[:6]}",
            code=f"WO-{uuid4().hex[:4].upper()}",
            timezone="UTC",
            status=BusinessStatus.ACTIVE.value,
        )
        wh_dest = Warehouse(
            name=f"Dest WH {uuid4().hex[:6]}",
            code=f"WD-{uuid4().hex[:4].upper()}",
            timezone="UTC",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(wh_origin)
        session.add(wh_dest)
        await session.flush()

        product = Product(
            seller_id=seller.id,
            sku=f"SKU-TRF-{uuid4().hex[:6].upper()}",
            name="Transfer Discrepancy Test Product",
            unit_of_measure="EA",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(product)
        await session.flush()

        # Seed 20 available units at origin warehouse
        await inventory_crud.update_balance_projection(
            session,
            seller_id=seller.id,
            product_id=product.id,
            warehouse_id=wh_origin.id,
            inventory_state=InventoryState.AVAILABLE.value,
            quantity_delta=Decimal("20.00"),
        )
        seller_id = seller.id
        wh_orig_id = wh_origin.id
        wh_dest_id = wh_dest.id
        product_id = product.id

    scope = {
        "user_id": str(admin_id),
        "role": UserRole.ADMINISTRATOR.value,
        "seller_ids": [],
        "warehouse_ids": [],
    }

    # Create transfer of 10 units
    transfer = await transfer_controller.create_transfer(
        {
            "seller_id": str(seller_id),
            "origin_warehouse_id": str(wh_orig_id),
            "destination_warehouse_id": str(wh_dest_id),
            "lines": [{"product_id": str(product_id), "requested_quantity": "10.00"}],
        },
        scope,
    )
    # Approve and dispatch transfer
    await transfer_controller.approve_transfer(transfer.id, scope)
    dispatched = await transfer_controller.dispatch_transfer(transfer.id, scope)
    assert dispatched.status == TransferStatus.DISPATCHED.value

    # Receive transfer short (8 good, 0 damaged -> 2 missing)
    line_id = dispatched.lines[0].id
    received = await transfer_controller.receive_transfer(
        transfer.id,
        {
            "lines": [
                {
                    "line_id": str(line_id),
                    "received_good_quantity": "8.00",
                    "received_damaged_quantity": "0.00",
                }
            ]
        },
        scope,
    )

    assert received.status == TransferStatus.DISCREPANCY_REVIEW.value
    assert received.lines[0].missing_quantity == Decimal("2.00")
    assert received.lines[0].received_good_quantity == Decimal("8.00")

    # Verify destination available balance is 8.00
    async with transaction_session() as session:
        dest_bal = await inventory_crud.get_balance_for_update(
            session,
            seller_id=seller_id,
            product_id=product_id,
            warehouse_id=wh_dest_id,
            inventory_state=InventoryState.AVAILABLE.value,
        )
        assert dest_bal.quantity == Decimal("8.00")


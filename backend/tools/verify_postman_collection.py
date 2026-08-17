"""
Postman Collection Automated API Verifier.

Parses and validates functional endpoints declared in postman_collection.json
against the active FastAPI application using ASGI transport.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx
from httpx import ASGITransport

# Set up environment and imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config.settings import get_settings
from core.database.database import connect_to_database, close_database_connection
from core.database.seed import initialize_schema_for_development, seed_initial_data
from main import app


async def run_postman_verification() -> None:
    print("=" * 80)
    print("POSTMAN COLLECTION API VERIFICATION")
    print("=" * 80)

    # 1. Connect and initialize DB
    await connect_to_database()
    await initialize_schema_for_development()
    await seed_initial_data()

    passed = 0
    failed = 0
    total = 0

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        # -------------------------------------------------------------
        # 1. Health & Readiness
        # -------------------------------------------------------------
        print("\n[1] Verifying Health & Readiness Endpoints...")
        r_live = await client.get("/health/live")
        total += 1
        if r_live.status_code == 200 and r_live.json().get("status") == "live":
            passed += 1
            print("  [PASS] GET /health/live -> 200 OK (live)")
        else:
            failed += 1
            print(f"  [FAIL] GET /health/live failed: {r_live.status_code} {r_live.text}")

        r_ready = await client.get("/health/ready")
        total += 1
        if r_ready.status_code == 200 and r_ready.json().get("status") == "ready":
            passed += 1
            print("  [PASS] GET /health/ready -> 200 OK (ready)")
        else:
            failed += 1
            print(f"  [FAIL] GET /health/ready failed: {r_ready.status_code} {r_ready.text}")

        # -------------------------------------------------------------
        # 2. Authentication
        # -------------------------------------------------------------
        print("\n[2] Verifying Authentication Endpoints...")
        settings = get_settings()
        login_payload = {
            "email": settings.bootstrap_admin_email,
            "password": settings.bootstrap_admin_password,
        }
        r_login = await client.post("/api/v1/auth/login", json=login_payload)
        total += 1
        if r_login.status_code == 200 and "access_token" in r_login.json():
            passed += 1
            token_data = r_login.json()
            admin_token = token_data["access_token"]
            refresh_tok = token_data.get("refresh_token")
            headers = {"Authorization": f"Bearer {admin_token}"}
            print("  [PASS] POST /api/v1/auth/login -> 200 OK (JWT Received)")
        else:
            failed += 1
            print(f"  [FAIL] POST /api/v1/auth/login failed: {r_login.status_code} {r_login.text}")
            return

        r_me = await client.get("/api/v1/auth/me", headers=headers)
        total += 1
        if r_me.status_code == 200 and r_me.json().get("role") == "ADMINISTRATOR":
            passed += 1
            print("  [PASS] GET /api/v1/auth/me -> 200 OK (Role: ADMINISTRATOR)")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/auth/me failed: {r_me.status_code} {r_me.text}")

        # -------------------------------------------------------------
        # 3. Master Data: Sellers, Warehouses, Users
        # -------------------------------------------------------------
        print("\n[3] Verifying Master Data Endpoints...")
        r_sellers = await client.get("/api/v1/sellers", headers=headers)
        total += 1
        if r_sellers.status_code == 200 and len(r_sellers.json()) > 0:
            passed += 1
            seller_id = r_sellers.json()[0]["id"]
            print(f"  [PASS] GET /api/v1/sellers -> 200 OK ({len(r_sellers.json())} sellers, first: {seller_id})")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/sellers failed: {r_sellers.status_code}")

        r_wh = await client.get("/api/v1/warehouses", headers=headers)
        total += 1
        if r_wh.status_code == 200 and len(r_wh.json()) > 0:
            passed += 1
            wh_id = r_wh.json()[0]["id"]
            print(f"  [PASS] GET /api/v1/warehouses -> 200 OK ({len(r_wh.json())} warehouses, first: {wh_id})")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/warehouses failed: {r_wh.status_code}")

        r_users = await client.get("/api/v1/users", headers=headers)
        total += 1
        if r_users.status_code == 200:
            passed += 1
            print(f"  [PASS] GET /api/v1/users -> 200 OK ({len(r_users.json())} users)")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/users failed: {r_users.status_code}")

        # -------------------------------------------------------------
        # 4. Catalog: Products & Locations
        # -------------------------------------------------------------
        print("\n[4] Verifying Catalog Endpoints...")
        sku = f"POSTMAN-SKU-{uuid4().hex[:6].upper()}"
        prod_payload = {
            "seller_id": seller_id,
            "sku": sku,
            "name": f"Postman Test Item {sku}",
            "description": "Created during Postman collection verification",
            "barcode": f"BAR-{uuid4().hex[:8].upper()}",
            "requires_serial": False,
        }
        r_prod = await client.post("/api/v1/products", json=prod_payload, headers=headers)
        total += 1
        if r_prod.status_code == 201:
            passed += 1
            product = r_prod.json()
            product_id = product["id"]
            print(f"  [PASS] POST /api/v1/products -> 201 Created (ID: {product_id}, SKU: {sku})")
        else:
            failed += 1
            print(f"  [FAIL] POST /api/v1/products failed: {r_prod.status_code} {r_prod.text}")

        r_prods = await client.get("/api/v1/products", headers=headers)
        total += 1
        if r_prods.status_code == 200:
            passed += 1
            print(f"  [PASS] GET /api/v1/products -> 200 OK ({len(r_prods.json())} products)")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/products failed: {r_prods.status_code}")

        loc_code = f"POSTMAN-BIN-{uuid4().hex[:4].upper()}"
        loc_payload = {
            "warehouse_id": wh_id,
            "code": loc_code,
            "zone": "A",
            "aisle": "01",
            "rack": "01",
            "shelf": "01",
            "bin": "01",
            "location_type": "STORAGE",
        }
        r_loc = await client.post("/api/v1/warehouse-locations", json=loc_payload, headers=headers)
        total += 1
        if r_loc.status_code == 201:
            passed += 1
            location_id = r_loc.json()["id"]
            print(f"  [PASS] POST /api/v1/warehouse-locations -> 201 Created (Code: {loc_code})")
        else:
            failed += 1
            print(f"  [FAIL] POST /api/v1/warehouse-locations failed: {r_loc.status_code} {r_loc.text}")

        # -------------------------------------------------------------
        # 5. Inventory: Balances, Movements, Reconcile
        # -------------------------------------------------------------
        print("\n[5] Verifying Inventory Endpoints...")
        r_bal = await client.get("/api/v1/inventory/balances", headers=headers)
        total += 1
        if r_bal.status_code == 200:
            passed += 1
            print(f"  [PASS] GET /api/v1/inventory/balances -> 200 OK ({len(r_bal.json())} balance records)")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/inventory/balances failed: {r_bal.status_code}")

        r_mov = await client.get("/api/v1/inventory/movements", headers=headers)
        total += 1
        if r_mov.status_code == 200:
            passed += 1
            print(f"  [PASS] GET /api/v1/inventory/movements -> 200 OK ({len(r_mov.json())} ledger movements)")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/inventory/movements failed: {r_mov.status_code}")

        r_rec = await client.post(
            "/api/v1/inventory/reconcile",
            json={"warehouse_id": wh_id, "seller_id": seller_id},
            headers=headers,
        )
        total += 1
        if r_rec.status_code == 201:
            passed += 1
            print(f"  [PASS] POST /api/v1/inventory/reconcile -> 201 Created (Status: {r_rec.json().get('status')})")
        else:
            failed += 1
            print(f"  [FAIL] POST /api/v1/inventory/reconcile failed: {r_rec.status_code} {r_rec.text}")

        # -------------------------------------------------------------
        # 6. Inbound Receiving
        # -------------------------------------------------------------
        print("\n[6] Verifying Inbound Receiving Endpoints...")
        receipt_payload = {
            "seller_id": seller_id,
            "warehouse_id": wh_id,
            "source_type": "CARRIER_TRACKING",
            "client_draft_id": str(uuid4()),
            "source_reference": f"PO-POSTMAN-{uuid4().hex[:6].upper()}",
            "supplier_name": "Postman Test Supplier",
        }
        r_rcp = await client.post("/api/v1/receipts", json=receipt_payload, headers=headers)
        total += 1
        if r_rcp.status_code == 201:
            passed += 1
            receipt = r_rcp.json()
            receipt_id = receipt["id"]
            print(f"  [PASS] POST /api/v1/receipts -> 201 Created (Receipt: {receipt['receipt_number']})")
        else:
            failed += 1
            print(f"  [FAIL] POST /api/v1/receipts failed: {r_rcp.status_code} {r_rcp.text}")
            receipt_id = None

        if receipt_id:
            r_line = await client.post(
                f"/api/v1/receipts/{receipt_id}/lines",
                json={
                    "product_id": product_id,
                    "expected_quantity": 50.0,
                    "sellable_quantity": 50.0,
                    "damaged_quantity": 0.0,
                    "quarantined_quantity": 0.0,
                },
                headers=headers,
            )
            total += 1
            if r_line.status_code == 201:
                passed += 1
                print("  [PASS] POST /api/v1/receipts/{id}/lines -> 201 Created")
            else:
                failed += 1
                print(f"  [FAIL] POST /api/v1/receipts/lines failed: {r_line.status_code} {r_line.text}")

            r_complete = await client.post(
                f"/api/v1/receipts/{receipt_id}/complete",
                json={
                    "idempotency_key": str(uuid4()),
                    "location_id": location_id,
                },
                headers=headers,
            )
            total += 1
            if r_complete.status_code == 200 and r_complete.json().get("status") == "COMPLETED":
                passed += 1
                print("  [PASS] POST /api/v1/receipts/{id}/complete -> 200 OK (Status: COMPLETED)")
            else:
                failed += 1
                print(f"  [FAIL] POST /api/v1/receipts/complete failed: {r_complete.status_code} {r_complete.text}")

        # -------------------------------------------------------------
        # 7. Outbound Orders & Fulfillment
        # -------------------------------------------------------------
        print("\n[7] Verifying Orders & Fulfillment Endpoints...")
        order_payload = {
            "seller_id": seller_id,
            "warehouse_id": wh_id,
            "seller_order_number": f"ORD-POSTMAN-{uuid4().hex[:6].upper()}",
            "customer_name": "Jane Doe",
            "shipping_address_line1": "123 Test St",
            "city": "Bengaluru",
            "state": "KA",
            "postal_code": "560001",
            "lines": [
                {
                    "product_id": product_id,
                    "ordered_quantity": 10.0,
                }
            ],
        }
        r_ord = await client.post("/api/v1/orders", json=order_payload, headers=headers)
        total += 1
        if r_ord.status_code == 201:
            passed += 1
            order = r_ord.json()
            order_id = order["id"]
            print(f"  [PASS] POST /api/v1/orders -> 201 Created (Order: {order['seller_order_number']})")
        else:
            failed += 1
            print(f"  [FAIL] POST /api/v1/orders failed: {r_ord.status_code} {r_ord.text}")
            order_id = None

        if order_id:
            r_res = await client.post(
                f"/api/v1/orders/{order_id}/reserve",
                json={"notes": "Reserve available stock for fulfillment"},
                headers=headers,
            )
            total += 1
            if r_res.status_code == 200 and r_res.json().get("status") == "RESERVED":
                passed += 1
                print("  [PASS] POST /api/v1/orders/{id}/reserve -> 200 OK (Status: RESERVED)")
            else:
                failed += 1
                print(f"  [FAIL] POST /api/v1/orders/reserve failed: {r_res.status_code} {r_res.text}")

            r_pick = await client.post(
                "/api/v1/pick-tasks",
                json={"order_id": order_id, "priority": 2},
                headers=headers,
            )
            total += 1
            if r_pick.status_code == 201:
                passed += 1
                pick_task = r_pick.json()
                pick_task_id = pick_task["id"]
                pick_task_line_id = pick_task["lines"][0]["id"]
                print(f"  [PASS] POST /api/v1/pick-tasks -> 201 Created (ID: {pick_task['id']})")
            else:
                failed += 1
                print(f"  [FAIL] POST /api/v1/pick-tasks failed: {r_pick.status_code} {r_pick.text}")
                pick_task_id = None

            if pick_task_id:
                r_comp_pick = await client.post(
                    f"/api/v1/pick-tasks/{pick_task_id}/complete",
                    json={
                        "lines": [
                            {
                                "pick_task_line_id": pick_task_line_id,
                                "picked_quantity": 10.0,
                                "short_quantity": 0.0,
                            }
                        ]
                    },
                    headers=headers,
                )
                total += 1
                if r_comp_pick.status_code == 200:
                    passed += 1
                    print("  [PASS] POST /api/v1/pick-tasks/{id}/complete -> 200 OK")
                else:
                    failed += 1
                    print(f"  [FAIL] POST /api/v1/pick-tasks/complete failed: {r_comp_pick.status_code} {r_comp_pick.text}")

                r_ship = await client.post(
                    "/api/v1/shipments",
                    json={
                        "order_id": order_id,
                        "warehouse_id": wh_id,
                        "carrier": "Bluedart",
                        "tracking_number": f"TRK-{uuid4().hex[:8].upper()}",
                        "packages": [
                            {
                                "box_type": "BOX-1",
                                "weight_lbs": 3.5,
                                "length_in": 12.0,
                                "width_in": 8.0,
                                "height_in": 6.0,
                            }
                        ],
                    },
                    headers=headers,
                )
                total += 1
                if r_ship.status_code == 201:
                    passed += 1
                    print(f"  [PASS] POST /api/v1/shipments -> 201 Created (Tracking: {r_ship.json().get('tracking_number')})")
                else:
                    failed += 1
                    print(f"  [FAIL] POST /api/v1/shipments failed: {r_ship.status_code} {r_ship.text}")

        # -------------------------------------------------------------
        # 8. Multi-Warehouse Transfers
        # -------------------------------------------------------------
        print("\n[8] Verifying Multi-Warehouse Transfers...")
        r_all_wh = await client.get("/api/v1/warehouses", headers=headers)
        wh_list = r_all_wh.json()
        wh_dest = wh_list[1]["id"] if len(wh_list) > 1 else wh_id

        transfer_payload = {
            "seller_id": seller_id,
            "origin_warehouse_id": wh_id,
            "destination_warehouse_id": wh_dest,
            "notes": "Postman transfer verification",
            "lines": [{"product_id": product_id, "requested_quantity": 5}],
        }
        r_trans = await client.post("/api/v1/transfers", json=transfer_payload, headers=headers)
        total += 1
        if r_trans.status_code == 201:
            passed += 1
            transfer = r_trans.json()
            transfer_id = transfer["id"]
            print(f"  [PASS] POST /api/v1/transfers -> 201 Created (Transfer: {transfer['transfer_number']})")
        else:
            failed += 1
            print(f"  [FAIL] POST /api/v1/transfers failed: {r_trans.status_code} {r_trans.text}")

        r_trans_list = await client.get("/api/v1/transfers", headers=headers)
        total += 1
        if r_trans_list.status_code == 200:
            passed += 1
            print(f"  [PASS] GET /api/v1/transfers -> 200 OK (Total: {r_trans_list.json().get('total')})")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/transfers failed: {r_trans_list.status_code}")

        # -------------------------------------------------------------
        # 9. Returns & Dispositions
        # -------------------------------------------------------------
        print("\n[9] Verifying Returns & Dispositions...")
        return_payload = {
            "seller_id": seller_id,
            "warehouse_id": wh_id,
            "rma_number": f"RMA-POSTMAN-{uuid4().hex[:6].upper()}",
            "lines": [
                {
                    "product_id": product_id,
                    "expected_quantity": 2,
                    "reason_code": "DEFECTIVE",
                }
            ],
        }
        r_ret = await client.post("/api/v1/returns", json=return_payload, headers=headers)
        total += 1
        if r_ret.status_code == 201:
            passed += 1
            ret = r_ret.json()
            return_id = ret["id"]
            print(f"  [PASS] POST /api/v1/returns -> 201 Created (RMA: {ret['rma_number']})")
        else:
            failed += 1
            print(f"  [FAIL] POST /api/v1/returns failed: {r_ret.status_code} {r_ret.text}")
            return_id = None

        r_ret_list = await client.get("/api/v1/returns", headers=headers)
        total += 1
        if r_ret_list.status_code == 200:
            passed += 1
            print(f"  [PASS] GET /api/v1/returns -> 200 OK (Total: {r_ret_list.json().get('total')})")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/returns failed: {r_ret_list.status_code}")

        # -------------------------------------------------------------
        # 10. Seller Portal Views
        # -------------------------------------------------------------
        print("\n[10] Verifying Seller Portal Endpoints...")
        r_s_inv = await client.get("/api/v1/seller/inventory", headers=headers)
        total += 1
        if r_s_inv.status_code == 200:
            passed += 1
            print("  [PASS] GET /api/v1/seller/inventory -> 200 OK")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/seller/inventory failed: {r_s_inv.status_code}")

        r_s_ord = await client.get("/api/v1/seller/orders", headers=headers)
        total += 1
        if r_s_ord.status_code == 200:
            passed += 1
            print("  [PASS] GET /api/v1/seller/orders -> 200 OK")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/seller/orders failed: {r_s_ord.status_code}")

        r_s_rcp = await client.get("/api/v1/seller/receipts", headers=headers)
        total += 1
        if r_s_rcp.status_code == 200:
            passed += 1
            print("  [PASS] GET /api/v1/seller/receipts -> 200 OK")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/seller/receipts failed: {r_s_rcp.status_code}")

        r_s_shp = await client.get("/api/v1/seller/shipments", headers=headers)
        total += 1
        if r_s_shp.status_code == 200:
            passed += 1
            print("  [PASS] GET /api/v1/seller/shipments -> 200 OK")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/seller/shipments failed: {r_s_shp.status_code}")

        # -------------------------------------------------------------
        # 11. Manager Dashboard & Reports
        # -------------------------------------------------------------
        print("\n[11] Verifying Manager Dashboard & Reports...")
        r_dash = await client.get("/api/v1/manager/dashboard", headers=headers)
        total += 1
        if r_dash.status_code == 200:
            passed += 1
            print("  [PASS] GET /api/v1/manager/dashboard -> 200 OK")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/manager/dashboard failed: {r_dash.status_code}")

        r_exc = await client.get("/api/v1/manager/exceptions", headers=headers)
        total += 1
        if r_exc.status_code == 200:
            passed += 1
            print("  [PASS] GET /api/v1/manager/exceptions -> 200 OK")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/manager/exceptions failed: {r_exc.status_code}")

        r_rec_rep = await client.get("/api/v1/reports/inventory-reconciliation", headers=headers)
        total += 1
        if r_rec_rep.status_code == 200:
            passed += 1
            print("  [PASS] GET /api/v1/reports/inventory-reconciliation -> 200 OK")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/reports/inventory-reconciliation failed: {r_rec_rep.status_code}")

        # -------------------------------------------------------------
        # 12. Opening Inventory Migration
        # -------------------------------------------------------------
        print("\n[12] Verifying Opening Inventory Migration...")
        seller_code = r_sellers.json()[0]["code"]
        wh_code = r_wh.json()[0]["code"]

        r_mbatch = await client.post(
            "/api/v1/migration/batches",
            json={"source_notes": "Postman migration verification batch"},
            headers=headers,
        )
        total += 1
        if r_mbatch.status_code == 201:
            passed += 1
            mbatch = r_mbatch.json()
            mbatch_id = mbatch["id"]
            print(f"  [PASS] POST /api/v1/migration/batches -> 201 Created (Batch: {mbatch['batch_number']})")
        else:
            failed += 1
            print(f"  [FAIL] POST /api/v1/migration/batches failed: {r_mbatch.status_code} {r_mbatch.text}")
            mbatch_id = None

        if mbatch_id:
            r_mrows = await client.post(
                f"/api/v1/migration/batches/{mbatch_id}/rows",
                json={
                    "rows": [
                        {
                            "source_workbook": "inventory_2026.csv",
                            "source_sheet": "Sheet1",
                            "source_row_number": 2,
                            "raw_seller_code": seller_code,
                            "raw_warehouse_code": wh_code,
                            "raw_sku": sku,
                            "raw_location_code": loc_code,
                            "raw_quantity": "100.00",
                            "raw_inventory_state": "AVAILABLE",
                        }
                    ]
                },
                headers=headers,
            )
            total += 1
            if r_mrows.status_code == 201:
                passed += 1
                print("  [PASS] POST /api/v1/migration/batches/{id}/rows -> 201 Created")
            else:
                failed += 1
                print(f"  [FAIL] POST /api/v1/migration/batches/rows failed: {r_mrows.status_code} {r_mrows.text}")

            r_mval = await client.post(f"/api/v1/migration/batches/{mbatch_id}/validate", headers=headers)
            total += 1
            if r_mval.status_code == 200 and r_mval.json().get("status") == "VALIDATED":
                passed += 1
                print("  [PASS] POST /api/v1/migration/batches/{id}/validate -> 200 OK (Status: VALIDATED)")
            else:
                failed += 1
                print(f"  [FAIL] POST /api/v1/migration/batches/validate failed: {r_mval.status_code} {r_mval.text}")

            r_mapprove = await client.post(f"/api/v1/migration/batches/{mbatch_id}/approve", headers=headers)
            total += 1
            if r_mapprove.status_code == 200 and r_mapprove.json().get("status") == "APPROVED":
                passed += 1
                print("  [PASS] POST /api/v1/migration/batches/{id}/approve -> 200 OK (Status: APPROVED)")
            else:
                failed += 1
                print(f"  [FAIL] POST /api/v1/migration/batches/approve failed: {r_mapprove.status_code} {r_mapprove.text}")

            r_mapply = await client.post(f"/api/v1/migration/batches/{mbatch_id}/apply", headers=headers)
            total += 1
            if r_mapply.status_code == 200 and r_mapply.json().get("status") == "APPLIED":
                passed += 1
                print("  [PASS] POST /api/v1/migration/batches/{id}/apply -> 200 OK (Status: APPLIED)")
            else:
                failed += 1
                print(f"  [FAIL] POST /api/v1/migration/batches/apply failed: {r_mapply.status_code} {r_mapply.text}")

        # -------------------------------------------------------------
        # 13. Read-Only AI Assistance
        # -------------------------------------------------------------
        print("\n[13] Verifying Read-Only AI Assistance...")
        r_ai_health = await client.get("/api/v1/ai/admin/provider-health", headers=headers)
        total += 1
        if r_ai_health.status_code == 200:
            passed += 1
            print("  [PASS] GET /api/v1/ai/admin/provider-health -> 200 OK")
        else:
            failed += 1
            print(f"  [FAIL] GET /api/v1/ai/admin/provider-health failed: {r_ai_health.status_code}")

        r_ai_inv = await client.post(
            "/api/v1/ai/inventory/availability",
            json={"sku": sku, "warehouse_id": wh_id, "seller_id": seller_id},
            headers=headers,
        )
        total += 1
        if r_ai_inv.status_code == 200 and "answer" in r_ai_inv.json():
            passed += 1
            print(f"  [PASS] POST /api/v1/ai/inventory/availability -> 200 OK (Audit ID: {r_ai_inv.json().get('interaction_id')})")
        else:
            failed += 1
            print(f"  [FAIL] POST /api/v1/ai/inventory/availability failed: {r_ai_inv.status_code} {r_ai_inv.text}")

        r_ai_ord = await client.post(
            "/api/v1/ai/status/order",
            json={"record_id": order_id, "seller_id": seller_id},
            headers=headers,
        )
        total += 1
        if r_ai_ord.status_code == 200:
            passed += 1
            print("  [PASS] POST /api/v1/ai/status/order -> 200 OK")
        else:
            failed += 1
            print(f"  [FAIL] POST /api/v1/ai/status/order failed: {r_ai_ord.status_code} {r_ai_ord.text}")

        r_ai_rcp = await client.post(
            "/api/v1/ai/status/receipt",
            json={"record_id": receipt_id, "seller_id": seller_id},
            headers=headers,
        )
        total += 1
        if r_ai_rcp.status_code == 200:
            passed += 1
            print("  [PASS] POST /api/v1/ai/status/receipt -> 200 OK")
        else:
            failed += 1
            print(f"  [FAIL] POST /api/v1/ai/status/receipt failed: {r_ai_rcp.status_code} {r_ai_rcp.text}")

        if return_id:
            r_ai_ret = await client.post(
                "/api/v1/ai/status/return",
                json={"record_id": return_id, "seller_id": seller_id},
                headers=headers,
            )
            total += 1
            if r_ai_ret.status_code == 200:
                passed += 1
                print("  [PASS] POST /api/v1/ai/status/return -> 200 OK")
            else:
                failed += 1
                print(f"  [FAIL] POST /api/v1/ai/status/return failed: {r_ai_ret.status_code} {r_ai_ret.text}")

    await close_database_connection()

    print("\n" + "=" * 80)
    print(f"POSTMAN VERIFICATION SUMMARY: {passed}/{total} Passed ({failed} Failed)")
    print("=" * 80)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_postman_verification())

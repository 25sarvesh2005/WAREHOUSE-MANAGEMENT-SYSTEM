"""
Unit tests verifying Model Context Protocol (MCP) server tools, context scoping, and HTTP endpoints.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from common.auth import create_access_token
from core.constants import BusinessStatus, InventoryMovementType, InventoryState, UserRole
from core.database.database import transaction_session
from core.models.catalog_model import Product
from core.models.identity_model import Seller, User, Warehouse
from core.models.inventory_model import InventoryBalance, InventoryMovement
from main import app
from mcp_server.context import RequesterContext
from mcp_server.tools import (
    tool_exception_listing,
    tool_inventory_lookup,
    tool_ledger_explanation,
    tool_order_status,
    tool_receipt_status,
)


@pytest.mark.asyncio
async def test_mcp_inventory_lookup_and_ledger_explanation():
    """Verify MCP inventory_lookup and ledger_explanation tools return scoped evidence."""
    async with transaction_session() as session:
        user = User(
            email=f"mcp-user-{uuid4().hex[:6]}@test.com",
            name="MCP Test User",
            hashed_password="hash",
            role=UserRole.ADMINISTRATOR.value,
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(user)
        seller = Seller(
            name=f"MCP Seller {uuid4().hex[:6]}",
            code=f"MCP-{uuid4().hex[:4].upper()}",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(seller)
        wh = Warehouse(
            name=f"MCP Reno WH {uuid4().hex[:6]}",
            code=f"MCP-RNO-{uuid4().hex[:4].upper()}",
            timezone="America/Los_Angeles",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(wh)
        await session.flush()

        product = Product(
            seller_id=seller.id,
            sku=f"SKU-MCP-{uuid4().hex[:6]}",
            name="MCP Headset Pro",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(product)
        await session.flush()

        # Add balance and ledger movement
        balance = InventoryBalance(
            seller_id=seller.id,
            product_id=product.id,
            warehouse_id=wh.id,
            inventory_state=InventoryState.AVAILABLE.value,
            quantity=Decimal("75.00"),
        )
        session.add(balance)

        movement = InventoryMovement(
            seller_id=seller.id,
            product_id=product.id,
            warehouse_id=wh.id,
            inventory_state=InventoryState.AVAILABLE.value,
            quantity_delta=Decimal("75.00"),
            movement_type=InventoryMovementType.RECEIPT.value,
            source_type="receipts",
            source_id=uuid4(),
            idempotency_key=f"mcp-mvt-{uuid4().hex[:8]}",
            occurred_at=datetime.now(UTC),
        )
        session.add(movement)
        await session.flush()

        user_id = user.id
        seller_id = seller.id
        wh_id = wh.id
        sku = product.sku

    requester = RequesterContext(
        user_id=user_id,
        email="mcp@test.com",
        role=UserRole.ADMINISTRATOR.value,
        seller_id=seller_id,
        warehouse_id=wh_id,
    )

    # Test inventory_lookup
    balances = await tool_inventory_lookup(sku=sku, requester=requester)
    assert len(balances) == 1
    assert balances[0]["sku"] == sku
    assert balances[0]["available_quantity"] == 75.0

    # Test ledger_explanation
    ledger = await tool_ledger_explanation(sku=sku, limit=5, requester=requester)
    assert len(ledger) >= 1
    assert ledger[0]["sku"] == sku
    assert ledger[0]["quantity_delta"] == 75.0


@pytest.mark.asyncio
async def test_mcp_exception_listing_tool():
    """Verify tool_exception_listing aggregates exception categories."""
    requester = RequesterContext(
        user_id=uuid4(),
        email="admin@test.com",
        role=UserRole.ADMINISTRATOR.value,
    )
    res = await tool_exception_listing(requester=requester)
    assert "total_exceptions" in res
    assert "overdue_receipts" in res
    assert "short_pick_exceptions" in res
    assert "expired_reservations" in res


@pytest.mark.asyncio
async def test_mcp_http_endpoints():
    """Verify GET /mcp capabilities catalog and POST /mcp/call execution over HTTP."""
    user_id = uuid4()
    token = create_access_token({
        "user_id": str(user_id),
        "email": "mcp-api@test.com",
        "role": UserRole.ADMINISTRATOR.value,
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        # 1. GET /mcp
        resp = await client.get("/mcp")
        assert resp.status_code == 200
        catalog = resp.json()
        assert catalog["protocol_version"] == "2024-11-05"
        tool_names = [t["name"] for t in catalog["tools"]]
        assert "inventory_lookup" in tool_names
        assert "exception_listing" in tool_names

        # 2. POST /mcp/call without auth -> 401
        unauth_resp = await client.post("/mcp/call", json={"name": "exception_listing", "arguments": {}})
        assert unauth_resp.status_code == 401

        # 3. POST /mcp/call with valid Bearer token
        call_resp = await client.post(
            "/mcp/call",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "exception_listing", "arguments": {}},
        )
        assert call_resp.status_code == 200
        data = call_resp.json()
        assert data["isError"] is False
        assert len(data["content"]) == 1
        assert "total_exceptions" in data["content"][0]["data"]

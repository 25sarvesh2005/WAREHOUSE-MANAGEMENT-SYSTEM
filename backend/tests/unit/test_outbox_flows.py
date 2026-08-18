"""
Unit tests verifying transactional outbox operations and event emission.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from core.constants import (
    BusinessStatus,
    InventoryState,
    OrderStatus,
    OutboxEventStatus,
    OutboxEventType,
    UserRole,
)
from core.controllers.order_controller import order_controller
from core.controllers.receiving_controller import receiving_controller
from core.cruds import catalog_crud, identity_crud, inventory_crud, outbox_crud
from core.database.database import transaction_session
from core.models.catalog_model import Product
from core.models.identity_model import Seller, User, Warehouse
from core.models.outbox_model import OutboxEvent


@pytest.mark.asyncio
async def test_outbox_crud_lifecycle():
    """Verify outbox CRUD operations: create, fetch pending, mark dispatched, mark failed."""
    async with transaction_session() as session:
        # Create pending event
        test_payload = {"key": "value", "id": str(uuid4())}
        event = await outbox_crud.create_outbox_event(
            session,
            event_type=OutboxEventType.ORDER_CREATED.value,
            payload=test_payload,
        )
        assert event.id is not None
        assert event.status == OutboxEventStatus.PENDING.value
        assert event.attempts == 0
        assert event.payload == test_payload

        # Fetch pending events
        pending = await outbox_crud.fetch_pending_events(session, limit=50)
        matching = [e for e in pending if e.id == event.id]
        assert len(matching) == 1
        assert matching[0].event_type == OutboxEventType.ORDER_CREATED.value

        # Mark dispatched
        await outbox_crud.mark_event_dispatched(session, event.id)
        assert event.status == OutboxEventStatus.DISPATCHED.value
        assert event.attempts == 1

        # Mark failed with next attempt
        retry_time = datetime.now(UTC) + timedelta(minutes=5)
        await outbox_crud.mark_event_failed(session, event.id, error="Network timeout", next_attempt_at=retry_time)
        assert event.status == OutboxEventStatus.FAILED.value
        assert event.attempts == 2
        assert event.last_error == "Network timeout"
        assert event.next_attempt_at == retry_time


@pytest.mark.asyncio
async def test_outbox_atomic_rollback():
    """Verify that a rolled back transaction also rolls back outbox events."""
    event_id = None
    try:
        async with transaction_session() as session:
            event = await outbox_crud.create_outbox_event(
                session,
                event_type="TEST_ROLLBACK_EVENT",
                payload={"test": "data"},
            )
            event_id = event.id
            assert event_id is not None
            # Force an exception to trigger rollback
            raise RuntimeError("Intentional rollback for test")
    except RuntimeError:
        pass

    # Verify event was not persisted
    async with transaction_session() as session:
        queried = await session.get(OutboxEvent, event_id)
        assert queried is None


@pytest.mark.asyncio
async def test_receiving_controller_emits_outbox():
    """Verify ReceivingController.create_receipt emits a RECEIPT_CREATED outbox event."""
    async with transaction_session() as session:
        user = User(
            email=f"rcv-outbox-{uuid4().hex[:6]}@test.com",
            name="Receiving Outbox User",
            hashed_password="hash",
            role=UserRole.WAREHOUSE_MANAGER.value,
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(user)
        # Create seller and warehouse
        seller = Seller(
            name=f"Outbox Test Seller {uuid4().hex[:6]}",
            code=f"OB-{uuid4().hex[:4].upper()}",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(seller)
        wh = Warehouse(
            name=f"Outbox Reno WH {uuid4().hex[:6]}",
            code=f"OB-RNO-{uuid4().hex[:4].upper()}",
            timezone="America/Los_Angeles",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(wh)
        await session.flush()
        user_id = user.id
        seller_id = seller.id
        wh_id = wh.id

    scope = {
        "user_id": str(user_id),
        "role": UserRole.WAREHOUSE_MANAGER.value,
        "seller_ids": [str(seller_id)],
        "warehouse_ids": [str(wh_id)],
    }

    receipt_data = {
        "seller_id": str(seller_id),
        "warehouse_id": str(wh_id),
        "source_type": "CARRIER_TRACKING",
        "source_reference": f"TRACK-{uuid4().hex[:8]}",
    }

    receipt = await receiving_controller.create_receipt(receipt_data, scope)
    assert receipt is not None

    async with transaction_session() as session:
        stmt = (
            select(OutboxEvent)
            .where(
                OutboxEvent.event_type == OutboxEventType.RECEIPT_CREATED.value,
                OutboxEvent.status == OutboxEventStatus.PENDING.value,
            )
            .order_by(OutboxEvent.created_at.desc())
        )
        result = await session.execute(stmt)
        events = result.scalars().all()
        matching = [e for e in events if e.payload.get("receipt_id") == str(receipt.id)]
        assert len(matching) == 1
        assert matching[0].payload["receipt_number"] == receipt.receipt_number


@pytest.mark.asyncio
async def test_order_controller_emits_outbox():
    """Verify OrderController.create_order and cancel_order emit matching outbox events."""
    async with transaction_session() as session:
        user = User(
            email=f"ord-outbox-{uuid4().hex[:6]}@test.com",
            name="Order Outbox User",
            hashed_password="hash",
            role=UserRole.ADMINISTRATOR.value,
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(user)
        seller = Seller(
            name=f"Order Outbox Seller {uuid4().hex[:6]}",
            code=f"OOS-{uuid4().hex[:4].upper()}",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(seller)
        wh = Warehouse(
            name=f"Order Outbox WH {uuid4().hex[:6]}",
            code=f"OOW-{uuid4().hex[:4].upper()}",
            timezone="America/Los_Angeles",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(wh)
        await session.flush()

        product = Product(
            seller_id=seller.id,
            sku=f"SKU-OOS-{uuid4().hex[:6]}",
            name="Outbox Test Product",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(product)
        await session.flush()
        user_id = user.id
        seller_id = seller.id
        wh_id = wh.id
        prod_id = product.id

    scope = {
        "user_id": str(user_id),
        "role": UserRole.ADMINISTRATOR.value,
        "seller_ids": [str(seller_id)],
        "warehouse_ids": [str(wh_id)],
    }

    order_payload = {
        "seller_id": str(seller_id),
        "warehouse_id": str(wh_id),
        "seller_order_number": f"ORD-OB-{uuid4().hex[:8]}",
        "customer_name": "Test Customer",
        "lines": [{"product_id": str(prod_id), "ordered_quantity": 5}],
    }

    created_order = await order_controller.create_order(order_payload, scope)
    assert created_order is not None

    async with transaction_session() as session:
        stmt = (
            select(OutboxEvent)
            .where(
                OutboxEvent.event_type == OutboxEventType.ORDER_CREATED.value,
                OutboxEvent.status == OutboxEventStatus.PENDING.value,
            )
            .order_by(OutboxEvent.created_at.desc())
        )
        events = (await session.execute(stmt)).scalars().all()
        matching = [e for e in events if e.payload.get("order_id") == str(created_order.id)]
        assert len(matching) == 1

    # Now cancel order and verify ORDER_CANCELLED event
    cancelled_order = await order_controller.cancel_order(created_order.id, scope)
    assert cancelled_order.status == OrderStatus.CANCELLED.value

    async with transaction_session() as session:
        stmt = (
            select(OutboxEvent)
            .where(
                OutboxEvent.event_type == OutboxEventType.ORDER_CANCELLED.value,
                OutboxEvent.status == OutboxEventStatus.PENDING.value,
            )
            .order_by(OutboxEvent.created_at.desc())
        )
        events = (await session.execute(stmt)).scalars().all()
        matching = [e for e in events if e.payload.get("order_id") == str(created_order.id)]
        assert len(matching) == 1

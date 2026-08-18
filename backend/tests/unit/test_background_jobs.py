"""
Unit tests verifying background jobs: outbox dispatch, receipt aging, transfer delay, and return aging.
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
    OutboxEventStatus,
    OutboxEventType,
    ReceiptStatus,
    ReturnStatus,
    TransferStatus,
    UserRole,
)
from core.cruds import outbox_crud
from core.database.database import transaction_session
from core.jobs.outbox_dispatch_job import (
    dispatch_pending_outbox_events,
    register_outbox_handler,
)
from core.jobs.receipt_aging_job import check_aging_receipts
from core.jobs.return_aging_job import check_aging_returns
from core.jobs.transfer_delay_job import check_delayed_transfers
from core.models.identity_model import Seller, User, Warehouse
from core.models.outbox_model import OutboxEvent
from core.models.receiving_model import Receipt
from core.models.return_model import Return
from core.models.transfer_model import Transfer


@pytest.mark.asyncio
async def test_outbox_dispatcher_success_and_handler():
    """Verify outbox dispatcher processes pending events and calls registered handlers."""
    received_payloads: list[dict[str, object]] = []

    async def custom_handler(event: OutboxEvent):
        received_payloads.append(event.payload)

    register_outbox_handler("TEST_DISPATCH_TYPE", custom_handler)

    test_payload = {"job_test_id": str(uuid4())}
    async with transaction_session() as session:
        event = await outbox_crud.create_outbox_event(
            session,
            event_type="TEST_DISPATCH_TYPE",
            payload=test_payload,
        )
        event_id = event.id

    async with transaction_session() as session:
        result = await dispatch_pending_outbox_events(session, batch_size=500)
        assert result["dispatched"] >= 1

    # Verify handler was called
    matching = [p for p in received_payloads if p.get("job_test_id") == test_payload["job_test_id"]]
    assert len(matching) == 1

    # Verify event status in DB
    async with transaction_session() as session:
        refreshed = await session.get(OutboxEvent, event_id)
        assert refreshed is not None
        assert refreshed.status == OutboxEventStatus.DISPATCHED.value
        assert refreshed.attempts == 1


@pytest.mark.asyncio
async def test_outbox_dispatcher_dead_letter():
    """Verify outbox events exceeding max_attempts transition to DEAD_LETTER."""
    async with transaction_session() as session:
        event = await outbox_crud.create_outbox_event(
            session,
            event_type="TEST_DEAD_LETTER",
            payload={"dead": "letter"},
        )
        event.attempts = 5  # Already at max attempts
        await session.flush()
        event_id = event.id

    async with transaction_session() as session:
        result = await dispatch_pending_outbox_events(session, batch_size=500, max_attempts=5)
        assert result["dead_letter"] >= 1

    async with transaction_session() as session:
        refreshed = await session.get(OutboxEvent, event_id)
        assert refreshed is not None
        assert refreshed.status == "DEAD_LETTER"


@pytest.mark.asyncio
async def test_receipt_aging_job():
    """Verify check_aging_receipts detects overdue draft receipts and emits outbox alerts."""
    async with transaction_session() as session:
        seller = Seller(
            name=f"Aging Seller {uuid4().hex[:6]}",
            code=f"AG-{uuid4().hex[:4].upper()}",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(seller)
        wh = Warehouse(
            name=f"Aging Reno WH {uuid4().hex[:6]}",
            code=f"AG-RNO-{uuid4().hex[:4].upper()}",
            timezone="America/Los_Angeles",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(wh)
        await session.flush()

        # Create an aging receipt (created 3 days ago)
        old_time = datetime.now(UTC) - timedelta(days=3)
        receipt = Receipt(
            receipt_number=f"RCV-AGE-{uuid4().hex[:6].upper()}",
            seller_id=seller.id,
            warehouse_id=wh.id,
            source_type="CARRIER_TRACKING",
            source_reference="TRACK-AGE-1",
            status=ReceiptStatus.DRAFT.value,
            created_at=old_time,
            updated_at=old_time,
        )
        session.add(receipt)
        await session.flush()
        receipt_id = receipt.id

    async with transaction_session() as session:
        res = await check_aging_receipts(session, threshold_hours=48)
        assert res["aging_receipts_found"] >= 1
        assert res["alerts_emitted"] >= 1

    # Verify alert event in outbox
    async with transaction_session() as session:
        stmt = select(OutboxEvent).where(
            OutboxEvent.event_type == OutboxEventType.RECEIPT_AGING_ALERT.value
        )
        events = (await session.execute(stmt)).scalars().all()
        matching = [e for e in events if e.payload.get("receipt_id") == str(receipt_id)]
        assert len(matching) >= 1
        assert matching[0].payload["age_hours"] >= 48


@pytest.mark.asyncio
async def test_transfer_delay_job():
    """Verify check_delayed_transfers detects delayed in-transit transfers."""
    async with transaction_session() as session:
        seller = Seller(
            name=f"Trf Delay Seller {uuid4().hex[:6]}",
            code=f"TDS-{uuid4().hex[:4].upper()}",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(seller)
        origin_wh = Warehouse(
            name=f"Trf Origin WH {uuid4().hex[:6]}",
            code=f"TDO-{uuid4().hex[:4].upper()}",
            timezone="America/Los_Angeles",
            status=BusinessStatus.ACTIVE.value,
        )
        dest_wh = Warehouse(
            name=f"Trf Dest WH {uuid4().hex[:6]}",
            code=f"TDD-{uuid4().hex[:4].upper()}",
            timezone="America/New_York",
            status=BusinessStatus.ACTIVE.value,
        )
        user = User(
            email=f"trf-delay-{uuid4().hex[:6]}@test.com",
            name="Transfer Delay User",
            hashed_password="hash",
            role=UserRole.ADMINISTRATOR.value,
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(user)
        session.add(origin_wh)
        session.add(dest_wh)
        await session.flush()

        old_dispatch = datetime.now(UTC) - timedelta(days=10)
        transfer = Transfer(
            transfer_number=f"TRF-DLY-{uuid4().hex[:6].upper()}",
            seller_id=seller.id,
            origin_warehouse_id=origin_wh.id,
            destination_warehouse_id=dest_wh.id,
            status=TransferStatus.DISPATCHED.value,
            created_by_user_id=user.id,
            dispatched_at=old_dispatch,
            created_at=old_dispatch,
            updated_at=old_dispatch,
        )
        session.add(transfer)
        await session.flush()
        transfer_id = transfer.id

    async with transaction_session() as session:
        res = await check_delayed_transfers(session, max_transit_days=7)
        assert res["delayed_transfers_found"] >= 1
        assert res["alerts_emitted"] >= 1

    async with transaction_session() as session:
        stmt = select(OutboxEvent).where(
            OutboxEvent.event_type == OutboxEventType.TRANSFER_DELAY_ALERT.value
        )
        events = (await session.execute(stmt)).scalars().all()
        matching = [e for e in events if e.payload.get("transfer_id") == str(transfer_id)]
        assert len(matching) >= 1
        assert matching[0].payload["transit_days"] >= 7


@pytest.mark.asyncio
async def test_return_aging_job():
    """Verify check_aging_returns detects uninspected received returns past SLA."""
    async with transaction_session() as session:
        seller = Seller(
            name=f"Ret Aging Seller {uuid4().hex[:6]}",
            code=f"RAS-{uuid4().hex[:4].upper()}",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(seller)
        wh = Warehouse(
            name=f"Ret Aging WH {uuid4().hex[:6]}",
            code=f"RAW-{uuid4().hex[:4].upper()}",
            timezone="America/Los_Angeles",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(wh)
        await session.flush()

        old_received = datetime.now(UTC) - timedelta(hours=36)
        ret = Return(
            return_number=f"RET-AGE-{uuid4().hex[:6].upper()}",
            seller_id=seller.id,
            warehouse_id=wh.id,
            status=ReturnStatus.RECEIVED.value,
            received_at=old_received,
            created_at=old_received,
            updated_at=old_received,
        )
        session.add(ret)
        await session.flush()
        return_id = ret.id

    async with transaction_session() as session:
        res = await check_aging_returns(session, threshold_hours=24)
        assert res["aging_returns_found"] >= 1
        assert res["alerts_emitted"] >= 1

    async with transaction_session() as session:
        stmt = select(OutboxEvent).where(
            OutboxEvent.event_type == OutboxEventType.RETURN_AGING_ALERT.value
        )
        events = (await session.execute(stmt)).scalars().all()
        matching = [e for e in events if e.payload.get("return_id") == str(return_id)]
        assert len(matching) >= 1
        assert matching[0].payload["age_hours"] >= 24

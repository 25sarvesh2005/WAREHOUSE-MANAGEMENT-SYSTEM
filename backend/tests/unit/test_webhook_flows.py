"""
Unit tests for the enterprise webhook subsystem: HMAC signatures, subscriptions,
outbox event dispatch, delivery audit logs, and inbound carrier/order ingestion.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from common.pinned_webhook_transport import _PinnedNetworkBackend
from common.webhook_signer import (
    compute_inbound_webhook_signature,
    compute_webhook_signature,
    verify_inbound_webhook_signature,
    verify_webhook_signature,
    verify_webhook_timestamp,
)
from common.webhook_url import PublicHttpsDestination, ensure_public_https_url
from core.cruds import outbox_crud, webhook_crud
from core.database.database import transaction_session
from core.services.webhook_dispatcher_service import dispatch_outbox_event_to_webhooks
from main import app


def test_hmac_signature_generation_and_verification():
    """Verify HMAC-SHA256 signature computation and constant-time comparison."""
    secret = "secret_key_1234567890abcdef"
    payload = b'{"event":"order.created","order_id":"12345"}'

    sig = compute_webhook_signature(payload, secret)
    assert sig.startswith("sha256=")
    assert len(sig) == 7 + 64  # 'sha256=' + 64 hex characters

    # Valid verification
    assert verify_webhook_signature(payload, sig, secret) is True

    # Tampered payload
    tampered_payload = b'{"event":"order.created","order_id":"99999"}'
    assert verify_webhook_signature(tampered_payload, sig, secret) is False

    # Wrong secret
    assert verify_webhook_signature(payload, sig, "wrong_secret") is False

    # Malformed signature header
    assert verify_webhook_signature(payload, "invalid_header", secret) is False
    assert verify_webhook_signature(payload, None, secret) is False


def test_webhook_timestamp_replay_protection():
    """Verify timestamp freshness check rejects expired or heavily drifted timestamps."""
    now_epoch = int(time.time())

    # Current timestamp within tolerance
    assert verify_webhook_timestamp(str(now_epoch), max_drift_seconds=300) is True

    # Expired timestamp (10 minutes ago)
    old_epoch = now_epoch - 600
    assert verify_webhook_timestamp(str(old_epoch), max_drift_seconds=300) is False

    # ISO-8601 string support
    iso_now = datetime.now(UTC).isoformat()
    assert verify_webhook_timestamp(iso_now, max_drift_seconds=300) is True

    # Invalid timestamp string
    assert verify_webhook_timestamp("not-a-timestamp") is False
    assert verify_webhook_timestamp(None) is False


def test_inbound_signature_binds_timestamp_and_delivery_id():
    body = b'{"event":"order.created"}'
    timestamp = str(int(time.time()))
    delivery_id = "delivery-001"
    secret = "a-long-random-shared-secret-for-tests"
    signature = compute_inbound_webhook_signature(body, timestamp, delivery_id, secret)

    assert verify_inbound_webhook_signature(body, signature, timestamp, delivery_id, secret)
    assert not verify_inbound_webhook_signature(body, signature, timestamp, "delivery-002", secret)
    assert not verify_inbound_webhook_signature(
        body, signature, str(int(timestamp) - 1), delivery_id, secret
    )


@pytest.mark.asyncio
async def test_pinned_network_backend_uses_validated_ip():
    destination = PublicHttpsDestination("hooks.example", 443, ("8.8.8.8",))
    backend = _PinnedNetworkBackend(destination)
    connected_to = []

    class StubBackend:
        async def connect_tcp(self, host, port, **kwargs):
            connected_to.append((host, port))
            return object()

    backend._backend = StubBackend()
    await backend.connect_tcp("hooks.example", 443)
    assert connected_to == [("8.8.8.8", 443)]

    with pytest.raises(OSError):
        await backend.connect_tcp("127.0.0.1", 443)


@pytest.mark.asyncio
async def test_webhook_destination_requires_public_https():
    with pytest.raises(ValueError):
        await ensure_public_https_url("http://8.8.8.8/hook")
    with pytest.raises(ValueError):
        await ensure_public_https_url("https://127.0.0.1/hook")
    with pytest.raises(ValueError):
        await ensure_public_https_url("https://user:pass@example.com/hook")

    await ensure_public_https_url("https://8.8.8.8/hook")


@pytest.mark.asyncio
async def test_inbound_webhook_requires_hmac_when_secret_is_configured(monkeypatch):
    monkeypatch.setattr(
        "core.apis.routes.webhook_routes.get_settings",
        lambda: SimpleNamespace(
            inbound_webhook_secret="configured-test-secret", app_env="production"
        ),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        response = await client.post(
            "/api/v1/webhooks/inbound/carrier",
            json={
                "carrier": "FEDEX",
                "tracking_number": "1Z9999999999999999",
                "event_status": "DELIVERED",
            },
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_inbound_webhook_rejects_replayed_delivery_id(monkeypatch):
    secret = "a-long-random-shared-secret-for-replay-test"
    monkeypatch.setattr(
        "core.apis.routes.webhook_routes.get_settings",
        lambda: SimpleNamespace(inbound_webhook_secret=secret, app_env="production"),
    )
    body = json.dumps(
        {
            "carrier": "FEDEX",
            "tracking_number": "1Z9999999999999999",
            "event_status": "DELIVERED",
        },
        separators=(",", ":"),
    ).encode()
    timestamp = str(int(time.time()))
    delivery_id = f"delivery-{uuid4()}"
    headers = {
        "X-Whitfield-Timestamp": timestamp,
        "X-Whitfield-Delivery": delivery_id,
        "X-Whitfield-Signature": compute_inbound_webhook_signature(
            body,
            timestamp,
            delivery_id,
            secret,
        ),
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        first = await client.post("/api/v1/webhooks/inbound/carrier", content=body, headers=headers)
        replay = await client.post(
            "/api/v1/webhooks/inbound/carrier", content=body, headers=headers
        )

    assert first.status_code == 200
    assert replay.status_code == 409


@pytest.mark.asyncio
async def test_webhook_subscription_crud():
    """Verify subscription creation, listing, matching, and deletion."""
    async with transaction_session() as session:
        sub = await webhook_crud.create_subscription(
            session,
            tenant_id="SL-AURA",
            url="https://api.merchant.com/webhook",
            secret="test_secret_12345678",
            event_types=["order.reserved", "shipment.shipped"],
            description="Aura Merchant ERP Webhook",
        )
        assert sub.id is not None
        assert sub.status == "ACTIVE"

        # Listing
        subs = await webhook_crud.list_subscriptions(session, tenant_id="SL-AURA")
        assert any(s.id == sub.id for s in subs)

        # Event matching
        matched = await webhook_crud.get_active_subscriptions_for_event(session, "order.reserved")
        assert any(s.id == sub.id for s in matched)

        unmatched = await webhook_crud.get_active_subscriptions_for_event(
            session, "inventory.damaged"
        )
        assert not any(s.id == sub.id for s in unmatched)

        # Delete
        deleted = await webhook_crud.delete_subscription(session, sub.id)
        assert deleted is True
        check = await webhook_crud.get_subscription(session, sub.id)
        assert check is None


@pytest.mark.asyncio
async def test_outbox_webhook_dispatch_and_audit_logging(monkeypatch):
    """Verify that OutboxEvents trigger HTTP dispatch and persist WebhookDelivery audit records."""
    async with transaction_session() as session:
        # 1. Create a subscription
        sub = await webhook_crud.create_subscription(
            session,
            tenant_id="GLOBAL",
            url="https://mock-endpoint.whitfield.test/webhook",
            secret="test_secret_for_mock_delivery",
            event_types=["order.allocated"],
            description="Test Dispatch Target",
        )

        # 2. Mock httpx to intercept and record request
        intercepted_requests = []

        class MockResponse:
            status_code = 200
            text = '{"received": true}'

        async def mock_post(self, url, content=None, headers=None):
            intercepted_requests.append({"url": str(url), "content": content, "headers": headers})
            return MockResponse()

        import httpx
        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        async def allow_test_webhook_url(_url):
            return PublicHttpsDestination("mock-endpoint.whitfield.test", 443, ("8.8.8.8",))

        monkeypatch.setattr(
            "core.services.webhook_dispatcher_service.ensure_public_https_url",
            allow_test_webhook_url,
        )

        # 3. Create an outbox event
        event = await outbox_crud.create_outbox_event(
            session,
            event_type="order.allocated",
            payload={"order_number": "ORD-TEST-999", "units": 50},
        )

        # 4. Dispatch
        dispatched = await dispatch_outbox_event_to_webhooks(event, session)
        assert dispatched >= 1
        assert len(intercepted_requests) >= 1

        mock_req = next(
            (r for r in intercepted_requests if r["url"] == "https://mock-endpoint.whitfield.test/webhook"),
            None,
        )
        assert mock_req is not None
        assert mock_req["headers"]["X-Whitfield-Event"] == "order.allocated"
        assert "X-Whitfield-Signature" in mock_req["headers"]
        assert mock_req["headers"]["X-Whitfield-Signature"].startswith("sha256=")

        # 5. Verify WebhookDelivery audit log entry
        deliveries = await webhook_crud.list_deliveries(session, subscription_id=sub.id)
        assert len(deliveries) >= 1
        last_delivery = deliveries[0]
        assert last_delivery.status_code == 200
        assert last_delivery.event_type == "order.allocated"
        assert last_delivery.error is None
        assert last_delivery.latency_ms is not None


@pytest.mark.asyncio
async def test_inbound_carrier_webhook_endpoint():
    """Verify POST /api/v1/webhooks/inbound/carrier accepts tracking events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        res = await client.post(
            "/api/v1/webhooks/inbound/carrier",
            json={
                "carrier": "FEDEX",
                "tracking_number": "1Z9999999999999999",
                "event_status": "OUT_FOR_DELIVERY",
                "location": "Reno, NV",
                "notes": "On delivery vehicle",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ACCEPTED"
        assert data["tracking_number"] == "1Z9999999999999999"


@pytest.mark.asyncio
async def test_inbound_marketplace_order_webhook_endpoint():
    """Verify POST /api/v1/webhooks/inbound/order enqueues marketplace orders."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        res = await client.post(
            "/api/v1/webhooks/inbound/order",
            json={
                "external_order_id": "SHOPIFY-ORD-8812",
                "source": "SHOPIFY",
                "seller_tenant_id": "SL-AURA",
                "customer_name": "Jane Smith",
                "shipping_address": {"city": "Columbus", "state": "OH"},
                "lines": [{"sku": "SKU-AURA-100", "qty": 2}],
            },
        )
        assert res.status_code == 202
        data = res.json()
        assert data["status"] == "ENQUEUED"
        assert data["external_order_id"] == "SHOPIFY-ORD-8812"

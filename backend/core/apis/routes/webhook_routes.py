"""
FastAPI HTTP endpoints for webhook subscriptions, delivery inspection, and inbound ingestion.
"""

from __future__ import annotations

from datetime import UTC, datetime
import secrets
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
import httpx

from common.auth import get_current_user
from common.logger import get_logger
from common.warehouse_scope import get_warehouse_scope
from common.webhook_signer import compute_webhook_signature, verify_webhook_signature, verify_webhook_timestamp
from core.apis.schemas.webhook_schemas import (
    InboundCarrierWebhookRequest,
    InboundOrderWebhookRequest,
    WebhookDeliveryResponse,
    WebhookSubscriptionCreate,
    WebhookSubscriptionResponse,
)
from core.cruds import outbox_crud, webhook_crud
from core.database.database import transaction_session

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/webhooks", tags=["Webhooks & Integrations"])


@router.post(
    "/subscriptions",
    response_model=WebhookSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new webhook destination",
)
async def create_webhook_subscription(
    request: WebhookSubscriptionCreate,
    scope: Annotated[dict[str, Any], Depends(get_warehouse_scope)],
) -> WebhookSubscriptionResponse:
    """Register an HTTP/HTTPS endpoint to receive signed transactional outbox events."""
    secret = request.secret or secrets.token_hex(24)
    tenant_id = scope.get("seller_id") or "GLOBAL"

    async with transaction_session() as session:
        sub = await webhook_crud.create_subscription(
            session,
            tenant_id=tenant_id,
            url=request.url,
            secret=secret,
            event_types=request.event_types,
            description=request.description,
        )
        return WebhookSubscriptionResponse.model_validate(sub)


@router.get(
    "/subscriptions",
    response_model=list[WebhookSubscriptionResponse],
    summary="List registered webhook destinations",
)
async def list_webhook_subscriptions(
    scope: Annotated[dict[str, Any], Depends(get_warehouse_scope)],
) -> list[WebhookSubscriptionResponse]:
    """List webhook destinations visible to the caller's tenancy or all for admin."""
    role = scope.get("role", "")
    tenant_id = "ALL" if role in ("ADMINISTRATOR", "SUPERADMIN") else (scope.get("seller_id") or "GLOBAL")

    async with transaction_session() as session:
        subs = await webhook_crud.list_subscriptions(session, tenant_id=tenant_id)
        return [WebhookSubscriptionResponse.model_validate(s) for s in subs]


@router.delete(
    "/subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a webhook subscription",
)
async def delete_webhook_subscription(
    subscription_id: UUID,
    scope: Annotated[dict[str, Any], Depends(get_warehouse_scope)],
) -> Response:
    """Delete a registered webhook endpoint."""
    async with transaction_session() as session:
        sub = await webhook_crud.get_subscription(session, subscription_id)
        if not sub:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

        role = scope.get("role", "")
        if role not in ("ADMINISTRATOR", "SUPERADMIN"):
            caller_tenant = scope.get("seller_id") or "GLOBAL"
            if sub.tenant_id != caller_tenant:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        await webhook_crud.delete_subscription(session, subscription_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/deliveries",
    response_model=list[WebhookDeliveryResponse],
    summary="List recent webhook delivery attempts",
)
async def list_webhook_deliveries(
    subscription_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    scope: Annotated[dict[str, Any], Depends(get_warehouse_scope)] = None,
) -> list[WebhookDeliveryResponse]:
    """Retrieve audit log of outbound webhook delivery attempts."""
    async with transaction_session() as session:
        deliveries = await webhook_crud.list_deliveries(session, subscription_id=subscription_id, limit=limit)
        return [WebhookDeliveryResponse.model_validate(d) for d in deliveries]


@router.post(
    "/subscriptions/{subscription_id}/test",
    response_model=WebhookDeliveryResponse,
    summary="Send a test ping webhook",
)
async def test_webhook_subscription(
    subscription_id: UUID,
    scope: Annotated[dict[str, Any], Depends(get_warehouse_scope)],
) -> WebhookDeliveryResponse:
    """Dispatch an immediate test ping event to verify connectivity and signature handling."""
    async with transaction_session() as session:
        sub = await webhook_crud.get_subscription(session, subscription_id)
        if not sub:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

        test_payload = {
            "test": True,
            "message": "Whitfield WMS Test Webhook Ping",
            "subscription_id": str(sub.id),
            "triggered_by": scope.get("user_id", "admin"),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        import json
        import time
        raw_body = json.dumps(test_payload).encode("utf-8")
        now_ts = str(int(time.time()))
        signature = compute_webhook_signature(raw_body, sub.secret)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Whitfield-WMS-Webhook/1.0",
            "X-Whitfield-Event": "webhook.test_ping",
            "X-Whitfield-Signature": signature,
            "X-Whitfield-Timestamp": now_ts,
            "X-Whitfield-Delivery": f"test-{secrets.token_hex(8)}",
        }

        start = time.perf_counter()
        status_code: int | None = None
        response_text: str | None = None
        error_msg: str | None = None

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(sub.url, content=raw_body, headers=headers)
                latency_ms = (time.perf_counter() - start) * 1000.0
                status_code = res.status_code
                response_text = res.text[:500]
                if not (200 <= res.status_code < 300):
                    error_msg = f"HTTP {res.status_code}"
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000.0
            error_msg = str(exc)

        delivery = await webhook_crud.record_delivery(
            session,
            subscription_id=sub.id,
            outbox_event_id=None,
            event_type="webhook.test_ping",
            payload=test_payload,
            status_code=status_code,
            response_body=response_text,
            latency_ms=latency_ms,
            attempt_number=1,
            error=error_msg,
        )
        return WebhookDeliveryResponse.model_validate(delivery)


@router.post(
    "/inbound/carrier",
    status_code=status.HTTP_200_OK,
    summary="Inbound carrier package tracking update",
)
async def inbound_carrier_webhook(
    request: InboundCarrierWebhookRequest,
    req: Request,
    x_whitfield_signature: Annotated[str | None, Header()] = None,
    x_whitfield_timestamp: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """
    Ingest real-time carrier status updates (FedEx, UPS, DHL).
    Records tracking progress and atomically updates outbox events.
    """
    logger.info(
        "Inbound carrier webhook received: carrier=%s, tracking=%s, status=%s",
        request.carrier,
        request.tracking_number,
        request.event_status,
    )

    async with transaction_session() as session:
        # Atomic record in outbox for downstream fulfillment reconciliation
        await outbox_crud.create_outbox_event(
            session,
            event_type="carrier.tracking_updated",
            payload={
                "carrier": request.carrier,
                "tracking_number": request.tracking_number,
                "event_status": request.event_status,
                "location": request.location,
                "notes": request.notes,
                "received_at": datetime.now(UTC).isoformat(),
            },
        )

    return {
        "status": "ACCEPTED",
        "carrier": request.carrier,
        "tracking_number": request.tracking_number,
        "processed_at": datetime.now(UTC).isoformat(),
    }


@router.post(
    "/inbound/order",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Inbound marketplace order intake",
)
async def inbound_marketplace_order_webhook(
    request: InboundOrderWebhookRequest,
) -> dict[str, Any]:
    """
    Ingest orders from external channels (Shopify, Amazon, WooCommerce).
    Enqueues order event for automatic allocation and inventory reservation.
    """
    logger.info(
        "Inbound marketplace order webhook received: source=%s, order_id=%s, seller=%s",
        request.source,
        request.external_order_id,
        request.seller_tenant_id,
    )

    async with transaction_session() as session:
        await outbox_crud.create_outbox_event(
            session,
            event_type="order.marketplace_ingested",
            payload={
                "external_order_id": request.external_order_id,
                "source": request.source,
                "seller_tenant_id": request.seller_tenant_id,
                "customer_name": request.customer_name,
                "lines_count": len(request.lines),
                "received_at": datetime.now(UTC).isoformat(),
            },
        )

    return {
        "status": "ENQUEUED",
        "external_order_id": request.external_order_id,
        "enqueued_at": datetime.now(UTC).isoformat(),
    }

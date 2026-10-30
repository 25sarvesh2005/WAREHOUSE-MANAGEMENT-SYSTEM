"""
FastAPI HTTP endpoints for webhook subscriptions, delivery inspection, and inbound ingestion.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from common.logger import get_logger
from common.pinned_webhook_transport import PinnedWebhookTransport
from common.warehouse_scope import get_warehouse_scope
from common.webhook_signer import (
    compute_webhook_signature,
    verify_inbound_webhook_signature,
    verify_webhook_timestamp,
)
from common.webhook_url import ensure_public_https_url
from core.apis.schemas.webhook_schemas import (
    InboundCarrierWebhookRequest,
    InboundOrderWebhookRequest,
    WebhookDeliveryResponse,
    WebhookSubscriptionCreate,
    WebhookSubscriptionResponse,
)
from core.config.settings import get_settings
from core.cruds import outbox_crud, webhook_crud
from core.database.database import transaction_session

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/webhooks", tags=["Webhooks & Integrations"])


async def _require_valid_inbound_signature(request: Request) -> str | None:
    """Validate the shared-secret HMAC and timestamp for inbound integrations."""
    settings = get_settings()
    secret = settings.inbound_webhook_secret.strip()
    if not secret and settings.app_env in ("development", "test"):
        return None

    signature = request.headers.get("X-Whitfield-Signature")
    timestamp = request.headers.get("X-Whitfield-Timestamp")
    delivery_id = request.headers.get("X-Whitfield-Delivery")
    body = await request.body()
    if (
        not delivery_id
        or len(delivery_id) > 255
        or not verify_webhook_timestamp(timestamp)
        or not verify_inbound_webhook_signature(
        body,
        signature,
        timestamp,
        delivery_id,
        secret,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature, timestamp, or delivery ID",
        )
    return delivery_id


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
    try:
        await ensure_public_https_url(request.url)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    secret = request.secret or secrets.token_hex(24)
    seller_ids = scope.get("seller_ids", [])
    if scope.get("role") == "SELLER":
        if len(seller_ids) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A seller webhook must be scoped to exactly one seller account",
            )
        tenant_id = seller_ids[0]
    else:
        tenant_id = "GLOBAL"

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
    seller_ids = scope.get("seller_ids", [])

    async with transaction_session() as session:
        if role in ("ADMINISTRATOR", "SUPERADMIN"):
            subs = await webhook_crud.list_subscriptions(session, tenant_id="ALL")
        else:
            subscriptions_by_id = {}
            for seller_id in seller_ids:
                for sub in await webhook_crud.list_subscriptions(session, tenant_id=seller_id):
                    subscriptions_by_id[sub.id] = sub
            if not seller_ids:
                for sub in await webhook_crud.list_subscriptions(session, tenant_id="GLOBAL"):
                    subscriptions_by_id[sub.id] = sub
            subs = list(subscriptions_by_id.values())
        return [
            WebhookSubscriptionResponse.model_validate(s).model_copy(update={"secret": None})
            for s in subs
        ]


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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

        role = scope.get("role", "")
        if role not in ("ADMINISTRATOR", "SUPERADMIN"):
            caller_tenants = set(scope.get("seller_ids", []))
            if sub.tenant_id not in caller_tenants:
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
        deliveries = await webhook_crud.list_deliveries(
            session,
            subscription_id=subscription_id,
            limit=limit,
        )
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found",
            )

        test_payload = {
            "test": True,
            "message": "Whitfield WMS Test Webhook Ping",
            "subscription_id": str(sub.id),
            "triggered_by": scope.get("user_id", "admin"),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        try:
            destination = await ensure_public_https_url(sub.url)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error

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
            async with httpx.AsyncClient(
                transport=PinnedWebhookTransport(destination),
                timeout=5.0,
                follow_redirects=False,
                trust_env=False,
            ) as client:
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
) -> dict[str, Any]:
    """
    Ingest real-time carrier status updates (FedEx, UPS, DHL).
    Records tracking progress and atomically updates outbox events.
    """
    delivery_id = await _require_valid_inbound_signature(req)
    logger.info(
        "Inbound carrier webhook received: carrier=%s, tracking=%s, status=%s",
        request.carrier,
        request.tracking_number,
        request.event_status,
    )

    try:
        async with transaction_session() as session:
            if delivery_id is not None:
                await webhook_crud.record_inbound_delivery(
                    session,
                    provider=f"carrier:{request.carrier.upper()}",
                    delivery_id=delivery_id,
                )
            # Atomic record in outbox for downstream fulfillment reconciliation.
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
    except webhook_crud.DuplicateInboundWebhookDelivery as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Webhook delivery was already processed",
        ) from error

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
    req: Request,
) -> dict[str, Any]:
    """
    Ingest orders from external channels (Shopify, Amazon, WooCommerce).
    Enqueues order event for automatic allocation and inventory reservation.
    """
    delivery_id = await _require_valid_inbound_signature(req)
    logger.info(
        "Inbound marketplace order webhook received: source=%s, order_id=%s, seller=%s",
        request.source,
        request.external_order_id,
        request.seller_tenant_id,
    )

    try:
        async with transaction_session() as session:
            if delivery_id is not None:
                await webhook_crud.record_inbound_delivery(
                    session,
                    provider=f"marketplace:{request.source.upper()}",
                    delivery_id=delivery_id,
                )
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
    except webhook_crud.DuplicateInboundWebhookDelivery as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Webhook delivery was already processed",
        ) from error

    return {
        "status": "ENQUEUED",
        "external_order_id": request.external_order_id,
        "enqueued_at": datetime.now(UTC).isoformat(),
    }

"""
Model Context Protocol (MCP) read-only tool definitions for warehouse operations.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any
from uuid import UUID

from pydantic import Field

from common.logger import get_logger
from core.database.database import transaction_session
from core.services.ai import read_tools
from mcp_server.context import RequesterContext

logger = get_logger(__name__)


class MCPToolError(RuntimeError):
    """Base error for MCP tool execution failures."""


class MCPScopeViolationError(MCPToolError):
    """Raised when an MCP client attempts out-of-scope data access."""


class MCPRecordNotFoundError(MCPToolError):
    """Raised when a requested operational record does not exist."""


async def tool_inventory_lookup(
    sku: Annotated[str, Field(description="Product SKU or product name to search")],
    requester: RequesterContext,
) -> list[dict[str, Any]]:
    """
    Look up available inventory stock balances for a SKU or product name.

    Returns available quantities grouped by warehouse, scoped by caller tenant permissions.
    """
    logger.info("MCP tool: inventory_lookup sku=%s caller=%s", sku, requester.email)
    try:
        async with transaction_session() as session:
            rows = await read_tools.lookup_available_inventory(
                session,
                sku=sku,
                seller_id=requester.seller_id,
                seller_ids=requester.seller_ids if not requester.seller_id else None,
                warehouse_id=requester.warehouse_id,
                warehouse_ids=requester.warehouse_ids if not requester.warehouse_id else None,
            )
            return [
                {
                    "seller_id": str(r.seller_id),
                    "seller_code": r.seller_code,
                    "product_id": str(r.product_id),
                    "sku": r.sku,
                    "product_name": r.product_name,
                    "warehouse_id": str(r.warehouse_id),
                    "warehouse_code": r.warehouse_code,
                    "available_quantity": float(r.available_quantity),
                }
                for r in rows
            ]
    except Exception as exc:
        logger.error("MCP tool inventory_lookup error: %s", exc, exc_info=True)
        raise MCPToolError(f"Inventory lookup failed: {exc}") from exc


async def tool_ledger_explanation(
    sku: Annotated[str, Field(description="Product SKU to retrieve movement ledger history for")],
    requester: RequesterContext,
    limit: Annotated[int, Field(description="Maximum movement records to return (default 10)")] = 10,
) -> list[dict[str, Any]]:
    """
    Retrieve append-only inventory movement ledger history for an audit explanation.
    """
    logger.info("MCP tool: ledger_explanation sku=%s limit=%d caller=%s", sku, limit, requester.email)
    try:
        async with transaction_session() as session:
            rows = await read_tools.lookup_recent_ledger_movements(
                session,
                sku=sku,
                seller_id=requester.seller_id,
                seller_ids=requester.seller_ids if not requester.seller_id else None,
                warehouse_id=requester.warehouse_id,
                warehouse_ids=requester.warehouse_ids if not requester.warehouse_id else None,
                limit=limit,
            )
            return [
                {
                    "movement_id": str(r.movement_id),
                    "seller_code": r.seller_code,
                    "sku": r.sku,
                    "product_name": r.product_name,
                    "warehouse_code": r.warehouse_code,
                    "inventory_state": r.inventory_state,
                    "quantity_delta": float(r.quantity_delta),
                    "movement_type": r.movement_type,
                    "source_type": r.source_type,
                    "source_id": str(r.source_id),
                    "reason_code": r.reason_code,
                    "reason_text": r.reason_text,
                    "recorded_at": r.recorded_at.isoformat(),
                }
                for r in rows
            ]
    except Exception as exc:
        logger.error("MCP tool ledger_explanation error: %s", exc, exc_info=True)
        raise MCPToolError(f"Ledger explanation query failed: {exc}") from exc


async def tool_order_status(
    requester: RequesterContext,
    reference_number: Annotated[str | None, Field(description="Seller order reference number")] = None,
    order_id: Annotated[str | None, Field(description="Internal order UUID")] = None,
) -> dict[str, Any] | None:
    """
    Query the status and fulfillment lines of a customer order.
    """
    if not reference_number and not order_id:
        raise MCPToolError("Must provide either reference_number or order_id")

    order_uuid = UUID(order_id) if order_id else None
    logger.info("MCP tool: order_status ref=%s id=%s", reference_number, order_id)
    try:
        async with transaction_session() as session:
            evidence = await read_tools.lookup_order_status(
                session,
                record_id=order_uuid,
                reference_number=reference_number,
                seller_id=requester.seller_id,
                warehouse_id=requester.warehouse_id,
            )
            if not evidence:
                return None
            return {
                "record_type": evidence.record_type,
                "record_id": str(evidence.record_id),
                "reference_number": evidence.reference_number,
                "status": evidence.status,
                "seller_code": evidence.seller_code,
                "warehouse_codes": evidence.warehouse_codes,
                "summary": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in evidence.summary.items()},
                "details": [
                    {k: (float(v) if hasattr(v, "as_tuple") else str(v) if isinstance(v, UUID) else v) for k, v in d.items()}
                    for d in evidence.details
                ],
            }
    except Exception as exc:
        logger.error("MCP tool order_status error: %s", exc, exc_info=True)
        raise MCPToolError(f"Order status query failed: {exc}") from exc


async def tool_receipt_status(
    requester: RequesterContext,
    receipt_number: Annotated[str | None, Field(description="Inbound receipt number")] = None,
    receipt_id: Annotated[str | None, Field(description="Internal receipt UUID")] = None,
) -> dict[str, Any] | None:
    """
    Query the status and line dispositions of an inbound receiving receipt.
    """
    if not receipt_number and not receipt_id:
        raise MCPToolError("Must provide either receipt_number or receipt_id")

    rcv_uuid = UUID(receipt_id) if receipt_id else None
    logger.info("MCP tool: receipt_status num=%s id=%s", receipt_number, receipt_id)
    try:
        async with transaction_session() as session:
            evidence = await read_tools.lookup_receipt_status(
                session,
                record_id=rcv_uuid,
                reference_number=receipt_number,
                seller_id=requester.seller_id,
                warehouse_id=requester.warehouse_id,
            )
            if not evidence:
                return None
            return {
                "record_type": evidence.record_type,
                "record_id": str(evidence.record_id),
                "reference_number": evidence.reference_number,
                "status": evidence.status,
                "seller_code": evidence.seller_code,
                "warehouse_codes": evidence.warehouse_codes,
                "summary": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in evidence.summary.items()},
                "details": [
                    {k: (float(v) if hasattr(v, "as_tuple") else str(v) if isinstance(v, UUID) else v) for k, v in d.items()}
                    for d in evidence.details
                ],
            }
    except Exception as exc:
        logger.error("MCP tool receipt_status error: %s", exc, exc_info=True)
        raise MCPToolError(f"Receipt status query failed: {exc}") from exc


async def tool_transfer_status(
    requester: RequesterContext,
    transfer_number: Annotated[str | None, Field(description="Transfer order reference number")] = None,
    transfer_id: Annotated[str | None, Field(description="Internal transfer UUID")] = None,
) -> dict[str, Any] | None:
    """
    Query status and line progress of an inter-warehouse inventory transfer.
    """
    if not transfer_number and not transfer_id:
        raise MCPToolError("Must provide either transfer_number or transfer_id")

    trf_uuid = UUID(transfer_id) if transfer_id else None
    logger.info("MCP tool: transfer_status num=%s id=%s", transfer_number, transfer_id)
    try:
        async with transaction_session() as session:
            evidence = await read_tools.lookup_transfer_status(
                session,
                record_id=trf_uuid,
                reference_number=transfer_number,
                seller_id=requester.seller_id,
                warehouse_id=requester.warehouse_id,
            )
            if not evidence:
                return None
            return {
                "record_type": evidence.record_type,
                "record_id": str(evidence.record_id),
                "reference_number": evidence.reference_number,
                "status": evidence.status,
                "seller_code": evidence.seller_code,
                "warehouse_codes": evidence.warehouse_codes,
                "summary": {k: (v.isoformat() if hasattr(v, "isoformat") else str(v) if isinstance(v, UUID) else v) for k, v in evidence.summary.items()},
                "details": [
                    {k: (float(v) if hasattr(v, "as_tuple") else str(v) if isinstance(v, UUID) else v) for k, v in d.items()}
                    for d in evidence.details
                ],
            }
    except Exception as exc:
        logger.error("MCP tool transfer_status error: %s", exc, exc_info=True)
        raise MCPToolError(f"Transfer status query failed: {exc}") from exc


async def tool_shipment_status(
    requester: RequesterContext,
    tracking_number: Annotated[str | None, Field(description="Carrier tracking number")] = None,
    shipment_id: Annotated[str | None, Field(description="Internal shipment UUID")] = None,
) -> dict[str, Any] | None:
    """
    Query tracking status and package contents of an outbound fulfillment shipment.
    """
    if not tracking_number and not shipment_id:
        raise MCPToolError("Must provide either tracking_number or shipment_id")

    shp_uuid = UUID(shipment_id) if shipment_id else None
    logger.info("MCP tool: shipment_status trk=%s id=%s", tracking_number, shipment_id)
    try:
        async with transaction_session() as session:
            evidence = await read_tools.lookup_shipment_status(
                session,
                record_id=shp_uuid,
                reference_number=tracking_number,
                seller_id=requester.seller_id,
                warehouse_id=requester.warehouse_id,
            )
            if not evidence:
                return None
            return {
                "record_type": evidence.record_type,
                "record_id": str(evidence.record_id),
                "reference_number": evidence.reference_number,
                "status": evidence.status,
                "seller_code": evidence.seller_code,
                "warehouse_codes": evidence.warehouse_codes,
                "summary": {k: (v.isoformat() if hasattr(v, "isoformat") else str(v) if isinstance(v, UUID) else v) for k, v in evidence.summary.items()},
                "details": [
                    {k: (float(v) if hasattr(v, "as_tuple") else str(v) if isinstance(v, UUID) else v) for k, v in d.items()}
                    for d in evidence.details
                ],
            }
    except Exception as exc:
        logger.error("MCP tool shipment_status error: %s", exc, exc_info=True)
        raise MCPToolError(f"Shipment status query failed: {exc}") from exc


async def tool_return_status(
    requester: RequesterContext,
    return_number: Annotated[str | None, Field(description="Return RMA or return number")] = None,
    return_id: Annotated[str | None, Field(description="Internal return UUID")] = None,
) -> dict[str, Any] | None:
    """
    Query receipt and inspection disposition status of a customer return.
    """
    if not return_number and not return_id:
        raise MCPToolError("Must provide either return_number or return_id")

    ret_uuid = UUID(return_id) if return_id else None
    logger.info("MCP tool: return_status num=%s id=%s", return_number, return_id)
    try:
        async with transaction_session() as session:
            evidence = await read_tools.lookup_return_status(
                session,
                record_id=ret_uuid,
                reference_number=return_number,
                seller_id=requester.seller_id,
                warehouse_id=requester.warehouse_id,
            )
            if not evidence:
                return None
            return {
                "record_type": evidence.record_type,
                "record_id": str(evidence.record_id),
                "reference_number": evidence.reference_number,
                "status": evidence.status,
                "seller_code": evidence.seller_code,
                "warehouse_codes": evidence.warehouse_codes,
                "summary": {k: (v.isoformat() if hasattr(v, "isoformat") else str(v) if isinstance(v, UUID) else v) for k, v in evidence.summary.items()},
                "details": [
                    {k: (float(v) if hasattr(v, "as_tuple") else str(v) if isinstance(v, UUID) else v) for k, v in d.items()}
                    for d in evidence.details
                ],
            }
    except Exception as exc:
        logger.error("MCP tool return_status error: %s", exc, exc_info=True)
        raise MCPToolError(f"Return status query failed: {exc}") from exc


async def tool_exception_listing(
    requester: RequesterContext,
) -> dict[str, Any]:
    """
    Query operational exception records across warehouse subsystems.
    """
    logger.info("MCP tool: exception_listing caller=%s", requester.email)
    try:
        async with transaction_session() as session:
            evidence = await read_tools.lookup_operational_exceptions(
                session,
                seller_id=requester.seller_id,
                seller_ids=requester.seller_ids if not requester.seller_id else None,
                warehouse_id=requester.warehouse_id,
                warehouse_ids=requester.warehouse_ids if not requester.warehouse_id else None,
            )
            return {
                "total_exceptions": evidence.total_exceptions,
                "overdue_receipts": evidence.overdue_receipts,
                "short_pick_exceptions": evidence.short_pick_exceptions,
                "expired_reservations": evidence.expired_or_expiring_reservations,
                "transfer_variances": evidence.transfer_variances,
                "return_inspection_queues": evidence.return_inspection_queues,
                "migration_validation_failures": evidence.migration_validation_failures,
            }
    except Exception as exc:
        logger.error("MCP tool exception_listing error: %s", exc, exc_info=True)
        raise MCPToolError(f"Exception listing query failed: {exc}") from exc


MCP_TOOLS = {
    "inventory_lookup": tool_inventory_lookup,
    "ledger_explanation": tool_ledger_explanation,
    "order_status": tool_order_status,
    "receipt_status": tool_receipt_status,
    "transfer_status": tool_transfer_status,
    "shipment_status": tool_shipment_status,
    "return_status": tool_return_status,
    "exception_listing": tool_exception_listing,
}

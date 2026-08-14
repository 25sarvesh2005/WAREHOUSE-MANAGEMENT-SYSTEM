"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/responses/inventory_response.py
Purpose     : Define inventory response schemas.

Responsibilities:
    - Serialize inventory balances, movements, and reconciliation records.

Flow:
    Controller data -> Pydantic response schema -> FastAPI JSON

Used By:
    - core/apis/routes/inventory_routes.py

Returns:
    BaseModel instances - Serialized response payloads.

Raises:
    pydantic.ValidationError: When model payload does not match schema.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InventoryBalanceResponse(BaseModel):
    """Public operational inventory balance response."""

    id: UUID
    seller_id: UUID
    product_id: UUID
    warehouse_id: UUID
    location_id: UUID | None
    inventory_state: str
    quantity: Decimal
    version: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryMovementResponse(BaseModel):
    """Public inventory movement ledger record response."""

    id: UUID
    seller_id: UUID
    product_id: UUID
    warehouse_id: UUID
    location_id: UUID | None
    inventory_state: str
    quantity_delta: Decimal
    movement_type: str
    source_type: str
    source_id: UUID
    source_line_id: UUID | None
    idempotency_key: str
    reason_code: str | None
    reason_text: str | None
    actor_user_id: UUID | None
    correlation_id: str | None
    occurred_at: datetime
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReconciliationResponse(BaseModel):
    """Public inventory reconciliation snapshot response."""

    id: UUID
    warehouse_id: UUID
    seller_id: UUID | None
    snapshot_time: datetime
    status: str
    total_ledger_quantity: Decimal
    total_balance_quantity: Decimal
    variance_quantity: Decimal
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

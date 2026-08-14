"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/requests/inventory_request.py
Purpose     : Define inventory request schemas.

Responsibilities:
    - Validate query filters for balances and movements.
    - Validate reconciliation request parameters.

Flow:
    HTTP request query/body -> Pydantic request schema

Used By:
    - core/apis/routes/inventory_routes.py

Returns:
    BaseModel instances - Validated request payloads.

Raises:
    pydantic.ValidationError: When validation fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ReconciliationRequest(BaseModel):
    """Request body to trigger inventory reconciliation and variance calculation."""

    warehouse_id: UUID = Field(description="Target warehouse UUID.")
    seller_id: UUID | None = Field(default=None, description="Optional target seller UUID.")
    notes: str | None = Field(
        default=None, max_length=1000, description="Optional investigation notes."
    )

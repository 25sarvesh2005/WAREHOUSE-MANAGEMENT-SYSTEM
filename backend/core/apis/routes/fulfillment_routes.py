"""
FastAPI HTTP endpoints for pick tasks, packages, and manual shipment dispatch.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from common.pagination import normalize_pagination
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.fulfillment_request import (
    PickTaskCompleteRequest,
    PickTaskCreateRequest,
    ShipmentCreateRequest,
)
from core.apis.schemas.responses.fulfillment_response import PickTaskResponse, ShipmentResponse
from core.controllers.fulfillment_controller import fulfillment_controller

router = APIRouter(prefix="/v1", tags=["Fulfillment & Shipments"])


@router.post(
    "/pick-tasks",
    response_model=PickTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create warehouse pick task",
)
async def create_pick_task(
    request: PickTaskCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> PickTaskResponse:
    """Generate a warehouse worker pick task for a reserved order."""
    task = await fulfillment_controller.create_pick_task(request.model_dump(), scope)
    return PickTaskResponse.model_validate(task)


@router.get(
    "/pick-tasks",
    response_model=list[PickTaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List warehouse pick tasks",
)
async def list_pick_tasks(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    warehouse_id: UUID | None = Query(default=None, description="Warehouse facility UUID"),
    assigned_user_id: UUID | None = Query(default=None, description="Worker user UUID"),
    status_filter: str | None = Query(
        default=None, alias="status", description="Pick task status"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PickTaskResponse]:
    """List warehouse pick tasks matching search filters."""
    norm_limit, norm_offset = normalize_pagination(limit, offset)
    tasks = await fulfillment_controller.list_pick_tasks(
        scope,
        warehouse_id=warehouse_id,
        assigned_user_id=assigned_user_id,
        status=status_filter,
        limit=norm_limit,
        offset=norm_offset,
    )
    return [PickTaskResponse.model_validate(t) for t in tasks]


@router.get(
    "/pick-tasks/{pick_task_id}",
    response_model=PickTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get pick task by ID",
)
async def get_pick_task(
    pick_task_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> PickTaskResponse:
    """Retrieve pick task details by ID."""
    task = await fulfillment_controller.get_pick_task(pick_task_id, scope)
    return PickTaskResponse.model_validate(task)


@router.post(
    "/pick-tasks/{pick_task_id}/complete",
    response_model=PickTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete warehouse pick task",
)
async def complete_pick_task(
    pick_task_id: UUID,
    request: PickTaskCompleteRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> PickTaskResponse:
    """Complete a pick task (handles normal picks & short-pick exceptions)."""
    task = await fulfillment_controller.complete_pick_task(
        pick_task_id, request.model_dump(), scope
    )
    return PickTaskResponse.model_validate(task)


@router.post(
    "/shipments",
    response_model=ShipmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create order shipment dispatch",
)
async def create_shipment(
    request: ShipmentCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ShipmentResponse:
    """Create order shipment, attach packages, and post SHIPPED inventory movements."""
    shipment = await fulfillment_controller.create_shipment(request.model_dump(), scope)
    return ShipmentResponse.model_validate(shipment)


@router.get(
    "/shipments",
    response_model=list[ShipmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List shipments",
)
async def list_shipments(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    order_id: UUID | None = Query(default=None, description="Order UUID"),
    warehouse_id: UUID | None = Query(default=None, description="Warehouse UUID"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ShipmentResponse]:
    """List order shipment records matching filters."""
    norm_limit, norm_offset = normalize_pagination(limit, offset)
    shipments = await fulfillment_controller.list_shipments(
        scope,
        order_id=order_id,
        warehouse_id=warehouse_id,
        limit=norm_limit,
        offset=norm_offset,
    )
    return [ShipmentResponse.model_validate(s) for s in shipments]


@router.get(
    "/shipments/{shipment_id}",
    response_model=ShipmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get shipment details by ID",
)
async def get_shipment(
    shipment_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ShipmentResponse:
    """Retrieve shipment record by ID."""
    shipment = await fulfillment_controller.get_shipment(shipment_id, scope)
    return ShipmentResponse.model_validate(shipment)

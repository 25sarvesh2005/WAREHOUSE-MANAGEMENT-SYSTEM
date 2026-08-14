"""
Return Routes.

FastAPI endpoints for customer / seller returns and inspection dispositions:
    - POST /v1/returns: Create return draft/expected RMA.
    - GET /v1/returns: List returns.
    - GET /v1/returns/{return_id}: Retrieve single return details.
    - POST /v1/returns/{return_id}/receive: Register parcel receipt into RETURN_INSPECTION.
    - POST /v1/returns/{return_id}/inspect: Log inspection outcome dispositions.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from common.logger import get_logger
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.return_request import (
    ReturnCreateRequest,
    ReturnInspectRequest,
    ReturnReceiveRequest,
)
from core.apis.schemas.responses.return_response import ReturnListResponse, ReturnResponse
from core.controllers.return_controller import ReturnController

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/returns", tags=["Returns & Dispositions"])
return_controller = ReturnController()


@router.post(
    "",
    response_model=ReturnResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Customer / Seller Inbound Return",
)
async def create_return(
    request: ReturnCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ReturnResponse:
    """Create a new expected return RMA or unidentified inbound return."""
    logger.info("Calling POST /v1/returns endpoint")
    ret = await return_controller.create_return(request.model_dump(), scope)
    return ReturnResponse.model_validate(ret)


@router.get(
    "",
    response_model=ReturnListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Customer / Seller Returns",
)
async def list_returns(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(None, description="Filter by seller tenant UUID"),
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse UUID"),
    status_val: str | None = Query(None, alias="status", description="Filter by return status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ReturnListResponse:
    """List returns with optional query filters."""
    logger.info("Calling GET /v1/returns endpoint")
    returns, total = await return_controller.list_returns(
        scope,
        seller_id=seller_id,
        warehouse_id=warehouse_id,
        status_val=status_val,
        limit=limit,
        offset=offset,
    )
    items = [ReturnResponse.model_validate(r) for r in returns]
    return ReturnListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{return_id}",
    response_model=ReturnResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Return Details",
)
async def get_return(
    return_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ReturnResponse:
    """Retrieve single return details."""
    logger.info("Calling GET /v1/returns/%s endpoint", return_id)
    ret = await return_controller.get_return(return_id, scope)
    return ReturnResponse.model_validate(ret)


@router.post(
    "/{return_id}/receive",
    response_model=ReturnResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive Inbound Return Parcel (Move Stock to RETURN_INSPECTION)",
)
async def receive_return(
    return_id: UUID,
    request: ReturnReceiveRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ReturnResponse:
    """Receive return parcel, placing stock strictly into RETURN_INSPECTION state."""
    logger.info("Calling POST /v1/returns/%s/receive endpoint", return_id)
    ret = await return_controller.receive_return(return_id, request.model_dump(), scope)
    return ReturnResponse.model_validate(ret)


@router.post(
    "/{return_id}/inspect",
    response_model=ReturnResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect & Log Return Dispositions",
)
async def inspect_and_dispose_return(
    return_id: UUID,
    request: ReturnInspectRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ReturnResponse:
    """Inspect return and log disposition movements into final target inventory states."""
    logger.info("Calling POST /v1/returns/%s/inspect endpoint", return_id)
    ret = await return_controller.inspect_and_dispose_return(
        return_id, request.model_dump(), scope
    )
    return ReturnResponse.model_validate(ret)

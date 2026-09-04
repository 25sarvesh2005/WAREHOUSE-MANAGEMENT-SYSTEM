"""
FastAPI HTTP endpoints for customer/seller returns and inspection dispositions.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.logger import get_logger
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.return_request import (
    ReturnCreateRequest,
    ReturnInspectRequest,
    ReturnReceiveRequest,
)
from core.apis.schemas.responses.return_response import ReturnListResponse, ReturnResponse
from core.controllers.return_controller import return_controller

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/returns", tags=["Returns & Dispositions"])


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
    """Create a new expected return RMA or unidentified inbound return.

    Validates seller ownership and warehouse scope before creating the return record.
    """
    try:
        logger.info("Calling POST /v1/returns endpoint")
        ret = await return_controller.create_return(request.model_dump(), scope)
        return ReturnResponse.model_validate(ret)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/returns endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "",
    response_model=ReturnListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Customer / Seller Returns",
)
async def list_returns(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    q: str | None = Query(
        default=None,
        max_length=100,
        description="Case-insensitive return number, RMA, or tracking search",
    ),
    seller_id: UUID | None = Query(None, description="Filter by seller tenant UUID"),
    warehouse_id: UUID | None = Query(None, description="Filter by warehouse UUID"),
    status_val: str | None = Query(None, alias="status", description="Filter by return status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ReturnListResponse:
    """List returns with optional query filters.

    Supports text search across return number, RMA, or tracking number, alongside tenant and warehouse scoping.

    Args:
        scope: Security context containing accessible sellers and warehouses.
        q: Optional case-insensitive text search query.
        seller_id: Optional seller filter.
        warehouse_id: Optional warehouse filter.
        status_val: Optional return status filter.
        limit: Max pagination records.
        offset: Pagination offset.

    Returns:
        ReturnListResponse: Paginated returns and total count.

    Raises:
        HTTPException: 500 if an unexpected error occurs during query execution.
    """
    try:
        logger.info("Calling GET /v1/returns endpoint")
        normalized_q = q.strip() if q and q.strip() else None
        returns, total = await return_controller.list_returns(
            scope,
            q=normalized_q,
            seller_id=seller_id,
            warehouse_id=warehouse_id,
            status_val=status_val,
            limit=limit,
            offset=offset,
        )
        items = [ReturnResponse.model_validate(r) for r in returns]
        return ReturnListResponse(items=items, total=total, limit=limit, offset=offset)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/returns endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Retrieve single return details.

    Enforces seller and warehouse scope access before returning the record.
    """
    try:
        logger.info("Calling GET /v1/returns/%s endpoint", return_id)
        ret = await return_controller.get_return(return_id, scope)
        return ReturnResponse.model_validate(ret)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/returns/{return_id} endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Receive return parcel, placing stock strictly into RETURN_INSPECTION state.

    Posts a RETURN_RECEIVED inventory movement and transitions the return to IN_INSPECTION.
    """
    try:
        logger.info("Calling POST /v1/returns/%s/receive endpoint", return_id)
        ret = await return_controller.receive_return(return_id, request.model_dump(), scope)
        return ReturnResponse.model_validate(ret)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/returns/{return_id}/receive endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Inspect return and log disposition movements into final target inventory states.

    Routes return stock into AVAILABLE, DAMAGED, or QUARANTINE based on inspection outcome.
    """
    try:
        logger.info("Calling POST /v1/returns/%s/inspect endpoint", return_id)
        ret = await return_controller.inspect_and_dispose_return(
            return_id, request.model_dump(), scope
        )
        return ReturnResponse.model_validate(ret)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/returns/{return_id}/inspect endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )

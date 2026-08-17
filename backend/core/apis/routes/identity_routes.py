"""
FastAPI HTTP endpoints for authentication, user management, and tenant assignments.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.logger import get_logger
from common.rate_limit import login_rate_limiter, refresh_rate_limiter
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.identity_request import (
    LoginRequest,
    RefreshRequest,
    RegisterSellerRequest,
    SellerCreateRequest,
    SellerStatusUpdateRequest,
    UserCreateRequest,
    UserSellerAssignmentRequest,
    UserStatusUpdateRequest,
    UserWarehouseAssignmentRequest,
    WarehouseCreateRequest,
)
from core.apis.schemas.responses.identity_response import (
    AssignmentResponse,
    SellerResponse,
    TokenResponse,
    UserResponse,
    WarehouseResponse,
)
from core.controllers.identity_controller import identity_controller

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["Identity"])


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user",
    dependencies=[Depends(login_rate_limiter)],
)
async def login(request: LoginRequest) -> TokenResponse:
    """Authenticate a user and return a bearer token.

    Validates credentials, checks account status, and issues signed JWT access and refresh tokens.
    """
    try:
        logger.info("Calling POST /v1/auth/login endpoint")
        response = await identity_controller.login(request.model_dump(mode="json"))
        return TokenResponse(**response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/auth/login endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/auth/register-seller",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Public seller self-registration",
)
async def register_seller(request: RegisterSellerRequest) -> UserResponse:
    """Public self-registration endpoint for merchants/sellers.

    Creates a PENDING seller account awaiting administrator approval.
    """
    try:
        logger.info("Calling POST /v1/auth/register-seller endpoint")
        response = await identity_controller.register_seller_public(request.model_dump(mode="json"))
        return UserResponse(**response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/auth/register-seller endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate a refresh token",
    dependencies=[Depends(refresh_rate_limiter)],
)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    """Rotate a refresh token and return a new access and refresh token pair.

    Validates the refresh token, revokes it, and issues a fresh token pair.
    """
    try:
        logger.info("Calling POST /v1/auth/refresh endpoint")
        response = await identity_controller.refresh(request.model_dump(mode="json"))
        return TokenResponse(**response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/auth/refresh endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/auth/logout",
    status_code=status.HTTP_200_OK,
    summary="Log out the authenticated user",
)
async def logout(
    request: RefreshRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> dict:
    """Log out the authenticated user by revoking all refresh tokens.

    Invalidates the provided refresh token to prevent further session rotation.
    """
    try:
        logger.info("Calling POST /v1/auth/logout endpoint")
        await identity_controller.logout(scope, request.model_dump(mode="json"))
        return {"detail": "Logged out successfully"}
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/auth/logout endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/auth/me",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Read the authenticated JWT scope",
)
async def read_me(scope: Annotated[dict, Depends(get_warehouse_scope)]) -> dict:
    """Return the authenticated user's effective scope.

    Reflects the decoded JWT claims including role, seller_ids, and warehouse_ids.
    """
    try:
        logger.info("Calling GET /v1/auth/me endpoint")
        return scope
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/auth/me endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
)
async def create_user(
    request: UserCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> UserResponse:
    """Create a user account.

    Administrator-only endpoint to provision user accounts with a specific role.
    """
    try:
        logger.info("Calling POST /v1/users endpoint")
        response = await identity_controller.create_user(request.model_dump(mode="json"), scope)
        return UserResponse(**response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/users endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/users/{user_id}/approve",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve pending seller registration",
)
async def approve_seller(
    user_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> UserResponse:
    """Administrator or Manager endpoint to approve a pending seller account.

    Transitions the user status from PENDING to ACTIVE.
    """
    try:
        logger.info(f"Calling POST /v1/users/{user_id}/approve endpoint")
        response = await identity_controller.approve_seller(user_id, scope)
        return UserResponse(**response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/users/{user_id}/approve endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user account status",
)
async def update_user_status(
    user_id: UUID,
    request: UserStatusUpdateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> UserResponse:
    """Update the status of a user account.

    Allows administrators to activate, suspend, or deactivate any user account.
    """
    try:
        logger.info(f"Calling PATCH /v1/users/{user_id}/status endpoint")
        response = await identity_controller.update_user_status(user_id, request.status, scope)
        return UserResponse(**response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in PATCH /v1/users/{user_id}/status endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/users",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List users",
)
async def list_users(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[UserResponse]:
    """List user accounts for administrators.

    Returns paginated user records visible to the authenticated administrator.
    """
    try:
        logger.info("Calling GET /v1/users endpoint")
        response = await identity_controller.list_users(scope, limit=limit, offset=offset)
        return [UserResponse(**user) for user in response]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/users endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/sellers",
    response_model=SellerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a seller",
)
async def create_seller(
    request: SellerCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> SellerResponse:
    """Create a seller tenant.

    Provisions a new seller tenant and its associated user account.
    """
    try:
        logger.info("Calling POST /v1/sellers endpoint")
        response = await identity_controller.create_seller(request.model_dump(mode="json"), scope)
        return SellerResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/sellers endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.patch(
    "/sellers/{seller_id}/status",
    response_model=SellerResponse,
    status_code=status.HTTP_200_OK,
    summary="Update seller tenant status",
)
async def update_seller_status(
    seller_id: UUID,
    request: SellerStatusUpdateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> SellerResponse:
    """Update the business status of a seller tenant.

    Allows administrators to activate, suspend, or terminate a seller account.
    """
    try:
        logger.info(f"Calling PATCH /v1/sellers/{seller_id}/status endpoint")
        response = await identity_controller.update_seller_status(seller_id, request.status, scope)
        return SellerResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in PATCH /v1/sellers/{seller_id}/status endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/sellers",
    response_model=list[SellerResponse],
    status_code=status.HTTP_200_OK,
    summary="List sellers",
)
async def list_sellers(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[SellerResponse]:
    """List sellers visible to the requester.

    Scopes results to tenants the authenticated user is permitted to view.
    """
    try:
        logger.info("Calling GET /v1/sellers endpoint")
        response = await identity_controller.list_sellers(scope, limit=limit, offset=offset)
        return [SellerResponse.model_validate(seller) for seller in response]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/sellers endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/warehouses",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a warehouse",
)
async def create_warehouse(
    request: WarehouseCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> WarehouseResponse:
    """Create a warehouse facility.

    Administrator-only endpoint to provision a new physical warehouse location.
    """
    try:
        logger.info("Calling POST /v1/warehouses endpoint")
        response = await identity_controller.create_warehouse(
            request.model_dump(mode="json"),
            scope,
        )
        return WarehouseResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/warehouses endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/warehouses",
    response_model=list[WarehouseResponse],
    status_code=status.HTTP_200_OK,
    summary="List warehouses",
)
async def list_warehouses(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[WarehouseResponse]:
    """List warehouses visible to the requester.

    Scopes results to warehouses accessible by the authenticated requester.
    """
    try:
        logger.info("Calling GET /v1/warehouses endpoint")
        response = await identity_controller.list_warehouses(scope, limit=limit, offset=offset)
        return [WarehouseResponse.model_validate(warehouse) for warehouse in response]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/warehouses endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/assignments/sellers",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a user to a seller",
)
async def assign_user_to_seller(
    request: UserSellerAssignmentRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> AssignmentResponse:
    """Assign a user to a seller.

    Grants the user access to manage the specified seller tenant's operations.
    """
    try:
        logger.info("Calling POST /v1/assignments/sellers endpoint")
        response = await identity_controller.assign_user_to_seller(
            request.model_dump(mode="json"),
            scope,
        )
        return AssignmentResponse(**response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/assignments/sellers endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/assignments/warehouses",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a user to a warehouse",
)
async def assign_user_to_warehouse(
    request: UserWarehouseAssignmentRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> AssignmentResponse:
    """Assign a user to a warehouse.

    Grants the user access to operate within the specified warehouse facility.
    """
    try:
        logger.info("Calling POST /v1/assignments/warehouses endpoint")
        response = await identity_controller.assign_user_to_warehouse(
            request.model_dump(mode="json"),
            scope,
        )
        return AssignmentResponse(**response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/assignments/warehouses endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )

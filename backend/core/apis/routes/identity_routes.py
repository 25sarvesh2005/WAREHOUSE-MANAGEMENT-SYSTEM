"""
FastAPI HTTP endpoints for authentication, user management, and tenant assignments.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

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

router = APIRouter(prefix="/v1", tags=["Identity"])


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user",
    dependencies=[Depends(login_rate_limiter)],
)
async def login(request: LoginRequest) -> TokenResponse:
    """Authenticate a user and return a bearer token."""
    response = await identity_controller.login(request.model_dump(mode="json"))
    return TokenResponse(**response)


@router.post(
    "/auth/register-seller",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Public seller self-registration",
)
async def register_seller(request: RegisterSellerRequest) -> UserResponse:
    """Public self-registration endpoint for merchants/sellers."""
    response = await identity_controller.register_seller_public(request.model_dump(mode="json"))
    return UserResponse(**response)


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate a refresh token",
    dependencies=[Depends(refresh_rate_limiter)],
)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    """Rotate a refresh token and return a new access and refresh token pair."""
    response = await identity_controller.refresh(request.model_dump(mode="json"))
    return TokenResponse(**response)


@router.post(
    "/auth/logout",
    status_code=status.HTTP_200_OK,
    summary="Log out the authenticated user",
)
async def logout(
    request: RefreshRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> dict:
    """Log out the authenticated user by revoking all refresh tokens."""
    await identity_controller.logout(scope, request.model_dump(mode="json"))
    return {"detail": "Logged out successfully"}


@router.get(
    "/auth/me",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Read the authenticated JWT scope",
)
async def read_me(scope: Annotated[dict, Depends(get_warehouse_scope)]) -> dict:
    """Return the authenticated user's effective scope."""
    return scope


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
    """Create a user account."""
    response = await identity_controller.create_user(request.model_dump(mode="json"), scope)
    return UserResponse(**response)


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
    """Administrator or Manager endpoint to approve a pending seller account."""
    response = await identity_controller.approve_seller(user_id, scope)
    return UserResponse(**response)


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
    """Update the status of a user account."""
    response = await identity_controller.update_user_status(user_id, request.status, scope)
    return UserResponse(**response)


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
    """List user accounts for administrators."""
    response = await identity_controller.list_users(scope, limit=limit, offset=offset)
    return [UserResponse(**user) for user in response]


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
    """Create a seller tenant."""
    response = await identity_controller.create_seller(request.model_dump(mode="json"), scope)
    return SellerResponse.model_validate(response)


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
    """Update the business status of a seller tenant."""
    response = await identity_controller.update_seller_status(seller_id, request.status, scope)
    return SellerResponse.model_validate(response)


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
    """List sellers visible to the requester."""
    response = await identity_controller.list_sellers(scope, limit=limit, offset=offset)
    return [SellerResponse.model_validate(seller) for seller in response]


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
    """Create a warehouse facility."""
    response = await identity_controller.create_warehouse(
        request.model_dump(mode="json"),
        scope,
    )
    return WarehouseResponse.model_validate(response)


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
    """List warehouses visible to the requester."""
    response = await identity_controller.list_warehouses(scope, limit=limit, offset=offset)
    return [WarehouseResponse.model_validate(warehouse) for warehouse in response]


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
    """Assign a user to a seller."""
    response = await identity_controller.assign_user_to_seller(
        request.model_dump(mode="json"),
        scope,
    )
    return AssignmentResponse(**response)


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
    """Assign a user to a warehouse."""
    response = await identity_controller.assign_user_to_warehouse(
        request.model_dump(mode="json"),
        scope,
    )
    return AssignmentResponse(**response)


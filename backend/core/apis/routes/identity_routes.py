"""
--------------------------------------------------------------------------------
File        : core/apis/routes/identity_routes.py
Purpose     : Expose authentication and identity HTTP endpoints.

Responsibilities:
    - Validate request bodies and authentication dependencies.
    - Call identity controller methods without database access in routes.
    - Convert unexpected route errors into safe HTTP 500 responses.

Flow:
    HTTP request
        ->
    Route validates schema and scope
        ->
    Identity controller
        ->
    Response schema

Used By:
    - core/apis/api.py

Returns:
    APIRouter - Registered identity API routes.

Raises:
    HTTPException: For route-level and controller-raised API errors.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.auth import get_current_user
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
    """
    Authenticate a user and return a bearer token.

    The route validates the JSON body and delegates all credential checks and
    audit behavior to the identity controller.

    Args:
        request: Login request body.

    Returns:
        TokenResponse: Signed access token.

    Raises:
        HTTPException: For invalid credentials, inactive users, or server errors.
    """
    try:
        logger.info("Calling POST /v1/auth/login endpoint")
        response = await identity_controller.login(request.model_dump(mode="json"))
        return TokenResponse(**response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/auth/login endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/auth/register-seller",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Public seller self-registration",
)
async def register_seller(request: RegisterSellerRequest) -> UserResponse:
    """
    Public self-registration endpoint for merchants/sellers.
    The account enters PENDING_APPROVAL status until approved by an administrator.
    """
    try:
        logger.info("Calling POST /v1/auth/register-seller endpoint")
        response = await identity_controller.register_seller_public(request.model_dump(mode="json"))
        return UserResponse(**response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/auth/register-seller endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate a refresh token",
    dependencies=[Depends(refresh_rate_limiter)],
)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    """
    Rotate a refresh token and return a new access and refresh token pair.

    The submitted raw refresh token is validated, revoked, and replaced in a
    single atomic transaction. This endpoint does not require a Bearer header.

    Args:
        request: Refresh token request body.

    Returns:
        TokenResponse: New signed access and refresh tokens.

    Raises:
        HTTPException: For invalid, expired, or replayed tokens.
    """
    try:
        logger.info("Calling POST /v1/auth/refresh endpoint")
        response = await identity_controller.refresh(request.model_dump(mode="json"))
        return TokenResponse(**response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/auth/refresh endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/auth/logout",
    status_code=status.HTTP_200_OK,
    summary="Log out the authenticated user",
)
async def logout(
    request: RefreshRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> dict:
    """
    Log out the authenticated user by revoking all refresh tokens.

    The caller must supply a valid Bearer JWT in the Authorization header and
    the raw refresh token in the request body. All active refresh tokens for
    the user are revoked and the token_version is incremented.

    Args:
        request: Refresh token request body (token to revoke).
        scope: Authenticated warehouse scope dependency.

    Returns:
        dict: Confirmation payload with status message.

    Raises:
        HTTPException: For invalid credentials or server errors.
    """
    try:
        logger.info("Calling POST /v1/auth/logout endpoint")
        await identity_controller.logout(scope, request.model_dump(mode="json"))
        return {"detail": "Logged out successfully"}
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/auth/logout endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/auth/me",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Read the authenticated JWT scope",
)
async def read_me(scope: dict = Depends(get_warehouse_scope)) -> dict:
    """
    Return the authenticated user's effective scope.

    This endpoint helps the frontend initialize permission routing from the same
    JWT-derived scope the backend uses for access decisions.

    Args:
        scope: Authenticated warehouse scope dependency.

    Returns:
        dict: Effective requester scope.

    Raises:
        HTTPException: If authentication or scope validation fails.
    """
    try:
        logger.info("Calling GET /v1/auth/me endpoint")
        return scope
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/auth/me endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
)
async def create_user(
    request: UserCreateRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> UserResponse:
    """
    Create a user account.

    The route is protected and delegates administrator checks, password hashing,
    duplicate handling, and auditing to the controller.

    Args:
        request: User creation request body.
        scope: Authenticated warehouse scope dependency.

    Returns:
        UserResponse: Created user without sensitive fields.

    Raises:
        HTTPException: For permission, conflict, validation, or server errors.
    """
    try:
        logger.info("Calling POST /v1/users endpoint")
        response = await identity_controller.create_user(request.model_dump(mode="json"), scope)
        return UserResponse(**response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/users endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/users/{user_id}/approve",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve pending seller registration",
)
async def approve_seller(
    user_id: str,
    scope: dict = Depends(get_warehouse_scope),
) -> UserResponse:
    """
    Administrator or Manager endpoint to approve a pending seller account.
    """
    try:
        logger.info("Calling POST /v1/users/%s/approve endpoint", user_id)
        from uuid import UUID
        response = await identity_controller.approve_seller(UUID(user_id), scope)
        return UserResponse(**response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/users/%s/approve endpoint: %s", user_id, error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user account status",
)
async def update_user_status(
    user_id: str,
    request: UserStatusUpdateRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> UserResponse:
    """
    Update the status of a user account (e.g. ACTIVE, INACTIVE, SUSPENDED, PENDING_APPROVAL).
    """
    try:
        logger.info("Calling PATCH /v1/users/%s/status endpoint to %s", user_id, request.status)
        from uuid import UUID
        response = await identity_controller.update_user_status(UUID(user_id), request.status, scope)
        return UserResponse(**response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in PATCH /v1/users/%s/status endpoint: %s", user_id, error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/users",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List users",
)
async def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[UserResponse]:
    """
    List user accounts for administrators.

    Pagination is validated at the route and normalized again by the controller
    before querying the database.

    Args:
        limit: Maximum number of rows.
        offset: Row offset.
        scope: Authenticated warehouse scope dependency.

    Returns:
        list[UserResponse]: Public user records.

    Raises:
        HTTPException: For permission or server errors.
    """
    try:
        logger.info("Calling GET /v1/users endpoint")
        response = await identity_controller.list_users(scope, limit=limit, offset=offset)
        return [UserResponse(**user) for user in response]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/users endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/sellers",
    response_model=SellerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a seller",
)
async def create_seller(
    request: SellerCreateRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> SellerResponse:
    """
    Create a seller tenant.

    The controller enforces administrator-only creation and records an audit
    event in the same transaction as the seller row.

    Args:
        request: Seller creation request body.
        scope: Authenticated warehouse scope dependency.

    Returns:
        SellerResponse: Created seller record.

    Raises:
        HTTPException: For permission, conflict, validation, or server errors.
    """
    try:
        logger.info("Calling POST /v1/sellers endpoint")
        response = await identity_controller.create_seller(request.model_dump(mode="json"), scope)
        return SellerResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/sellers endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.patch(
    "/sellers/{seller_id}/status",
    response_model=SellerResponse,
    status_code=status.HTTP_200_OK,
    summary="Update seller tenant status",
)
async def update_seller_status(
    seller_id: str,
    request: SellerStatusUpdateRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> SellerResponse:
    """
    Update the business status of a seller tenant (e.g. ACTIVE, INACTIVE, SUSPENDED).
    """
    try:
        logger.info("Calling PATCH /v1/sellers/%s/status endpoint to %s", seller_id, request.status)
        from uuid import UUID
        response = await identity_controller.update_seller_status(UUID(seller_id), request.status, scope)
        return SellerResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in PATCH /v1/sellers/%s/status endpoint: %s", seller_id, error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/sellers",
    response_model=list[SellerResponse],
    status_code=status.HTTP_200_OK,
    summary="List sellers",
)
async def list_sellers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[SellerResponse]:
    """
    List sellers visible to the requester.

    Administrators receive all records and seller-scoped users receive only
    assigned seller records.

    Args:
        limit: Maximum number of rows.
        offset: Row offset.
        scope: Authenticated warehouse scope dependency.

    Returns:
        list[SellerResponse]: Visible seller records.

    Raises:
        HTTPException: For authentication, authorization, or server errors.
    """
    try:
        logger.info("Calling GET /v1/sellers endpoint")
        response = await identity_controller.list_sellers(scope, limit=limit, offset=offset)
        return [SellerResponse.model_validate(seller) for seller in response]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/sellers endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/warehouses",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a warehouse",
)
async def create_warehouse(
    request: WarehouseCreateRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> WarehouseResponse:
    """
    Create a warehouse facility.

    Warehouse creation is administrator-only and records an audited master-data
    change through the identity controller.

    Args:
        request: Warehouse creation request body.
        scope: Authenticated warehouse scope dependency.

    Returns:
        WarehouseResponse: Created warehouse record.

    Raises:
        HTTPException: For permission, conflict, validation, or server errors.
    """
    try:
        logger.info("Calling POST /v1/warehouses endpoint")
        response = await identity_controller.create_warehouse(
            request.model_dump(mode="json"),
            scope,
        )
        return WarehouseResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/warehouses endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/warehouses",
    response_model=list[WarehouseResponse],
    status_code=status.HTTP_200_OK,
    summary="List warehouses",
)
async def list_warehouses(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[WarehouseResponse]:
    """
    List warehouses visible to the requester.

    Administrators receive all warehouses and worker roles receive only assigned
    warehouse records.

    Args:
        limit: Maximum number of rows.
        offset: Row offset.
        scope: Authenticated warehouse scope dependency.

    Returns:
        list[WarehouseResponse]: Visible warehouse records.

    Raises:
        HTTPException: For authentication, authorization, or server errors.
    """
    try:
        logger.info("Calling GET /v1/warehouses endpoint")
        response = await identity_controller.list_warehouses(scope, limit=limit, offset=offset)
        return [WarehouseResponse.model_validate(warehouse) for warehouse in response]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/warehouses endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/assignments/sellers",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a user to a seller",
)
async def assign_user_to_seller(
    request: UserSellerAssignmentRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AssignmentResponse:
    """
    Assign a user to a seller.

    This route is administrative and supports the seller tenant scope used by
    seller portal and cross-seller access controls.

    Args:
        request: Seller assignment request body.
        scope: Authenticated warehouse scope dependency.

    Returns:
        AssignmentResponse: Created assignment record.

    Raises:
        HTTPException: For permission, conflict, validation, or server errors.
    """
    try:
        logger.info("Calling POST /v1/assignments/sellers endpoint")
        response = await identity_controller.assign_user_to_seller(
            request.model_dump(mode="json"),
            scope,
        )
        return AssignmentResponse(**response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/assignments/sellers endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/assignments/warehouses",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a user to a warehouse",
)
async def assign_user_to_warehouse(
    request: UserWarehouseAssignmentRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AssignmentResponse:
    """
    Assign a user to a warehouse.

    This route is administrative and supports warehouse-scoped operational
    access for receivers, pickers, packers, and managers.

    Args:
        request: Warehouse assignment request body.
        scope: Authenticated warehouse scope dependency.

    Returns:
        AssignmentResponse: Created assignment record.

    Raises:
        HTTPException: For permission, conflict, validation, or server errors.
    """
    try:
        logger.info("Calling POST /v1/assignments/warehouses endpoint")
        response = await identity_controller.assign_user_to_warehouse(
            request.model_dump(mode="json"),
            scope,
        )
        return AssignmentResponse(**response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/assignments/warehouses endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error

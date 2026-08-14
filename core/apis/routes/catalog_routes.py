"""
--------------------------------------------------------------------------------
File        : core/apis/routes/catalog_routes.py
Purpose     : Expose catalog, warehouse location, and seller policy endpoints.

Responsibilities:
    - Validate catalog request schemas and authenticated scope dependencies.
    - Call catalog controller methods without database access in routes.
    - Convert unexpected route failures into safe HTTP 500 responses.

Flow:
    HTTP request
        ->
    Route validates schema and scope
        ->
    Catalog controller
        ->
    Response schema

Used By:
    - core/apis/api.py

Returns:
    APIRouter - Registered catalog API routes.

Raises:
    HTTPException: For route-level and controller-raised API errors.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.logger import get_logger
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.catalog_request import (
    ProductCreateRequest,
    ProductIdentifierCreateRequest,
    SellerOrderPolicyCreateRequest,
    WarehouseLocationCreateRequest,
)
from core.apis.schemas.responses.catalog_response import (
    ProductIdentifierResponse,
    ProductResponse,
    SellerOrderPolicyResponse,
    WarehouseLocationResponse,
)
from core.controllers.catalog_controller import catalog_controller

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["Catalog"])


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
async def create_product(
    request: ProductCreateRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> ProductResponse:
    """
    Create a seller product/SKU record.

    The route validates transport shape and delegates permission, seller
    existence, duplicate handling, and audit behavior to the controller.

    Args:
        request: Product creation request body.
        scope: Authenticated warehouse scope dependency.

    Returns:
        ProductResponse: Created product record.

    Raises:
        HTTPException: For permission, conflict, validation, or server errors.
    """
    try:
        logger.info("Calling POST /v1/products endpoint")
        response = await catalog_controller.create_product(request.model_dump(mode="json"), scope)
        return ProductResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/products endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/products",
    response_model=list[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="List products",
)
async def list_products(
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[ProductResponse]:
    """
    List products visible to the requester.

    Seller-scoped users can only see their seller's product catalog while
    administrators may list all products.

    Args:
        seller_id: Optional seller UUID filter.
        limit: Maximum number of rows.
        offset: Row offset.
        scope: Authenticated warehouse scope dependency.

    Returns:
        list[ProductResponse]: Visible product records.

    Raises:
        HTTPException: For access denial or server errors.
    """
    try:
        logger.info("Calling GET /v1/products endpoint")
        response = await catalog_controller.list_products(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [ProductResponse.model_validate(product) for product in response]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/products endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/product-identifiers",
    response_model=ProductIdentifierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product identifier",
)
async def create_product_identifier(
    request: ProductIdentifierCreateRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> ProductIdentifierResponse:
    """
    Create an alternate identifier for a product.

    The controller verifies administrative permission and product existence
    before persisting the identifier.

    Args:
        request: Product identifier creation request body.
        scope: Authenticated warehouse scope dependency.

    Returns:
        ProductIdentifierResponse: Created identifier record.

    Raises:
        HTTPException: For permission, not-found, conflict, validation, or server errors.
    """
    try:
        logger.info("Calling POST /v1/product-identifiers endpoint")
        response = await catalog_controller.create_product_identifier(
            request.model_dump(mode="json"),
            scope,
        )
        return ProductIdentifierResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/product-identifiers endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/warehouse-locations",
    response_model=WarehouseLocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a warehouse location",
)
async def create_warehouse_location(
    request: WarehouseLocationCreateRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> WarehouseLocationResponse:
    """
    Create a warehouse location.

    Administrators and assigned warehouse managers can create location records
    while the route remains free of database access.

    Args:
        request: Warehouse location creation request body.
        scope: Authenticated warehouse scope dependency.

    Returns:
        WarehouseLocationResponse: Created location record.

    Raises:
        HTTPException: For permission, not-found, conflict, validation, or server errors.
    """
    try:
        logger.info("Calling POST /v1/warehouse-locations endpoint")
        response = await catalog_controller.create_warehouse_location(
            request.model_dump(mode="json"),
            scope,
        )
        return WarehouseLocationResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/warehouse-locations endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/warehouse-locations",
    response_model=list[WarehouseLocationResponse],
    status_code=status.HTTP_200_OK,
    summary="List warehouse locations",
)
async def list_warehouse_locations(
    warehouse_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[WarehouseLocationResponse]:
    """
    List warehouse locations visible to the requester.

    Non-admin warehouse workers are restricted to assigned warehouses while
    administrators may list all warehouse locations.

    Args:
        warehouse_id: Optional warehouse UUID filter.
        limit: Maximum number of rows.
        offset: Row offset.
        scope: Authenticated warehouse scope dependency.

    Returns:
        list[WarehouseLocationResponse]: Visible location records.

    Raises:
        HTTPException: For access denial or server errors.
    """
    try:
        logger.info("Calling GET /v1/warehouse-locations endpoint")
        response = await catalog_controller.list_warehouse_locations(
            scope,
            warehouse_id=warehouse_id,
            limit=limit,
            offset=offset,
        )
        return [WarehouseLocationResponse.model_validate(location) for location in response]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/warehouse-locations endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/seller-order-policies",
    response_model=SellerOrderPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a seller order policy",
)
async def create_seller_order_policy(
    request: SellerOrderPolicyCreateRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> SellerOrderPolicyResponse:
    """
    Create a seller order policy version.

    Policy values must be explicitly supplied by business owners and the
    controller audits the resulting policy version.

    Args:
        request: Seller policy creation request body.
        scope: Authenticated warehouse scope dependency.

    Returns:
        SellerOrderPolicyResponse: Created policy record.

    Raises:
        HTTPException: For permission, not-found, conflict, validation, or server errors.
    """
    try:
        logger.info("Calling POST /v1/seller-order-policies endpoint")
        response = await catalog_controller.create_seller_order_policy(
            request.model_dump(mode="json"),
            scope,
        )
        return SellerOrderPolicyResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/seller-order-policies endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/seller-order-policies",
    response_model=list[SellerOrderPolicyResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller order policies",
)
async def list_seller_order_policies(
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[SellerOrderPolicyResponse]:
    """
    List seller order policies visible to the requester.

    Seller-scoped users can inspect only their assigned policies while
    administrators can inspect all policy versions.

    Args:
        seller_id: Optional seller UUID filter.
        limit: Maximum number of rows.
        offset: Row offset.
        scope: Authenticated warehouse scope dependency.

    Returns:
        list[SellerOrderPolicyResponse]: Visible policy records.

    Raises:
        HTTPException: For access denial or server errors.
    """
    try:
        logger.info("Calling GET /v1/seller-order-policies endpoint")
        response = await catalog_controller.list_seller_order_policies(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [SellerOrderPolicyResponse.model_validate(policy) for policy in response]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/seller-order-policies endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error

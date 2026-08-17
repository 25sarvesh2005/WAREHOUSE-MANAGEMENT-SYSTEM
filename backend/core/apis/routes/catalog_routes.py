"""
FastAPI HTTP endpoints for catalog, warehouse locations, and seller policies.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

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

router = APIRouter(prefix="/v1", tags=["Catalog"])


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
async def create_product(
    request: ProductCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ProductResponse:
    """Create a seller product/SKU record."""
    response = await catalog_controller.create_product(request.model_dump(mode="json"), scope)
    return ProductResponse.model_validate(response)


@router.get(
    "/products",
    response_model=list[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="List products",
)
async def list_products(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ProductResponse]:
    """List products visible to the requester."""
    response = await catalog_controller.list_products(
        scope,
        seller_id=seller_id,
        limit=limit,
        offset=offset,
    )
    return [ProductResponse.model_validate(product) for product in response]


@router.post(
    "/product-identifiers",
    response_model=ProductIdentifierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product identifier",
)
async def create_product_identifier(
    request: ProductIdentifierCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ProductIdentifierResponse:
    """Create an alternate identifier for a product."""
    response = await catalog_controller.create_product_identifier(
        request.model_dump(mode="json"),
        scope,
    )
    return ProductIdentifierResponse.model_validate(response)


@router.post(
    "/warehouse-locations",
    response_model=WarehouseLocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a warehouse location",
)
async def create_warehouse_location(
    request: WarehouseLocationCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> WarehouseLocationResponse:
    """Create a warehouse location."""
    response = await catalog_controller.create_warehouse_location(
        request.model_dump(mode="json"),
        scope,
    )
    return WarehouseLocationResponse.model_validate(response)


@router.get(
    "/warehouse-locations",
    response_model=list[WarehouseLocationResponse],
    status_code=status.HTTP_200_OK,
    summary="List warehouse locations",
)
async def list_warehouse_locations(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    warehouse_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[WarehouseLocationResponse]:
    """List warehouse locations visible to the requester."""
    response = await catalog_controller.list_warehouse_locations(
        scope,
        warehouse_id=warehouse_id,
        limit=limit,
        offset=offset,
    )
    return [WarehouseLocationResponse.model_validate(location) for location in response]


@router.post(
    "/seller-order-policies",
    response_model=SellerOrderPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a seller order policy",
)
async def create_seller_order_policy(
    request: SellerOrderPolicyCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> SellerOrderPolicyResponse:
    """Create a seller order policy version."""
    response = await catalog_controller.create_seller_order_policy(
        request.model_dump(mode="json"),
        scope,
    )
    return SellerOrderPolicyResponse.model_validate(response)


@router.get(
    "/seller-order-policies",
    response_model=list[SellerOrderPolicyResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller order policies",
)
async def list_seller_order_policies(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[SellerOrderPolicyResponse]:
    """List seller order policies visible to the requester."""
    response = await catalog_controller.list_seller_order_policies(
        scope,
        seller_id=seller_id,
        limit=limit,
        offset=offset,
    )
    return [SellerOrderPolicyResponse.model_validate(policy) for policy in response]


"""
FastAPI HTTP endpoints for catalog, warehouse locations, and seller policies.
"""

from __future__ import annotations

from typing import Annotated
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
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ProductResponse:
    """Create a seller product/SKU record.

    Validates seller ownership and uniqueness before persisting the product.
    """
    try:
        logger.info("Calling POST /v1/products endpoint")
        response = await catalog_controller.create_product(request.model_dump(mode="json"), scope)
        return ProductResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/products endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """List products visible to the requester.

    Automatically scopes results to the authenticated requester's seller tenants.
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
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/products endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Create an alternate identifier for a product.

    Attaches a barcode, SKU alias, or external reference to an existing product.
    """
    try:
        logger.info("Calling POST /v1/product-identifiers endpoint")
        response = await catalog_controller.create_product_identifier(
            request.model_dump(mode="json"),
            scope,
        )
        return ProductIdentifierResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/product-identifiers endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Create a warehouse location.

    Defines a physical storage slot (bin, aisle, zone) within a warehouse facility.
    """
    try:
        logger.info("Calling POST /v1/warehouse-locations endpoint")
        response = await catalog_controller.create_warehouse_location(
            request.model_dump(mode="json"),
            scope,
        )
        return WarehouseLocationResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/warehouse-locations endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """List warehouse locations visible to the requester.

    Scopes results to warehouses accessible by the authenticated requester.
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
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/warehouse-locations endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Create a seller order policy version.

    Defines fulfilment rules such as allocation strategy, backorder, and reservation expiry.
    """
    try:
        logger.info("Calling POST /v1/seller-order-policies endpoint")
        response = await catalog_controller.create_seller_order_policy(
            request.model_dump(mode="json"),
            scope,
        )
        return SellerOrderPolicyResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/seller-order-policies endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """List seller order policies visible to the requester.

    Scopes results to the authenticated requester's accessible seller tenants.
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
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/seller-order-policies endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )

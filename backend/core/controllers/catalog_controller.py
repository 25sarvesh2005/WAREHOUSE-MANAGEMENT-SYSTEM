"""
Catalog Controller.

Orchestrates catalog products, warehouse locations, and seller order policies.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from common.logger import get_logger
from common.pagination import normalize_pagination
from common.warehouse_scope import assert_seller_access, assert_warehouse_access, require_roles
from core.constants import AuditActionType, BusinessStatus, UserRole
from core.cruds import audit_crud, catalog_crud, identity_crud
from core.database.database import transaction_session
from core.models.catalog_model import (
    Product,
    ProductIdentifier,
    SellerOrderPolicy,
    WarehouseLocation,
)

logger = get_logger(__name__)


class CatalogController:
    """Controller for catalog and policy workflows."""

    async def create_product(
        self,
        product_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> Product:
        """
        Create a product/SKU master-data record.

        Product creation is administrative in the first release slice and is
        audited with seller and SKU metadata.

        Args:
            product_data: Validated product creation payload.
            scope: Authenticated requester scope.

        Returns:
            Product: Persisted product model.

        Raises:
            HTTPException: If unauthorized, seller is missing, or SKU conflicts.
        """
        logger.info("Executing CatalogController.create_product")
        require_roles(scope, {UserRole.ADMINISTRATOR})
        actor_id = UUID(str(scope["user_id"]))
        seller_id = UUID(str(product_data["seller_id"]))
        try:
            async with transaction_session() as session:
                seller = await identity_crud.get_seller_by_id(session, seller_id)
                if seller is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Seller not found",
                    )

                product = Product(
                    seller_id=seller_id,
                    sku=str(product_data["sku"]).strip().upper(),
                    name=str(product_data["name"]).strip(),
                    description=product_data.get("description"),
                    unit_of_measure=str(product_data.get("unit_of_measure", "EA")).strip().upper(),
                    weight=product_data.get("weight"),
                    length=product_data.get("length"),
                    width=product_data.get("width"),
                    height=product_data.get("height"),
                    status=str(product_data.get("status", BusinessStatus.ACTIVE.value)),
                )
                await catalog_crud.create_product(session, product)
                await audit_crud.create_audit_event(
                    session,
                    actor_user_id=actor_id,
                    action_type=AuditActionType.PRODUCT_CREATED.value,
                    source_record_type="products",
                    source_record_id=product.id,
                    metadata_json={"seller_id": str(seller_id), "sku": product.sku},
                )
                logger.info("Product created successfully %s", product.id)
                return product
        except IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product already exists",
            ) from error

    async def list_products(
        self,
        scope: dict[str, Any],
        *,
        seller_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[Product]:
        """
        List products visible to the requester.

        Seller users are restricted to their assigned seller IDs while
        administrators may request any seller or all sellers.

        Args:
            scope: Authenticated requester scope.
            seller_id: Optional seller UUID filter.
            limit: Requested page size.
            offset: Requested offset.

        Returns:
            list[Product]: Visible product records.

        Raises:
            HTTPException: If seller-scoped access is denied.
        """
        logger.info("Executing CatalogController.list_products")
        normalized_limit, normalized_offset = normalize_pagination(limit, offset)
        if seller_id is not None:
            assert_seller_access(scope, str(seller_id))
        elif scope.get("role") != UserRole.ADMINISTRATOR.value and scope.get("seller_ids"):
            seller_id = UUID(str(scope["seller_ids"][0]))

        async with transaction_session() as session:
            products = await catalog_crud.list_products(
                session,
                seller_id=seller_id,
                limit=normalized_limit,
                offset=normalized_offset,
            )
            if scope.get("role") == UserRole.ADMINISTRATOR.value:
                return products
            allowed = {str(allowed_id) for allowed_id in scope.get("seller_ids", [])}
            return [product for product in products if str(product.seller_id) in allowed]

    async def create_product_identifier(
        self,
        identifier_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> ProductIdentifier:
        """
        Create an alternate identifier for a product.

        Identifier creation is administrative and the product must exist before
        the identifier can be persisted.

        Args:
            identifier_data: Validated identifier payload.
            scope: Authenticated requester scope.

        Returns:
            ProductIdentifier: Persisted identifier model.

        Raises:
            HTTPException: If unauthorized, product is missing, or identifier conflicts.
        """
        logger.info("Executing CatalogController.create_product_identifier")
        require_roles(scope, {UserRole.ADMINISTRATOR})
        product_id = UUID(str(identifier_data["product_id"]))
        try:
            async with transaction_session() as session:
                product = await catalog_crud.get_product_by_id(session, product_id)
                if product is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Product not found",
                    )

                identifier = ProductIdentifier(
                    product_id=product_id,
                    identifier_type=str(identifier_data["identifier_type"]),
                    identifier_value=str(identifier_data["identifier_value"]).strip().upper(),
                    is_primary=bool(identifier_data.get("is_primary", False)),
                )
                await catalog_crud.create_product_identifier(session, identifier)
                logger.info("Product identifier created successfully %s", identifier.id)
                return identifier
        except IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product identifier already exists",
            ) from error

    async def create_warehouse_location(
        self,
        location_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> WarehouseLocation:
        """
        Create a warehouse location record.

        Administrators may create locations for any warehouse and warehouse
        managers may create locations only for assigned warehouses.

        Args:
            location_data: Validated location payload.
            scope: Authenticated requester scope.

        Returns:
            WarehouseLocation: Persisted location model.

        Raises:
            HTTPException: If unauthorized, warehouse is missing, or code conflicts.
        """
        logger.info("Executing CatalogController.create_warehouse_location")
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        warehouse_id = UUID(str(location_data["warehouse_id"]))
        assert_warehouse_access(scope, str(warehouse_id))
        try:
            async with transaction_session() as session:
                warehouse = await identity_crud.get_warehouse_by_id(session, warehouse_id)
                if warehouse is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Warehouse not found",
                    )
                location = WarehouseLocation(
                    warehouse_id=warehouse_id,
                    code=str(location_data["code"]).strip().upper(),
                    location_type=str(location_data["location_type"]),
                    status=str(location_data.get("status", BusinessStatus.ACTIVE.value)),
                )
                await catalog_crud.create_warehouse_location(session, location)
                logger.info("Warehouse location created successfully %s", location.id)
                return location
        except IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Warehouse location already exists",
            ) from error

    async def list_warehouse_locations(
        self,
        scope: dict[str, Any],
        *,
        warehouse_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[WarehouseLocation]:
        """
        List warehouse locations visible to the requester.

        Non-admin workers are limited to assigned warehouses; administrators may
        request any warehouse or all warehouses.

        Args:
            scope: Authenticated requester scope.
            warehouse_id: Optional warehouse UUID filter.
            limit: Requested page size.
            offset: Requested offset.

        Returns:
            list[WarehouseLocation]: Visible location records.

        Raises:
            HTTPException: If warehouse-scoped access is denied.
        """
        logger.info("Executing CatalogController.list_warehouse_locations")
        normalized_limit, normalized_offset = normalize_pagination(limit, offset)
        if warehouse_id is not None:
            assert_warehouse_access(scope, str(warehouse_id))
        elif scope.get("role") != UserRole.ADMINISTRATOR.value and scope.get("warehouse_ids"):
            warehouse_id = UUID(str(scope["warehouse_ids"][0]))

        async with transaction_session() as session:
            locations = await catalog_crud.list_warehouse_locations(
                session,
                warehouse_id=warehouse_id,
                limit=normalized_limit,
                offset=normalized_offset,
            )
            if scope.get("role") == UserRole.ADMINISTRATOR.value:
                return locations
            allowed = {str(allowed_id) for allowed_id in scope.get("warehouse_ids", [])}
            return [location for location in locations if str(location.warehouse_id) in allowed]

    async def create_seller_order_policy(
        self,
        policy_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> SellerOrderPolicy:
        """
        Create a seller order policy version.

        Policy values must be explicitly supplied by the business owner; the
        platform does not invent backorder, partial, or expiry behavior.

        Args:
            policy_data: Validated seller policy payload.
            scope: Authenticated requester scope.

        Returns:
            SellerOrderPolicy: Persisted policy model.

        Raises:
            HTTPException: If unauthorized, seller is missing, or persistence fails.
        """
        logger.info("Executing CatalogController.create_seller_order_policy")
        require_roles(scope, {UserRole.ADMINISTRATOR})
        actor_id = UUID(str(scope["user_id"]))
        seller_id = UUID(str(policy_data["seller_id"]))
        try:
            async with transaction_session() as session:
                seller = await identity_crud.get_seller_by_id(session, seller_id)
                if seller is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Seller not found",
                    )
                policy = SellerOrderPolicy(
                    seller_id=seller_id,
                    allow_backorder=bool(policy_data["allow_backorder"]),
                    allow_partial_fulfillment=bool(policy_data["allow_partial_fulfillment"]),
                    reservation_expiry_minutes=int(policy_data["reservation_expiry_minutes"]),
                    allocation_strategy=str(policy_data["allocation_strategy"]),
                    cancellation_policy=policy_data.get("cancellation_policy"),
                )
                await catalog_crud.create_seller_order_policy(session, policy)
                await audit_crud.create_audit_event(
                    session,
                    actor_user_id=actor_id,
                    action_type=AuditActionType.POLICY_CREATED.value,
                    source_record_type="seller_order_policies",
                    source_record_id=policy.id,
                    metadata_json={"seller_id": str(seller_id), "version": policy.version},
                )
                logger.info("Seller order policy created successfully %s", policy.id)
                return policy
        except IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Seller policy conflict",
            ) from error

    async def list_seller_order_policies(
        self,
        scope: dict[str, Any],
        *,
        seller_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[SellerOrderPolicy]:
        """
        List seller policy versions visible to the requester.

        Seller users can only see policies for assigned sellers while
        administrators may inspect every seller policy.

        Args:
            scope: Authenticated requester scope.
            seller_id: Optional seller UUID filter.
            limit: Requested page size.
            offset: Requested offset.

        Returns:
            list[SellerOrderPolicy]: Visible policy records.

        Raises:
            HTTPException: If seller-scoped access is denied.
        """
        logger.info("Executing CatalogController.list_seller_order_policies")
        normalized_limit, normalized_offset = normalize_pagination(limit, offset)
        if seller_id is not None:
            assert_seller_access(scope, str(seller_id))
        elif scope.get("role") != UserRole.ADMINISTRATOR.value and scope.get("seller_ids"):
            seller_id = UUID(str(scope["seller_ids"][0]))

        async with transaction_session() as session:
            policies = await catalog_crud.list_seller_order_policies(
                session,
                seller_id=seller_id,
                limit=normalized_limit,
                offset=normalized_offset,
            )
            if scope.get("role") == UserRole.ADMINISTRATOR.value:
                return policies
            allowed = {str(allowed_id) for allowed_id in scope.get("seller_ids", [])}
            return [policy for policy in policies if str(policy.seller_id) in allowed]


catalog_controller = CatalogController()

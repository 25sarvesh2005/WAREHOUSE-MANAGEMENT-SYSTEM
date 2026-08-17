"""
Seller Portal Controller.

Enforces seller scope isolation across inventory, orders, receipts, shipments, returns, and transfers.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from common.logger import get_logger
from common.warehouse_scope import assert_seller_access, require_roles
from core.constants import UserRole
from core.cruds import (
    fulfillment_crud,
    inventory_crud,
    order_crud,
    receiving_crud,
    return_crud,
    transfer_crud,
)
from core.database.database import transaction_session

logger = get_logger(__name__)


class SellerPortalController:
    """Controller enforcing seller-scoped access control across operational entities."""

    def _resolve_seller_ids(
        self,
        scope: dict[str, Any],
        seller_id_param: UUID | None,
    ) -> list[UUID] | None:
        """
        Resolve the seller filter from authenticated role scope.

        Args:
            scope: Authenticated requester scope.
            seller_id_param: Optional seller filter supplied by an administrator or seller.

        Returns:
            list[UUID] | None: Seller IDs to apply, or None for administrator-wide reads.

        Raises:
            HTTPException: If the seller user has no matching seller scope.
        """
        role = scope.get("role")
        if role == UserRole.SELLER.value:
            scoped_ids = [UUID(str(value)) for value in scope.get("seller_ids", [])]
            if not scoped_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No seller scope assigned",
                )
            if seller_id_param is not None:
                assert_seller_access(scope, str(seller_id_param))
                return [seller_id_param]
            return scoped_ids

        if seller_id_param is not None:
            assert_seller_access(scope, str(seller_id_param))
            return [seller_id_param]

        return None

    async def list_seller_inventory(
        self,
        scope: dict[str, Any],
        seller_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Any]:
        """List inventory balance records scoped strictly to seller."""
        require_roles(scope, {UserRole.SELLER, UserRole.ADMINISTRATOR})
        seller_ids = self._resolve_seller_ids(scope, seller_id)

        async with transaction_session() as session:
            balances = await inventory_crud.list_balances(
                session,
                seller_ids=seller_ids,
                limit=limit,
                offset=offset,
            )
            return list(balances)

    async def list_seller_orders(
        self,
        scope: dict[str, Any],
        seller_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Any]:
        """List customer orders scoped strictly to seller."""
        require_roles(scope, {UserRole.SELLER, UserRole.ADMINISTRATOR})
        seller_ids = self._resolve_seller_ids(scope, seller_id)

        async with transaction_session() as session:
            orders = await order_crud.list_orders(
                session,
                seller_ids=seller_ids,
                limit=limit,
                offset=offset,
            )
            return list(orders)

    async def list_seller_receipts(
        self,
        scope: dict[str, Any],
        seller_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Any]:
        """List inbound receiving receipts scoped strictly to seller."""
        require_roles(scope, {UserRole.SELLER, UserRole.ADMINISTRATOR})
        seller_ids = self._resolve_seller_ids(scope, seller_id)

        async with transaction_session() as session:
            receipts = await receiving_crud.list_receipts(
                session,
                seller_ids=seller_ids,
                limit=limit,
                offset=offset,
            )
            return list(receipts)

    async def list_seller_shipments(
        self,
        scope: dict[str, Any],
        seller_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Any]:
        """List outbound order shipments scoped strictly to seller."""
        require_roles(scope, {UserRole.SELLER, UserRole.ADMINISTRATOR})
        seller_ids = self._resolve_seller_ids(scope, seller_id)

        async with transaction_session() as session:
            shipments = await fulfillment_crud.list_shipments(
                session,
                seller_ids=seller_ids,
                limit=limit,
                offset=offset,
            )
            return list(shipments)

    async def list_seller_returns(
        self,
        scope: dict[str, Any],
        seller_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Any]:
        """List customer returns scoped strictly to seller."""
        require_roles(scope, {UserRole.SELLER, UserRole.ADMINISTRATOR})
        seller_ids = self._resolve_seller_ids(scope, seller_id)

        async with transaction_session() as session:
            returns, _ = await return_crud.list_returns(
                session,
                seller_ids=seller_ids,
                limit=limit,
                offset=offset,
            )
            return list(returns)

    async def list_seller_transfers(
        self,
        scope: dict[str, Any],
        seller_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Any]:
        """List stock transfers scoped strictly to seller."""
        require_roles(scope, {UserRole.SELLER, UserRole.ADMINISTRATOR})
        seller_ids = self._resolve_seller_ids(scope, seller_id)

        async with transaction_session() as session:
            transfers, _ = await transfer_crud.list_transfers(
                session,
                seller_ids=seller_ids,
                limit=limit,
                offset=offset,
            )
            return list(transfers)


seller_portal_controller = SellerPortalController()

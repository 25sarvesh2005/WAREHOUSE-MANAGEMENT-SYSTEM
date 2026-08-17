"""
Permission scope and access control assertions for seller and warehouse tenancies.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status

from common.auth import get_current_user
from common.logger import get_logger
from core.constants import UserRole

logger = get_logger(__name__)


def _as_string_list(value: object) -> list[str]:
    """
    Convert a JWT claim value to a list of strings.

    This helper tolerates missing claims and prevents malformed scope values from
    leaking into controller checks.

    Args:
        value: Raw JWT claim value.

    Returns:
        list[str]: Normalized string values.

    Raises:
        None.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


async def get_warehouse_scope(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    FastAPI dependency returning authenticated role and assignment scope.

    Seller, receiver, picker/packer, and manager roles must carry their scoped
    assignment IDs in the JWT; administrators may be globally scoped.

    Args:
        current_user: JWT payload from get_current_user().

    Returns:
        dict[str, Any]: User ID, role, seller IDs, and warehouse IDs.

    Raises:
        HTTPException: If a scoped role has no matching assignment.
    """
    role = str(current_user.get("role", ""))
    seller_ids = _as_string_list(current_user.get("seller_ids"))
    warehouse_ids = _as_string_list(current_user.get("warehouse_ids"))

    if role == UserRole.SELLER.value and not seller_ids:
        logger.warning("Seller token missing seller scope")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seller scope required")

    if (
        role
        in {
            UserRole.RECEIVER.value,
            UserRole.PICKER_PACKER.value,
            UserRole.WAREHOUSE_MANAGER.value,
        }
        and not warehouse_ids
    ):
        logger.warning("Warehouse worker token missing warehouse scope")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Warehouse scope required",
        )

    return {
        "user_id": str(current_user["user_id"]),
        "email": str(current_user.get("email", "")),
        "name": str(current_user.get("name", "")),
        "role": role,
        "seller_ids": seller_ids,
        "warehouse_ids": warehouse_ids,
        "token_version": int(current_user.get("token_version", 0)),
    }


def require_roles(scope: dict[str, Any], allowed_roles: set[UserRole]) -> None:
    """
    Require the authenticated scope to contain one of the allowed roles.

    Controllers call this helper before privileged administrative or warehouse
    workflows to keep permission failures consistent.

    Args:
        scope: Effective authenticated scope.
        allowed_roles: Roles permitted for the operation.

    Returns:
        None.

    Raises:
        HTTPException: If the role is not allowed.
    """
    role = str(scope.get("role", ""))
    allowed_values = {allowed_role.value for allowed_role in allowed_roles}
    if role not in allowed_values:
        logger.warning("Role %s denied; required one of %s", role, sorted(allowed_values))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def assert_seller_access(scope: dict[str, Any], seller_id: str | UUID) -> None:
    """
    Require access to a seller unless the user is an administrator.

    Seller-scoped queries must always derive allowed seller IDs from JWT scope
    rather than trusting request body ownership.

    Args:
        scope: Effective authenticated scope.
        seller_id: Seller ID being accessed (str or UUID).

    Returns:
        None.

    Raises:
        HTTPException: If seller access is denied.
    """
    if scope.get("role") == UserRole.ADMINISTRATOR.value:
        return
    normalized_id = str(seller_id)
    if normalized_id not in set(scope.get("seller_ids", [])):
        logger.warning("User %s denied seller %s", scope.get("user_id"), normalized_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def assert_warehouse_access(scope: dict[str, Any], warehouse_id: str | UUID) -> None:
    """
    Require access to a warehouse unless the user is an administrator.

    Warehouse-scoped workflows use assignment IDs from the JWT, preserving the
    tenancy and warehouse isolation rule.

    Args:
        scope: Effective authenticated scope.
        warehouse_id: Warehouse ID being accessed (str or UUID).

    Returns:
        None.

    Raises:
        HTTPException: If warehouse access is denied.
    """
    if scope.get("role") == UserRole.ADMINISTRATOR.value:
        return
    normalized_id = str(warehouse_id)
    if normalized_id not in set(scope.get("warehouse_ids", [])):
        logger.warning("User %s denied warehouse %s", scope.get("user_id"), normalized_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


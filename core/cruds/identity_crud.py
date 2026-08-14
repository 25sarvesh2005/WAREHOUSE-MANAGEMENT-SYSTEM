"""
--------------------------------------------------------------------------------
File        : core/cruds/identity_crud.py
Purpose     : Perform pure database operations for identity and access records.

Responsibilities:
    - Create and read users, sellers, warehouses, and assignments.
    - Keep persistence concerns separate from HTTP and authorization policy.

Flow:
    Identity controller
        ->
    CRUD function receives AsyncSession
        ->
    SQLAlchemy executes PostgreSQL query

Used By:
    - core/controllers/identity_controller.py
    - core/database/seed.py

Returns:
    CRUD functions -> SQLAlchemy model instances or collections.

Raises:
    sqlalchemy.exc.SQLAlchemyError: On database failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.logger import get_logger
from core.models.identity_model import (
    RefreshToken,
    Seller,
    User,
    UserSellerAssignment,
    UserWarehouseAssignment,
    Warehouse,
)

logger = get_logger(__name__)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """
    Read a user by normalized email address.

    This function performs only the lookup and leaves password checks and status
    decisions to the controller.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        email: Normalized email address.

    Returns:
        User | None: Matching user or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("Reading user by email %s", email)
    result = await session.execute(
        select(User)
        .options(selectinload(User.seller_assignments), selectinload(User.warehouse_assignments))
        .where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    """
    Read a user by unique ID.

    Assignment relationships are loaded for JWT scope construction and admin
    visibility responses.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        user_id: User UUID.

    Returns:
        User | None: Matching user or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("Reading user by id %s", user_id)
    result = await session.execute(
        select(User)
        .options(selectinload(User.seller_assignments), selectinload(User.warehouse_assignments))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user: User) -> User:
    """
    Persist a new user record.

    The caller owns password hashing, role validation, and audit creation while
    this function only adds and flushes the model.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        user: Unsaved User model.

    Returns:
        User: Persisted user with generated ID.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert fails.
    """
    logger.debug("Creating user %s", user.email)
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def update_user_last_login(session: AsyncSession, user: User) -> User:
    """
    Update a user's last login timestamp.

    This write supports auditability of authentication activity without altering
    role or assignment state.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        user: Persisted User model.

    Returns:
        User: Updated user model.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the update fails.
    """
    logger.debug("Updating last_login_at for user %s", user.id)
    now = datetime.now(UTC)
    user.last_login_at = now
    user.updated_at = now
    await session.flush()
    return user


async def update_user_status(session: AsyncSession, user: User, status: str) -> User:
    """
    Update a user's account status.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        user: Persisted User model.
        status: New status string (e.g. ACTIVE, INACTIVE, SUSPENDED).

    Returns:
        User: Updated user model.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the update fails.
    """
    logger.debug("Updating status for user %s to %s", user.id, status)
    user.status = status
    user.updated_at = datetime.now(UTC)
    await session.flush()
    return user


async def update_seller_status(session: AsyncSession, seller: Seller, status: str) -> Seller:
    """
    Update a seller tenant's business status.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        seller: Persisted Seller model.
        status: New status string (e.g. ACTIVE, INACTIVE, SUSPENDED).

    Returns:
        Seller: Updated seller model.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the update fails.
    """
    logger.debug("Updating status for seller %s to %s", seller.id, status)
    seller.status = status
    seller.updated_at = datetime.now(UTC)
    await session.flush()
    return seller


async def list_users(session: AsyncSession, *, limit: int, offset: int) -> list[User]:
    """
    List users in deterministic creation order.

    This function supports administrative user visibility and intentionally does
    not apply permission checks itself.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        limit: Maximum number of rows.
        offset: Row offset.

    Returns:
        list[User]: User records.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("Listing users limit=%s offset=%s", limit, offset)
    result = await session.execute(
        select(User).order_by(User.created_at).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def create_seller(session: AsyncSession, seller: Seller) -> Seller:
    """
    Persist a seller tenant record.

    This function does not decide who can create sellers; authorization belongs
    in the controller.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        seller: Unsaved Seller model.

    Returns:
        Seller: Persisted seller.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert fails.
    """
    logger.debug("Creating seller %s", seller.code)
    session.add(seller)
    await session.flush()
    await session.refresh(seller)
    return seller


async def list_sellers(session: AsyncSession, *, limit: int, offset: int) -> list[Seller]:
    """
    List seller tenant records.

    The controller applies seller visibility rules before exposing the returned
    records to callers.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        limit: Maximum number of rows.
        offset: Row offset.

    Returns:
        list[Seller]: Seller records.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("Listing sellers limit=%s offset=%s", limit, offset)
    result = await session.execute(
        select(Seller).order_by(Seller.code).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def get_seller_by_id(session: AsyncSession, seller_id: UUID) -> Seller | None:
    """
    Read a seller by unique ID.

    This function performs no tenant filtering and must be called only from a
    controller that has already applied scope rules.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        seller_id: Seller UUID.

    Returns:
        Seller | None: Matching seller or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("Reading seller by id %s", seller_id)
    result = await session.execute(select(Seller).where(Seller.id == seller_id))
    return result.scalar_one_or_none()


async def create_warehouse(session: AsyncSession, warehouse: Warehouse) -> Warehouse:
    """
    Persist a warehouse facility record.

    The controller owns administrative authorization and operational validation.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        warehouse: Unsaved Warehouse model.

    Returns:
        Warehouse: Persisted warehouse.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert fails.
    """
    logger.debug("Creating warehouse %s", warehouse.code)
    session.add(warehouse)
    await session.flush()
    await session.refresh(warehouse)
    return warehouse


async def list_warehouses(session: AsyncSession, *, limit: int, offset: int) -> list[Warehouse]:
    """
    List warehouse records.

    The controller narrows results to assigned warehouses when the requester is
    not globally administrative.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        limit: Maximum number of rows.
        offset: Row offset.

    Returns:
        list[Warehouse]: Warehouse records.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("Listing warehouses limit=%s offset=%s", limit, offset)
    result = await session.execute(
        select(Warehouse).order_by(Warehouse.code).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def get_seller_by_code(session: AsyncSession, code: str) -> Seller | None:
    """Read a seller by normalized code."""
    logger.debug("Reading seller by code %s", code)
    result = await session.execute(select(Seller).where(Seller.code == code))
    return result.scalar_one_or_none()


async def get_warehouse_by_id(session: AsyncSession, warehouse_id: UUID) -> Warehouse | None:
    """
    Read a warehouse by unique ID.

    This function performs only persistence lookup and leaves assignment checks
    to the caller.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        warehouse_id: Warehouse UUID.

    Returns:
        Warehouse | None: Matching warehouse or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("Reading warehouse by id %s", warehouse_id)
    result = await session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    return result.scalar_one_or_none()


async def get_warehouse_by_code(session: AsyncSession, code: str) -> Warehouse | None:
    """Read a warehouse by normalized code."""
    logger.debug("Reading warehouse by code %s", code)
    result = await session.execute(select(Warehouse).where(Warehouse.code == code))
    return result.scalar_one_or_none()


async def assign_user_to_seller(
    session: AsyncSession,
    *,
    user_id: UUID,
    seller_id: UUID,
    assignment_role: str,
) -> UserSellerAssignment:
    """
    Persist an active seller assignment for a user.

    Assignment business rules and duplicate handling remain controller concerns.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        user_id: User UUID.
        seller_id: Seller UUID.
        assignment_role: Assignment role label.

    Returns:
        UserSellerAssignment: Persisted assignment.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert fails.
    """
    logger.debug("Assigning user %s to seller %s", user_id, seller_id)
    assignment = UserSellerAssignment(
        user_id=user_id,
        seller_id=seller_id,
        assignment_role=assignment_role,
    )
    session.add(assignment)
    await session.flush()
    return assignment


async def assign_user_to_warehouse(
    session: AsyncSession,
    *,
    user_id: UUID,
    warehouse_id: UUID,
    assignment_role: str,
) -> UserWarehouseAssignment:
    """
    Persist an active warehouse assignment for a user.

    Assignment business rules and duplicate handling remain controller concerns.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        user_id: User UUID.
        warehouse_id: Warehouse UUID.
        assignment_role: Assignment role label.

    Returns:
        UserWarehouseAssignment: Persisted assignment.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert fails.
    """
    logger.debug("Assigning user %s to warehouse %s", user_id, warehouse_id)
    assignment = UserWarehouseAssignment(
        user_id=user_id,
        warehouse_id=warehouse_id,
        assignment_role=assignment_role,
    )
    session.add(assignment)
    await session.flush()
    return assignment


async def create_refresh_token(
    session: AsyncSession,
    *,
    user_id: UUID,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    """
    Persist a hashed refresh token for a user session.

    Raw token values are never stored; the caller is responsible for generating
    a cryptographically random token and hashing it before passing it here.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        user_id: Owning user UUID.
        token_hash: SHA-256 hex digest of the raw refresh token.
        expires_at: Token expiry timestamp in UTC.

    Returns:
        RefreshToken: Persisted refresh token record.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert fails.
    """
    logger.debug("Creating refresh token for user %s", user_id)
    token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(token)
    await session.flush()
    return token


async def get_refresh_token_by_hash(
    session: AsyncSession,
    token_hash: str,
) -> RefreshToken | None:
    """
    Read a valid, non-revoked, non-expired refresh token by its hash.

    Expired and revoked tokens are excluded so the controller can treat a None
    result as a uniform invalid-token rejection.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        token_hash: SHA-256 hex digest of the submitted raw token.

    Returns:
        RefreshToken | None: Matching token record or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("Looking up refresh token by hash")
    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def revoke_refresh_token(
    session: AsyncSession,
    token: RefreshToken,
) -> RefreshToken:
    """
    Mark a refresh token as revoked to prevent future use.

    Revocation is soft so audit trails remain intact.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        token: Active RefreshToken record to revoke.

    Returns:
        RefreshToken: Updated token with revoked flag set.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the update fails.
    """
    logger.debug("Revoking refresh token for user %s", token.user_id)
    token.revoked = True
    await session.flush()
    return token


async def revoke_all_refresh_tokens_for_user(
    session: AsyncSession,
    user_id: UUID,
) -> int:
    """
    Revoke every active refresh token belonging to a user.

    This is called on logout or token-version bump to immediately invalidate all
    existing sessions for the user.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        user_id: User UUID whose tokens should be revoked.

    Returns:
        int: Number of tokens revoked.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the update fails.
    """
    from sqlalchemy import update

    logger.debug("Revoking all refresh tokens for user %s", user_id)
    result = await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )
    count = result.rowcount
    logger.debug("Revoked %s refresh tokens for user %s", count, user_id)
    return count


async def increment_user_token_version(
    session: AsyncSession,
    user: User,
) -> User:
    """
    Increment a user's token version to immediately invalidate all existing JWTs.

    Token version is embedded in every issued JWT; the dependency chain validates
    this field is current so stale tokens are rejected without a database lookup
    on every request.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        user: Persisted User model.

    Returns:
        User: Updated user with incremented token_version.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the update fails.
    """
    logger.debug("Incrementing token_version for user %s", user.id)
    user.token_version = user.token_version + 1
    await session.flush()
    return user

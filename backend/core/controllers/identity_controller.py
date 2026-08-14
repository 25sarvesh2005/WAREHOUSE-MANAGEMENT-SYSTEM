"""
--------------------------------------------------------------------------------
File        : core/controllers/identity_controller.py
Purpose     : Orchestrate authentication, users, sellers, warehouses, and assignments.

Responsibilities:
    - Own identity business checks and role enforcement.
    - Open transaction units of work and call CRUD functions.
    - Create audit events for administrative and authentication actions.

Flow:
    Route handler
        ->
    IdentityController method
        ->
    transaction_session() plus CRUD functions
        ->
    Response-ready domain data

Used By:
    - core/apis/routes/identity_routes.py

Returns:
    Controller methods -> dict/list payloads for response schemas.

Raises:
    HTTPException: On authentication, authorization, validation, or conflict failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from common.auth import create_access_token, hash_password, verify_password
from common.logger import get_logger
from common.pagination import normalize_pagination
from common.warehouse_scope import require_roles
from core.constants import AuditActionType, BusinessStatus, UserRole, UserStatus
from core.cruds import audit_crud, identity_crud
from core.database.database import transaction_session
from core.models.identity_model import Seller, User, Warehouse

logger = get_logger(__name__)

_REFRESH_TOKEN_BYTES = 64


def _hash_token(raw_token: str) -> str:
    """
    Return the SHA-256 hex digest of a raw token string.

    Raw token values must never be stored; only their digest reaches the
    database so a credential compromise of the token table does not allow
    session impersonation.

    Args:
        raw_token: Cryptographically random raw token string.

    Returns:
        str: Hexadecimal SHA-256 digest.

    Raises:
        None.
    """
    return hashlib.sha256(raw_token.encode()).hexdigest()


class IdentityController:
    """Controller for identity and master access workflows."""

    def _user_response(self, user: User) -> dict[str, Any]:
        """
        Build a public user response payload.

        Password hashes are intentionally excluded and assignment IDs include
        only active, non-revoked assignments.

        Args:
            user: Persisted user model.

        Returns:
            dict[str, Any]: Response-ready user payload.

        Raises:
            None.
        """
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "status": user.status,
            "token_version": user.token_version,
            "seller_ids": [
                assignment.seller_id
                for assignment in user.seller_assignments
                if assignment.revoked_at is None
            ],
            "warehouse_ids": [
                assignment.warehouse_id
                for assignment in user.warehouse_assignments
                if assignment.revoked_at is None
            ],
            "created_by_user_id": getattr(user, "created_by_user_id", None),
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    def _token_payload(self, user: User) -> dict[str, Any]:
        """
        Build the JWT payload for an authenticated user.

        The payload follows the implementation contract and includes seller and
        warehouse assignment scopes derived from persisted active assignments.

        Args:
            user: Persisted user model with assignments loaded.

        Returns:
            dict[str, Any]: JWT claim payload.

        Raises:
            None.
        """
        response = self._user_response(user)
        return {
            "user_id": str(response["id"]),
            "email": response["email"],
            "name": response["name"],
            "role": response["role"],
            "seller_ids": [str(seller_id) for seller_id in response["seller_ids"]],
            "warehouse_ids": [str(warehouse_id) for warehouse_id in response["warehouse_ids"]],
            "token_version": response["token_version"],
        }

    async def login(self, login_data: dict[str, Any]) -> dict[str, str]:
        """
        Authenticate a user and return an access token.

        The user must exist, have an active account, and pass password
        verification before an audit event and JWT are created.

        Args:
            login_data: Login request dictionary with email and password.

        Returns:
            dict[str, str]: Access token response payload.

        Raises:
            HTTPException: If credentials are invalid or the user is inactive.
        """
        logger.info("Executing IdentityController.login")
        normalized_email = str(login_data["email"]).strip().lower()
        try:
            async with transaction_session() as session:
                user = await identity_crud.get_user_by_email(session, normalized_email)
                password_matches = user is not None and verify_password(
                    str(login_data["password"]),
                    user.hashed_password,
                )
                if not password_matches:
                    logger.warning("Failed login for email %s", normalized_email)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication credentials",
                    )
                if user.status != UserStatus.ACTIVE.value:
                    logger.warning("Inactive user attempted login %s", normalized_email)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User is not active",
                    )

                await identity_crud.update_user_last_login(session, user)
                await audit_crud.create_audit_event(
                    session,
                    actor_user_id=user.id,
                    action_type=AuditActionType.AUTH_LOGIN.value,
                    source_record_type="users",
                    source_record_id=user.id,
                    metadata_json={"email": user.email},
                )
                from core.config.settings import get_settings

                settings = get_settings()
                raw_refresh = secrets.token_urlsafe(_REFRESH_TOKEN_BYTES)
                expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expire_days)
                await identity_crud.create_refresh_token(
                    session,
                    user_id=user.id,
                    token_hash=_hash_token(raw_refresh),
                    expires_at=expires_at,
                )
                token = create_access_token(self._token_payload(user))
                logger.info("User logged in successfully %s", user.id)
                return {
                    "access_token": token,
                    "refresh_token": raw_refresh,
                    "token_type": "bearer",
                }
        except HTTPException:
            raise

    async def refresh_token(self, current_user: dict[str, Any]) -> dict[str, str]:
        """
        Refresh an active user's access token and record audit evidence.

        Args:
            current_user: Authenticated JWT claims dictionary.

        Returns:
            dict[str, str]: New access token payload.

        Raises:
            HTTPException: If user no longer exists or is inactive.
        """
        logger.info("Executing IdentityController.refresh_token")
        user_id = UUID(str(current_user["user_id"]))
        async with transaction_session() as session:
            user = await identity_crud.get_user_by_id(session, user_id)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )
            if user.status != UserStatus.ACTIVE.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not active",
                )
            await audit_crud.create_audit_event(
                session,
                actor_user_id=user.id,
                action_type=AuditActionType.AUTH_TOKEN_REFRESH.value,
                source_record_type="users",
                source_record_id=user.id,
                metadata_json={"email": user.email},
            )
            token = create_access_token(self._token_payload(user))
            return {
                "access_token": token,
                "token_type": "bearer",
            }

    async def create_user(
        self,
        user_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create a user account following RBAC role hierarchy.

        - Admin can create any role (Managers, Receivers, Pickers, Sellers, Admins).
        - Managers can only create Receivers and Picker/Packers.
        """
        logger.info("Executing IdentityController.create_user")
        actor_role = str(scope["role"])
        actor_id = UUID(str(scope["user_id"]))
        target_role = str(user_data["role"])

        if actor_role == UserRole.ADMINISTRATOR.value:
            pass
        elif actor_role == UserRole.WAREHOUSE_MANAGER.value:
            if target_role not in {UserRole.RECEIVER.value, UserRole.PICKER_PACKER.value}:
                logger.warning("Manager attempted unauthorized role registration: %s", target_role)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse Managers can only create Receivers and Picker/Packers",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role is not authorized to register new user accounts",
            )

        normalized_email = str(user_data["email"]).strip().lower()
        try:
            async with transaction_session() as session:
                user = User(
                    email=normalized_email,
                    name=str(user_data["name"]).strip(),
                    hashed_password=hash_password(str(user_data["password"])),
                    role=target_role,
                    status=str(user_data.get("status", UserStatus.ACTIVE.value)),
                    created_by_user_id=actor_id,
                )
                await identity_crud.create_user(session, user)

                if "warehouse_id" in user_data and user_data["warehouse_id"]:
                    w_id = UUID(str(user_data["warehouse_id"]))
                    await identity_crud.create_user_warehouse_assignment(
                        session, user_id=user.id, warehouse_id=w_id, assignment_role=target_role
                    )

                await audit_crud.create_audit_event(
                    session,
                    actor_user_id=actor_id,
                    action_type=AuditActionType.USER_CREATED.value,
                    source_record_type="users",
                    source_record_id=user.id,
                    metadata_json={"email": user.email, "role": user.role, "created_by": str(actor_id)},
                )
                logger.info("User created successfully %s by actor %s", user.id, actor_id)
                return self._user_response(user)
        except IntegrityError as error:
            logger.warning("Duplicate or invalid user create request for %s", normalized_email)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists",
            ) from error

    async def register_seller_public(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Public registration for Sellers only (pending administrator approval).
        """
        logger.info("Executing IdentityController.register_seller_public")
        normalized_email = str(payload["email"]).strip().lower()
        company_name = str(payload["company_name"]).strip()
        code_raw = str(payload.get("seller_code") or company_name[:10].replace(" ", ""))
        seller_code = "".join(c for c in code_raw if c.isalnum() or c in "_-").upper() or "SELLER"

        try:
            async with transaction_session() as session:
                user = User(
                    email=normalized_email,
                    name=str(payload["name"]).strip(),
                    hashed_password=hash_password(str(payload["password"])),
                    role=UserRole.SELLER.value,
                    status=UserStatus.PENDING_APPROVAL.value,
                )
                await identity_crud.create_user(session, user)

                existing_seller = await identity_crud.get_seller_by_code(session, seller_code)
                if not existing_seller:
                    seller = Seller(
                        code=seller_code,
                        name=company_name,
                        contact_email=normalized_email,
                        status=BusinessStatus.ACTIVE.value,
                    )
                    await identity_crud.create_seller(session, seller)
                else:
                    seller = existing_seller

                await identity_crud.assign_user_to_seller(
                    session,
                    user_id=user.id,
                    seller_id=seller.id,
                    assignment_role=UserRole.SELLER.value,
                )

                logger.info("Public seller registration created (pending approval) %s", user.id)
                return self._user_response(user)
        except IntegrityError as error:
            logger.warning("Duplicate seller registration for email %s", normalized_email)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User or seller account already exists",
            ) from error

    async def approve_seller(self, user_id: UUID, scope: dict[str, Any]) -> dict[str, Any]:
        """
        Administrator or Manager endpoint to approve a pending seller account.
        """
        logger.info("Executing IdentityController.approve_seller")
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        actor_id = UUID(str(scope["user_id"]))
        async with transaction_session() as session:
            user = await identity_crud.get_user_by_id(session, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            await identity_crud.update_user_status(session, user, UserStatus.ACTIVE.value)

            # Also activate all associated seller tenant entities
            for assignment in user.seller_assignments:
                seller = await identity_crud.get_seller_by_id(session, assignment.seller_id)
                if seller and seller.status != BusinessStatus.ACTIVE.value:
                    await identity_crud.update_seller_status(session, seller, BusinessStatus.ACTIVE.value)

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.USER_UPDATED.value,
                source_record_type="users",
                source_record_id=user.id,
                metadata_json={"action": "APPROVED_SELLER", "email": user.email},
            )
            logger.info("Seller approved successfully %s", user.id)
            return self._user_response(user)

    async def update_user_status(
        self,
        user_id: UUID,
        status_val: str,
        scope: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update the status of any worker or user account (ACTIVE, INACTIVE, SUSPENDED, PENDING_APPROVAL).
        """
        logger.info("Executing IdentityController.update_user_status")
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        actor_id = UUID(str(scope["user_id"]))
        actor_role = str(scope["role"])

        valid_statuses = {
            UserStatus.ACTIVE.value,
            UserStatus.INACTIVE.value,
            UserStatus.SUSPENDED.value,
            UserStatus.PENDING_APPROVAL.value,
        }
        if status_val not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status '{status_val}'. Allowed: {', '.join(sorted(valid_statuses))}",
            )

        async with transaction_session() as session:
            user = await identity_crud.get_user_by_id(session, user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            # Hierarchy protection: Managers cannot suspend/modify Administrators
            if actor_role == UserRole.WAREHOUSE_MANAGER.value and user.role == UserRole.ADMINISTRATOR.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Warehouse Managers cannot modify Administrator accounts",
                )

            old_status = user.status
            await identity_crud.update_user_status(session, user, status_val)

            # If user is a seller and activated, also activate seller tenant
            if status_val == UserStatus.ACTIVE.value and user.role == UserRole.SELLER.value:
                for assignment in user.seller_assignments:
                    seller = await identity_crud.get_seller_by_id(session, assignment.seller_id)
                    if seller and seller.status != BusinessStatus.ACTIVE.value:
                        await identity_crud.update_seller_status(session, seller, BusinessStatus.ACTIVE.value)

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.USER_UPDATED.value,
                source_record_type="users",
                source_record_id=user.id,
                metadata_json={"old_status": old_status, "new_status": status_val, "email": user.email},
            )
            logger.info("User status updated successfully %s: %s -> %s", user.id, old_status, status_val)
            return self._user_response(user)

    async def update_seller_status(
        self,
        seller_id: UUID,
        status_val: str,
        scope: dict[str, Any],
    ) -> Seller:
        """
        Update the business status of a seller tenant (ACTIVE, INACTIVE, SUSPENDED).
        """
        logger.info("Executing IdentityController.update_seller_status")
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        actor_id = UUID(str(scope["user_id"]))

        valid_statuses = {
            BusinessStatus.ACTIVE.value,
            BusinessStatus.INACTIVE.value,
            BusinessStatus.SUSPENDED.value,
        }
        if status_val not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status '{status_val}'. Allowed: {', '.join(sorted(valid_statuses))}",
            )

        async with transaction_session() as session:
            seller = await identity_crud.get_seller_by_id(session, seller_id)
            if not seller:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found")

            old_status = seller.status
            await identity_crud.update_seller_status(session, seller, status_val)

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.SELLER_UPDATED.value,
                source_record_type="sellers",
                source_record_id=seller.id,
                metadata_json={"old_status": old_status, "new_status": status_val, "code": seller.code},
            )
            logger.info("Seller status updated successfully %s: %s -> %s", seller.id, old_status, status_val)
            return seller

    async def list_users(
        self,
        scope: dict[str, Any],
        *,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        """
        List user accounts for administrators and warehouse managers.

        Args:
            scope: Authenticated requester scope.
            limit: Requested page size.
            offset: Requested offset.

        Returns:
            list[dict[str, Any]]: Public user payloads.

        Raises:
            HTTPException: If the requester is not authorized.
        """
        logger.info("Executing IdentityController.list_users")
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        normalized_limit, normalized_offset = normalize_pagination(limit, offset)
        async with transaction_session() as session:
            users = await identity_crud.list_users(
                session,
                limit=normalized_limit,
                offset=normalized_offset,
            )
            return [self._user_response(user) for user in users]

    async def create_seller(
        self,
        seller_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> Seller:
        """
        Create a seller tenant as an administrator.

        Seller codes are normalized to uppercase and seller creation is audited
        inside the same transaction.

        Args:
            seller_data: Validated seller creation payload.
            scope: Authenticated requester scope.

        Returns:
            Seller: Persisted seller model.

        Raises:
            HTTPException: If unauthorized or the seller code already exists.
        """
        logger.info("Executing IdentityController.create_seller")
        require_roles(scope, {UserRole.ADMINISTRATOR})
        actor_id = UUID(str(scope["user_id"]))
        try:
            async with transaction_session() as session:
                seller = Seller(
                    code=str(seller_data["code"]).strip().upper(),
                    name=str(seller_data["name"]).strip(),
                    contact_email=seller_data.get("contact_email"),
                    contact_phone=seller_data.get("contact_phone"),
                    status=str(seller_data.get("status", BusinessStatus.ACTIVE.value)),
                )
                await identity_crud.create_seller(session, seller)
                await audit_crud.create_audit_event(
                    session,
                    actor_user_id=actor_id,
                    action_type=AuditActionType.SELLER_CREATED.value,
                    source_record_type="sellers",
                    source_record_id=seller.id,
                    metadata_json={"code": seller.code},
                )
                logger.info("Seller created successfully %s", seller.id)
                return seller
        except IntegrityError as error:
            logger.warning("Duplicate seller code %s", seller_data.get("code"))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Seller already exists",
            ) from error

    async def list_sellers(
        self,
        scope: dict[str, Any],
        *,
        limit: int,
        offset: int,
    ) -> list[Seller]:
        """
        List sellers visible to the requester.

        Administrators see all sellers; seller-scoped users see only assigned
        seller records.

        Args:
            scope: Authenticated requester scope.
            limit: Requested page size.
            offset: Requested offset.

        Returns:
            list[Seller]: Visible seller records.

        Raises:
            ValueError: If pagination parameters are invalid.
        """
        logger.info("Executing IdentityController.list_sellers")
        normalized_limit, normalized_offset = normalize_pagination(limit, offset)
        async with transaction_session() as session:
            sellers = await identity_crud.list_sellers(
                session,
                limit=normalized_limit,
                offset=normalized_offset,
            )
            if scope.get("role") == UserRole.ADMINISTRATOR.value:
                return sellers
            allowed = {str(seller_id) for seller_id in scope.get("seller_ids", [])}
            return [seller for seller in sellers if str(seller.id) in allowed]

    async def create_warehouse(
        self,
        warehouse_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> Warehouse:
        """
        Create a warehouse facility as an administrator.

        Warehouse codes are normalized to uppercase and initial Reno/Columbus
        seeding is handled separately by the database seed module.

        Args:
            warehouse_data: Validated warehouse creation payload.
            scope: Authenticated requester scope.

        Returns:
            Warehouse: Persisted warehouse model.

        Raises:
            HTTPException: If unauthorized or the warehouse code already exists.
        """
        logger.info("Executing IdentityController.create_warehouse")
        require_roles(scope, {UserRole.ADMINISTRATOR})
        actor_id = UUID(str(scope["user_id"]))
        try:
            async with transaction_session() as session:
                warehouse = Warehouse(
                    code=str(warehouse_data["code"]).strip().upper(),
                    name=str(warehouse_data["name"]).strip(),
                    address_line1=warehouse_data.get("address_line1"),
                    city=warehouse_data.get("city"),
                    state=warehouse_data.get("state"),
                    postal_code=warehouse_data.get("postal_code"),
                    timezone=str(warehouse_data.get("timezone", "America/Los_Angeles")),
                    status=str(warehouse_data.get("status", BusinessStatus.ACTIVE.value)),
                )
                await identity_crud.create_warehouse(session, warehouse)
                await audit_crud.create_audit_event(
                    session,
                    actor_user_id=actor_id,
                    action_type=AuditActionType.WAREHOUSE_CREATED.value,
                    source_record_type="warehouses",
                    source_record_id=warehouse.id,
                    metadata_json={"code": warehouse.code},
                )
                logger.info("Warehouse created successfully %s", warehouse.id)
                return warehouse
        except IntegrityError as error:
            logger.warning("Duplicate warehouse code %s", warehouse_data.get("code"))
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Warehouse already exists",
            ) from error

    async def list_warehouses(
        self,
        scope: dict[str, Any],
        *,
        limit: int,
        offset: int,
    ) -> list[Warehouse]:
        """
        List warehouses visible to the requester.

        Administrators see all warehouses; warehouse-scoped users see only
        assigned facilities.

        Args:
            scope: Authenticated requester scope.
            limit: Requested page size.
            offset: Requested offset.

        Returns:
            list[Warehouse]: Visible warehouse records.

        Raises:
            ValueError: If pagination parameters are invalid.
        """
        logger.info("Executing IdentityController.list_warehouses")
        normalized_limit, normalized_offset = normalize_pagination(limit, offset)
        async with transaction_session() as session:
            warehouses = await identity_crud.list_warehouses(
                session,
                limit=normalized_limit,
                offset=normalized_offset,
            )
            if scope.get("role") == UserRole.ADMINISTRATOR.value:
                return warehouses
            allowed = {str(warehouse_id) for warehouse_id in scope.get("warehouse_ids", [])}
            return [warehouse for warehouse in warehouses if str(warehouse.id) in allowed]

    async def assign_user_to_seller(
        self,
        assignment_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Assign a user to a seller as an administrator.

        Assignment writes are audited and support future seller-scoped portal
        visibility without trusting request body scope at read time.

        Args:
            assignment_data: Validated assignment payload.
            scope: Authenticated requester scope.

        Returns:
            dict[str, Any]: Assignment response payload.

        Raises:
            HTTPException: If unauthorized or duplicate.
        """
        logger.info("Executing IdentityController.assign_user_to_seller")
        require_roles(scope, {UserRole.ADMINISTRATOR})
        try:
            async with transaction_session() as session:
                assignment = await identity_crud.assign_user_to_seller(
                    session,
                    user_id=UUID(str(assignment_data["user_id"])),
                    seller_id=UUID(str(assignment_data["seller_id"])),
                    assignment_role=str(assignment_data["assignment_role"]),
                )
                return {
                    "id": assignment.id,
                    "user_id": assignment.user_id,
                    "seller_id": assignment.seller_id,
                    "warehouse_id": None,
                    "assignment_role": assignment.assignment_role,
                }
        except IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assignment already exists",
            ) from error

    async def assign_user_to_warehouse(
        self,
        assignment_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Assign a user to a warehouse as an administrator.

        Assignment writes are audited in later workflow-specific expansion; this
        first slice persists the active assignment boundary.

        Args:
            assignment_data: Validated assignment payload.
            scope: Authenticated requester scope.

        Returns:
            dict[str, Any]: Assignment response payload.

        Raises:
            HTTPException: If unauthorized or duplicate.
        """
        logger.info("Executing IdentityController.assign_user_to_warehouse")
        require_roles(scope, {UserRole.ADMINISTRATOR})
        try:
            async with transaction_session() as session:
                assignment = await identity_crud.assign_user_to_warehouse(
                    session,
                    user_id=UUID(str(assignment_data["user_id"])),
                    warehouse_id=UUID(str(assignment_data["warehouse_id"])),
                    assignment_role=str(assignment_data["assignment_role"]),
                )
                return {
                    "id": assignment.id,
                    "user_id": assignment.user_id,
                    "seller_id": None,
                    "warehouse_id": assignment.warehouse_id,
                    "assignment_role": assignment.assignment_role,
                }
        except IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assignment already exists",
            ) from error

    async def refresh(self, refresh_data: dict[str, Any]) -> dict[str, str]:
        """
        Rotate a refresh token and issue a new access token.

        The submitted raw refresh token is hashed and looked up; only a valid,
        non-revoked, non-expired record produces a new token pair. The old
        refresh token is revoked atomically before the new pair is created to
        prevent replay attacks.

        Args:
            refresh_data: Refresh request dictionary with refresh_token.

        Returns:
            dict[str, str]: New access and refresh token response payload.

        Raises:
            HTTPException: If the refresh token is invalid, expired, or the
                user account is no longer active.
        """
        logger.info("Executing IdentityController.refresh")
        raw_token = str(refresh_data["refresh_token"])
        token_hash = _hash_token(raw_token)
        async with transaction_session() as session:
            stored = await identity_crud.get_refresh_token_by_hash(session, token_hash)
            if stored is None:
                logger.warning("Refresh attempt with invalid or expired token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )
            user = await identity_crud.get_user_by_id(session, stored.user_id)
            if user is None or user.status != UserStatus.ACTIVE.value:
                logger.warning("Refresh denied for inactive user %s", stored.user_id)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not active",
                )

            # Rotate: revoke old token, issue new pair atomically
            await identity_crud.revoke_refresh_token(session, stored)

            from core.config.settings import get_settings

            settings = get_settings()
            raw_refresh = secrets.token_urlsafe(_REFRESH_TOKEN_BYTES)
            expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expire_days)
            await identity_crud.create_refresh_token(
                session,
                user_id=user.id,
                token_hash=_hash_token(raw_refresh),
                expires_at=expires_at,
            )
            await audit_crud.create_audit_event(
                session,
                actor_user_id=user.id,
                action_type=AuditActionType.AUTH_TOKEN_REFRESH.value,
                source_record_type="users",
                source_record_id=user.id,
                metadata_json={"email": user.email},
            )
            new_access = create_access_token(self._token_payload(user))
            logger.info("Refresh token rotated for user %s", user.id)
            return {
                "access_token": new_access,
                "refresh_token": raw_refresh,
                "token_type": "bearer",
            }

    async def logout(self, scope: dict[str, Any], refresh_data: dict[str, Any]) -> None:
        """
        Log out the authenticated user by revoking all refresh tokens.

        All active refresh tokens for the user are revoked and the user's
        token_version is incremented to immediately invalidate outstanding
        access JWTs once token_version validation is active.

        Args:
            scope: Authenticated requester scope.
            refresh_data: Logout request dictionary with refresh_token.

        Returns:
            None.

        Raises:
            HTTPException: If the supplied refresh token is unrecognized.
        """
        logger.info("Executing IdentityController.logout")
        user_id = UUID(str(scope["user_id"]))
        raw_token = str(refresh_data.get("refresh_token", ""))

        async with transaction_session() as session:
            if raw_token:
                token_hash = _hash_token(raw_token)
                stored = await identity_crud.get_refresh_token_by_hash(session, token_hash)
                if stored is None or str(stored.user_id) != str(user_id):
                    logger.warning(
                        "Logout with mismatched or invalid refresh token for user %s", user_id
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication credentials",
                    )

            revoked = await identity_crud.revoke_all_refresh_tokens_for_user(session, user_id)
            user = await identity_crud.get_user_by_id(session, user_id)
            if user is not None:
                await identity_crud.increment_user_token_version(session, user)
            await audit_crud.create_audit_event(
                session,
                actor_user_id=user_id,
                action_type=AuditActionType.AUTH_LOGOUT.value,
                source_record_type="users",
                source_record_id=user_id,
                metadata_json={"revoked_tokens": revoked},
            )
            logger.info("User %s logged out; revoked %s refresh token(s)", user_id, revoked)


identity_controller = IdentityController()

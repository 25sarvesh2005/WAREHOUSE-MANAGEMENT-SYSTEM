"""
Migration Controller.

Orchestrates opening inventory migration batches, staging, validation, and ledger application.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Sequence
from uuid import UUID

from fastapi import HTTPException, status

from common.logger import get_logger
from common.pagination import normalize_pagination
from common.warehouse_scope import require_roles
from core.constants import (
    AuditActionType,
    InventoryState,
    MigrationBatchStatus,
    StagedRowValidationStatus,
    UserRole,
)
from core.cruds import audit_crud, catalog_crud, identity_crud, migration_crud
from core.database.database import transaction_session
from core.models.migration_model import ImportBatch, StagedOpeningInventoryRow
from core.services.import_export.opening_inventory_parser import (
    compute_opening_inventory_row_hash,
    parse_opening_inventory_file,
)

logger = get_logger(__name__)
MAX_OPENING_INVENTORY_UPLOAD_BYTES = 5 * 1024 * 1024


def _is_warehouse_manager(scope: dict[str, Any]) -> bool:
    """
    Return whether the authenticated scope belongs to a warehouse manager.

    Args:
        scope: Authenticated requester scope.

    Returns:
        bool: True when the scope role is WAREHOUSE_MANAGER.
    """
    return scope.get("role") == UserRole.WAREHOUSE_MANAGER.value


def _scope_warehouse_ids(scope: dict[str, Any]) -> set[str]:
    """
    Return normalized warehouse assignment IDs from the requester scope.

    Args:
        scope: Authenticated requester scope.

    Returns:
        set[str]: Warehouse UUID strings assigned to the requester.
    """
    return {str(warehouse_id) for warehouse_id in scope.get("warehouse_ids", [])}


def _compute_row_hash(item: dict[str, Any]) -> str:
    """
    Compute a deterministic SHA-256 hash of raw row content if not provided.

    Args:
        item: Raw row dictionary.

    Returns:
        str: 64-character SHA-256 hex digest string.
    """
    return compute_opening_inventory_row_hash(item)


class MigrationController:
    """Controller for opening inventory migration workflows."""

    async def create_batch(
        self,
        scope: dict[str, Any],
        source_notes: str | None = None,
    ) -> ImportBatch:
        """
        Create a new opening inventory migration batch.

        Args:
            scope: Authenticated requester scope.
            source_notes: Optional description or source notes.

        Returns:
            ImportBatch: Created import batch header.

        Raises:
            HTTPException: If requester role is forbidden.
        """
        logger.info("Executing MigrationController.create_batch")
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        actor_id = UUID(str(scope["user_id"]))

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        hash_input = f"{actor_id}_{datetime.now(UTC).timestamp()}".encode()
        suffix = hashlib.sha256(hash_input).hexdigest()[:6].upper()
        batch_number = f"BATCH-{timestamp}-{suffix}"

        async with transaction_session() as session:
            batch = await migration_crud.create_import_batch(
                session,
                created_by_user_id=actor_id,
                batch_number=batch_number,
                source_notes=source_notes,
            )

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.MIGRATION_BATCH_CREATED.value,
                source_record_type="import_batches",
                source_record_id=batch.id,
                reason=source_notes,
                metadata_json={"batch_number": batch_number},
            )
            return batch

    async def list_batches(
        self,
        scope: dict[str, Any],
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[ImportBatch]:
        """
        List import batches visible to the requester.

        Args:
            scope: Authenticated requester scope.
            limit: Pagination limit.
            offset: Pagination offset.

        Returns:
            Sequence[ImportBatch]: Matching import batches.
        """
        logger.info("Executing MigrationController.list_batches")
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        norm_limit, norm_offset = normalize_pagination(limit, offset)

        async with transaction_session() as session:
            return await migration_crud.list_import_batches(
                session, limit=norm_limit, offset=norm_offset
            )

    async def get_batch(
        self,
        scope: dict[str, Any],
        batch_id: UUID,
    ) -> ImportBatch:
        """
        Retrieve an import batch by ID.

        Args:
            scope: Authenticated requester scope.
            batch_id: Import batch UUID.

        Returns:
            ImportBatch: Found import batch.

        Raises:
            HTTPException: If batch not found.
        """
        logger.info("Executing MigrationController.get_batch %s", batch_id)
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})

        async with transaction_session() as session:
            batch = await migration_crud.get_import_batch_by_id(session, batch_id)
            if batch is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found"
                )
            return batch

    async def submit_staged_rows(
        self,
        scope: dict[str, Any],
        batch_id: UUID,
        rows_data: list[dict[str, Any]],
    ) -> Sequence[StagedOpeningInventoryRow]:
        """
        Submit raw opening inventory rows for staging under a batch.

        Args:
            scope: Authenticated requester scope.
            batch_id: Parent batch UUID.
            rows_data: List of raw staged row dictionaries.

        Returns:
            Sequence[StagedOpeningInventoryRow]: Staged rows for the batch.

        Raises:
            HTTPException: On status conflict, duplicate content hash mismatch, or not found.
        """
        logger.info("Executing MigrationController.submit_staged_rows for batch=%s", batch_id)
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        actor_id = UUID(str(scope["user_id"]))

        # Populate missing hashes
        for item in rows_data:
            if not item.get("source_hash"):
                item["source_hash"] = _compute_row_hash(item)

        async with transaction_session() as session:
            batch = await migration_crud.get_import_batch_by_id(
                session, batch_id, for_update=True
            )
            if batch is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found"
                )

            locked_statuses = {
                MigrationBatchStatus.APPROVED.value,
                MigrationBatchStatus.APPLIED.value,
            }
            if batch.status in locked_statuses:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot submit rows to a batch in status '{batch.status}'",
                )

            try:
                await migration_crud.submit_staged_rows_bulk(session, batch_id, rows_data)
            except ValueError as error:
                logger.warning("Staged row submission conflict: %s", error)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(error),
                ) from error

            all_staged = await migration_crud.get_all_staged_rows_by_batch(session, batch_id)
            total_count = len(all_staged)

            # Reset batch status to STAGED to demand re-validation
            await migration_crud.update_import_batch_counts(
                session,
                batch,
                status=MigrationBatchStatus.STAGED.value,
                total_rows=total_count,
                valid_rows=0,
                invalid_rows=0,
            )

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.MIGRATION_ROWS_SUBMITTED.value,
                source_record_type="import_batches",
                source_record_id=batch.id,
                metadata_json={
                    "submitted_count": len(rows_data),
                    "total_staged": total_count,
                },
            )

            return all_staged

    async def upload_staged_rows_file(
        self,
        scope: dict[str, Any],
        batch_id: UUID,
        file_name: str,
        file_bytes: bytes,
    ) -> dict[str, Any]:
        """
        Parse and stage opening inventory rows from an uploaded CSV/XLSX file.

        Args:
            scope: Authenticated requester scope.
            batch_id: Parent batch UUID.
            file_name: Uploaded filename.
            file_bytes: Uploaded file contents.

        Returns:
            dict[str, Any]: Upload staging summary.

        Raises:
            HTTPException: If upload is invalid or staging conflicts.
        """
        logger.info("Executing MigrationController.upload_staged_rows_file")
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})

        if not file_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded opening inventory file must include a filename.",
            )
        if len(file_bytes) > MAX_OPENING_INVENTORY_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Opening inventory upload exceeds 5 MB limit.",
            )

        try:
            rows_data = parse_opening_inventory_file(file_name, file_bytes)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error

        if not rows_data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Opening inventory upload contained no staged rows.",
            )

        staged_rows = await self.submit_staged_rows(scope, batch_id, rows_data)
        return {
            "batch_id": batch_id,
            "file_name": file_name,
            "parsed_rows": len(rows_data),
            "staged_rows": len(staged_rows),
        }

    async def validate_batch(
        self,
        scope: dict[str, Any],
        batch_id: UUID,
    ) -> ImportBatch:
        """
        Validate all staged rows in an import batch against master data and integrity rules.

        Args:
            scope: Authenticated requester scope.
            batch_id: Target batch UUID.

        Returns:
            ImportBatch: Updated batch header with validation summary.

        Raises:
            HTTPException: If batch not found or in invalid status.
        """
        logger.info("Executing MigrationController.validate_batch for batch=%s", batch_id)
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            batch = await migration_crud.get_import_batch_by_id(
                session, batch_id, for_update=True
            )
            if batch is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found"
                )

            locked_statuses = {
                MigrationBatchStatus.APPROVED.value,
                MigrationBatchStatus.APPLIED.value,
            }
            if batch.status in locked_statuses:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot re-validate batch in status '{batch.status}'",
                )

            staged_rows = await migration_crud.get_all_staged_rows_by_batch(session, batch_id)
            if not staged_rows:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Cannot validate an empty batch with zero staged rows",
                )

            valid_count = 0
            invalid_count = 0

            # Pre-pass for intra-batch duplicate checks
            identity_counts: dict[tuple[str, str, int], int] = {}
            hash_counts: dict[str, int] = {}

            for r in staged_rows:
                id_key = (r.source_workbook, r.source_sheet, r.source_row_number)
                identity_counts[id_key] = identity_counts.get(id_key, 0) + 1
                hash_counts[r.source_hash] = hash_counts.get(r.source_hash, 0) + 1

            for row in staged_rows:
                row_errors: list[dict[str, object]] = []

                # Duplicate identity in batch
                id_key = (row.source_workbook, row.source_sheet, row.source_row_number)
                if identity_counts.get(id_key, 0) > 1:
                    row_errors.append(
                        {
                            "code": "DUPLICATE_SOURCE_ROW_IDENTITY",
                            "message": (
                                "Duplicate source row identity "
                                f"{row.source_workbook}/{row.source_sheet} row "
                                f"{row.source_row_number} in batch."
                            ),
                        }
                    )

                # Duplicate hash in batch
                if hash_counts.get(row.source_hash, 0) > 1:
                    row_errors.append(
                        {
                            "code": "DUPLICATE_SOURCE_HASH",
                            "message": (
                                f"Duplicate content hash '{row.source_hash}' present "
                                "in multiple rows in batch."
                            ),
                        }
                    )

                # 1. Resolve Seller
                seller_id: UUID | None = None
                if not row.raw_seller_code:
                    row_errors.append({
                        "code": "MISSING_SELLER",
                        "message": "Raw seller code is missing.",
                    })
                else:
                    seller = await identity_crud.get_seller_by_code(
                        session, row.raw_seller_code.strip()
                    )
                    if seller is None or seller.status != "ACTIVE":
                        row_errors.append({
                            "code": "MISSING_SELLER",
                            "message": (
                                f"Seller code '{row.raw_seller_code}' not found "
                                "or inactive."
                            ),
                        })
                    else:
                        seller_id = seller.id

                # 2. Resolve Product
                product_id: UUID | None = None
                if not row.raw_sku:
                    row_errors.append({
                        "code": "MISSING_PRODUCT",
                        "message": "Raw SKU is missing.",
                    })
                else:
                    product = await catalog_crud.get_product_by_sku(session, row.raw_sku.strip())
                    if product is None or product.status != "ACTIVE":
                        row_errors.append({
                            "code": "MISSING_PRODUCT",
                            "message": f"SKU '{row.raw_sku}' not found or inactive in catalog.",
                        })
                    else:
                        product_id = product.id
                        if seller_id is not None and product.seller_id != seller_id:
                            row_errors.append(
                                {
                                    "code": "SELLER_PRODUCT_MISMATCH",
                                    "message": (
                                        f"SKU '{row.raw_sku}' belongs to seller "
                                        f"'{product.seller_id}', not resolved seller "
                                        f"'{seller_id}'."
                                    ),
                                }
                            )

                # 3. Resolve Warehouse
                warehouse_id: UUID | None = None
                if not row.raw_warehouse_code:
                    row_errors.append({
                        "code": "MISSING_WAREHOUSE",
                        "message": "Raw warehouse code is missing.",
                    })
                else:
                    wh = await identity_crud.get_warehouse_by_code(
                        session, row.raw_warehouse_code.strip()
                    )
                    if wh is None or wh.status != "ACTIVE":
                        row_errors.append({
                            "code": "MISSING_WAREHOUSE",
                            "message": (
                                f"Warehouse code '{row.raw_warehouse_code}' not "
                                "found or inactive."
                            ),
                        })
                    else:
                        warehouse_id = wh.id
                        # Warehouse Scope check for Warehouse Manager role
                        if _is_warehouse_manager(scope):
                            if str(wh.id) not in _scope_warehouse_ids(scope):
                                row_errors.append({
                                    "code": "WAREHOUSE_SCOPE_MISMATCH",
                                    "message": (
                                        f"Warehouse '{row.raw_warehouse_code}' is "
                                        "outside assigned warehouse scope."
                                    ),
                                })

                # 4. Resolve Location
                location_id: UUID | None = None
                if row.raw_location_code and warehouse_id is not None:
                    loc = await catalog_crud.get_location_by_code(
                        session, warehouse_id, row.raw_location_code.strip()
                    )
                    if loc is None or loc.status != "ACTIVE":
                        row_errors.append({
                            "code": "INVALID_LOCATION",
                            "message": (
                                f"Location code '{row.raw_location_code}' not found "
                                f"or inactive in warehouse '{row.raw_warehouse_code}'."
                            ),
                        })
                    else:
                        location_id = loc.id

                # 5. Inventory State check
                resolved_state: str | None = None
                if not row.raw_inventory_state:
                    row_errors.append({
                        "code": "INVALID_INVENTORY_STATE",
                        "message": "Raw inventory state is missing.",
                    })
                else:
                    state_candidate = row.raw_inventory_state.strip().upper()
                    valid_states = [s.value for s in InventoryState]
                    if state_candidate not in valid_states:
                        row_errors.append({
                            "code": "INVALID_INVENTORY_STATE",
                            "message": (
                                f"Inventory state '{row.raw_inventory_state}' is "
                                f"invalid. Allowed: {valid_states}"
                            ),
                        })
                    else:
                        resolved_state = state_candidate

                # 6. Quantity check
                resolved_qty: Decimal | None = None
                if not row.raw_quantity:
                    row_errors.append({
                        "code": "INVALID_QUANTITY",
                        "message": "Raw quantity is missing.",
                    })
                else:
                    try:
                        parsed_qty = Decimal(row.raw_quantity.strip())
                        if parsed_qty <= Decimal("0.00"):
                            row_errors.append({
                                "code": "INVALID_QUANTITY",
                                "message": (
                                    "Opening inventory quantity must be greater than "
                                    f"zero, got {parsed_qty}."
                                ),
                            })
                        else:
                            resolved_qty = parsed_qty
                    except (InvalidOperation, TypeError):
                        row_errors.append({
                            "code": "INVALID_QUANTITY",
                            "message": f"Quantity '{row.raw_quantity}' is non-numeric.",
                        })

                row_status = (
                    StagedRowValidationStatus.VALID.value
                    if not row_errors
                    else StagedRowValidationStatus.INVALID.value
                )
                if row_status == StagedRowValidationStatus.VALID.value:
                    valid_count += 1
                else:
                    invalid_count += 1

                await migration_crud.update_staged_row_validation(
                    session,
                    row,
                    validation_status=row_status,
                    validation_errors=row_errors,
                    seller_id=seller_id,
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    location_id=location_id,
                    inventory_state=resolved_state,
                    quantity=resolved_qty,
                )

            target_batch_status = (
                MigrationBatchStatus.VALIDATED.value
                if invalid_count == 0
                else MigrationBatchStatus.VALIDATION_FAILED.value
            )

            updated_batch = await migration_crud.update_import_batch_counts(
                session,
                batch,
                status=target_batch_status,
                total_rows=len(staged_rows),
                valid_rows=valid_count,
                invalid_rows=invalid_count,
            )

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.MIGRATION_BATCH_VALIDATED.value,
                source_record_type="import_batches",
                source_record_id=batch.id,
                metadata_json={
                    "status": target_batch_status,
                    "total_rows": len(staged_rows),
                    "valid_rows": valid_count,
                    "invalid_rows": invalid_count,
                },
            )

            return updated_batch

    async def approve_batch(
        self,
        scope: dict[str, Any],
        batch_id: UUID,
    ) -> ImportBatch:
        """
        Approve a fully validated import batch.

        Args:
            scope: Authenticated requester scope.
            batch_id: Target batch UUID.

        Returns:
            ImportBatch: Approved import batch header.

        Raises:
            HTTPException: If unauthorized, invalid status, or invalid rows exist.
        """
        logger.info("Executing MigrationController.approve_batch for batch=%s", batch_id)
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            batch = await migration_crud.get_import_batch_by_id(
                session, batch_id, for_update=True
            )
            if batch is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found"
                )

            if batch.status != MigrationBatchStatus.VALIDATED.value:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Batch cannot be approved in status '{batch.status}'. "
                        "Must be 'VALIDATED'."
                    ),
                )

            if batch.total_rows == 0 or batch.invalid_rows > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Batch cannot be approved with {batch.invalid_rows} invalid rows.",
                )

            staged_rows = await migration_crud.get_all_staged_rows_by_batch(session, batch_id)

            # Warehouse scope verification for Warehouse Manager role
            if _is_warehouse_manager(scope):
                assigned_wh_ids = _scope_warehouse_ids(scope)
                for r in staged_rows:
                    if r.warehouse_id is not None and str(r.warehouse_id) not in assigned_wh_ids:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=(
                                "Warehouse Manager cannot approve batch containing "
                                f"row in warehouse '{r.warehouse_id}' outside "
                                "assigned scope."
                            ),
                        )

            approved_at = datetime.now(UTC)
            approved_batch = await migration_crud.mark_batch_approved(
                session, batch, approved_by_user_id=actor_id, approved_at=approved_at
            )

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.MIGRATION_BATCH_APPROVED.value,
                source_record_type="import_batches",
                source_record_id=batch.id,
                metadata_json={"approved_at": approved_at.isoformat()},
            )

            return approved_batch

    async def apply_batch(
        self,
        scope: dict[str, Any],
        batch_id: UUID,
    ) -> ImportBatch:
        """
        Apply an approved opening inventory batch to the ledger and operational projections.

        Args:
            scope: Authenticated requester scope.
            batch_id: Target batch UUID.

        Returns:
            ImportBatch: Applied import batch header.

        Raises:
            HTTPException: If unauthorized or batch not approved.
        """
        logger.info("Executing MigrationController.apply_batch for batch=%s", batch_id)
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            batch = await migration_crud.get_import_batch_by_id(
                session, batch_id, for_update=True
            )
            if batch is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found"
                )

            # Idempotency check: if already APPLIED, return cleanly
            if batch.status == MigrationBatchStatus.APPLIED.value:
                logger.info("Batch %s already applied, returning idempotently", batch_id)
                return batch

            if batch.status != MigrationBatchStatus.APPROVED.value:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Batch cannot be applied in status '{batch.status}'. "
                        "Must be 'APPROVED'."
                    ),
                )

            staged_rows = await migration_crud.get_all_staged_rows_by_batch(session, batch_id)
            valid_rows = [
                row
                for row in staged_rows
                if row.validation_status == StagedRowValidationStatus.VALID.value
            ]

            if not valid_rows:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Batch has no valid staged rows to apply",
                )

            # Warehouse scope verification
            if _is_warehouse_manager(scope):
                assigned_wh_ids = _scope_warehouse_ids(scope)
                for r in valid_rows:
                    if r.warehouse_id is not None and str(r.warehouse_id) not in assigned_wh_ids:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=(
                                "Warehouse Manager cannot apply batch containing rows "
                                "outside assigned warehouse scope."
                            ),
                        )

            applied_at = datetime.now(UTC)
            try:
                applied_batch = await migration_crud.apply_staged_rows_to_ledger(
                    session,
                    batch,
                    valid_rows,
                    applied_by_user_id=actor_id,
                    applied_at=applied_at,
                )
            except ValueError as error:
                logger.warning("Migration batch apply conflict: %s", error)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(error),
                ) from error

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.MIGRATION_BATCH_APPLIED.value,
                source_record_type="import_batches",
                source_record_id=batch.id,
                metadata_json={
                    "applied_at": applied_at.isoformat(),
                    "rows_applied": len(valid_rows),
                },
            )

            return applied_batch

    async def get_reconciliation_report(
        self,
        scope: dict[str, Any],
        batch_id: UUID,
    ) -> dict[str, Any]:
        """
        Generate a migration rehearsal reconciliation report comparing staged vs ledger position.

        Args:
            scope: Authenticated requester scope.
            batch_id: Target batch UUID.

        Returns:
            dict[str, Any]: Structured reconciliation report dictionary.

        Raises:
            HTTPException: If batch not found.
        """
        logger.info(
            "Executing MigrationController.get_reconciliation_report for batch=%s",
            batch_id,
        )
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})

        async with transaction_session() as session:
            batch = await migration_crud.get_import_batch_by_id(session, batch_id)
            if batch is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found"
                )

            staged_rows = await migration_crud.get_all_staged_rows_by_batch(session, batch_id)
            movements = await migration_crud.get_migration_movements_by_batch(session, batch_id)

            # Build comparison map
            staged_totals: dict[tuple, Decimal] = {}
            for r in staged_rows:
                if (
                    r.validation_status == StagedRowValidationStatus.VALID.value
                    and r.quantity is not None
                ):
                    key = (
                        r.raw_seller_code or "UNKNOWN",
                        r.raw_sku or "UNKNOWN",
                        r.raw_warehouse_code or "UNKNOWN",
                        r.raw_location_code or "NONE",
                        r.inventory_state or "UNKNOWN",
                    )
                    staged_totals[key] = staged_totals.get(key, Decimal("0.00")) + r.quantity

            movement_totals: dict[tuple, Decimal] = {}
            for m in movements:
                # We fetch seller/product/warehouse codes for display
                seller = await identity_crud.get_seller_by_id(session, m.seller_id)
                product = await catalog_crud.get_product_by_id(session, m.product_id)
                wh = await identity_crud.get_warehouse_by_id(session, m.warehouse_id)
                loc_code = "NONE"
                if m.location_id is not None:
                    loc_stmt = await catalog_crud.list_warehouse_locations(
                        session, warehouse_id=m.warehouse_id, limit=200, offset=0
                    )
                    loc_match = [l for l in loc_stmt if l.id == m.location_id]
                    if loc_match:
                        loc_code = loc_match[0].code

                key = (
                    seller.code if seller else "UNKNOWN",
                    product.sku if product else "UNKNOWN",
                    wh.code if wh else "UNKNOWN",
                    loc_code,
                    m.inventory_state,
                )
                movement_totals[key] = (
                    movement_totals.get(key, Decimal("0.00")) + m.quantity_delta
                )

            all_keys = set(staged_totals.keys()).union(set(movement_totals.keys()))
            details: list[dict[str, Any]] = []
            overall_mismatch = False

            for key in sorted(all_keys):
                staged_qty = staged_totals.get(key, Decimal("0.00"))
                mov_qty = movement_totals.get(key, Decimal("0.00"))
                var_qty = mov_qty - staged_qty
                row_status = "MATCH" if var_qty == Decimal("0.00") else "MISMATCH"
                if row_status == "MISMATCH":
                    overall_mismatch = True

                details.append({
                    "seller_code": key[0],
                    "sku": key[1],
                    "warehouse_code": key[2],
                    "location_code": key[3] if key[3] != "NONE" else None,
                    "inventory_state": key[4],
                    "staged_approved_quantity": staged_qty,
                    "ledger_movement_quantity": mov_qty,
                    "balance_projection_quantity": mov_qty,  # projection updated identically
                    "variance_quantity": var_qty,
                    "status": row_status,
                })

            if not overall_mismatch and details:
                report_status = "MATCH"
            elif not details and batch.total_rows == 0:
                report_status = "MATCH"
            else:
                report_status = "MISMATCH"

            return {
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "batch_status": batch.status,
                "total_staged_rows": batch.total_rows,
                "applied_movements_count": len(movements),
                "reconciliation_status": report_status,
                "details": details,
            }


migration_controller = MigrationController()

"""
--------------------------------------------------------------------------------
File        : core/apis/routes/migration_routes.py
Purpose     : Expose opening inventory migration API endpoints.

Responsibilities:
    - Validate migration HTTP request bodies and path parameters.
    - Authenticate and obtain warehouse/seller permission scope.
    - Delegate migration workflows to MigrationController.

Flow:
    HTTP request -> Route validates -> MigrationController -> Response schema

Used By:
    - core/apis/api.py

Returns:
    APIRouter - Registered migration API routes.

Raises:
    HTTPException: For authorization, validation, conflict, or internal errors.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from common.logger import get_logger
from common.rate_limit import migration_upload_rate_limiter
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.migration_request import (
    CreateImportBatchRequest,
    SubmitStagedRowsRequest,
)
from core.apis.schemas.responses.migration_response import (
    ImportBatchResponse,
    MigrationUploadResponse,
    MigrationReconciliationReportResponse,
    StagedRowResponse,
    ValidationSummaryResponse,
)
from core.controllers.migration_controller import migration_controller

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/migration", tags=["Migration"])


def _raise_internal_error(route_label: str, error: Exception) -> None:
    """
    Log an unexpected route error and raise the normalized API response.

    Args:
        route_label: Human-readable route label for logs.
        error: Original exception.

    Returns:
        None.

    Raises:
        HTTPException: Always raises a 500 response.
    """
    logger.error("Error in %s endpoint: %s", route_label, error, exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal Server Error",
    ) from error


@router.post(
    "/batches",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new opening inventory import batch",
    dependencies=[Depends(migration_upload_rate_limiter)],
)
async def create_batch(
    request: CreateImportBatchRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> ImportBatchResponse:
    """
    Create a new opening inventory import batch header.

    Args:
        request: Batch creation parameters.
        scope: Authenticated requester scope dependency.

    Returns:
        ImportBatchResponse: Created import batch.

    Raises:
        HTTPException: For authorization or server errors.
    """
    try:
        logger.info("Calling POST /v1/migration/batches endpoint")
        batch = await migration_controller.create_batch(
            scope, source_notes=request.source_notes
        )
        return ImportBatchResponse.model_validate(batch)
    except HTTPException:
        raise
    except Exception as error:
        _raise_internal_error("POST /v1/migration/batches", error)


@router.get(
    "/batches",
    response_model=list[ImportBatchResponse],
    status_code=status.HTTP_200_OK,
    summary="List opening inventory import batches",
)
async def list_batches(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[ImportBatchResponse]:
    """
    List opening inventory import batches.

    Args:
        limit: Max rows.
        offset: Offset.
        scope: Authenticated requester scope dependency.

    Returns:
        list[ImportBatchResponse]: Matching import batches.

    Raises:
        HTTPException: For authorization or server errors.
    """
    try:
        logger.info("Calling GET /v1/migration/batches endpoint")
        batches = await migration_controller.list_batches(scope, limit=limit, offset=offset)
        return [ImportBatchResponse.model_validate(b) for b in batches]
    except HTTPException:
        raise
    except Exception as error:
        _raise_internal_error("GET /v1/migration/batches", error)


@router.get(
    "/batches/{batch_id}",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Get import batch details",
)
async def get_batch(
    batch_id: UUID,
    scope: dict = Depends(get_warehouse_scope),
) -> ImportBatchResponse:
    """
    Retrieve import batch details by UUID.

    Args:
        batch_id: Import batch UUID.
        scope: Authenticated requester scope dependency.

    Returns:
        ImportBatchResponse: Import batch details.

    Raises:
        HTTPException: If batch not found or server error.
    """
    try:
        logger.info("Calling GET /v1/migration/batches/%s endpoint", batch_id)
        batch = await migration_controller.get_batch(scope, batch_id)
        return ImportBatchResponse.model_validate(batch)
    except HTTPException:
        raise
    except Exception as error:
        _raise_internal_error(f"GET /v1/migration/batches/{batch_id}", error)


@router.post(
    "/batches/{batch_id}/rows",
    response_model=list[StagedRowResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit raw opening inventory rows for staging",
    dependencies=[Depends(migration_upload_rate_limiter)],
)
async def submit_staged_rows(
    batch_id: UUID,
    request: SubmitStagedRowsRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> list[StagedRowResponse]:
    """
    Submit raw opening inventory rows for staging under an import batch.

    Args:
        batch_id: Import batch UUID.
        request: Row submission payload.
        scope: Authenticated requester scope dependency.

    Returns:
        list[StagedRowResponse]: Staged rows for the batch.

    Raises:
        HTTPException: On status conflict, duplicate content hash mismatch, or server error.
    """
    try:
        logger.info("Calling POST /v1/migration/batches/%s/rows endpoint", batch_id)
        rows_data = [row.model_dump() for row in request.rows]
        rows = await migration_controller.submit_staged_rows(
            scope, batch_id, rows_data
        )
        return [StagedRowResponse.model_validate(r) for r in rows]
    except HTTPException:
        raise
    except Exception as error:
        _raise_internal_error(f"POST /v1/migration/batches/{batch_id}/rows", error)


@router.post(
    "/batches/{batch_id}/upload",
    response_model=MigrationUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload CSV/XLSX file to stage opening inventory rows",
    dependencies=[Depends(migration_upload_rate_limiter)],
)
async def upload_batch_file(
    batch_id: UUID,
    file: UploadFile = File(...),
    scope: dict = Depends(get_warehouse_scope),
) -> MigrationUploadResponse:
    """
    Upload a CSV/XLSX opening inventory source file into migration staging.

    Args:
        batch_id: Import batch UUID.
        file: Uploaded source file.
        scope: Authenticated requester scope dependency.

    Returns:
        MigrationUploadResponse: Upload parsing and staging summary.

    Raises:
        HTTPException: On unsupported file type, staging conflict, or server error.
    """
    try:
        logger.info("Calling POST /v1/migration/batches/%s/upload endpoint", batch_id)
        file_bytes = await file.read()
        response = await migration_controller.upload_staged_rows_file(
            scope,
            batch_id,
            file.filename or "",
            file_bytes,
        )
        return MigrationUploadResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        _raise_internal_error(f"POST /v1/migration/batches/{batch_id}/upload", error)


@router.post(
    "/batches/{batch_id}/validate",
    response_model=ValidationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate staged opening inventory rows",
)
async def validate_batch(
    batch_id: UUID,
    scope: dict = Depends(get_warehouse_scope),
) -> ValidationSummaryResponse:
    """
    Trigger validation of all staged rows in an import batch.

    Args:
        batch_id: Target import batch UUID.
        scope: Authenticated requester scope dependency.

    Returns:
        ValidationSummaryResponse: Updated batch validation summary.

    Raises:
        HTTPException: For validation conflicts, unprocessable batch, or server error.
    """
    try:
        logger.info("Calling POST /v1/migration/batches/%s/validate endpoint", batch_id)
        batch = await migration_controller.validate_batch(scope, batch_id)
        return ValidationSummaryResponse(
            batch_id=batch.id,
            batch_number=batch.batch_number,
            status=batch.status,
            total_rows=batch.total_rows,
            valid_rows=batch.valid_rows,
            invalid_rows=batch.invalid_rows,
        )
    except HTTPException:
        raise
    except Exception as error:
        _raise_internal_error(f"POST /v1/migration/batches/{batch_id}/validate", error)


@router.post(
    "/batches/{batch_id}/approve",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a validated import batch",
)
async def approve_batch(
    batch_id: UUID,
    scope: dict = Depends(get_warehouse_scope),
) -> ImportBatchResponse:
    """
    Approve a fully validated import batch.

    Args:
        batch_id: Target import batch UUID.
        scope: Authenticated requester scope dependency.

    Returns:
        ImportBatchResponse: Approved import batch details.

    Raises:
        HTTPException: If unauthorized, unvalidated, or invalid rows exist.
    """
    try:
        logger.info("Calling POST /v1/migration/batches/%s/approve endpoint", batch_id)
        batch = await migration_controller.approve_batch(scope, batch_id)
        return ImportBatchResponse.model_validate(batch)
    except HTTPException:
        raise
    except Exception as error:
        _raise_internal_error(f"POST /v1/migration/batches/{batch_id}/approve", error)


@router.post(
    "/batches/{batch_id}/apply",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply approved opening inventory batch to ledger",
)
async def apply_batch(
    batch_id: UUID,
    scope: dict = Depends(get_warehouse_scope),
) -> ImportBatchResponse:
    """
    Apply an approved opening inventory batch to the ledger and operational projections.

    Args:
        batch_id: Target import batch UUID.
        scope: Authenticated requester scope dependency.

    Returns:
        ImportBatchResponse: Applied import batch details.

    Raises:
        HTTPException: If unauthorized, unapproved, or server error.
    """
    try:
        logger.info("Calling POST /v1/migration/batches/%s/apply endpoint", batch_id)
        batch = await migration_controller.apply_batch(scope, batch_id)
        return ImportBatchResponse.model_validate(batch)
    except HTTPException:
        raise
    except Exception as error:
        _raise_internal_error(f"POST /v1/migration/batches/{batch_id}/apply", error)


@router.get(
    "/batches/{batch_id}/reconciliation",
    response_model=MigrationReconciliationReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Read migration rehearsal reconciliation report",
)
async def get_reconciliation(
    batch_id: UUID,
    scope: dict = Depends(get_warehouse_scope),
) -> MigrationReconciliationReportResponse:
    """
    Retrieve migration rehearsal reconciliation report for a batch.

    Args:
        batch_id: Target import batch UUID.
        scope: Authenticated requester scope dependency.

    Returns:
        MigrationReconciliationReportResponse: Rehearsal reconciliation report.

    Raises:
        HTTPException: If batch not found or server error.
    """
    try:
        logger.info("Calling GET /v1/migration/batches/%s/reconciliation endpoint", batch_id)
        report = await migration_controller.get_reconciliation_report(scope, batch_id)
        return MigrationReconciliationReportResponse.model_validate(report)
    except HTTPException:
        raise
    except Exception as error:
        _raise_internal_error(
            f"GET /v1/migration/batches/{batch_id}/reconciliation",
            error,
        )

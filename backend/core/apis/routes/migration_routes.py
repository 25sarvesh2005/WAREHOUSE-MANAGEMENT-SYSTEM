"""
FastAPI HTTP endpoints for opening inventory migration.
"""

from __future__ import annotations

from typing import Annotated
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
    MigrationReconciliationReportResponse,
    MigrationUploadResponse,
    StagedRowResponse,
    ValidationSummaryResponse,
)
from core.controllers.migration_controller import migration_controller

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/migration", tags=["Migration"])


@router.post(
    "/batches",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new opening inventory import batch",
    dependencies=[Depends(migration_upload_rate_limiter)],
)
async def create_batch(
    request: CreateImportBatchRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ImportBatchResponse:
    """Create a new opening inventory import batch header.

    Provisions a named batch container to stage and validate opening inventory rows.
    """
    try:
        logger.info("Calling POST /v1/migration/batches endpoint")
        batch = await migration_controller.create_batch(scope, source_notes=request.source_notes)
        return ImportBatchResponse.model_validate(batch)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/migration/batches endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/batches",
    response_model=list[ImportBatchResponse],
    status_code=status.HTTP_200_OK,
    summary="List opening inventory import batches",
)
async def list_batches(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ImportBatchResponse]:
    """List opening inventory import batches.

    Returns batches scoped to the authenticated requester's accessible warehouses.
    """
    try:
        logger.info("Calling GET /v1/migration/batches endpoint")
        batches = await migration_controller.list_batches(scope, limit=limit, offset=offset)
        return [ImportBatchResponse.model_validate(b) for b in batches]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/migration/batches endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/batches/{batch_id}",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Get import batch details",
)
async def get_batch(
    batch_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ImportBatchResponse:
    """Retrieve import batch details by UUID.

    Returns full batch record including row counts and current processing status.
    """
    try:
        logger.info(f"Calling GET /v1/migration/batches/{batch_id} endpoint")
        batch = await migration_controller.get_batch(scope, batch_id)
        return ImportBatchResponse.model_validate(batch)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/migration/batches/{batch_id} endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> list[StagedRowResponse]:
    """Submit raw opening inventory rows for staging under an import batch.

    Rows are stored with PENDING status awaiting validation before apply.
    """
    try:
        logger.info(f"Calling POST /v1/migration/batches/{batch_id}/rows endpoint")
        rows_data = [row.model_dump() for row in request.rows]
        rows = await migration_controller.submit_staged_rows(scope, batch_id, rows_data)
        return [StagedRowResponse.model_validate(r) for r in rows]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/migration/batches/{batch_id}/rows endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/batches/{batch_id}/upload",
    response_model=MigrationUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload CSV/XLSX file to stage opening inventory rows",
    dependencies=[Depends(migration_upload_rate_limiter)],
)
async def upload_batch_file(
    batch_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    file: UploadFile = File(...),
) -> MigrationUploadResponse:
    """Upload a CSV/XLSX opening inventory source file into migration staging.

    Parses the file and stages all valid rows under the specified import batch.
    """
    try:
        logger.info(f"Calling POST /v1/migration/batches/{batch_id}/upload endpoint")
        file_bytes = await file.read()
        response = await migration_controller.upload_staged_rows_file(
            scope,
            batch_id,
            file.filename or "",
            file_bytes,
        )
        return MigrationUploadResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/migration/batches/{batch_id}/upload endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/batches/{batch_id}/validate",
    response_model=ValidationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate staged opening inventory rows",
)
async def validate_batch(
    batch_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ValidationSummaryResponse:
    """Trigger validation of all staged rows in an import batch.

    Checks product references, quantities, and warehouse scoping for every staged row.
    """
    try:
        logger.info(f"Calling POST /v1/migration/batches/{batch_id}/validate endpoint")
        batch = await migration_controller.validate_batch(scope, batch_id)
        return ValidationSummaryResponse(
            batch_id=batch.id,
            batch_number=batch.batch_number,
            status=batch.status,
            total_rows=batch.total_rows,
            valid_rows=batch.valid_rows,
            invalid_rows=batch.invalid_rows,
        )
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/migration/batches/{batch_id}/validate endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/batches/{batch_id}/approve",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a validated import batch",
)
async def approve_batch(
    batch_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ImportBatchResponse:
    """Approve a fully validated import batch.

    Transitions the batch to APPROVED status, enabling it to be applied to the ledger.
    """
    try:
        logger.info(f"Calling POST /v1/migration/batches/{batch_id}/approve endpoint")
        batch = await migration_controller.approve_batch(scope, batch_id)
        return ImportBatchResponse.model_validate(batch)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/migration/batches/{batch_id}/approve endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/batches/{batch_id}/apply",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply approved opening inventory batch to ledger",
)
async def apply_batch(
    batch_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ImportBatchResponse:
    """Apply an approved opening inventory batch to the ledger and operational projections.

    Converts staged rows into inventory movements and updates balance records.
    """
    try:
        logger.info(f"Calling POST /v1/migration/batches/{batch_id}/apply endpoint")
        batch = await migration_controller.apply_batch(scope, batch_id)
        return ImportBatchResponse.model_validate(batch)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/migration/batches/{batch_id}/apply endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/batches/{batch_id}/reconciliation",
    response_model=MigrationReconciliationReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Read migration rehearsal reconciliation report",
)
async def get_reconciliation(
    batch_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> MigrationReconciliationReportResponse:
    """Retrieve migration rehearsal reconciliation report for a batch.

    Compares staged row totals against live inventory balances to surface discrepancies.
    """
    try:
        logger.info(f"Calling GET /v1/migration/batches/{batch_id}/reconciliation endpoint")
        report = await migration_controller.get_reconciliation_report(scope, batch_id)
        return MigrationReconciliationReportResponse.model_validate(report)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(
            f"Error in GET /v1/migration/batches/{batch_id}/reconciliation endpoint: {error}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )

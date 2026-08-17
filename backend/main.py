"""
--------------------------------------------------------------------------------
File        : main.py
Purpose     : Create and configure the Whitfield Warehouse FastAPI application.

Responsibilities:
    - Load environment variables and configure application lifecycle.
    - Connect and close PostgreSQL resources.
    - Register routers, CORS, and health endpoints.

Flow:
    Process startup
        ->
    lifespan() connects database and seeds required records
        ->
    FastAPI serves API and health endpoints
        ->
    Process shutdown closes database connection

Used By:
    - uvicorn
    - tests using ASGITransport

Returns:
    app -> FastAPI - ASGI application object.

Raises:
    HTTPException: When readiness dependencies fail.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

load_dotenv()

from datetime import UTC, datetime
import time

from common.logger import get_logger
from common.request_id import RequestIDMiddleware
from core.apis.api import api_router
from core.config.settings import get_settings, validate_production_configuration
import asyncio
from core.database.database import (
    check_database_ready,
    close_database_connection,
    connect_to_database,
    transaction_session,
)
from core.database.seed import initialize_schema_for_development, seed_initial_data
from core.jobs.reservation_expiry_job import release_expired_reservations
from sqlalchemy import text

logger = get_logger(__name__)


async def _get_alembic_head() -> str:
    """Return the current applied Alembic migration revision from the database.

    Queries the alembic_version table directly so the health status reflects
    the real migration state rather than a hardcoded constant.

    Returns:
        str: Current applied revision hash, or 'unknown' if unavailable.

    Raises:
        None: Errors are swallowed and 'unknown' is returned to keep the
            health endpoint available even on schema issues.
    """
    try:
        async with transaction_session() as session:
            result = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            return str(row[0]) if row else "no_migrations_applied"
    except Exception as error:
        logger.warning("Could not read alembic_version: %s", error)
        return "unknown"


async def _periodic_reservation_expiry_worker(interval_seconds: int = 60) -> None:
    """Periodically release expired reservations in background."""
    logger.info("Reservation expiry background worker started (interval=%ds)", interval_seconds)
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            async with transaction_session() as session:
                result = await release_expired_reservations(session)
                if result.get("released_reservations_count", 0) > 0:
                    logger.info("Background expiry released: %s", result)
        except asyncio.CancelledError:
            logger.info("Reservation expiry background worker cancelled")
            break
        except Exception as error:
            logger.error("Error in reservation expiry background worker: %s", error, exc_info=True)


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    """
    Manage application startup and shutdown lifecycle.

    Startup connects to PostgreSQL, optionally initializes the development/test
    schema, and seeds required bootstrap records before requests are served.

    Args:
        app_instance: FastAPI application instance.

    Yields:
        None: Control back to FastAPI while the app is running.

    Raises:
        Exception: If startup database initialization or production validation fails.
    """
    logger.info("Starting Whitfield Warehouse API")
    runtime_settings = get_settings()
    warnings = validate_production_configuration(runtime_settings)
    for warning in warnings:
        logger.warning("Configuration Warning: %s", warning)

    await connect_to_database()

    if runtime_settings.initialize_schema_on_startup:
        logger.info("Schema auto-init enabled (INITIALIZE_SCHEMA_ON_STARTUP=true)")
        await initialize_schema_for_development()
    else:
        logger.info(
            "Schema auto-init skipped (INITIALIZE_SCHEMA_ON_STARTUP=false) "
            "— Alembic migrations are expected to be applied externally."
        )

    await seed_initial_data()
    expiry_task = asyncio.create_task(_periodic_reservation_expiry_worker())
    try:
        yield
    finally:
        expiry_task.cancel()
        try:
            await expiry_task
        except asyncio.CancelledError:
            pass
        await close_database_connection()
        logger.info("Whitfield Warehouse API shutdown complete")


settings = get_settings()
_is_production = settings.app_env == "production"

app = FastAPI(
    title="Whitfield Fulfillment Warehouse Operations API",
    description="Transactional warehouse operations and seller visibility platform.",
    version="0.1.0",
    lifespan=lifespan,
    # Hide interactive API docs in production to prevent surface disclosure.
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# TrustedHostMiddleware is outermost — rejects spoofed Host headers before
# CORS or any business logic runs. Returns 400 for untrusted hosts.
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts_list,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RequestIDMiddleware runs inside CORS: reads/generates X-Request-ID, sets
# request.state.request_id and REQUEST_ID_CTX_VAR for log correlation.
app.add_middleware(RequestIDMiddleware)

app.include_router(api_router)


@app.get("/", status_code=status.HTTP_200_OK, summary="Root health summary")
async def root() -> dict[str, str]:
    """
    Return a lightweight application summary.

    This endpoint verifies the process is serving HTTP without checking external
    dependencies.

    Returns:
        dict[str, str]: Application name and status.

    Raises:
        None.
    """
    return {"service": "whitfield-warehouse-operations", "status": "running"}


@app.get("/health/live", status_code=status.HTTP_200_OK, summary="Liveness health check")
async def liveness() -> dict[str, str]:
    """
    Return process liveness status.

    Liveness intentionally avoids external dependency checks so orchestration can
    distinguish process failure from temporary dependency unavailability.

    Returns:
        dict[str, str]: Liveness status.

    Raises:
        None.
    """
    return {"status": "live"}


@app.get("/health/ready", status_code=status.HTTP_200_OK, summary="Readiness health check")
async def readiness() -> dict[str, str]:
    """
    Return application readiness status.

    Readiness verifies database connectivity and returns a generic 503 if the
    required dependency check fails.

    Returns:
        dict[str, str]: Readiness status.

    Raises:
        HTTPException: If the database is not ready.
    """
    try:
        await check_database_ready()
        return {"status": "ready"}
    except Exception as error:
        logger.error("Readiness check failed: %s", error, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is not ready",
        ) from error


@app.get(
    "/health/status",
    status_code=status.HTTP_200_OK,
    summary="Structured operational status and diagnostic health report",
)
async def operational_status() -> dict[str, object]:
    """
    Provide structured runtime operations status including database, migrations, and AI readiness.

    Returns:
        dict[str, object]: Comprehensive health diagnostic status.
    """
    current_settings = get_settings()
    db_status = "unhealthy"
    db_latency_ms = None
    t0 = time.perf_counter()
    try:
        await check_database_ready()
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        db_status = "connected"
    except Exception as exc:
        logger.warning("Database health check issue: %s", exc)

    ai_configured = False
    if current_settings.ai_provider == "google_genai":
        ai_configured = bool(
            current_settings.google_genai_api_key.strip()
            or current_settings.google_api_key.strip()
        )

    ai_status = "DISABLED"
    if current_settings.ai_enabled:
        ai_status = "HEALTHY" if ai_configured else "KEY_MISSING"

    voice_stt_configured = bool(
        (current_settings.voice_stt_provider == "deepgram" and current_settings.deepgram_api_key.strip())
        or (current_settings.voice_stt_provider == "sarvam" and current_settings.sarvam_api_key.strip())
    )
    voice_tts_configured = bool(
        current_settings.voice_tts_provider == "sarvam" and current_settings.sarvam_api_key.strip()
    )

    overall_status = "HEALTHY" if db_status == "connected" else "DEGRADED"
    warnings = validate_production_configuration(current_settings)

    return {
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "whitfield-warehouse-operations",
        "version": "0.1.0",
        "app_env": current_settings.app_env,
        "database": {
            "status": db_status,
            "latency_ms": db_latency_ms,
        },
        "alembic_head": await _get_alembic_head(),
        "ai": {
            "enabled": current_settings.ai_enabled,
            "provider": current_settings.ai_provider,
            "model": current_settings.ai_model,
            "status": ai_status,
        },
        "voice": {
            "stt_provider": current_settings.voice_stt_provider,
            "tts_provider": current_settings.voice_tts_provider,
            "stt_configured": voice_stt_configured,
            "tts_configured": voice_tts_configured,
            "default_language": current_settings.voice_default_language,
        },
        "warnings": warnings,
    }


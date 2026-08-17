"""
--------------------------------------------------------------------------------
File        : core/apis/api.py
Purpose     : Aggregate versioned API routers.

Responsibilities:
    - Create the `/api` router boundary.
    - Register domain route modules in one place.
    - Apply the global default rate limit to all routes.

Flow:
    main.py
        ->
    app.include_router(api_router)
        ->
    Versioned route modules

Used By:
    - main.py

Returns:
    api_router -> APIRouter - Mounted application API router.

Raises:
    None.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from common.rate_limit import global_rate_limiter
from core.apis.routes.ai_routes import router as ai_router
from core.apis.routes.catalog_routes import router as catalog_router
from core.apis.routes.fulfillment_routes import router as fulfillment_router
from core.apis.routes.identity_routes import router as identity_router
from core.apis.routes.inventory_routes import router as inventory_router
from core.apis.routes.migration_routes import router as migration_router
from core.apis.routes.order_routes import router as order_router
from core.apis.routes.receiving_routes import router as receiving_router
from core.apis.routes.reporting_routes import router as reporting_router
from core.apis.routes.return_routes import router as return_router
from core.apis.routes.seller_routes import router as seller_router
from core.apis.routes.transfer_routes import router as transfer_router
from core.apis.routes.voice_routes import router as voice_router

# The global_rate_limiter dependency is applied here at the aggregator level
# so every route in every domain router inherits the 120 req/min default.
# Routes that need stricter limits (auth, AI, voice, migration) declare their
# own tighter dependencies on top of this baseline.
api_router = APIRouter(prefix="/api", dependencies=[Depends(global_rate_limiter)])
api_router.include_router(ai_router)
api_router.include_router(voice_router)
api_router.include_router(identity_router)
api_router.include_router(catalog_router)
api_router.include_router(inventory_router)
api_router.include_router(receiving_router)
api_router.include_router(order_router)
api_router.include_router(fulfillment_router)
api_router.include_router(transfer_router)
api_router.include_router(return_router)
api_router.include_router(seller_router)
api_router.include_router(reporting_router)
api_router.include_router(migration_router)

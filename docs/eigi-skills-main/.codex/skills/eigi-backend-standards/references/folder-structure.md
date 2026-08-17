# Eigi Backend Folder Structure

Use this reference when adding backend files or deciding where code belongs. Vaani Core (`agent-360/backend/vaani_core`) is the canonical example, but the same responsibilities apply across Eigi repos.

Every new or modified function and method in these folders must include a docstring. Keep short helper docstrings concise, but do not omit them.

## Top-Level Backend Files

- `main.py`: Runtime entrypoint. Load environment variables, expose the ASGI `app`, configure the process logger, and start Uvicorn when executed directly. Keep application wiring in the API app module, not here.
- `.gitignore`: Required for every backend structure, even before GitHub/Git initialization. Keep secrets, virtualenvs, caches, logs, generated files, and local databases out of source control.
- `requirements.txt` or equivalent dependency file: Backend runtime dependencies.
- `Dockerfile`, `run.sh`, scripts: Deployment and local startup helpers. Do not put API logic here.
- `logs/`: Runtime log output. Application code should write through logger helpers, not manually create ad hoc log files.

Use this compact backend `.gitignore` baseline and extend it only for repo-specific generated files:

```gitignore
.env
.env.*
!.env.example
venv/
.venv/
__pycache__/
*.py[cod]
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage
dist/
build/
*.egg-info/
logs/
*.log
*.sqlite*
.DS_Store
.idea/
.vscode/
```

## `commons/`

Use `commons/` for shared cross-cutting helpers used by multiple backend layers.

- `commons/logger.py`: Central logging setup. It creates file handlers, applies a formatter, prevents duplicate propagation, and exposes `logger(__name__)` for normal modules. It may also expose specialized loggers such as conversation, S3, infra, scheduler, or LoRA loggers.
- `commons/auth.py`, `auth_utils.py`, `api_key_auth.py`, `public_auth.py`, `proxy_auth.py`: Authentication and authorization helpers. Keep token parsing, API key validation, cookie handling, and shared auth utilities here when they are reused across routes.
- `commons/cookie_utils.py`, `s3_utils.py`, `oauth_utils.py`: Shared utility code that is not tied to one controller.

Do not put business workflows in `commons/`. If logic belongs to one domain, put it under that domain's controller/service.

## `core/apis/api.py`

Use this as the FastAPI application aggregator.

Responsibilities:

- Create the `FastAPI` app.
- Define application lifespan startup/shutdown behavior.
- Connect and close database clients.
- Start and stop schedulers or dispatchers.
- Configure global exception handlers.
- Configure CORS and custom middleware.
- Import routers from `core/apis/routes`.
- Register routers with `app.include_router(...)` and clear tags/prefixes.

Do not implement endpoint business logic here. Add a new router import and `app.include_router(...)` entry when creating a new API surface.

## `core/apis/routes/`

Use route modules for HTTP endpoint definitions.

Responsibilities:

- Create an `APIRouter`.
- Declare HTTP methods, paths, status codes, dependencies, path/query/body params, and response models.
- Add docstrings to every route handler.
- Decode route-level auth if that is the local pattern.
- Log `Calling METHOD /path endpoint`.
- Call the relevant controller method.
- Catch and re-raise `HTTPException`; convert unknown errors to a route-level 500.

Routes should not contain database queries, provider calls, or multi-step domain workflows.

## `core/apis/schemas/requests/`

Use request schemas for API input contracts.

Responsibilities:

- Define Pydantic `BaseModel` classes for request bodies.
- Add `Field` constraints, defaults, descriptions, and examples when useful.
- Reuse enums from models or domain modules when the value is part of the domain.
- Keep transport validation here, not persistence behavior.

## `core/apis/schemas/responses/`

Use response schemas for API output contracts.

Responsibilities:

- Define Pydantic response models returned by routes.
- Hide internal-only fields and raw secrets.
- Use `from_attributes = True` or local equivalent when serializing model objects.
- Keep response wrappers consistent with nearby endpoints.

## `core/controllers/`

Use controllers for domain orchestration.

Responsibilities:

- Instantiate CRUD classes and services used by the domain.
- Add docstrings to every controller method.
- Enforce ownership, role, status, and business rules.
- Coordinate several CRUD/service calls into one API operation.
- Raise meaningful `HTTPException`s for domain failures.
- Log `Executing Controller.method`, warnings for expected rejected states, and errors for unexpected failures.
- Return dictionaries or response-ready objects expected by routes.

Controllers should not define HTTP routes and should not contain low-level provider client setup unless no service layer exists yet.

## `core/cruds/`

Use CRUD classes for persistence operations.

Responsibilities:

- Define the domain CRUD class directly in the resource CRUD file unless the target repo already has a required local base class.
- Import the domain model used by the CRUD operations.
- Add docstrings to every CRUD method.
- Implement database-specific queries and updates.
- Own database/session access when the repo exposes a shared database/session helper from `database.py` or the local equivalent. In that style, routes and controllers should not accept or pass a `db` parameter.
- Convert string IDs to ObjectId when needed.
- Log `Executing CRUDClass.method` and persistence errors.
- Return models, lists, booleans, counts, or persistence-specific results.

CRUD methods should not decode auth tokens, inspect HTTP requests, or assemble final API response envelopes.

## `core/models/`

Use models for stored data shape.

Responsibilities:

- Define ODMantic, SQLAlchemy, Pydantic, or repo-specific persistence models.
- Define collection/table names, timestamps, default factories, indexes, and storage-only fields.
- Define enums tightly coupled to stored domain values.
- Store secrets only as hashes, encrypted values, or redacted display prefixes when possible.

Models should not call external services or perform route/controller workflows.

## `core/services/`

Use services for external integrations and reusable complex behavior.

Common service folder patterns:

- `service.py`: Main service facade for the domain.
- `client.py` or `client_manager.py`: Provider client lifecycle.
- `providers/`: Provider-specific implementations behind a common interface.
- `exceptions/`: Domain-specific service exceptions.
- Domain subfolders such as `chat/`, `mcp/`, `proxy/`, `payment/`, `voice/`, `video/`, `eigi/`, or `memory/`.

Responsibilities:

- Call external APIs and SDKs.
- Add docstrings to every service function and method.
- Manage provider-specific request/response normalization.
- Own retries, timeouts, connection health, and cleanup when relevant.
- Implement reusable workflows that are too large or too provider-specific for controllers.
- Log method entry, provider success/failure, and cleanup failures.

Services should not own route-level auth parsing or FastAPI dependency declarations.

## `core/database/`

Use database modules for database lifecycle and shared persistence setup.

Responsibilities:

- Create and expose database clients/engines.
- Provide shared database clients, engines, or session helpers used by CRUD classes.
- Connect and close database connections.
- Initialize default records.
- Create or verify indexes.
- Run startup migrations that are safe for app startup.

## `core/jobs/`, `core/config/`, `core/constants/`, `core/utils/`

- `core/jobs/`: Scheduler setup and recurring background jobs.
- `core/config/`: Configuration objects that are not plain environment loading.
- `core/constants/`: Shared constants and provider parameters.
- `core/utils/`: Reusable helpers that are more application-specific than `commons/`.

Do not use these folders as dumping grounds. Prefer a domain service when behavior belongs to a business capability.

## Adding a New API Surface

When adding a new backend feature:

1. Add request and response schemas if the endpoint has structured input/output.
2. Add or update the persistence model if storage shape changes.
3. Add CRUD methods for database operations.
4. Add a service only for external integrations or reusable complex workflows.
5. Add a controller method for domain orchestration and authorization.
6. Add a route that calls the controller and handles route-level auth/logging/errors.
7. Register the router in `core/apis/api.py` or the target repo's equivalent API aggregator.
8. Confirm every new or modified function and method has a docstring.

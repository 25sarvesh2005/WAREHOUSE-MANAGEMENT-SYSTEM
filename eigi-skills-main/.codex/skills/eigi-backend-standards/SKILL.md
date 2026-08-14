---
name: eigi-backend-standards
description: Shared Eigi backend engineering standards for creating, modifying, or reviewing backend code in any Eigi repo. Use for Python/FastAPI-style APIs and services that need consistent route/controller/service/CRUD layering, folder placement, required function docstrings, logging, try/except handling, schemas, and models. Use Vaani Core as the canonical reference implementation while adapting to the target repo's local structure.
---

# Eigi Backend Standards

Use this skill to write backend code that follows Eigi conventions. Inspect the target repo first, then apply the closest local pattern. When a repo has no stronger convention, use `agent-360/backend/vaani_core` as the reference implementation.

For detailed folder and file responsibilities, read [references/folder-structure.md](references/folder-structure.md) before adding new backend files or moving code between layers.

For concrete router, controller, CRUD, and service examples, read [references/examples.md](references/examples.md) before writing new backend modules.

## Core Flow

Prefer this layering for API work:

```text
API route -> controller -> service and/or CRUD -> model/database or external provider
```

- Keep routes thin: HTTP method/path, dependencies, auth token decoding, request parsing, response schema wrapping, and route-level error handling.
- Put business decisions in controllers: ownership checks, domain validation, orchestration, and response payload assembly.
- Put database access in CRUD classes: reads, writes, filters, ObjectId conversion, and persistence-specific operations.
- Put external integrations and reusable workflows in services.
- Put request/response wire contracts in schemas and storage shape in models.

## API Docstrings

Every new or modified function and method must have a docstring. This includes route handlers, controllers, CRUD methods, services, helpers, private methods, startup/shutdown functions, and validators.

Docstrings must start with a concise two-line description: first line for purpose, second line for behavior or business rule. If the function has parameters, include `Args` and describe each argument. If it can raise an exception or error, include `Raises` and list the expected error type/status.

Include `Returns` when the function returns a value. Add an `Example` only when the payload, query string, or behavior is not obvious. Use [references/examples.md](references/examples.md) for concrete docstring examples.

## Logging

Use the repo logger helper when available:

```python
from core import logger

logging = logger(__name__)
```

Use these log message patterns consistently:

- Route entry: `logging.info("Calling METHOD /path endpoint")`.
- Dynamic route entry: `logging.info(f"Calling GET /v1/resources/{resource_id} endpoint")`.
- Controller/service/CRUD entry: `logging.info("Executing ClassName.method_name")`.
- Expected blocked state: `logging.warning(...)` for inactive users, invalid ownership, missing records, duplicate names, invalid transitions, or denied access.
- Route error: `logging.error(f"Error in METHOD /path endpoint: {error}")`.
- Controller/service/CRUD error: `logging.error(f"Error in ClassName.method_name: {error}")`.

Do not log raw secrets, access tokens, API keys, passwords, private prompts, or full sensitive payloads. Log stable IDs, prefixes, counts, provider names, and state changes when useful.

## Route Error Handling

Wrap route handlers in `try`/`except`. Re-raise `HTTPException` unchanged and convert unknown exceptions to a consistent 500.

Keep route auth checks aligned with nearby code. In Vaani Core-style routes, decode the bearer token, reject missing/invalid users with `401`, reject inactive users with `403`, and delegate ownership/domain checks to the controller.

See [references/examples.md](references/examples.md) for a full router example.

## Controller Error Handling

Controllers should log method entry and make domain failures explicit.

Use controller `warning` logs for expected business rejections. Use `error` logs for unexpected failures. Do not hide useful 400/401/403/404/409 errors behind a generic 500.

See [references/examples.md](references/examples.md) for full controller examples, including duplicate checks, not-found checks, ownership checks, and unexpected error handling.

## CRUD and Service Rules

CRUD classes should be small persistence wrappers:

- Define the domain CRUD class directly in the resource CRUD file unless the target repo already has a required local base class.
- Import the model class used by the CRUD operations.
- Keep database/session wiring inside the CRUD layer when the repo exposes a shared database/session helper; do not add route/controller `db` parameters unless the target repo already requires dependency-injected sessions.
- Convert string IDs to ObjectId where the repo expects ObjectId storage.
- Log method entry and persistence failures.
- Re-raise database errors unless the CRUD method has enough context to return a domain-safe result.

Services should own provider clients, external calls, background workflows, and reusable non-CRUD logic. Services may normalize provider errors when they own the integration contract, but they should not contain route-only auth parsing or HTTP request glue.

## Schema and Model Rules

- Use request schemas for bodies and structured query payloads.
- Use response schemas when an endpoint returns structured data.
- Use `Field` constraints and descriptions for validation and OpenAPI clarity.
- Use enums for constrained status/type values.
- Keep secret storage hashed or redacted. Return raw secrets only at creation time when the product explicitly requires it.
- Keep timestamps, defaults, collection names, and storage-only fields in models.

## Repository Hygiene

When creating a backend structure, add or update `.gitignore` even if the repo is not Git-initialized yet. It must exclude environment files, virtualenvs, Python caches, test/build caches, logs, local databases, and editor/OS noise. See [references/folder-structure.md](references/folder-structure.md) for the compact backend template.

## Finish Checklist

- Inspect nearby files and follow local naming and response conventions.
- Read [references/folder-structure.md](references/folder-structure.md) when adding files or deciding layer placement.
- Read [references/examples.md](references/examples.md) when creating a new router, controller, CRUD class, or service.
- Keep routes thin and controllers responsible for domain orchestration.
- Add docstrings to every new or modified function and method.
- Add entry, warning, and error logs in the same format as existing backend code.
- Preserve meaningful domain `HTTPException`s.
- Add or update `.gitignore` for env files, virtualenvs, caches, logs, and generated artifacts.
- Register new routers in the app/API aggregator.

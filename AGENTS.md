# Whitfield Warehouse Management System — Agent Guide

This is the WMS monorepo for the Whitfield Fulfillment platform.
It contains a FastAPI backend (`backend/`) and a Vite + React frontend (`frontend/`).

## Eigi Skills

Use `.codex/skills/eigi-backend-standards` for all backend API work in `backend/`.
It guides route, controller, CRUD, service, schema, model, logging, docstring, test, and backend `.gitignore` standards.

Use `.codex/skills/eigi-frontend-standards` for all frontend work in `frontend/`.
It guides route/page, feature component, shared UI, API client, hook/store, styling, test, env, and frontend `.gitignore` standards.

Inspect nearby code first and follow the closest local convention.
Read the matching `SKILL.md` first and load references only when needed.

> [!NOTE]
> The eigi skills live in `eigi-skills-main/.codex/skills/`. Reference them as
> `eigi-skills-main/.codex/skills/eigi-backend-standards/SKILL.md` and
> `eigi-skills-main/.codex/skills/eigi-frontend-standards/SKILL.md`.

## Running the Application

### Backend

```powershell
cd backend
pip install -r requirements.txt        # first time only
# Copy .env.example to .env and fill in secrets
uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

Backend runs at **http://127.0.0.1:8080**. Swagger docs at `/docs`.

### Frontend

```powershell
cd frontend
npm install                            # first time only
npm run dev
```

Frontend dev server at **http://127.0.0.1:5173**. API calls are proxied to `http://127.0.0.1:8080` via Vite.

### Running Both Together (from repo root)

Open two terminals:
1. Terminal 1 → backend start command above
2. Terminal 2 → frontend start command above

## Architecture

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Database | PostgreSQL (async SQLAlchemy 2.x + asyncpg), Alembic |
| Auth | JWT, bcrypt |
| Frontend | Vite, React 19, TypeScript, TanStack Router |
| AI | Read-only assistant (Google GenAI) |
| Voice | Deepgram / Sarvam STT/TTS |
| CLI | Typer |

## Key Directories

```
backend/
  main.py                    # FastAPI entrypoint — run with uvicorn
  common/                    # shared: logger, auth, pagination, rate_limit
  core/
    apis/api.py              # router aggregator
    apis/routes/             # thin HTTP route handlers
    controllers/             # domain orchestration
    cruds/                   # persistence layer
    models/                  # SQLAlchemy models
    services/                # external integrations
    database/                # DB lifecycle, seed
    config/                  # Settings / Pydantic config
    jobs/                    # background jobs

frontend/
  src/
    routes/                  # TanStack Router pages
    components/              # shared + feature UI components
    lib/                     # api-client, types, auth, session
    hooks/                   # React hooks
    styles.css               # global styles
```

## CI

CI runs on push to `main`/`master`/`develop`. See `.github/workflows/ci.yml`.
Backend: import check, compileall, pytest, frontend-secret audit.
Frontend: typecheck, lint, production build.

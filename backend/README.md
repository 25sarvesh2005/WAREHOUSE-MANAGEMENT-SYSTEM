# Whitfield Warehouse Operations Backend

Enterprise backend service for Whitfield Fulfillment warehouse operations, real-time inventory ledger, bicoastal order fulfillment, AI assistant, and voice-guided receiving.

## Architecture

- **Framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL (SQLAlchemy 2.0 asyncpg + psycopg for migrations)
- **Migrations**: Alembic
- **Authentication**: JWT (HS256) + bcrypt
- **Observability**: Structured JSON-ready logging with per-request correlation ID tracking (`[rid=...]`)
- **Safety**: Multi-layer rate limiting, trusted host protection, transactional row-level locking

## Local Development

```powershell
# Install dependencies
pip install -r requirements.txt

# Run the dev server
uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

## Running Tests

```powershell
# Run full unit and E2E test suite
pytest tests/ -v
```

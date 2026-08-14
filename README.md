# Whitfield Fulfillment Warehouse Operations

Initial implementation scaffold for the warehouse operations platform described in
`IMPLEMENTATION.md`.

## Local Backend

1. Create a Python 3.11+ environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set `DATABASE_URL`,
   `MIGRATION_DATABASE_URL`, and `JWT_SECRET`.
4. Use the direct Supabase connection for both URLs when IPv6 is available. On
   an IPv4-only runtime, use the Supavisor session pooler on port 5432 for
   `DATABASE_URL` and retain the direct URL for migrations when reachable.
   Transaction pooling on port 6543 is reserved for serverless deployment and
   is intentionally rejected by this persistent backend.
5. Run `uvicorn main:app --reload`.

Passwords containing reserved URL characters must be percent-encoded. Keep real
credentials in `.env` or the deployment secret manager; never commit them or
place Supabase secret/service-role keys in frontend environment files.

Development schema initialization enables RLS on application tables and revokes
table privileges from Supabase's `anon` and `authenticated` roles. The browser
uses the FastAPI API, not Supabase Data API access. Future Alembic revisions must
preserve the same deny-by-default treatment for every new table in an exposed
schema.

The first implementation slice includes app wiring, health endpoints, authentication,
identity scope helpers, and master-data scaffolding for sellers, warehouses, locations,
products, identifiers, and seller order policies.

## Launch Hardening Checks

Before controlled launch, run the Phase 5 checklist in
`docs/runbooks/phase5_controlled_launch_checklist.md`. The repeatable frontend
secret audit is:

```powershell
python -m tools.audit_frontend_secrets
```

It scans browser-delivered source and build artifacts for backend-only secret
markers such as Supabase service-role keys, database URLs, and JWT secrets.

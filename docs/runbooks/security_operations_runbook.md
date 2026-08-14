# Security Operations Runbook: Whitfield Fulfillment Warehouse

## 1. Authentication & JWT Management

### Token Contract:
- **Access Tokens**: Short-lived JWTs (default 60 minutes) containing `user_id`, `email`, `name`, `role`, `seller_ids`, `warehouse_ids`, and `token_version`.
- **Token Versioning**: When an account is suspended or credentials rotated, `token_version` is incremented, immediately invalidating active tokens without database round-trips.
- **Refresh Flow**: `POST /api/v1/auth/refresh` issues a fresh access token for active users.

### Production Environment Validation:
On startup, `validate_production_configuration` enforces:
- `JWT_SECRET` must be at least 32 characters and distinct from default placeholders.
- `BOOTSTRAP_ADMIN_PASSWORD` cannot use default credentials in production.
- Secret audit tool (`tools/audit_frontend_secrets.py`) verifies that no backend tokens, database URLs, or API keys leak into browser assets.

---

## 2. Rate Limiting Policy

Sliding-window in-memory rate limiters protect sensitive endpoints against brute force and resource exhaustion:

| Endpoint Group | Max Requests | Window (Seconds) | Action on Breach |
|---|---|---|---|
| `POST /api/v1/auth/login` | 10 | 60 | HTTP 429 + `Retry-After` header |
| `POST /api/v1/auth/refresh` | 20 | 60 | HTTP 429 + `Retry-After` header |
| `All /api/v1/ai/*` routes | 40 | 60 | HTTP 429 + `Retry-After` header |
| `Migration uploads/batches` | 15 | 60 | HTTP 429 + `Retry-After` header |

---

## 3. Secret Hygiene & CI Auditing

Run the frontend secret audit tool before any deployment:
```bash
python tools/audit_frontend_secrets.py
```
This tool scans all frontend TypeScript, HTML, CSS, and build artifacts under `.output/` for forbidden markers (`service_role`, `SUPABASE_SERVICE_ROLE`, `JWT_SECRET`, `DATABASE_URL`, `GOOGLE_GENAI_API_KEY`, etc.).

---

## 4. Incident Response & Credential Compromise

If administrative credentials or JWT secrets are suspected of compromise:
1. Rotate `JWT_SECRET` immediately in secret management.
2. Invalidate all active user sessions by incrementing `token_version` for all users in the database.
3. Check audit logs (`GET /api/v1/admin/audit` or `audit_events` table) for anomalous actor activity.

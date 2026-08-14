# AI Operations Runbook: Whitfield Fulfillment Warehouse

## 1. Overview & Architecture

The Whitfield Fulfillment Warehouse operations platform integrates a read-only and draft-only AI operations assistant powered by Google Gemini (with safe deterministic fallback capabilities).

### Core Operational Principles:
1. **Zero Direct DB Mutations**: AI never directly writes to inventory balances, orders, transfers, receipts, returns, or shipments.
2. **Draft-Only Workflows**: Recommendation generation produces structured draft actions (`ai_draft_actions`) marked `requires_approval = True`. A human manager or administrator must explicitly review and approve or reject any operational proposal.
3. **Strict RBAC & Tenant Scoping**: Every AI request verifies the caller's JWT scope and enforces warehouse and seller isolation filters.
4. **Complete Audit Logging**: Every prompt excerpt, tool call, hash, safety decision, and user feedback is recorded in `ai_interactions`, `ai_tool_calls`, and `ai_feedbacks`.

---

## 2. Configuration & Runtime Settings

| Setting | Default | Production Value | Purpose |
|---|---|---|---|
| `AI_ENABLED` | `false` | `true` | Enable AI assistant subsystem |
| `AI_PROVIDER` | `disabled` | `google_genai` | Active AI provider (`google_genai` or `disabled`) |
| `AI_MODEL` | `gemini-3.1-flash-lite-preview` | `gemini-3.1-flash-lite-preview` | Foundation model designation |
| `GOOGLE_GENAI_API_KEY` | `""` | `[SECURE-SECRET]` | Google GenAI API Key (backend only) |
| `AI_LOG_PROMPT_EXCERPTS`| `false` | `true` | Store truncated sanitized excerpts in audit logs |
| `AI_PROMPT_EXCERPT_CHARS`| `500` | `500` | Excerpt length ceiling |

---

## 3. Operational Endpoints

- `GET /api/v1/ai/admin/provider-health`: Check provider engine readiness, key configuration, and runtime latency.
- `GET /api/v1/ai/admin/interactions`: List audited interactions with category, provider, and status filters.
- `GET /api/v1/ai/admin/interactions/{id}`: Detailed trace including tool call executions, inputs/outputs, and feedbacks.
- `POST /api/v1/ai/interactions/{id}/feedback`: Capture user helpful/unhelpful rating and commentary.
- `POST /api/v1/ai/exceptions/summary`: Aggregated operational variances and AI narrative.
- `POST /api/v1/ai/drafts/recommendation`: Generate reviewable draft operational actions.
- `GET /api/v1/ai/drafts`: Manager queue of draft actions.
- `POST /api/v1/ai/drafts/{id}/reject`: Reject an operational recommendation.

---

## 4. Key Rotation & Provider Failover

If the Gemini API key expires, encounters quota limits, or is rotated:
1. Update `GOOGLE_GENAI_API_KEY` in deployment environment secrets (or `.env`).
2. Verify readiness at `GET /health/status` or `GET /api/v1/ai/admin/provider-health`.
3. If provider fails, the platform automatically falls back to deterministic rule engines with zero downtime or user disruption.

---

## 5. User Feedback Triage Workflow

1. Navigate to **Admin -> AI Audit & Provider Health**.
2. Filter for interactions with unhelpful feedback ratings.
3. Review the prompt excerpt, safety evaluation, retrieved database references, and user comments.
4. If database evidence was insufficient, verify index synchronization or catalog data completeness.

# Whitfield Warehouse Operations Backend

Enterprise backend service for Whitfield Fulfillment warehouse operations, real-time inventory ledger, bicoastal order fulfillment, AI assistant, and voice-guided receiving.

---

## 🏗️ Architecture & Core Components

- **Framework**: FastAPI (Python 3.11+) + Uvicorn ASGI Server
- **Database**: PostgreSQL 16 (SQLAlchemy 2.0 asyncpg for runtime + psycopg for migrations)
- **Migrations**: Alembic with synchronous migration runner
- **Authentication**: Scoped JWT (HS256) + bcrypt password hashing (5 RBAC roles)
- **AI Intelligence**: Google Gemini 2.5 Flash (`google-genai`) with grounded read-only RAG tools
- **Speech Pipeline**: Native Web Speech API, Sarvam AI & Deepgram STT/TTS audio adapters
- **Observability**: Structured JSON-ready logging with per-request correlation ID tracking (`[rid=...]`)
- **Concurrency Safety**: Pessimistic `SELECT FOR UPDATE` row-level locks on inventory balances
- **Rate Limiting**: Sliding-window multi-tier rate limiting with in-memory bucket store

---

## 👥 Seeded Personas & Credentials

| Role / Persona | User ID (Email) | Password | Access Scope |
|---|---|---|---|
| 👑 **Administrator** | `admin@whitfield.com` | `WhitfieldAdmin123!` | Global tenant provisioning, facility control, system & AI audit logs |
| 🏬 **Warehouse Manager** | `manager@whitfield.com` | `WhitfieldManager123!` | Multi-facility inventory management across Reno (RNO) & Columbus (CMH) |
| 📥 **Dock Receiver** | `receiver@whitfield.com` | `WhitfieldReceiver123!` | Inbound shipments, pallet validation, and Voice AI intake station |
| 📦 **Lead Picker/Packer** | `picker@whitfield.com` | `WhitfieldPicker123!` | Pick waves, short-pick quarantine, carrier dispatch & tracking |
| 🏷️ **Seller Partner** | `seller@whitfield.com` | `WhitfieldSeller123!` | Aura Electronics merchant portal (`SL-AURA`), dedicated SKU stock & RMAs |

---

## 💻 Local Development

```powershell
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate # Linux / macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env

# 4. Run the development server
uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

- API Base: `http://127.0.0.1:8080`
- Interactive Swagger UI: `http://127.0.0.1:8080/docs`
- ReDoc Docs: `http://127.0.0.1:8080/redoc`

---

## 🧪 Running Automated Tests

```powershell
# Run full unit and E2E test suite (110 tests)
python -m pytest

# Run with verbose output
python -m pytest -v

# Run secret audit check
python tools/audit_frontend_secrets.py
```

All 110 automated tests pass with 100% green coverage.

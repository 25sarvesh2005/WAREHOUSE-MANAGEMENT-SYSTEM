<div align="center">

# ⚡ Whitfield WMS — Enterprise Backend Service
### *High-Performance, Concurrency-Safe Warehouse Operations, Real-Time Inventory Ledger, AI Copilot & Voice-Guided Logistics*

[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20Async-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%20AsyncPG-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-2.5%20Flash%20RAG-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![Pytest Suite](https://img.shields.io/badge/Tests-110%2F110%20Passed%20(100%25)-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](#-automated-testing--ci-verification)
[![Alembic Migrations](https://img.shields.io/badge/Alembic-Synchronous%20Runner-orange?style=for-the-badge)](https://alembic.sqlalchemy.org/)
[![Docker Ready](https://img.shields.io/badge/Docker-Multi--Stage%20Container-2496ED?style=for-the-badge&logo=docker&logoColor=white)](#-containerization--docker-deployment)

<p align="center">
  <a href="#-architecture--system-design"><strong>Architecture</strong></a> •
  <a href="#-key-capabilities--technical-highlights"><strong>Key Capabilities</strong></a> •
  <a href="#-seeded-personas--credentials"><strong>Credentials</strong></a> •
  <a href="#-exhaustive-api-routes-directory"><strong>API Directory</strong></a> •
  <a href="#-local-development--quickstart"><strong>Quickstart</strong></a> •
  <a href="#-automated-testing--ci-verification"><strong>Testing</strong></a> •
  <a href="#-concurrency-safety--locking-mechanics"><strong>Concurrency & Safety</strong></a> •
  <a href="#-troubleshooting--faq"><strong>Troubleshooting</strong></a>
</p>

---

</div>

## 📖 Overview

The **Whitfield WMS Backend** is an enterprise-tier asynchronous REST API engineered for mission-critical bicoastal fulfillment centers (*Reno, NV - `RNO`* & *Columbus, OH - `CMH`*). Built from the ground up to prevent race conditions during high-volume flash sales, it features a double-entry ledger, pessimistic row-level locking, conversational warehouse intelligence powered by **Google Gemini 2.5 Flash**, and hands-free voice-guided intake for dock workers.

---

## 🏗️ Architecture & System Design

```mermaid
flowchart TB
    subgraph ClientLayer["Client & Edge Subsystem"]
        SPA["Vite + React 19 Frontend"]
        VoiceClient["Voice Intake Station (Web Audio / STT)"]
        Scanner["Warehouse Barcode Scanners / Handhelds"]
        ExternalSellers["Merchant Portal API Clients"]
    end

    subgraph Gateway["Security & Ingress Gateway"]
        CORS["CORS Origin Validation"]
        RateLimiter["Sliding-Window Rate Limiter (Multi-Tier)"]
        ReqID["Correlation ID Middleware [rid=...]"]
        AuthGuard["JWT HS256 Guard & 5-Role RBAC Scope Validator"]
    end

    subgraph CoreEngine["FastAPI Core Business Engines (FastAPI 0.115+)"]
        AIController["🤖 Gemini RAG Copilot Controller"]
        VoiceController["🎙️ Hands-Free Voice Intake Engine"]
        InvController["📦 Concurrency Ledger & Stock Allocator"]
        OrderController["🛒 Bicoastal Order & Split-Fulfillment Engine"]
        ReceiveController["📥 Dock Receiving & Pallet Inspection"]
        TransferController["🚚 Multi-Facility Rebalance Orchestrator"]
        FulfillController["⚡ Pick Waves & Short-Pick Quarantine"]
        ReturnController["🔄 RMA & Reverse Logistics"]
    end

    subgraph BackgroundWorkers["Autonomous Background Jobs"]
        ExpiryJob["⏱️ Reservation Expiry Cleanup Worker (60s Loop)"]
        OutboxWorker["📬 Transactional Outbox Event Dispatcher"]
    end

    subgraph StorageLayer["Persistence & AI Infrastructure"]
        AsyncEngine["SQLAlchemy 2.0 Async Engine (asyncpg)"]
        PgPool[(PostgreSQL 16 Engine\nPessimistic SELECT FOR UPDATE Locks)]
        GeminiAPI["Google Gemini 2.5 Flash API (google-genai)"]
        AudioAdapters["Sarvam AI / Deepgram / WebSpeech Adapters"]
    end

    ClientLayer --> Gateway
    Gateway --> CoreEngine
    CoreEngine --> BackgroundWorkers
    CoreEngine --> StorageLayer
    AsyncEngine --> PgPool
    AIController --> GeminiAPI
    VoiceController --> AudioAdapters
```

---

## 🌟 Key Capabilities & Technical Highlights

### 1. 🛡️ Concurrency-Safe Double-Entry Inventory Ledger
* **Pessimistic Row-Level Locks:** All reservation, deduction, and transfer transactions execute inside strict `SELECT ... FOR UPDATE` row locks on `inventory_balances` to guarantee zero double-allocation or race conditions during flash-sales.
* **Granular Balance Tracking:** Real-time tracking across 4 discrete physical states: `on_hand`, `reserved`, `quarantine`, and `available_to_promise` (ATP).
* **Automatic Expiry Engine:** Background worker automatically expires stale stock reservations (configurable TTL) and replenishes ATP buffers without manual intervention.

### 2. 🤖 Grounded Conversational AI Warehouse Copilot (Gemini 2.5 Flash)
* **Grounded Read-Only RAG:** Leverages Google Gemini 2.5 Flash with strict read-only ledger tools (`get_inventory_balance`, `query_low_stock_skus`, `check_facility_capacities`, `draft_facility_transfer`).
* **Zero Mutation Risk:** Architectural isolation prevents AI from executing direct database mutations; it drafts recommendations for manager review and manual authorization.
* **Audit Trail Logging:** Every prompt, tool execution, grounding context, and response latency is permanently recorded in `ai_audit_logs`.

### 3. 🎙️ Hands-Free Voice Receiving Dock Station
* **Multilingual Dock Audio Pipeline:** Allows receiving dock operators wearing headsets to dictate inbound shipments, condition notes, and pallet counts hands-free.
* **Dual Audio Adapter Architecture:** Seamlessly supports native browser `Web Speech API` as well as cloud-native `Sarvam AI` / `Deepgram` STT pipelines.
* **Structured Intent Extraction:** Automatically converts natural language dictation into verified receiving drafts with supplier PO validation.

### 4. 🌐 Bicoastal Multi-Facility Routing & Split-Fulfillment
* **Intelligent Geo-Routing:** Evaluates order destination coordinates against `RNO` (West Coast) and `CMH` (East Coast) fulfillment nodes to minimize transit zones and carrier cost.
* **Short-Pick Quarantine Quarantine:** Automatically detects stock discrepancies during picking, isolates damaged items to quarantine, and triggers immediate re-routing.

---

## 👥 Seeded Personas & Credentials

The system seeds 5 enterprise personas covering all operational domains. All accounts are ready for testing with pre-allocated permission scopes:

| Persona | Role Badge | Email Address | Default Password | Scopes & Responsibilities |
|---|---|---|---|---|
| **Administrator** | `ADMIN` | `admin@whitfield.com` | `WhitfieldAdmin123!` | System configuration, tenant provisioning, audit log inspection, facility management |
| **Warehouse Manager** | `MANAGER` | `manager@whitfield.com` | `WhitfieldManager123!` | Inter-facility transfers, stock adjustments, wave releases, AI rebalancing approval |
| **Dock Receiver** | `RECEIVER` | `receiver@whitfield.com` | `WhitfieldReceiver123!` | Inbound PO check-in, pallet verification, Voice AI dock station, damage inspection |
| **Lead Picker/Packer** | `PICKER` | `picker@whitfield.com` | `WhitfieldPicker123!` | Wave picking, short-pick quarantine logging, packing slips, carrier dispatch |
| **Seller Partner** | `SELLER` | `seller@whitfield.com` | `WhitfieldSeller123!` | Merchant portal (`SL-AURA`), dedicated SKU stock reports, RMA requests |

> [!TIP]
> Both `.com` and `.local` email suffixes (e.g. `admin@whitfield.local`) are seeded and fully functional in development.

---

## 📡 Exhaustive API Routes Directory

All endpoints are versioned under `/api/v1/` and protected with rate limiters and JWT RBAC guards:

### 🔐 Authentication & Identity (`/api/v1/auth`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Authenticate user & issue JWT bearer token | Public |
| `POST` | `/api/v1/auth/refresh` | Refresh expired access tokens | JWT Refresh |
| `GET` | `/api/v1/auth/me` | Retrieve profile and active permission scopes | JWT Bearer |
| `POST` | `/api/v1/auth/logout` | Revoke token and terminate session | JWT Bearer |

### 🤖 AI Assistant Copilot (`/api/v1/ai`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/ai/chat` | Send conversational natural language query to Gemini | `MANAGER`, `ADMIN` |
| `GET` | `/api/v1/ai/audit-logs` | Retrieve chronological AI grounding and tool logs | `ADMIN` |
| `POST` | `/api/v1/ai/rebalance-draft` | Request automated inter-facility rebalance draft | `MANAGER`, `ADMIN` |

### 🎙️ Hands-Free Voice Receiving (`/api/v1/voice`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/voice/transcribe` | Ingest audio stream and extract receiving draft | `RECEIVER`, `MANAGER` |
| `POST` | `/api/v1/voice/parse-intent` | Parse text transcript into structured receiving payload | `RECEIVER`, `MANAGER` |
| `GET` | `/api/v1/voice/sessions` | List active dock voice sessions | `RECEIVER`, `MANAGER` |

### 📦 Inventory Ledger (`/api/v1/inventory`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/inventory/balances` | Query balances across facilities and SKUs | Authenticated |
| `POST` | `/api/v1/inventory/adjustments`| Execute manual inventory reconciliation with audit | `MANAGER`, `ADMIN` |
| `GET` | `/api/v1/inventory/ledger` | Query immutable double-entry ledger transactions | `MANAGER`, `ADMIN` |
| `POST` | `/api/v1/inventory/reserve` | Reserve stock for order allocation (Row-locked) | Internal / Order |

### 🛒 Orders & Wave Fulfillment (`/api/v1/orders` & `/api/v1/fulfillment`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/orders` | List customer sales orders with status filters | Authenticated |
| `POST` | `/api/v1/orders` | Ingest new customer order & run geo-allocation | `SELLER`, `ADMIN` |
| `POST` | `/api/v1/fulfillment/waves` | Generate optimized pick wave across facility zones | `PICKER`, `MANAGER` |
| `POST` | `/api/v1/fulfillment/picks/confirm` | Confirm picked items with barcode verification | `PICKER` |
| `POST` | `/api/v1/fulfillment/picks/short` | Report short-pick & quarantine discrepancy | `PICKER` |
| `POST` | `/api/v1/fulfillment/ship` | Generate carrier tracking & mark order dispatched | `PICKER`, `MANAGER` |

### 🚚 Transfers & Reverse Logistics (`/api/v1/transfers` & `/api/v1/returns`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/transfers` | List inter-facility transfers between RNO & CMH | Authenticated |
| `POST` | `/api/v1/transfers` | Initiate stock transfer with transit reservation | `MANAGER`, `ADMIN` |
| `POST` | `/api/v1/transfers/{id}/receive`| Complete transfer intake at destination facility | `RECEIVER`, `MANAGER` |
| `POST` | `/api/v1/returns/rma` | Create Return Merchandise Authorization (RMA) | `SELLER`, `MANAGER` |
| `POST` | `/api/v1/returns/{id}/inspect` | Inspect returned items and route to restock/scrap | `RECEIVER`, `MANAGER` |

---

## 💻 Local Development & Quickstart

### Prerequisites
* **Python**: `3.11`, `3.12`, or `3.13`
* **PostgreSQL**: `16+` (or Docker Postgres container)
* **Node.js**: `20+` (for running frontend alongside)

### Step-by-Step Setup

```powershell
# 1. Navigate to backend directory
cd backend

# 2. Create and activate Python virtual environment
python -m venv venv
.\venv\Scripts\activate          # Windows PowerShell
# source venv/bin/activate       # Linux / macOS

# 3. Install core dependencies
pip install -r requirements.txt

# 4. Configure environment secrets
cp .env.example .env
```

### Environment Configuration (`.env`)

```ini
# --- APPLICATION SETTINGS ---
APP_ENV=development
DEBUG=true
PORT=8080
HOST=127.0.0.1
SECRET_KEY=whitfield_super_secret_jwt_signing_key_min_32_chars_long!
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# --- DATABASE CONFIGURATION ---
# Async connection string for SQLAlchemy asyncpg engine
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/whitfield_wms
# Synchronous connection string for Alembic migrations
MIGRATION_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/whitfield_wms

# --- SEEDING & SCHEMA LIFECYCLE ---
INITIALIZE_SCHEMA_ON_STARTUP=true
SEED_SAMPLE_DATA=true

# --- AI COPILOT (GOOGLE GEMINI) ---
AI_ENABLED=true
AI_PROVIDER=google_genai
AI_MODEL=gemini-2.5-flash
GOOGLE_GENAI_API_KEY=your_gemini_api_key_here

# --- VOICE RECEIVING ENGINE ---
VOICE_ENABLED=true
SARVAM_API_KEY=your_sarvam_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# --- CORS & SECURITY ---
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
GLOBAL_RATE_LIMIT_PER_MINUTE=120
```

### Starting the Server

```powershell
# Start FastAPI ASGI server with auto-reload
uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

* 🚀 **API Root:** [http://127.0.0.1:8080](http://127.0.0.1:8080)
* 📚 **Interactive Swagger UI:** [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
* 📑 **ReDoc Documentation:** [http://127.0.0.1:8080/redoc](http://127.0.0.1:8080/redoc)
* 🩺 **Health Readiness Probe:** [http://127.0.0.1:8080/readyz](http://127.0.0.1:8080/readyz)

---

## 🧪 Automated Testing & CI Verification

The backend includes a comprehensive, battle-tested test suite with **110 unit and end-to-end test cases**:

```powershell
# Run the complete test suite
python -m pytest

# Run with verbose reporting and timing breakdown
python -m pytest -v --durations=10

# Run specific functional domain tests
python -m pytest tests/unit/test_ai_read_only_flows.py -v
python -m pytest tests/unit/test_voice_receiving_flows.py -v
python -m pytest tests/unit/test_inventory_flows.py -v
```

### Security & Secret Leak Audit
To ensure zero backend secrets, database connection strings, or private keys leak into client bundles:

```powershell
python tools/audit_frontend_secrets.py
```

---

## 🔒 Concurrency Safety & Locking Mechanics

When concurrent orders compete for remaining SKU stock (e.g. flash sales on `SKU-AURA-ANC100`):

```python
# Concurrency-safe pattern used in core/cruds/inventory_crud.py
async with transaction_session() as session:
    # 1. Acquire pessimistic row lock on specific facility SKU balance
    balance = await session.execute(
        select(InventoryBalance)
        .where(
            InventoryBalance.facility_id == facility_id,
            InventoryBalance.product_id == product_id
        )
        .with_for_update()  # <-- SELECT ... FOR UPDATE ensures serialization
    )
    # 2. Safely evaluate Available-to-Promise (ATP)
    atp = balance.on_hand - balance.reserved - balance.quarantine
    if atp < requested_quantity:
        raise InsufficientStockError("Stock depleted by concurrent transaction")
    
    # 3. Atomically mutate reserved quantity
    balance.reserved += requested_quantity
    await session.commit()
```

---

## 🐳 Containerization & Docker Deployment

### Multi-Stage Production Dockerfile

```dockerfile
# Build image
docker build -t whitfield-backend:latest -f Dockerfile .

# Run standalone container with PostgreSQL link
docker run -d \
  --name whitfield-backend \
  -p 8080:8080 \
  -e DATABASE_URL="postgresql+asyncpg://postgres:secret@db:5432/whitfield" \
  -e SECRET_KEY="production_32_char_secret_key" \
  whitfield-backend:latest
```

---

## 📊 Database Schema & Domain Entities

```
                          ┌──────────────────────────┐
                          │       facilities         │
                          │ (RNO - Reno, CMH - Col)  │
                          └─────────────┬────────────┘
                                        │
           ┌────────────────────────────┼───────────────────────────┐
           │ 1:N                        │ 1:N                       │ 1:N
┌──────────▼───────────┐   ┌────────────▼─────────┐    ┌────────────▼───────────┐
│  inventory_balances  │   │   receiving_orders   │    │      sales_orders      │
│  (on_hand, reserved, │   │ (Inbound PO receipts,│    │ (Bicoastal allocations,│
│   quarantine, ATP)   │   │  voice intake drafts)│    │  wave pick batches)    │
└──────────┬───────────┘   └──────────────────────┘    └────────────┬───────────┘
           │ 1:N                                                    │ 1:N
┌──────────▼───────────┐                               ┌────────────▼───────────┐
│   inventory_ledger   │                               │     order_items        │
│ (Immutable audit trail│                              │ (SKUs, requested qty,  │
│  of all balance delta│                               │  short-pick tracking)  │
└──────────────────────┘                               └────────────────────────┘
```

---

## 🛠️ Operational Troubleshooting & FAQ

<details>
<summary><strong>Q: Database connection fails on startup with asyncpg error?</strong></summary>

> **Resolution:** Ensure your PostgreSQL server is running and accessible on port `5432`. Verify that `DATABASE_URL` uses the `postgresql+asyncpg://` driver prefix while `MIGRATION_DATABASE_URL` uses `postgresql+psycopg://`.
</details>

<details>
<summary><strong>Q: How do I test the Gemini AI Copilot without an API key?</strong></summary>

> **Resolution:** Set `AI_ENABLED=false` or omit `GOOGLE_GENAI_API_KEY`. The backend will automatically fall back to deterministic heuristics and return structured read-only mock recommendations.
</details>

<details>
<summary><strong>Q: How do I trigger manual reservation expiry immediately?</strong></summary>

> **Resolution:** Run the maintenance tool directly:
> ```powershell
> python tools/release_expired_reservations.py
> ```
</details>

---

<div align="center">

**Whitfield Warehouse Management System** • Built with ⚡ by the Whitfield Engineering Team  
*Production-Ready • Concurrency-Safe • AI-Augmented*

</div>

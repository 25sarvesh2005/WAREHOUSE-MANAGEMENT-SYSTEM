<div align="center">

# 🏭 Whitfield Warehouse Management System (WMS)
### **Enterprise Bicoastal Fulfillment, Multi-Tenant Logistics & Natural Language AI Copilot**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React_19-Vite-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_Supabase-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-3.5_Flash-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Docker](https://img.shields.io/badge/Docker-Compose_Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

<br />

**Whitfield WMS** is a mission-critical, bicoastal fulfillment and warehouse operations platform. Engineered to eliminate spreadsheet fragmentation, it combines an **immutable double-entry inventory ledger**, **strict concurrency row-locking**, a **multilingual hands-free voice intake dock**, and a **Google Gemini-powered conversational AI copilot** across nationwide logistics centers.

[Explore Live Demo](#-quick-start) • [Architecture](#-architecture--system-design) • [AI Copilot](#-conversational-ai-copilot) • [API Documentation](#-api-endpoints--swagger) • [Deployment](#-cloud-deployment-guide)

</div>

---

## 🌟 Key Platform Highlights

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                  │
│  🏢 Bicoastal Hubs          📦 Multi-Tenant Brands       🤖 Gemini AI Copilot   🎙️ Hands-Free Dock│
│  Reno (NV) & Columbus (OH)  Aura, Nordic, Vitality, Apex Grounded Warehouse RAG  Voice-Driven Intake│
│                                                                                                  │
│  🔒 Strict Row Locking      📊 Double-Entry Ledger       🚚 Outbound Tracking    ⚡ Modern UI    │
│  SELECT FOR UPDATE Safety   Append-Only Audit Journal    UPS / FedEx / USPS      React 19 + Vite │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. 🤖 Conversational AI Warehouse Copilot (Google Gemini 3.5 Flash)
- **Natural Language Warehouse Inquiries:** Ask anything in plain English (e.g., *"What products have 0 quantity?"*, *"Which headphones are in stock across Reno and Columbus?"*, *"Show lowest stock items"*).
- **Grounded Read-Only RAG:** Grounded strictly in live PostgreSQL ledger evidence with safety guardrails — zero hallucination, zero unauthorized mutations.
- **Automated Rebalance Drafting:** Detects regional stock imbalances and drafts transfer orders between facilities for manager review.

### 2. 🎙️ Hands-Free Voice Receiving Dock (Sarvam & Deepgram STT/TTS)
- **Multilingual Dock Voice Intake:** Allows dock workers wearing headsets to dictate inbound deliveries hands-free while unloading trucks and scanning pallets.
- **Structured Draft Synthesis:** Extracts supplier barcodes, carrier tracking numbers, and damage notes automatically into verified receiving drafts.

### 3. 🛡️ Concurrency-Safe Double-Entry Inventory Ledger
- **Race Condition Prevention:** Powered by pessimistic `SELECT ... FOR UPDATE` row-level locks on inventory balance records to prevent double-allocation during flash sales.
- **Immutable Financial-Grade Movement Journal:** Tracks every unit across four discrete states: `AVAILABLE`, `RESERVED`, `DAMAGED`, and `QUARANTINED`.
- **Automated Background Workers:** Periodic task scheduler auto-releases expired reservations back to sellable stock.

### 4. 🏢 Bicoastal Multi-Tenant Architecture
- **2 Nationwide Fulfillment Hubs:**
  - **`RNO`**: Reno West Coast Fulfillment Center (Reno, NV — PST)
  - **`CMH`**: Columbus Midwest & East Coast Hub (Columbus, OH — EST)
- **4 Pre-Seeded Enterprise Merchant Tenants:**
  - **`SL-AURA`**: Aura Electronics Corp *(Smart wearables, ANC audio, wireless chargers)*
  - **`SL-NORD`**: Nordic Apparel Co *(Organic cotton hoodies, ripstop anoraks)*
  - **`SL-VITA`**: Vitality Nutrition Labs *(Electrolyte packs, isolate protein, magnesium)*
  - **`SL-APEX`**: Apex Workspace Innovations *(Mechanical keyboards, desk mats, precision mice)*

---

## 🏗️ Architecture & System Design

```mermaid
flowchart TB
    subgraph Client["Frontend Layer (React 19 + TanStack Router + Vite)"]
        UI["Web Portal (Dashboard, Inventory, Orders, AI, Voice)"]
        State["TanStack React Query Cache & Auth State"]
    end

    subgraph Backend["FastAPI High-Performance Backend Layer"]
        Router["API Gateway / 95+ Route Handlers"]
        Auth["JWT & RBAC Security Middleware (5 Roles)"]
        Controller["Domain Orchestration Layer"]
        Locking["Pessimistic Concurrency Engine (SELECT FOR UPDATE)"]
        
        subgraph AIService["AI & Voice Operations Subsystem"]
            Gemini["Google Gemini 3.5 Flash RAG"]
            Voice["Sarvam & Deepgram Audio Pipeline"]
        end
    end

    subgraph Data["Persistence & Storage Layer"]
        Postgres[(PostgreSQL 16 / Supabase)]
        Ledger[("Immutable Movement Ledger")]
        Balances[("Multi-State Inventory Balances")]
    end

    UI -->|REST API / HTTPS| Router
    Router --> Auth
    Auth --> Controller
    Controller --> Locking
    Controller --> AIService
    Locking --> Postgres
    Postgres --> Ledger
    Postgres --> Balances
```

---

## 💻 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 19, TypeScript, Vite, TanStack Router, TailwindCSS v4 | High-performance, responsive glassmorphic web portal |
| **Data Fetching** | TanStack React Query 5 | Optimistic UI updates, caching, background refetching |
| **Backend** | Python 3.11+, FastAPI, Uvicorn | Async ASGI backend, OpenAPI 3.1 schema auto-generation |
| **Database** | PostgreSQL 16, Async SQLAlchemy 2.x, `asyncpg`, Alembic | Relational storage, async connection pooling, schema migrations |
| **AI Intelligence**| Google Gemini 3.5 Flash (`google-genai`) | Grounded natural language warehouse queries & recommendations |
| **Speech Audio** | Sarvam AI & Deepgram STT/TTS | Multilingual voice intake processing for receiving docks |
| **Authentication**| JWT (HS256), Passlib (Bcrypt) | Scoped Role-Based Access Control across 5 granular personas |
| **Containerization**| Docker, Docker Compose | Production-ready multi-stage container packaging |

---

## 👥 Role-Based Access Control (RBAC)

The system comes pre-configured with 5 distinct personas:

| Role | Default Email | Password | Scope & Responsibilities |
|---|---|---|---|
| 👑 **Administrator** | `admin@whitfield.local` | `WhitfieldAdmin123!` | Global access, tenant provisioning, system logs, full visibility |
| 🏬 **Warehouse Manager** | `manager@whitfield.local` | `Manager123!` | Multi-facility management (Reno & Columbus), inter-facility transfers, exceptions |
| 📥 **Dock Receiver** | `receiver@whitfield.local` | `Receiver123!` | Inbound dock deliveries, pallet verification, voice intake station |
| 📦 **Lead Picker/Packer** | `picker@whitfield.local` | `Picker123!` | Pick waves, packing validation, carrier dispatch, tracking generation |
| 🏷️ **Seller Partner** | `seller@whitfield.local` | `Seller123!` | Aura Electronics tenant portal (`SL-AURA`), dedicated SKU stock & RMA tracking |

---

## ⚡ Quick Start (Local Development)

### Prerequisites
- **Node.js:** `v20+` (or `v22+`)
- **Python:** `3.11+` (or `3.13+`)
- **PostgreSQL:** Local instance or cloud database (Supabase / Neon)

### 1. Clone the Repository
```bash
git clone https://github.com/25sarvesh2005/WAREHOUSE-MANAGEMENT-SYSTEM.git
cd WAREHOUSE-MANAGEMENT-SYSTEM
```

### 2. Setup & Start Backend
```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Run FastAPI development server
uvicorn main:app --reload --host 127.0.0.1 --port 8080
```
*Backend runs at **`http://127.0.0.1:8080`**. Interactive Swagger docs at **`http://127.0.0.1:8080/docs`**.*

### 3. Setup & Start Frontend
```bash
# In a new terminal
cd frontend
npm install
npm run dev
```
*Frontend runs at **`http://127.0.0.1:5173`**.*

---

## 🐳 1-Command Docker Compose Deployment

To run the complete system (PostgreSQL 16 + FastAPI + Frontend) in isolated production containers:

```bash
# 1. Start all services
docker compose up -d --build

# 2. Seed enterprise demonstration data
docker compose exec backend python tools/seed_enterprise_data.py
```

Access the services:
- **Web Portal:** `http://localhost:5173`
- **Backend API:** `http://localhost:8080`
- **Swagger Documentation:** `http://localhost:8080/docs`

---

## 🚀 Cloud Deployment Guide

### Deploying Backend on Render / Railway
1. Create a new **Web Service** on [Render.com](https://render.com) from this repository.
2. Set Environment Variables:
   ```ini
   DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
   MIGRATION_DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname
   JWT_SECRET=your_32_char_random_jwt_secret
   AI_ENABLED=true
   AI_PROVIDER=google_genai
   AI_MODEL=gemini-3.5-flash
   GOOGLE_GENAI_API_KEY=your_gemini_api_key
   INITIALIZE_SCHEMA_ON_STARTUP=true
   FRONTEND_ORIGINS=https://your-frontend.vercel.app,http://localhost:5173
   ```
3. Deploy!

### Deploying Frontend on Vercel
1. Import repository into [Vercel.com](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Set **Framework Preset** to `Vite`.
4. Add Environment Variable:
   ```ini
   VITE_API_BASE_URL=https://your-backend-service.onrender.com
   ```
5. Click **Deploy**!

---

## 📡 API Endpoints & Modules

The platform exposes **95+ structured REST endpoints** organized under `/api/v1/`:

| Module | Route Prefix | Key Functionality |
|---|---|---|
| 🔐 **Authentication** | `/api/v1/auth` | JWT login, token refresh, current user profile |
| 🏷️ **Catalog** | `/api/v1/products` | Master SKUs, barcodes, weights, dimensions, facility bin locations |
| 📊 **Inventory** | `/api/v1/inventory` | Multi-state balances, ledger movements, manual adjustments |
| 📥 **Receiving** | `/api/v1/receipts` | Inbound shipments, 40ft container intake, putaway verification |
| 🛒 **Orders** | `/api/v1/orders` | Allocation, inventory reservations, lifecycle pipeline |
| 📦 **Fulfillment** | `/api/v1/fulfillment` | Pick wave generation, pick tasks, packing verification, shipments |
| 🔄 **Transfers** | `/api/v1/transfers` | Inter-facility transfer orders between Reno and Columbus |
| ↩️ **Returns** | `/api/v1/returns` | Customer RMA processing, return inspection, quarantine disposition |
| 🤖 **AI Assistant** | `/api/v1/ai` | Freeform stock reasoning, ledger explanation, exception summaries |
| 🎙️ **Voice AI** | `/api/v1/voice` | Audio transcription and structured receiving draft synthesis |
| 🏢 **Identity** | `/api/v1/sellers`, `/api/v1/warehouses` | Multi-tenant merchant and facility management |

---

## 📁 Repository Structure

```
WAREHOUSE-MANAGEMENT-SYSTEM/
├── backend/                        # FastAPI Backend Application
│   ├── main.py                     # ASGI entrypoint & lifespan management
│   ├── common/                     # Auth, logger, request ID, rate limiting
│   ├── core/
│   │   ├── apis/                   # 95+ REST route handlers & Pydantic schemas
│   │   ├── controllers/            # Business logic & transaction orchestration
│   │   ├── cruds/                  # SQLAlchemy persistence with row locking
│   │   ├── models/                 # SQLAlchemy 2.x ORM models
│   │   ├── services/ai/            # Gemini RAG provider & read-only tools
│   │   ├── services/voice/         # Sarvam & Deepgram audio pipeline
│   │   ├── database/               # Database engine, session, & seeders
│   │   └── jobs/                   # Background tasks (reservation expiry)
│   ├── tools/                      # Data seeders & enterprise verification scripts
│   ├── Dockerfile                  # Production backend container build
│   └── requirements.txt            # Python dependencies
├── frontend/                       # Vite + React 19 Frontend Web Portal
│   ├── src/
│   │   ├── routes/                 # TanStack Router page routes
│   │   ├── components/             # Glassmorphic UI kit, AI Copilot, Voice Dock
│   │   ├── hooks/                  # TanStack Query custom data hooks
│   │   ├── lib/                    # API client, TypeScript interfaces, auth
│   │   └── styles.css              # Modern CSS & Tailwind styling
│   ├── Dockerfile                  # Production frontend container build
│   └── package.json                # Frontend dependencies
├── docker-compose.yml              # Multi-container local/cloud orchestration
├── Dockerfile                      # Root container build for PaaS platforms
└── README.md                       # Platform documentation
```

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

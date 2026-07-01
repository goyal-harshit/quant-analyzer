# QuantAI System Architecture Specification

This document details the software architecture, design patterns, security protocols, and database schema of the QuantAI Indian Market Analytics platform.

---

## 1. System Topology Overview

QuantAI is structured as a decoupled, multi-container full-stack application. It leverages self-hosted, open-source infrastructure to guarantee a 100% free operation without proprietary lock-in.

```mermaid
graph TD
    User([Browser Client]) <-->|HTTPS / WSS| Nginx[Nginx Reverse Proxy]
    Nginx <-->|Static Files / Port 3000| Frontend[Next.js App Server]
    Nginx <-->|REST API / Port 8000| Backend[FastAPI App Server]
    
    subgraph FastAPI Backend Core
        Backend <-->|Read / Write| Postgres[(PostgreSQL + TimescaleDB)]
        Backend <-->|Cache & Sessions| Redis[(Redis Cache)]
        Backend <-->|Inference / Embeddings| Ollama[(Local Ollama Server)]
    end
    
    subgraph Background Workers
        CeleryWorker[Celery Worker Processes] <-->|Task Execution| Redis
        CeleryWorker <-->|Read / Write| Postgres
        CeleryBeat[Celery Beat Scheduler] -->|Periodic Tasks| Redis
    end
    
    subgraph External Telemetry Sources
        CeleryWorker & Backend -->|Guarded Calls| Yahoo[Yahoo Finance Direct v8]
        CeleryWorker & Backend -->|Guarded Calls| NSE[NSE Live Scrapers]
        CeleryWorker & Backend -->|REST API| MF[mfapi.in MF REST API]
        CeleryWorker & Backend -->|REST API| WorldBank[World Bank Macro API]
    end
```

---

## 2. Security Architecture

QuantAI implements a zero-trust architecture at the application layer, utilizing a strict double-submit cookie protection model alongside secure token validation.

### 2.1 Double-Submit CSRF & httpOnly Authentication

```mermaid
sequenceDiagram
    autonumber
    actor Browser as Browser Client
    participant API as FastAPI Backend
    participant DB as Postgres Database

    Note over Browser, API: Login Flow
    Browser->>API: POST /auth/login {email, password}
    API->>DB: Fetch user & verify bcrypt hash
    DB-->>API: User details
    Note over API: Mints JWT Access & Refresh Tokens
    Note over API: Generates secure CSRF Token
    API-->>Browser: Set-Cookie: access_token (httpOnly, Secure, SameSite=None)<br/>Set-Cookie: refresh_token (httpOnly, Secure, SameSite=None)<br/>Set-Cookie: csrf_token (Secure, SameSite=None)<br/>Response Body: {csrf_token, user_profile}

    Note over Browser, API: Mutating State Flow (e.g. POST /portfolio)
    Note over Browser: Client reads csrf_token from body/cookies<br/>and attaches as header 'X-CSRF-Token'
    Browser->>API: POST /api/v1/portfolio/1/positions {ticker, quantity}<br/>Headers: Cookie, X-CSRF-Token
    Note over API: CSRF Middleware verifies:<br/>Cookie csrf_token == Header X-CSRF-Token
    alt Verification Fails
        API-->>Browser: 403 Forbidden (CSRF token missing or mismatch)
    else Verification Succeeds
        API->>API: Decode httpOnly JWT Cookie & authorize user roles
        API->>DB: Add Position
        DB-->>API: Success
        API-->>Browser: 200 OK
    end
```

### 2.2 Role-Based Access Control (RBAC)
User authorization is enforced via custom FastAPI dependencies (`require_role` and `require_admin`).
- **User Roles**: `user` (default) and `admin`.
- **Account Verification**: Checked via `is_verified` flag. Accounts must complete the email verification flow to access write operations.

---

## 3. High-Reliability Data Fallback Chain

To mitigate rate limiting and 403/429 blocking, QuantAI uses a resilient data pipeline featuring circuit breakers, token bucket rate limiters, and a sequential provider chain.

```mermaid
sequenceDiagram
    autonumber
    participant Client as Client Request
    participant Chain as FallbackChain Manager
    participant DB as Database Provider
    participant Yahoo as Yahoo Direct Provider
    participant NSE as NsePython / Scraper
    participant Seed as Seed Data Backstop

    Client->>Chain: Get Market Quote (RELIANCE)
    
    Note over Chain, DB: Step 1: Read Cached Data
    Chain->>DB: Check freshness (Quote < 2 mins, Fund < 24h)
    alt Cache Hit (Fresh)
        DB-->>Chain: Return Cached Data (source='db')
        Chain-->>Client: Return 200 OK (cached=True)
    else Cache Miss / Stale
        DB-->>Chain: Stale / Not Found
        
        Note over Chain, Yahoo: Step 2: Try Primary Live Source
        alt Yahoo Breaker is CLOSED
            Chain->>Yahoo: Query Yahoo direct v8 API
            alt Yahoo succeeds
                Yahoo-->>Chain: Return Live Quote
                Chain->>DB: Upsert live values (write-through cache)
                Chain-->>Client: Return 200 OK (cached=False)
            else Yahoo fails / 429 Limit
                Note over Chain, Yahoo: Trips breaker to OPEN for 2 mins
                Yahoo-->>Chain: Error
            end
        end
        
        Note over Chain, NSE: Step 3: Try Secondary Source
        alt Chain Fallback (Yahoo failed/disabled)
            alt NSE Breaker is CLOSED
                Chain->>NSE: Scrape NSE Live
                alt NSE succeeds
                    NSE-->>Chain: Return live values
                    Chain->>DB: Upsert values
                    Chain-->>Client: Return 200 OK
                else NSE fails
                    Note over Chain, NSE: Trips breaker to OPEN
                    NSE-->>Chain: Error
                end
            end
        end
        
        Note over Chain, Seed: Step 4: Fallback to Local Seed Data
        alt All Live Sources Offline
            Chain->>Seed: Fetch Static Seed File
            Seed-->>Chain: Return Seed Data (source='seed')
            Chain-->>Client: Return 200 OK (source='seed', caution flag)
        end
    end
```

---

## 4. Grounded AI Chat RAG Pipeline

QuantAI features local AI grounding (Retrieval-Augmented Generation) using a local Ollama instance. This feeds structural company fundamentals, factor metrics, and market indices into the LLM context to deliver factual answers with source citations.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Admin System
    actor User as User Chat Client
    participant RAG as RAG Service
    participant Embed as Embedding Service (Ollama)
    participant DB as Postgres Vector Store
    participant LLM as LLM Engine (Llama 3.2)

    Note over Admin, DB: Ingestion & Vector Indexing Phase
    Admin->>RAG: Trigger reindex (POST /ai/rag/reindex)
    RAG->>DB: Load companies, fundamentals, and factors
    Note over RAG: Standardizes profile documents into Text
    RAG->>Embed: Embed text blocks (nomic-embed-text, 768-dim)
    Embed-->>RAG: Float vectors
    RAG->>DB: Save document mappings + vectors (JSON storage)

    Note over User, LLM: Question & Answering Phase
    User->>RAG: Ask: "Compare TCS and INFY composite scores"
    RAG->>Embed: Embed query text
    Embed-->>RAG: Query vector
    RAG->>DB: Cosine similarity search over vector indices
    DB-->>RAG: Top K matching documents (score > threshold)
    Note over RAG: Compiles System Prompt containing matched documents<br/>with numbered citations [1], [2]...
    RAG->>LLM: Send Grounded Prompt
    LLM-->>RAG: Factual Answer citing referenced sources
    RAG-->>User: Render grounded answer + sources array
```

---

## 5. Database Schema Specification

QuantAI uses TimescaleDB (time-series hypertable engine) built on top of Postgres. 

### 5.1 Time-Series Hypertables
- **`price_ohlcv`**: Stores daily price points for equities. Partitioned by `time` (7-day intervals).
- **`mf_nav`**: Stores NAV history for mutual funds. Partitioned by `date` (14-day intervals).

### 5.2 Key Entity Schemas

```
companies
├── id (UUID, PK)
├── symbol (VARCHAR, Unique Index)
├── name (VARCHAR)
├── sector (VARCHAR)
├── industry (VARCHAR)
├── market_cap (NUMERIC)
└── created_at (TIMESTAMP)

price_ohlcv (Hypertable)
├── time (TIMESTAMPTZ, PK Column)
├── symbol (VARCHAR, PK Column, Index)
├── open (NUMERIC)
├── high (NUMERIC)
├── low (NUMERIC)
├── close (NUMERIC)
├── volume (BIGINT)
└── adj_close (NUMERIC)

fundamentals
├── id (UUID, PK)
├── symbol (VARCHAR, Unique Index)
├── pe_ratio (NUMERIC)
├── pb_ratio (NUMERIC)
├── eps (NUMERIC)
├── roe (NUMERIC)
├── roce (NUMERIC)
├── dividend_yield (NUMERIC)
├── debt_equity (NUMERIC)
└── fetched_at (TIMESTAMP)

factor_scores
├── id (UUID, PK)
├── symbol (VARCHAR, Unique Index)
├── momentum_score (NUMERIC)
├── quality_score (NUMERIC)
├── value_score (NUMERIC)
├── growth_score (NUMERIC)
├── composite_score (NUMERIC)
└── computed_at (TIMESTAMP)

mf_schemes
├── id (UUID, PK)
├── scheme_code (INTEGER, Unique Index)
├── scheme_name (VARCHAR)
├── amc (VARCHAR)
├── category (VARCHAR)
└── sub_category (VARCHAR)

mf_nav (Hypertable)
├── date (DATE, PK Column)
├── scheme_code (INTEGER, PK Column, Index)
└── nav (NUMERIC)
```

---

## 6. Celery Periodic Task Topology

Background data ingestion and scheduled tasks are run via the Celery Beat scheduler:

| Task Name | Interval / Cron | Source | DB Table |
|---|---|---|---|
| `warm_live_universe_task` | Every 30 min (9:15-15:30 IST) | Yahoo Direct | `market_quotes` |
| `daily_eod_bhavcopy_task` | Daily 16:30 IST | NSE Bhavcopy | `price_ohlcv` |
| `mf_nav_daily_sync_task` | Daily 22:30 IST | mfapi.in | `mf_nav` |
| `alerts_evaluation_task` | Every 1 min | Database Cache | `alerts` (evaluates price trigger rules) |
| `rag_delta_reindex_task` | Weekly Sunday 02:00 | Database Store | `embeddings` (recompute factors/vectors) |

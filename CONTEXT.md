# QuantAI — Session Context and Migration Plan

## Current Architecture
- **Backend**: Monolithic FastAPI app in `/backend`
  - Routers: stocks.py, screener.py, portfolio.py, backtest.py, macro.py, ai.py
  - Services: data_service.py, factor_engine.py, ai_service.py
  - Models: database.py (basic Postgres), schemas.py
- **Frontend**: Next.js + TypeScript + Tailwind in `/frontend`
- **Infra**: Docker Compose with 6 services (backend, frontend, ollama, postgres, redis, celery_worker)

## Status (as of 2026-06-19)

### Fixed Bugs
1. **Quote endpoint 404** → Changed to 503, fixed `_fetch_yfinance_quote` to use `getattr()` instead of `.get()` on `fast_info` object
2. **Fundamentals endpoint 404** → Changed to 503
3. **Screener POST slow** → Replaced sequential loops with `_gather_limited` (bounded concurrency, default 8)
4. **Portfolio POST 500 (FK violation)** → Added `_ensure_demo_user()` that seeds a users row with placeholder `hashed_pw`
5. **Portfolio GET 500 (tuple unpack bug)** → Fixed slicing of `_gather_limited` flat list results
6. **Portfolio GET slow** → Changed 3×N sequential awaits into `_gather_limited`
7. **Portfolio FK path bug** → Fixed `select(PositionModel).where(PortfolioModel.id == ...)` → `where(PositionModel.portfolio_id == ...)`
8. **Portfolio GET response validation 500** → Removed `response_model=dict` from `@router.get("/{portfolio_id}")`

### Remaining Issues
- **yfinance globally 429'd** from container IP — all quote/fundamentals/price-history calls via Yahoo fail
- **nsepython also fails** — JSON decode errors (network/geo blocked)
- **Screener POST** → 503 because every fundamentals call fails
- **No real live data available** from any free source in this Docker network
- **High latency** — factor scores, technicals computed on-request (no precomputation)

### Test Results
| Endpoint | Status | Notes |
|---|---|---|
| POST /portfolio | ✅ 200 | Demo user auto-created |
| POST /portfolio/{id}/positions | ✅ 200 | |
| GET /portfolio/{id} | ✅ 200 | Sectors blank due to yfinance 429 |
| GET /portfolio/{id}/sector-allocation | ✅ 200 | All "Unknown" sector |
| GET /{ticker}/quote | ❌ 503 | yfinance 429 |
| GET /{ticker}/fundamentals | ❌ 503 | yfinance 429 |
| POST /screener | ❌ 503 | yfinance 429 |
| GET /sectors | ⚠️ empty | yfinance 429 |
| GET /{ticker}/factors | ✅ works | Uses cached/available data |
| GET /{ticker}/technicals | ✅ works | Same |
| GET /{ticker}/history | ✅ works | Same |
| GET /macro/* | ✅ works | Static data |
| POST /backtest/strategies | ✅ works | |

## Blueprint → Implementation Plan

The blueprint is at `C:\Users\harsh\Downloads\project\quant-investment-analyzer-blueprint.md` — a comprehensive production spec for Quant Investment Analyzer.

### Module Gap Analysis (vs Blueprint Section 3)

| Module | Status | Notes |
|---|---|---|
| Dashboard | ❌ Missing | No personalized home page |
| Stock Analysis | ✅ Partial | Has quote/history/fundamentals/factors/technicals endpoints |
| ETF Analysis | ❌ Missing | |
| Index Analysis | ❌ Missing | |
| Crypto Analysis | ❌ Missing | |
| Portfolio Analytics | ✅ Partial | Basic CRUD + risk metrics (Sharpe, beta, vol, MDD) |
| Quant Lab | ❌ Missing | Sandbox for custom factor models |
| Screener | ✅ Partial | Basic implementation, blocked by yfinance |
| AI Research Assistant | ❌ Missing | Basic ollama service, no RAG/tool-calling |
| News Intelligence | ❌ Missing | |
| Earnings Center | ❌ Missing | |
| Macro Dashboard | ✅ Partial | Static data only |
| Watchlists | ❌ Missing | |
| Alerts | ❌ Missing | |
| Backtesting | ✅ Partial | Basic implementation |
| Strategy Builder | ❌ Missing | No-code rule composer |

### Architecture Gaps (vs Blueprint Sections 5-7)

| Blueprint Spec | Current State | Delta |
|---|---|---|
| Microservices per domain | Monolithic FastAPI | Single app, no service decomposition |
| GraphQL gateway | REST only | N+1 query problem for composite pages |
| TimescaleDB hypertables | Plain Postgres | No time-series optimization for prices |
| Event bus (Redis Streams → Kafka) | No event bus | Tight coupling between services |
| Materialized views + precomputation | On-request computation | High latency |
| Background job queue | Celery worker exists but underused | Heavy work blocks HTTP requests |
| Multi-layer caching (Redis, CDN) | Basic TTL cache | No systematic cache strategy |
| Auth (Keycloak/Ory) | _ensure_demo_user hack | No real auth or RBAC |
| Normalized DB schema | Minimal tables | Missing 10+ tables |
| Vector store (pgvector → Qdrant) | Nothing | No embeddings or semantic search |
| Hybrid search (OpenSearch + vector) | Nothing | No search service |

### Database Gaps (vs Blueprint Section 7)

Current tables: users, portfolios, positions
Blueprint tables: + companies, fundamentals (normalized), factor_scores, watchlists, watchlist_items, alerts, strategies, backtest_runs, prices (Timescale hypertable)

### Latency Root Causes (Blueprint Section 13)
1. No precomputation — factor scores, technicals computed on-the-fly
2. No caching hierarchy — every request hits the data source
3. Monolithic requests — Stock Analysis page needs 4+ sequential API calls
4. Synchronous heavy work — no async job pattern
5. No GraphQL — frontend makes multiple round-trips

### Phased Implementation Plan

#### Phase A — Fix Latency & Data Sources (1-2 weeks)
1. Add seed/dummy data fallback for when yfinance/nsepython fail
2. Add retry with exponential backoff to yfinance calls
3. Precompute factor scores + technicals via nightly Celery job → cache in DB table
4. Add Redis caching layer for all API responses with TTL strategy
5. Convert expensive endpoints to async job pattern (return job ID, poll for result)

#### Phase B — Database Schema Overhaul (1 week)
1. Add companies, fundamentals (normalized EAV), factor_scores, watchlists, alerts, strategies, backtest_runs tables
2. Set up TimescaleDB hypertable for prices
3. Add proper foreign keys and indices matching blueprint ER diagram
4. Migration scripts for existing data

#### Phase C — New Modules (3-4 weeks)
1. Dashboard module (market overview, watchlist performance, macro snapshot)
2. Watchlists + Alerts CRUD + evaluation engine
3. Quant Lab (custom factor builder UI + backend)
4. Strategy Builder (no-code rules → backtest pipeline)
5. AI Research Assistant (RAG with tool-calling over filings/news/transcripts)

#### Phase D — Architecture Evolution (ongoing)
1. Introduce GraphQL gateway (or BFF pattern using Strawberry/Ariadne)
2. Event bus for data pipeline events (Redis Streams → Kafka/Redpanda)
3. Auth via Keycloak/Ory
4. Search service (OpenSearch + pgvector hybrid)
5. ETF/Index/Crypto modules

### Key Constraints
- 100% free/open-source only (no paid APIs or vendors)
- Must run via Docker Compose
- Data source reliability is the #1 blocker (yfinance 429)
- Latency is the #2 concern (user reports "very high latency")

## FYERS API Integration (Future Upgrade)

### Why FYERS
- **Only free live data source for Indian markets** — zero-cost trading account (no demat, no AMC) provides WebSocket streaming with millisecond latency
- **WebSocket ticks** — real-time LTP, OHLC, depth updates with no polling
- **Historical data** — REST API for daily/minute candles, positions, orders
- **Market data API** — Indices, option chains, market status via REST + WebSocket

### Setup Notes (for when user wants to migrate)
1. Register at [fyers.in](https://fyers.in) → Open a **trading-only account** (no demat needed, zero AMC)
2. Generate API credentials from My Profile → API Access
3. FYERS uses OAuth 2.0 with app ID + secret → redirect URL grant flow:
   ```
   https://api.fyers.in/api/v2/token
   ?client_id=YOUR_APP_ID
   &redirect_uri=YOUR_CALLBACK
   &response_type=code
   &state=STATE
   ```
4. Access token lifetime: 1 day (real-time) or longer for history-only tokens
5. Add `fyers-apiv3` Python library to requirements.txt
6. Create `backend/services/fyers_stream.py` — WebSocket manager for real-time ticks
7. Update `data_service.py` to prefer FYERS as primary source, falling back to NseIndiaApi → yfinance → seed data

### FYERS vs Alternatives
| Source | Cost | Latency | Coverage | Docker-Friendly |
|---|---|---|---|---|
| yfinance | Free | 15-min delay | Global | ❌ (429 blocked) |
| NseIndiaApi | Free | ~1s (polled) | NSE only | ✅ (httpx/http2) |
| nsepython | Free | ~1s (polled) | NSE only | ❌ (geo-blocked) |
| **FYERS** | **Free account** | **<100ms (WS)** | **NSE/BSE/Indices** | **✅ (dedicated API)** |
| Zerodha Kite | ₹200/month | <50ms (WS) | NSE/BSE/MCX | ✅ (paid) |

### When to Enable
- After core seed-data fallback is proven stable
- User registers for FYERS trading account (5 min process)
- Primarily for real-time portfolio tracking and alert evaluation engine
- Seed data continues as fallback when FYERS token expires or network issues occur

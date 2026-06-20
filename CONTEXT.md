# QuantAI — Session Context

## Project Direction (as of 2026-06-20)

**Full revamp** of existing codebase into a Groww-like comprehensive investment analyzer.

- **Scope**: Stocks, Mutual Funds, IPO/SME (MVP) → F&O, Commodities (later phases)
- **Target**: Personal use, single user, localhost/Docker
- **Constraint**: 100% free/open-source, zero paid APIs
- **Plan**: See `PROJECT_PLAN.md` for complete spec

### Key Decision: Revamp, Not Rewrite
Existing code has working infra (Docker Compose, Postgres+TimescaleDB, Redis, Celery, Ollama) but backend is messy and frontend is a scaffold. Approach:
- **Keep**: Docker Compose setup, database infra, Redis/Celery config
- **Restructure**: Backend → clean `modules/` pattern (stocks, mutual_funds, ipo, portfolio, etc.)
- **Rebuild**: Frontend from scratch with proper component architecture
- **Replace primary data source**: jugaad-data replaces yfinance as primary (yfinance 429 blocked)

## Current Architecture
- **Backend**: Monolithic FastAPI in `/backend`
  - Routers: stocks, screener, portfolio, backtest, macro, ai, alerts, auth, dashboard, earnings, insight, news, quant_lab, strategy_builder, watchlists
  - Services: data_service, factor_engine, ai_service, cache_service, celery_app, fast_data, fyers_client, ingestion_service, auth_service
  - Models: database.py (Postgres), schemas.py
- **Frontend**: Next.js + TypeScript + Tailwind in `/frontend` (scaffold, pages exist but minimal)
- **Infra**: Docker Compose (backend, frontend, ollama, postgres, redis, celery_worker)

## Known Issues (carried forward)

### Data Source Reality (verified 2026-06-20 from inside the container, Indian IP)
Empirically probed — what actually works from this machine:
- ✅ **Direct Yahoo v8 chart API** (`services/fast_data.py`, `query1.finance.yahoo.com/v8/finance/chart`) — the ONLY working live price/index source. Returns current data (RELIANCE, ^NSEI, INR=X all dated to the trading day).
- ✅ **NSE public APIs WITH cookie warming** (`services/nse_live.py`) — work from this IP: `/api/fiidiiTradeReact` (live FII/DII), `/api/all-upcoming-issues?category=ipo`, `/api/public-past-issues?category=eq` (IPOs). Bare requests get 403; warming cookies first fixes it.
- ✅ **mfapi.in** (MF NAV), **screener.in** (fundamentals), **World Bank API** (CPI/GDP, free no-key).
- ❌ **yfinance library** `download`/`Ticker.info` — JSONDecodeError (Yahoo blocks the library endpoints; the direct v8 chart API still works).
- ❌ **jugaad-data, nsepython, NseIndiaApi** — all fail (NSE 403 / JSON decode). The earlier plan to "switch to jugaad-data as primary" does NOT work here; use direct Yahoo + cookie-warmed nse_live instead.

### Stale-data fixes applied (2026-06-20)
Macro was hardcoded (2024–25 dates) / random; factor scores were flat 60; IPO/MF partly seed.
- Macro now LIVE: USD/INR (Yahoo INR=X), FII/DII (NSE), CPI+GDP (World Bank). Repo rate = RBI policy path (no free API; current-dated, labelled "last published").
- Factor/composite scores computed live from price momentum (`data_service._composite_for`), cached 1h.
- IPO now live from NSE; MF live from mfapi. Caches cleared after each fix.

### Backend Bugs (previously fixed, verify after revamp)
1. Quote endpoint → was 404, fixed to 503 with `getattr()` on `fast_info`
2. Portfolio FK violation → fixed with `_ensure_demo_user()`
3. Portfolio tuple unpack bug → fixed slicing of `_gather_limited` results
4. Screener slow → fixed with `_gather_limited` bounded concurrency

### Architecture Issues
- No precomputation — factor scores, technicals computed on-the-fly
- No systematic caching — every request hits data source
- Monolithic — no module separation
- No auth (not needed for personal use, but `_ensure_demo_user` hack should be cleaned up)

## Revamp Progress

| Task | Status | Notes |
|---|---|---|
| PROJECT_PLAN.md created | ✅ Done | Full spec with all modules, APIs, DB schema |
| Full Docker stack running | ✅ Done | `docker compose up` — all 7 containers healthy; Ollama llama3.2 pulled; real NSE quotes/dashboard/macro flowing |
| Backend `modules/` foundation | ✅ Done | `backend/modules/` package created per plan §4 (router/service/schemas/models pattern) |
| Mutual Fund module | ✅ Done | `modules/mutual_funds` — live mfapi.in search, NAV history, returns/CAGR, risk (vol/Sharpe/Sortino/maxDD), SIP calc, compare. Redis-cached + seed fallback |
| IPO module | ✅ Done | `modules/ipo` — upcoming/open/listed/SME/calendar, date-derived status, GMP, subscription, listing gains. Seed dataset + best-effort live NSE |
| Frontend: MF + IPO pages | ✅ Done | `/mutual-funds` (search, NAV chart, returns, risk, SIP) and `/ipo` (tabbed tracker) + sidebar nav + api.ts/hooks |
| CORS hardening | ✅ Done | Allow any localhost/127.0.0.1 port (local dev robustness) |
| Backend restructure to modules/ (existing routers) | ✅ Done | All 17 domains now under `backend/modules/<name>/`; `routers/` package removed; 65 routes verified working. `stocks` is the full router+service+schemas exemplar; thin domains have router.py calling the shared services layer. Remaining refinement: extract `service.py` from the other fat routers (portfolio/screener/watchlists/alerts). |
| Database schema overhaul | 🟡 Partial | New mf_schemes/mf_nav/ipos tables added via create_all; TimescaleDB hypertables not yet applied |
| Data source migration (jugaad-data) | ⬜ Not started | |
| Redis caching layer | 🟡 Partial | cache_service used by new modules; not yet systematic across all endpoints |
| Celery ingestion tasks (MF NAV, IPO refresh) | ⬜ Not started | MF/IPO served live+cached on-demand; no scheduled ingestion yet |
| MF holdings / sector allocation | ⬜ Not started | Needs mfdata.in or AMFI source |
| Portfolio / Watchlist / Alerts revamp | ⬜ Not started | Working in monolith; not yet moved to modules/ |
| Frontend rebuild (full) | 🟡 Partial | Existing pages work; MF/IPO added; full component-architecture rebuild pending |
| AI integration | ✅ Existing | Ollama insight/chat already wired and working |

*Updated 2026-06-20: Full Docker stack brought up and verified end-to-end. modules/ architecture established with the two missing MVP modules (Mutual Funds, IPO) built, wired, and visually verified with live data. Remaining: migrate existing routers into modules/, Celery ingestion for MF/IPO, MF holdings, TimescaleDB hypertables.*

## Hardening pass (2026-06-20) — live data + bug fixes

Audited every page/endpoint for stale data and functional bugs. Fixes:

- **Fundamentals were seed + wrong keys.** `data_service.get_fundamentals` called a broken internal scraper (`_fetch_screener_in_fundamentals` → `{}`), then 429'd yfinance, then seed — and returned camelCase keys the UI didn't read. Now routes through the working `screener_service` (via `fast_data`), normalises to snake_case (`pe_ratio`/`market_cap`/…), derives `pb_ratio` (price/book) and `debt_equity`, and `/stocks/{t}/fundamentals` attaches absolute single-stock `factor_scores` via `compute_quant_factors`. Real values now (e.g. TCS ROE 65%, ROCE 77%).
- **Seed-cache poisoning.** Seed fallback was cached 24h (same as live), so a transient miss masked live data all day. Now seed is cached only 120s (self-heals) and tagged `source:"seed"`; live cached 24h.
- **screener.in rate-limit blocks.** Bursts (warm-up/screener) tripped blocks → mass seed. Added a global throttle in `screener_service`: `Semaphore(2)` + 1.5s min-interval rate gate. Coverage went 2/10 → 17/18 live.
- **Screener timed out (>110s) then 500'd.** It screened all 1,103 seed tickers live (yfinance 429 storm) → bounded to NIFTY-50; removed the yfinance fundamentals fallback entirely (pure 429 noise here); coerced sparse fundamentals to numeric (factor engine `-NaN`); fixed `name=NaN` ValidationError. Now ~0.5s.
- **Sector 1w/1m were fabricated** (`1d × random`) → now real returns from member-stock price history.
- **Refresh buttons** now bypass cache end-to-end (macro/IPO/MF: `refresh` param threaded through routers→services→frontend hooks/buttons).
- **Celery was harmful**: `refresh-daily-seed-cache` wrote seed into `fund_` every 6h (re-poisoning); `ingest-prices` ran yfinance over 100 tickers/15min (429/403 storms). Disabled both; beat now runs only a light LIVE `warm_live_universe_task` (NIFTY-50). Backend `lifespan` warms the live universe on startup.
- **Verified live**: stocks (quote/history/fundamentals/technicals/factors), dashboard (indices/movers/sector/factor-signals), screener, portfolio P&L (live prices), macro, MF, IPO. **AI (Ollama llama3.2) confirmed working.**

Key constraint: free Indian data is fragile under load — screener.in blocks bursts, NSE needs cookie warming, Yahoo's library endpoints 429 (only the v8 chart API works). Always throttle batch fundamental fetches.*

## Data Source Strategy

| Source | Purpose | Priority |
|---|---|---|
| jugaad-data | Stocks (live + historical), F&O, indices | Primary |
| mfapi.in | Mutual fund NAV (14k+ schemes) | Primary |
| mfdata.in | MF holdings, ratios, analytics | Supplementary |
| yfinance | Fallback for stocks, commodities | Fallback |
| pnsea | NSE data fallback | Fallback |
| GNews API | News (100 req/day free) | Primary |
| NSE corporate actions | IPO data | Primary |
| VADER | Sentiment scoring | Internal |
| RBI DBIE / FRED | Macro data | Primary |

## File Structure Reference

```
quant-analyzer/
├── PROJECT_PLAN.md          ← Complete project specification
├── CONTEXT.md               ← This file (session context, progress tracking)
├── README.md                ← How to run the project
├── docker-compose.yml       ← Docker infra
├── backend/                 ← FastAPI backend (to be restructured)
├── frontend/                ← Next.js frontend (to be rebuilt)
└── tasks/                   ← Task files
```

---
*Last updated: 2026-06-20 — Full revamp direction established*

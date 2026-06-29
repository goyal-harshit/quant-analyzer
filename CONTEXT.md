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

## Audit-report fixes (2026-06-20)

Acted on `QuantAI_Audit_Report.docx`. Fixed the crash/correctness/UI items:
- **Backend**: `factor_engine.z_score` div-by-zero (the `.replace(0,1)` no-op on a scalar); `seed_data` EXTRA_STOCKS no longer overwrites rich 13-field STOCK_MASTER entries; `cache_service` correct async detection (`iscoroutine`) + in-memory TTL/size bound; `auth_service` generates+persists a random JWT secret instead of the known default; alerts `delete` ownership check (IDOR); removed hardcoded stale index fallback (NIFTY=25123…) from `data_service.get_market_summary`; AI report null-unpack guard; `fast_data` change_pct 0.0-is-falsy bug.
- **Frontend**: added `<Toaster/>` to layout (toasts were invisible app-wide); fixed Rules-of-Hooks violation in portfolio (hook after early return); fixed setState-during-render in watchlists; fixed invalid `justifyContent:'between'` → `'space-between'` on 4 pages; aligned globals.css color vars to the `T` tokens (single source of truth); added 401 response interceptor (expired token → clear + redirect to login); fixed Header `collapsed-sibling` invalid class (now collapse-aware via prop).
- **New pages**: `/notifications` (live feed: open/upcoming IPOs, top movers, VIX — wired to the header bell) and `/profile` (account details + quick links + sign-out — wired to the header avatar; guest state when logged out).

Deliberately deferred (larger architectural work, not needed for "runs smoother"): app-wide auth-gating of public routes (would break the current token-less frontend), httpOnly-cookie auth + refresh tokens, rate limiting, Alembic migrations, next/font swap, mobile hamburger/focus-traps, circuit breakers, real earnings/news sources, comprehensive tests + CI/CD.*

## Roadmap hardening — Foundation + Data Reliability (2026-06-27)

Acted on `QuantAI_Audit_Improvements_Roadmap.docx` §3.1 / §3.2 / §3.5 and Section 6
(prioritised next steps). Scope this pass: **Foundation pack + data-reliability layer**
(provider abstraction + circuit breakers). All work is additive and unit-verified —
**66 backend tests pass** (`cd backend && pytest`, runs against SQLite, no DB service needed).

- **Reliability primitives** — new `services/reliability.py`: per-source `CircuitBreaker`
  (CLOSED/OPEN/HALF_OPEN), `TokenBucket` rate limiter, `retry_async` (exp backoff + jitter),
  `SourceGuard` + a named registry (`guard_call("yahoo"|"screener"|"nse"|…)`). Stdlib-only,
  clock-injectable, deterministically tested (`tests/test_reliability.py`, 14 tests).
- **Breakers wired into the storm-prone call sites** — `fast_data._get` (Yahoo),
  `screener_service` (replaced the ad-hoc Semaphore+rate-gate with the shared guard),
  `nse_live.get_json` (breaker around its cookie-warm/retry loop). Only *source-health*
  failures (403/408/425/429/5xx) trip the breaker; 404/400 (symbol-absent) do not. This
  ends the documented 429/403 "storm" class — repeated failures short-circuit for a cooldown
  instead of stampeding the single worker.
- **Provider abstraction + fallback chain** — new `services/providers.py`: `DataProvider`
  protocol + `FallbackChain`. Single call site `market_data`; tags every value with
  `source` + `as_of`. Order is config-driven via `DATA_PROVIDER_ORDER` (default
  `yahoo,nsepython,jugaad,seed`; `build_chain()` always appends `seed` as backstop).
- **Multi-source redundancy (nsepython + jugaad-data)** — added `NsePythonProvider` and
  `JugaadProvider` as guarded `DataProvider`s. They lazy-import the sync libs, run calls in
  a thread (`asyncio.to_thread`) so they never block the loop, normalize the NSE quote-equity
  JSON / OHLC frames to the standard schema, and sit behind their own circuit breakers
  (`nsepython`/`jugaad`: trip after 3 failures, 2-min cooldown, no retries). They're absent
  from this host (NSE 403s) — but as guarded fallbacks they add authoritative redundancy for
  other envs / when Yahoo has gaps, at ~zero cost when blocked (breaker trips → chain falls
  through). Missing-lib and lib-error both degrade to None, never raise. `tests/test_providers.py`
  now 24 tests (fakes + normalizers + order-driven assembly).
- **Quant correctness suite** — `tests/test_quant_metrics.py` (23 golden-master tests):
  Sharpe/Sortino/Calmar/CAGR/max-drawdown/beta/alpha/VaR/CVaR + factor ranking + the
  single-stock `compute_quant_factors` pipeline, all against hand-computed fixtures.
  **Surfaced & fixed a real bug**: `compute_quant_factors` RSI returned `NaN` for an
  all-gains window (no zero-div guard, unlike `FactorEngine.rsi`) → now guarded.
- **Typed settings + response envelope** — `config.py` (pydantic-settings `Settings` +
  `get_settings()`; CORS now reads it in `main.py`) and `services/envelope.py`
  (`{data, source, as_of, cached}`). Both unit-tested.
- **Observability** — `/health` now reports per-source breaker state (`data_sources`).
- **CI** — `.github/workflows/ci.yml`: backend `ruff check` (scoped high-signal gate via
  `backend/ruff.toml`) + `pytest`; frontend `next build` (type-check + compile). Deliberately
  no eslint config added (Next 14 lints during build; adding one risks breaking the currently
  green deploy build). Also: removed 34 dead imports/empty-f-strings via ruff; made `tests/conftest.py`
  lazy-import the app so unit suites collect without the full web stack.

## Ingest-then-serve store (2026-06-27)

Audit §3.1 #4 — "endpoints read from DB; freshness is a column, not a live fetch."

- **Store tables** — new `models/market_store.py`: `market_quotes` / `market_bars` /
  `market_fundamentals`, each with `source` + `fetched_at` (+ `as_of`, + a `raw` JSON
  snapshot on quotes so serving from DB preserves the full live shape — no field regression).
  Plain SQLAlchemy (SQLite + Postgres); `market_bars` becomes a TimescaleDB hypertable on
  Postgres via `ensure_hypertables()` (best-effort, no-op on SQLite / when extension absent,
  called from lifespan).
- **Store service** — `services/market_store.py`: `upsert_quote/fundamentals/bars` (merge /
  delete-then-insert), freshness-gated `read_quote/fundamentals/bars` (stale row → miss →
  chain falls through), and `ingest_*` (fetch via the LIVE chain, write DB).
- **DB-first read path** — `DBProvider` (name `db`) added to `providers.py`, placed first in
  the READ chain. Two singletons now: `market_data` (`db→yahoo→nsepython→jugaad→seed`, for
  endpoints) and `live_data` (same minus `db`, for ingestion — avoids reading our own writes).
  DBProvider degrades to None on any DB error (never raises).
- **Scheduled refresh** — `refresh_market_store_task` (Celery) ingests quotes+fundamentals+
  history for the liquid universe through the guarded LIVE chain; wired into beat every 30 min.
  Safe to schedule now (every source is breaker-guarded — unlike the old yfinance jobs).
- **Stocks endpoints wired** — `modules/stocks/service.py` now serves quote, fundamentals,
  history, factors and technicals through store-first base accessors (`_base_fundamentals`,
  `_base_history`) with on-demand write-through. Quotes use the 2-min freshness gate;
  fundamentals the 24h gate; history is **coverage-gated** (`_min_rows ≈ 0.6 × calendar days`)
  so the store never under-serves a longer period than it has ingested — below threshold it
  falls through to live. Purely additive: any miss/stale/DB-down path reproduces the exact
  previous behaviour, so zero regression risk.
- Tests: `test_market_store.py` (10) + `test_stocks_quote_store.py` (6 — quote/fundamentals/
  history fast-path, fallback, write-through, refresh-bypass, coverage gate). **Suite now 94 tests.**

## Observability (2026-06-27)

Audit §3.5 — `services/observability.py` (dependency-light):
- **Structured JSON logs** — `JsonFormatter` emits single-line JSON (ts/level/logger/msg/
  request_id + any `extra={}`); `configure_logging(level, json)` installs it (set `LOG_JSON=false`
  for plain dev logs). Replaces `logging.basicConfig` in main.
- **Request IDs** — `RequestContextMiddleware` reads/issues `X-Request-ID`, binds it to a
  contextvar so every log line of a request correlates, echoes it on the response, and emits a
  structured access log per request.
- **Metrics** — tiny in-process registry (counters + summaries) rendered in Prometheus text at
  `GET /metrics` (no prometheus-client dep): `http_requests_total`, `http_request_duration_seconds`,
  `cache_requests_total{result=hit|miss}` (instrumented in cache_service), and
  `circuit_breaker_state{source,state}` gauges from the reliability layer.
- **Sentry** — `init_sentry()` in lifespan, active only when `SENTRY_DSN` set + SDK installed
  (graceful no-op otherwise).
- Config knobs: `LOG_LEVEL`, `LOG_JSON`, `METRICS_ENABLED`, `SENTRY_DSN`,
  `SENTRY_TRACES_SAMPLE_RATE`, `ENVIRONMENT`.
- Tests: `test_observability.py` (13, incl. full-app middleware header/propagation/`/metrics`).
  **Suite now 107 tests.**

## Auth hardening — httpOnly cookies + refresh tokens (2026-06-27)

Audit §3.4. (Enforcement was already in place: portfolio/watchlists/alerts/simulator all
require `get_current_user`, per-user scoped — the old demo-user hack is gone.)
- **Token storage off localStorage** — login now sets **httpOnly** `access_token` +
  `refresh_token` cookies (`set_auth_cookies`); the JWT is no longer kept in JS-readable
  storage (XSS can't steal it). Login still returns the token in the body for backward compat.
- **Header OR cookie** — `get_current_user`/`get_optional_user` resolve the token from the
  Authorization header first, then the cookie — so existing header clients keep working.
- **Refresh + logout** — `POST /auth/refresh` mints a new access token from the refresh cookie
  and rotates it; `POST /auth/logout` clears cookies. Access/refresh tokens carry a `type` claim
  enforced by `decode_token` (an access token can't be used as refresh, and vice-versa; legacy
  no-`type` tokens still validate as access).
- **Secret management** — `auth_service` reads the secret from typed settings (`JWT_SECRET_KEY`),
  with a loud error in `ENVIRONMENT=production` if it falls back to a machine-local generated one.
- **Frontend** — `lib/api.ts` uses `withCredentials` + silent refresh-on-401 (one retry, then
  redirect); `AuthProvider` stores only a non-sensitive `authed` marker, calls `/auth/logout`.
- **Prod cross-site** — `render.yaml` sets `COOKIE_SAMESITE=none` + `COOKIE_SECURE=true` (GH Pages
  → Render is cross-site, so the browser only sends the cookies under those attributes).
- Tests: `test_auth_cookies.py` (13: type enforcement, cookie/header/refresh/logout flows).
  conftest disables the rate limiter for the suite. Frontend `tsc --noEmit` clean. **Suite now 119 tests.**

## Phase A foundation — Alembic + CSRF (2026-06-28)

From `PROJECT_MASTER_PLAN.md` Phase A (logging + typed settings already done earlier this session).
- **Alembic migrations (P0, bug #1)** — `env.py` now imports ALL model modules (market_store +
  mutual_funds/ipo/simulator) so autogenerate is complete; baseline migration
  `b8ffc3251ccc_baseline_schema.py` captures all 20 tables (hand-fixed the JSONB columns to a
  portable `sa.JSON().with_variant(postgresql.JSONB, "postgresql")` so migrations run on SQLite+PG).
  `scripts/migrate.py` applies them idempotently across **fresh / legacy(create_all) / versioned**
  DBs (stamps an existing DB at baseline — safe adoption, no data loss). Dockerfile runs it before
  uvicorn; `DB_AUTO_CREATE=false` in render.yaml makes migrations authoritative in prod (create_all
  is now gated behind that env, default true for dev/test). CI verifies `upgrade head`/`downgrade base`;
  `test_migrations.py` fails on model/migration drift.
- **CSRF (bug #3)** — double-submit guard for the new cookie auth: `set_auth_cookies` also sets a
  readable `csrf_token` cookie and returns the token (echoed in the login/refresh body so the
  **cross-site** GH-Pages frontend can read it — it can't read the backend's cookie). `install_csrf_protection`
  middleware requires `X-CSRF-Token` == csrf cookie on cookie-authenticated unsafe methods; Bearer-header
  auth and `/api/v1/auth/*` are exempt. Frontend sends the header on mutations + clears it on logout.
- Tests: `test_migrations.py` (1) + CSRF cases in `test_auth_cookies.py`. **Suite now 125 tests.** Frontend `tsc` clean.

## Phase B — auth & notifications core (2026-06-28)

From `PROJECT_MASTER_PLAN.md` Phase B. Delivered the fully-testable items (#6 email, #7
reset/verify, #8 RBAC); OAuth social login (#5) deferred — needs live provider credentials.
- **RBAC** — `User.role` (default "user") + `User.is_verified` columns (migration
  `5158e99478e5`, batch-mode + server_default so existing rows backfill). `require_role(*roles)`
  / `require_admin` dependencies in auth_service; demo route `GET /api/v1/auth/admin/ping`.
  `UserOut` now returns `role` + `is_verified`.
- **Email transport** — `services/email_service.py`: pluggable `send_email` with
  console (dev default) / memory (tests, `outbox`) / smtp (aiosmtplib, prod) backends; never
  raises into the caller. Config: `EMAIL_BACKEND`, `SMTP_*`, `EMAIL_FROM`, `FRONTEND_BASE_URL`.
- **Password reset + email verification** — JWT `reset`/`verify` token types (short-lived);
  endpoints `POST /auth/forgot-password` (no user enumeration — always 200), `/auth/reset-password`,
  `/auth/send-verification`, `/auth/verify-email`. All under `/auth/*` so CSRF-exempt. Frontend
  `authApi` methods added.
- Tests: `test_rbac.py` (4) + `test_password_reset.py` (6, incl. token-type enforcement & weak-pw
  rejection, via the memory outbox). **Suite now 135 tests.** Frontend `tsc` clean.

Still deferred: OAuth social login (authlib Google/GitHub — needs creds), magic links,
file import/export + PDF reports (Phase C), RAG/pgvector AI grounding (Phase D),
dark/light + responsive/PWA (Phase E), store adoption across remaining modules.*

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
*Last updated: 2026-06-29 — Phases A + B (core) complete; 135 backend tests passing. Next: Phase C (file import/export) or Phase D (RAG/pgvector).*

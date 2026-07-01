# QuantAI — Project Health Audit & Fix Plan
Generated: 2026-07-01

## 1. Root Causes (the 3 things you reported)

### 1.1 Login → "Backend not reachable"
Error text lives in `frontend/app/login/page.tsx:29-30` — fires when axios gets **no response object** (network/CORS/timeout), not a 401.

`NEXT_PUBLIC_API_URL` is a browser-side var (`frontend/lib/api.ts:8`), baked in at **build time**, three different values depending on how you built:

| Build source | Baked API URL | Works when |
|---|---|---|
| `docker-compose.yml` (`frontend` service) | `http://localhost:8000/api/v1` | You open the app at `localhost:3000` **and** `docker compose up` has backend healthy on `:8000` |
| `.github/workflows/deploy.yml` (GH Pages) | `https://quant-analyzer-backend.onrender.com/api/v1` | Render backend is awake and DB reachable |
| Stale `frontend/out/` checked into repo | `http://localhost:8000/api/v1` | Same as docker case — **but this folder is a static export you may be serving directly**, e.g. via `npx serve out`, with no backend running at all |

Most likely triggers, in order:
1. **Render free-tier cold start.** `render.yaml` deploys the backend on Render's free plan. Free web services sleep after ~15 min idle and take 30–60s to wake. Frontend axios timeout is 45s (`lib/api.ts:14`) — first login attempt after idle can time out and read as "no response."
2. **Render backend has no Redis/Ollama.** `render.yaml:27-29` sets `REDIS_URL=""` and `OLLAMA_HOST=""` in prod. Not a login blocker by itself, but confirms prod is a stripped-down deploy — worth knowing before debugging further.
3. **Local docker-compose not actually up**, or `postgres`/`redis`/`ollama` health checks never pass, so `backend` never starts (it has `depends_on: condition: service_healthy`). Ollama image pull (several GB) on first run can stall this for a long time.
4. **Serving `frontend/out/` standalone** without a backend running on `localhost:8000` at all.

**Action:** confirm which of the 3 you're actually running, then verify `GET /health` on that exact backend URL from the same browser context (see §4 verification steps).

### 1.2 Main page showing wrong stock data
No mock-data bug in the code path itself — this is a **fallback-to-demo-data-by-design** behavior that isn't obvious to the end user:
- `frontend/app/dashboard/page.tsx` renders hardcoded `DEMO_INDICES` / `DEMO_MOVERS` / `DEMO_FACTOR_SIGNALS` whenever the live API call fails or returns empty, with a small warning banner (easy to miss).
- `frontend/app/page.tsx` (landing) does the same with `RAW` / `SCREENER_DATA`.
- Root cause is the same connectivity problem as §1.1 — if the backend is unreachable, demo numbers render silently-ish.
- Separately, even when the backend **is** reachable, `backend/services/data_service.py` only warms/serves `NIFTY_50_TICKERS` (50 tickers) for dashboard/universe endpoints, and `seed_data.py` has ~103 stocks total (`ALL_STOCKS`, line 734) — not 500. So "wrong" may also mean "narrower universe than expected," not just stale numbers.

**Action:** fix connectivity (§1.1), then make the demo-data banner impossible to miss (currently a low-contrast note), and decide whether to actually expand the universe or correct the landing-page claim (§1.3).

### 1.3 Landing page advertises features that don't exist yet
`frontend/app/page.tsx`:

| Claim (line) | Reality | Verdict |
|---|---|---|
| "500 Nifty 500 Stocks Covered" (line 314) | ~~Dashboard/universe hardcoded to `NIFTY_50_TICKERS` (50)~~ **FIXED**: `services/universe.py` `NIFTY_500_TICKERS` (500 curated real NSE names); screener + Quant Lab screen it via a fast network-free snapshot (~4.5s for 500). Screener has a Nifty 50 · Live / Nifty 500 toggle. | **True (built)** |
| "15 Quantitative Factors" (line 315) | ~~~6 factor types~~ **FIXED**: 15 factors in `factor_engine.py` (momentum, value, quality, growth, low-vol, size, reversal, profitability, financial-health, dividend, liquidity, low-beta, earnings-quality, trend, composite); exposed via `/quant-lab/factor-definitions`. | **True (built)** |
| "Live signals updated every 15 minutes" (line 333) | ~~No 15-min job~~ **FIXED**: Celery beat `warm-live-universe` + `refresh-market-store` now run `*/15`. | **True (built)** |
| Quant Lab: "Factor Builder, Portfolio Optimization, Risk Decomposition, Monte Carlo" | ~~static "Coming Soon" card~~ **FIXED**: `quant-lab/page.tsx` is a full factor-weight builder + ranking table; backend `/quant-lab/score` `/optimize` `/monte-carlo` live. | **Built** |
| "100% Free & Open Source", "0 API Keys Required" | Accurate — all data sources are free/keyless | **True** |
| AI Research Assistant (Ollama) | Real, works when Ollama configured; **prod Render deploy has `OLLAMA_HOST=""`**, so AI is effectively off in the live deployed site | **True locally, broken in prod** |
| Macro Dashboard (RBI/CPI/IIP/FII-DII/INR-USD) | Real, backed by World Bank + NSE + Yahoo | **True** |
| Portfolio analytics (Sharpe, beta, drawdown) | Real for Sharpe/performance; "factor decomposition" specifically not found | **Partially true** |

**Action:** either implement the gap (universe expansion, 9 more factors, Quant Lab) or rewrite the hero copy to match current reality. Given "priority on everything working," recommend rewriting copy now (cheap, immediate, honest) and tracking the feature build-out as P1/P2 below.

---

## 2. Function / Route Map (Backend — 103 routes, 19 modules)

All routes mounted in `backend/main.py`. Status legend: ✅ live-data implementation · ⚠ works but degrades to stub/seed under some condition · ❌ placeholder.

| Module | Routes | Status | Key file |
|---|---|---|---|
| auth | register, login, refresh, logout, me, forgot-password, reset-password, verify-email, send-verification, admin/ping (10) | ✅ | `backend/modules/auth/router.py`, `services/auth_service.py` |
| stocks | search, quote, fundamentals, history, factors, technicals, batch/quotes (7) | ✅ (⚠ falls to seed if all live sources fail) | `modules/stocks/service.py`, `services/data_service.py` |
| dashboard | market-summary, top-gainers-losers, sector-performance, factor-signals, universe-overview, indices, index (7) | ✅ (⚠ universe capped at NIFTY 50, seed fallback) | `modules/dashboard/router.py` |
| screener | screen, export, sectors (3) | ✅ | `modules/screener` |
| portfolio | CRUD + valuation + risk + import/export CSV/XLSX/PDF + tax (11) | ✅ | `modules/portfolio` |
| backtest | run, templates (2) | ✅ | `modules/backtest` |
| macro | dashboard, regime (2) | ✅ (regime is simple rule-based, not ML) | `modules/macro/router.py:79-104` |
| ai | chat, ask, report, insight, thesis, earnings-summary, RAG, conversations (12) | ⚠ | `modules/ai/router.py` — **earnings-summary is placeholder text (line 230)**; all AI needs Ollama, which is off in prod |
| alerts | CRUD, evaluate (4) | ✅ | `modules/alerts` |
| news | market news, ticker sentiment (2) | ✅ | `modules/news` |
| earnings | calendar, ticker history (2) | ✅ | `modules/earnings` |
| watchlists | CRUD, quotes, performance (6) | ✅ | `modules/watchlists` |
| quant_lab (backend) | factor scorer, factor defs (2) | ✅ backend exists, but **no frontend page consumes it** — UI shows "Coming Soon" | `modules/quant_lab` |
| simulator | portfolio CRUD, trades, performance, Sharpe/Sortino (7) | ✅ | `modules/simulator` |
| strategy_builder | rule backtest, templates (2) | ✅ | `modules/strategy_builder` |
| mutual_funds | search, SIP calc, compare, returns, risk (7) | ✅ | `modules/mutual_funds` |
| ipo | all, upcoming, open, listed, SME, calendar (6) | ✅ | `modules/ipo` |
| sectors | performance, heatmap, stocks (3) | ✅ | `modules/sectors` |
| compare | compare 2–5 stocks (2) | ✅ | `modules/compare` |
| insight | consolidated stock insight (1) | ✅ | `modules/insight` |

**Data providers:** Yahoo (direct), NSE (`nse[server]`), jugaad-data, nsepython, yfinance (fallback chain), Screener.in (scrape, sparse/rate-limited), World Bank, Google News RSS, mfapi.in — all free/keyless, all functional with retry/circuit-breaker logic in `services/reliability.py`. Seed data (`services/seed_data.py`, ~103 tickers) is the last-resort fallback and is what you see when live sources are exhausted.

## 3. Function / Page Map (Frontend — 21 routes)

| Page | Data | Status |
|---|---|---|
| `/` (landing) | Live fetch + hardcoded fallback (`RAW`, `SCREENER_DATA`) | ⚠ copy overstates scope (§1.3) |
| `/dashboard` | Live fetch + hardcoded fallback (`DEMO_*`) | ⚠ silent-ish demo banner |
| `/stocks/[ticker]` | Live only, no fallback | ✅ |
| `/ai` | Live + offline context fallback | ✅ (needs Ollama) |
| `/backtest`, `/compare`, `/indices`, `/indices/[slug]`, `/ipo`, `/macro`, `/mutual-funds`, `/notifications`, `/sectors`, `/screener` | Live only | ✅ |
| `/login`, `/register` | Live only, requires backend | ✅ (connectivity-dependent) |
| `/portfolio`, `/watchlists`, `/profile` | Live, auth-gated | ✅ |
| `/simulator` | Live + localStorage guest mode | ✅ |
| `/quant-lab` | None — static "Coming Soon" | ❌ **stub**, despite backend module existing |

---

## 4. Priority Fix Plan

> **Update 2026-07-01 — feature build executed.** P0 #4 (loud demo banner), P1 #5 (universe→500 + 15 factors + 15-min cadence), P1 #6 (real earnings-summary), and P1 #7 (Quant Lab built) are done. Also fixed a real prod bug: `cache_service` retried a down Redis on *every* get, turning a 500-name screen into a 9-minute stall (Render sets `REDIS_URL=""`) — now backed off with a reconnect cooldown + connect timeout. Remaining: P0 #1-3 (deployment diagnosis, your call), P2 items (health self-check, scrape resilience, JWT-secret confirm), and infra add-ons (OAuth needs creds; Playwright E2E; Umami/Uptime-Kuma).

**P0 — Blocking (do first)**
1. Determine which deployment you're actually testing (local docker vs GH Pages+Render vs standalone `out/`) and confirm the backend at that exact URL responds to `GET /health`.
2. If Render: hit the backend URL directly once to force cold-start wake, then retry login. If still failing, check Render dashboard logs for crash-on-boot (likely DB connection, since `REDIS_URL`/`OLLAMA_HOST` are empty by design — that's fine, but Postgres must be reachable).
3. If local docker: `docker compose ps` — confirm `postgres`/`redis` are `healthy` and `backend` is `Up`, not restarting.
4. Make the dashboard/landing "demo data" banner visually loud (red border, not a subtle note) so wrong-looking numbers are never mistaken for live data again.

**P1 — Correctness / honesty**
5. Rewrite landing-page hero stats (`frontend/app/page.tsx:314-315,333`) to match reality, or expand `NIFTY_50_TICKERS` universe to actually cover Nifty 500 and implement the remaining ~9 factors.
6. ~~Replace `ai/router.py:230` earnings-summary placeholder~~ **DONE (2026-07-01)**: `/ai/earnings-summary` now assembles real context — Screener.in quarterly figures (`get_ticker_earnings`) + fundamentals + recent Google-News headlines (`get_ticker_news`) — via `_build_earnings_context`, then summarises. Returns `data_available: false` honestly when free sources have nothing. (Verified live: TCS Q3 rev ₹58,052cr / PAT ₹14,526cr + 6 headlines.)
7. Decide Quant Lab: build it against the existing backend `quant_lab` module (fastest — backend logic already exists) or remove the "Coming Soon" teaser from the landing page until it ships.

**P2 — Hardening**
8. Add a startup health self-check the frontend can call to distinguish "backend asleep/cold" from "backend down" from "CORS blocked," and surface a more specific error than "Backend not reachable."
9. Improve Screener.in fundamentals scrape resilience (currently returns empty dict often, falls back to 24h-old seed).
10. Move JWT secret to a required env var in prod instead of the `.jwt_secret` file fallback (already correct in `render.yaml` via `generateValue: true` — just confirm it's not overridden).

---

## 5. Verification Checklist
- [ ] `curl <backend-url>/health` returns 200 from the same network context as your browser
- [ ] `docker compose ps` shows all services healthy (if running local)
- [ ] Render dashboard shows backend service "Live," not "Sleeping"/"Crashed"
- [ ] Login succeeds and `/api/v1/auth/me` returns user after login
- [ ] Dashboard loads without the demo-data banner
- [ ] Landing page copy matches what screener/dashboard actually return

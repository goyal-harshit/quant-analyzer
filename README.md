# QuantAI — India-First Quantitative Investment Analyzer

> Full-stack quant research platform for NSE/BSE equities: factor screener, backtester, portfolio tracker with broker imports, quant lab, macro dashboard, IPO tracker, mutual funds, and an AI research assistant that works with **any LLM** — Ollama (free, local), OpenAI, Anthropic, Gemini, or Groq.

**Live demo:** https://goyal-harshit.github.io/quant-analyzer

Built entirely on free and keyless data sources with automatic fallbacks. When the backend is unreachable, the frontend degrades gracefully to labelled demo data instead of breaking.

---

## Features

| Feature | Description |
|---|---|
| **Dashboard** | NIFTY/SENSEX indices, top gainers/losers, sector heatmap, factor signals |
| **Screener** | Filter the Nifty 500 universe by fundamentals (PE, PB, ROE) and momentum / quality / value / growth factor scores |
| **Stock Detail** | Price chart, fundamentals, 52-week range, AI analysis with your chosen model |
| **Compare & Sectors** | Side-by-side stock comparison; sector-level performance views |
| **Portfolio** | Positions, P&L, sector allocation; broker CSV/Excel import (Zerodha, Groww, Upstox, …); CSV/Excel/PDF export; LTCG/STCG tax report |
| **Watchlists & Alerts** | Multiple watchlists with auto-refreshing prices; price alerts and notifications |
| **Backtester** | Factor-based strategy backtesting with Sharpe, drawdown, and win-rate metrics |
| **Quant Lab** | Factor scoring, portfolio optimization, and Monte Carlo simulation |
| **Strategy Builder & Simulator** | Compose rule-based strategies; simulate trades without real money |
| **Macro** | RBI repo rate, CPI, IIP, FII/DII flows, GDP growth |
| **IPO Tracker** | Upcoming, open, and listed IPOs with GMP and subscription data |
| **Mutual Funds** | Search, compare, SIP calculator, risk metrics |
| **AI Chat** | Multi-provider assistant tuned for Indian equities, with RAG-grounded answers and citations backed by a local embedding index |
| **Auth** | JWT auth with httpOnly cookies + CSRF protection, roles, password reset, and email verification |

Other niceties: dark/light theme, JSON structured logs with request IDs, Prometheus metrics at `/metrics`, and a `/health` endpoint that reports DB, Redis, and per-data-source circuit-breaker state.

---

## Architecture

```
Next.js (static export)  ──REST──►  FastAPI (/api/v1/*)
                                       │
                     ┌─────────────────┼───────────────────┐
                     ▼                 ▼                   ▼
             PostgreSQL/Timescale    Redis            Ollama (LLM)
                     ▲                 ▲
                     └── Celery worker + beat (background ingestion)
```

- **Backend** (`backend/`) — FastAPI with domain modules under `modules/` (stocks, screener, portfolio, backtest, macro, ai, dashboard, news, earnings, quant-lab, strategy-builder, watchlists, alerts, auth, insight, mutual funds, ipo, simulator, compare, sectors). Schema is owned by Alembic migrations in production; in dev the schema is auto-created on startup.
- **Frontend** (`frontend/`) — Next.js 14 (App Router, static export) + TypeScript + Tailwind.
- **Reliability layer** — every external data source sits behind a circuit breaker and rate limiter with a fallback chain; market data is ingested into the DB and served DB-first with a freshness column, so the app stays usable when a free source throttles or goes down.
- **Redis is optional** — the app runs without it (no caching). Ollama is optional — AI features fall back to an offline report engine, or use a cloud provider key.

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 · TypeScript · Tailwind |
| Backend | FastAPI · Python 3.12 · SQLAlchemy (async) · Alembic |
| Database | PostgreSQL (TimescaleDB image in Docker) |
| Cache / queue | Redis (optional) · Celery worker + beat |
| AI / LLM | Ollama, OpenAI, Anthropic, Gemini, or Groq — your choice |
| Containers | Docker Compose |

---

## Quick start — Docker (recommended)

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/) and Git.

```bash
git clone https://github.com/goyal-harshit/quant-analyzer.git
cd quant-analyzer
cp backend/.env.example backend/.env
docker compose up --build
```

Open http://localhost:3000 — the full stack is running.

> First run pulls images (~2 GB). Subsequent starts are fast.

**On Windows** you can instead double-click `start-dev.bat`, which checks Docker, resolves port conflicts automatically (recorded in `.ports.json`), starts the stack, and opens the browser. See [QUICKSTART.md](QUICKSTART.md) and [DEV_SCRIPTS.md](DEV_SCRIPTS.md).

---

## Quick start — without Docker

### 1. Prerequisites

- Python 3.12+
- Node.js 18.17+
- PostgreSQL running locally

### 2. Clone & configure

```bash
git clone https://github.com/goyal-harshit/quant-analyzer.git
cd quant-analyzer
cp backend/.env.example backend/.env
```

Edit `backend/.env` — at minimum set your database credentials:

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/quantai_db
JWT_SECRET_KEY=change-this-to-any-random-string
```

### 3. Create the database

```bash
psql -U postgres -c "CREATE DATABASE quantai_db;"
```

### 4. Start the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The schema is created automatically on first start (`DB_AUTO_CREATE=true` is the dev default; production uses Alembic migrations instead). Backend is live at http://localhost:8000 — visit http://localhost:8000/docs for the interactive API explorer.

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend is live at http://localhost:3000.

---

## AI model setup

The app supports **5 AI providers**. Switch between them live from the sidebar or the AI chat page — no restart needed.

| Provider | Cost | Setup |
|---|---|---|
| **Ollama** | Free, runs locally | Install from [ollama.com](https://ollama.com/download), run `ollama serve`, then `ollama pull llama3.2` (8 GB RAM) or `mistral` / `qwen2.5` / `llama3.1` / `gemma2` (16 GB) / `phi3` (8 GB) |
| **Groq** | Free API tier | [console.groq.com](https://console.groq.com) → API Keys (no card required). Models: Llama 3.3 70B, Mixtral 8x7B, Llama 3.1 8B |
| **Gemini** | Free tier | [aistudio.google.com](https://aistudio.google.com) → Get API Key. Models: Gemini 2.0 Flash, 1.5 Flash (free), 1.5 Pro (paid) |
| **OpenAI** | Paid | [platform.openai.com](https://platform.openai.com) → API keys. Models: GPT-4o Mini, GPT-4o, GPT-3.5 Turbo |
| **Anthropic** | Paid | [console.anthropic.com](https://console.anthropic.com) → API Keys. Models: Claude 3 Haiku, Claude 3.5 Sonnet |

In the app: sidebar → model selector → pick the provider → paste your key (cloud providers) or pick your pulled model (Ollama).

> **API keys are stored in your browser only (localStorage). They are forwarded to your backend on each request and never stored server-side.**

RAG grounding (citations in AI answers) uses Ollama's `nomic-embed-text` embeddings with a local vector index — no external vector DB required.

---

## Configuration

All backend configuration lives in `backend/.env` — see [`backend/.env.example`](backend/.env.example) for the annotated full list. The essentials:

```env
DATABASE_URL=postgresql+asyncpg://quantai:quantai_pass@localhost:5432/quantai_db
REDIS_URL=redis://localhost:6379/0        # optional — app runs without Redis
OLLAMA_HOST=http://localhost:11434        # optional — only for local LLM
OLLAMA_MODEL=llama3.2
JWT_SECRET_KEY=change-this-to-a-random-secret-in-production
CORS_ORIGINS=http://localhost:3000
FRED_API_KEY=                             # optional, extends macro data (free key)
DATA_GOV_IN_KEY=                          # optional, extends macro data (free key)
```

Never commit `backend/.env` — it is gitignored, along with the generated `.jwt_secret`.

---

## Data sources (all free, no API keys)

| Data | Source |
|---|---|
| Stock quotes & history | Yahoo Finance v8 API (called directly, no library) |
| NSE live data | NSE endpoints (cookie-managed session, no key) |
| Mutual fund NAV | mfapi.in |
| Macro data | World Bank; FRED and data.gov.in with optional free keys |
| Fundamentals | Screener.in (scraped) + Yahoo Finance |

Every source is wrapped in a circuit breaker + rate limiter with a fallback chain, and market data is cached in the database (ingest-then-serve) so a throttled or blocked source does not take the app down. If no live data is available at all, the UI shows clearly-labelled demo data.

---

## Testing & CI

- **Backend:** `cd backend && pytest` — the suite runs against ephemeral SQLite, no Postgres needed. Linted with `ruff`.
- **Frontend:** `npm run build` type-checks and builds; `npm run test:e2e` runs Playwright E2E tests against the static export.
- **CI** (`.github/workflows/ci.yml`): backend ruff + Alembic migration up/down check + pytest; frontend build + Playwright E2E. Runs on every push and PR.

---

## Deploying to production

### Frontend → GitHub Pages (automatic)

Every push to `master` builds the static export and deploys via GitHub Actions (`.github/workflows/deploy.yml`).

One-time setup: GitHub repo → **Settings** → **Pages** → Source: **GitHub Actions**.

### Backend → Render (free tier)

1. [render.com](https://render.com) → sign up with GitHub
2. **New** → **Blueprint** → select this repo
3. Render reads `render.yaml` and creates the web service + PostgreSQL (JWT secret is auto-generated; nothing sensitive is committed)
4. Click **Apply** — backend live in ~5 min

> Render's free tier sleeps after 15 min of inactivity; the first request after sleep takes ~30 s.

---

## Project documentation

- [`docs/architecture.md`](docs/architecture.md) — system topology, security architecture, database schema
- [`docs/guides.md`](docs/guides.md) — user and administrator guides
- [`QUICKSTART.md`](QUICKSTART.md) — Windows dev environment quick start
- [`DEV_SCRIPTS.md`](DEV_SCRIPTS.md) — dev launcher scripts reference

---

## Troubleshooting

**Dashboard shows demo data**
→ Backend not reachable. Run it locally or deploy to Render, and check `NEXT_PUBLIC_API_URL` used at build time.

**Ollama shows "Unavailable"**
→ Run `ollama serve`, pull a model first (`ollama pull llama3.2`), then refresh.

**"API key not set" in AI chat**
→ Sidebar → model selector → enter your API key for the chosen provider.

**Backend fails to start: "database not found"**
→ `psql -U postgres -c "CREATE DATABASE quantai_db;"` then restart the backend.

**Port already in use**
→ On Windows, `start-dev.bat` resolves conflicts automatically. For the frontend alone: `npm run dev -- --port 3001`.

---

## Disclaimer

QuantAI is a research and educational tool. Nothing it produces is investment advice.

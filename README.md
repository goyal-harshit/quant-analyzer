# QuantAI — India-First Quantitative Investment Analyzer
### 100% Free · 100% Open-Source · Zero Payment, Anywhere

This is a fully open-source rebuild — **no paid APIs, no paid data vendors, no cloud bills required**. Every single component can run for free, forever, on your own laptop or a free-tier server.

| Layer | Tool | License/Cost |
|---|---|---|
| AI / LLM | **Ollama** + Llama 3.2 / Mistral / Qwen2.5 | Open-source, free, self-hosted |
| India Market Data | **jugaad-data**, **nsepython**, **yfinance** | Open-source, free, no API key |
| Macro Data | **RBI DBIE**, **MOSPI**, **data.gov.in**, **FRED** | Free, official government/public sources |
| Database | **PostgreSQL** + **TimescaleDB** | Open-source, free, self-hosted |
| Cache/Queue | **Redis** | Open-source, free, self-hosted |
| Backend | **FastAPI** | Open-source, free |
| Frontend | **Next.js**, **React**, **Tailwind** | Open-source, free |
| Containers | **Docker Compose** | Free |

Nothing in this stack requires a credit card at any point.

## What's Included

- **Interactive demo** (`QuantAI_App.jsx`) — a fully working React app with 25 real NSE stocks and simulated price/factor data. Its AI features try to call a local Ollama instance (`http://localhost:11434`) first; if that's unreachable — which it will be in a sandboxed preview, since browsers can't reach services on your own machine from there — it automatically falls back to a deterministic, data-driven offline analysis engine, so every feature still works with zero setup.
- **Full backend** (`/backend`) — FastAPI app with a real quant factor engine, an Ollama-powered AI service, and a data service chained across three free open-source India market data libraries with automatic fallback.
- **Frontend scaffold** (`/frontend`) — Next.js + TypeScript + Tailwind, wired to the backend API.
- **Docker Compose** — one command brings up Postgres+TimescaleDB, Redis, Ollama (with automatic model pull), the FastAPI backend, and the Next.js frontend.

## Quick Start

### Option 1 — Just run the interactive demo (zero setup)
Open `QuantAI_App.jsx` as a Claude artifact or drop it into any React+Tailwind project. It works completely standalone with simulated data. The AI features will use the offline rule-based engine unless you also have Ollama running locally on the same machine viewing the page (see Option 3).

### Option 2 — Full stack with Docker Compose (recommended)

```bash
# 1. Unzip the project
cd quant-analyzer

# 2. Set up environment variables (everything is free/optional)
cp backend/.env.example backend/.env
# No required edits — Ollama and free India data libraries need no keys.
# FRED_API_KEY / DATA_GOV_IN_KEY are optional, free registrations that
# only extend macro data coverage.

# 3. Bring up the whole stack
docker compose up --build

# This automatically:
#  - Starts PostgreSQL + TimescaleDB
#  - Starts Redis
#  - Starts Ollama and pulls the llama3.2 model (one-time, ~2GB download)
#  - Starts the FastAPI backend on :8000
#  - Starts the Next.js frontend on :3000

# Backend API:  http://localhost:8000
# API docs:     http://localhost:8000/docs
# Frontend:     http://localhost:3000
# Ollama:       http://localhost:11434
```

First boot will take a few minutes while Ollama pulls the model (free download, one-time). After that, everything runs offline with no internet dependency except for live market data refreshes.

### Option 3 — Run Ollama + the demo together locally (get real LLM output)

```bash
# 1. Install Ollama (free, one-time)
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a free open-source model
ollama pull llama3.2        # ~2GB, runs on 8GB RAM laptops

# 3. Start Ollama (it serves on localhost:11434 automatically)
ollama serve

# 4. Run the QuantAI_App.jsx demo in any local React dev server on the
#    SAME machine — now its AI calls will reach your local Ollama and
#    you'll get genuine LLM-generated analysis, completely free.
```

### Option 4 — Backend only, without Docker

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Free PostgreSQL options: install locally, or use Supabase's free tier
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/quantai_db"

# Make sure Ollama is running (see Option 3, steps 1-3)
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODEL="llama3.2"

uvicorn main:app --reload
```

## Free Model Recommendations (via Ollama)

| Model | Size | RAM Needed | Best For |
|---|---|---|---|
| `llama3.2:3b` | ~2GB | 8GB | Default — fast, good quality, runs on most laptops |
| `phi3:3.8b` | ~2.3GB | 8GB | Microsoft's compact open model, fast |
| `mistral:7b` | ~4GB | 16GB | Stronger general reasoning |
| `qwen2.5:7b` | ~4.5GB | 16GB | Best reasoning quality in this size class |

Pull any of these with `ollama pull <name>` and set `OLLAMA_MODEL` accordingly — all are open-weight, free for commercial use, no API key.

## Project Structure

```
quant-analyzer/
├── QuantAI_App.jsx          # Standalone interactive demo (calls Ollama, offline fallback)
├── docker-compose.yml       # Full stack incl. Ollama, auto model-pull
├── backend/
│   ├── main.py
│   ├── requirements.txt     # No paid SDKs — only open-source libraries
│   ├── Dockerfile
│   ├── .env.example         # No required keys
│   ├── models/
│   │   ├── database.py
│   │   └── schemas.py
│   ├── services/
│   │   ├── data_service.py  # jugaad-data → nsepython → yfinance fallback chain
│   │   ├── factor_engine.py # Quant factor computation
│   │   └── ai_service.py    # Ollama integration (free, self-hosted LLM)
│   └── routers/
│       ├── stocks.py
│       ├── screener.py
│       ├── portfolio.py
│       ├── backtest.py
│       ├── macro.py
│       └── ai.py
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.js
    └── lib/api.ts
```

## Free India Market Data Sources Used

| Source | What It Provides | Library/Access | Cost |
|---|---|---|---|
| NSE official archives | Historical OHLCV, official bhavcopy | `jugaad-data` (open-source) | Free |
| NSE live endpoints | Real-time quotes | `nsepython` (open-source) | Free |
| Yahoo Finance | Fallback price history + fundamentals (PE, PB, ROE etc.) | `yfinance` (open-source) | Free |
| RBI DBIE | Repo rate history | dbie.rbi.org.in (official, public) | Free |
| MOSPI | CPI inflation releases | mospi.gov.in (official, public) | Free |
| data.gov.in | Mirrors many government economic series | Free, optional API key | Free |
| FRED | India CPI and other macro series | Free registration | Free |

The data service tries these in fallback order automatically — if one is unavailable (NSE's official endpoints can be rate-limited or geo-restricted at times), it moves to the next free source rather than failing.

## Free Deployment Options (if you want this running 24/7 without your own hardware)

You don't need to pay anything to host this either:

- **Oracle Cloud Free Tier** — genuinely "always free" ARM VMs (4 OCPU / 24GB RAM), enough to run the whole stack including Ollama with a small model.
- **Render free tier** — for the FastAPI backend (sleeps when idle, fine for a portfolio project).
- **Railway free tier** — similar, good for demos.
- **Vercel free tier** — for the Next.js frontend (generous free tier, built for this exact use case).
- **Supabase free tier** — managed PostgreSQL if you don't want to self-host the database.

A genuinely zero-cost setup: Oracle Cloud Free Tier VM running Docker Compose with everything (Postgres, Redis, Ollama, FastAPI) + Vercel for the frontend.

## Important Notes

- **Not investment advice.** Every AI output includes a disclaimer. This is a research/educational tool.
- **Regulatory caution (India):** Per SEBI's Investment Adviser regulations, never present outputs as specific buy/sell recommendations if you monetize this. Consult a securities lawyer before any commercial launch.
- **NSE data reliability:** Official NSE endpoints (via `jugaad-data`/`nsepython`) can occasionally rate-limit or change without notice since they're not a formally documented public API — that's exactly why the fallback chain to `yfinance` exists.
- **Hardware reality check:** Ollama's quality scales with model size and your hardware. A 3B model on a laptop CPU will be noticeably less sharp than a hosted frontier model — that's the honest tradeoff for zero cost. For a stronger free option with more compute, consider Oracle's free ARM VM (4 OCPU/24GB) running a 7B model.
- **Backtest limitations:** Simplified for demonstration — doesn't fully account for point-in-time fundamental data availability (lookahead bias) or survivorship bias.

## What Changed From the Paid Version

| Component | Before | Now |
|---|---|---|
| AI / LLM | Anthropic Claude API (pay-per-use) | Ollama, self-hosted, free forever |
| Price/fundamentals | Implied paid vendors (Polygon, Tiingo) | jugaad-data + nsepython + yfinance, all free |
| Macro data keys | Assumed paid-tier access | RBI/MOSPI/data.gov.in (free, official) + free FRED tier |
| Hosting | Implied AWS/cloud spend | Self-hosted via Docker, or free-tier cloud (Oracle/Render/Vercel) |

Every dependency in `requirements.txt` and `package.json` is open-source. There is no point in this stack where you are required to enter a credit card.

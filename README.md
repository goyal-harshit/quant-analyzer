# QuantAI — India-First Quantitative Investment Analyzer

> Full-stack quant platform for NSE/BSE equity research. Screener, backtester, portfolio tracker, macro dashboard, IPO tracker, mutual funds, and an AI chat that works with **any LLM** — Ollama (free, local), OpenAI, Anthropic, Gemini, or Groq.

**Live demo:** https://goyal-harshit.github.io/quant-analyzer

---

## What's inside

| Layer | Tech | Cost |
|---|---|---|
| Frontend | Next.js 14 · TypeScript · Tailwind | Free |
| Backend | FastAPI · Python 3.12 | Free |
| Database | PostgreSQL (async, via SQLAlchemy) | Free |
| Cache | Redis (optional — app runs without it) | Free |
| Market data | Yahoo Finance v8 · NSE direct · mfapi | Free |
| AI / LLM | **Your choice** — Ollama, OpenAI, Anthropic, Gemini, Groq | Free–paid |
| Containers | Docker Compose | Free |

---

## Quick start — Docker (recommended)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac/Linux)
- Git

```bash
git clone https://github.com/goyal-harshit/quant-analyzer.git
cd quant-analyzer
cp backend/.env.example backend/.env
docker compose up --build
```

Open http://localhost:3000 — the full stack is running.

> First run pulls images (~2 GB). Subsequent starts are fast.

---

## Quick start — Without Docker

### 1. Prerequisites

```bash
# Python 3.12+
python --version

# Node.js 18+
node --version

# PostgreSQL running locally
# Windows: https://www.postgresql.org/download/windows/
# Mac:    brew install postgresql && brew services start postgresql
# Linux:  sudo apt install postgresql && sudo service postgresql start
```

### 2. Clone & configure

```bash
git clone https://github.com/goyal-harshit/quant-analyzer.git
cd quant-analyzer
cp backend/.env.example backend/.env
```

Edit `backend/.env` — at minimum set your database password:

```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/quantai_db
JWT_SECRET_KEY=change-this-to-any-random-string
```

### 3. Create the database

```bash
# Connect to PostgreSQL and create the database
psql -U postgres -c "CREATE DATABASE quantai_db;"
```

### 4. Start the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend is live at http://localhost:8000 — visit http://localhost:8000/docs for the API explorer.

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend is live at http://localhost:3000.

---

## AI model setup

The app supports **5 AI providers**. You can switch between them live from the sidebar or the AI chat page — no restart needed.

### Option A — Ollama (100% free, runs on your machine)

Best for privacy and zero cost. Requires a GPU or 8–16 GB RAM.

```bash
# 1. Install Ollama
# Windows / Mac: https://ollama.com/download
# Linux:
curl -fsSL https://ollama.com/install.sh | sh

# 2. Start Ollama
ollama serve

# 3. Pull a model (pick one based on your RAM)
ollama pull llama3.2      # 8 GB RAM  — fast, great for most tasks
ollama pull mistral       # 16 GB RAM — stronger reasoning
ollama pull qwen2.5       # 16 GB RAM — excellent for structured analysis
ollama pull llama3.1      # 16 GB RAM — Meta's latest 8B model
ollama pull phi3          # 8 GB RAM  — Microsoft's compact model
ollama pull gemma2        # 16 GB RAM — Google's open model
```

In the app: sidebar → model selector → **Ollama** → pick the model you pulled.

### Option B — Groq (free API, fastest inference)

[groq.com](https://console.groq.com) → create account → API Keys → New Key (free, no card required)

In the app: sidebar → model selector → **Groq** → paste your key → choose:
- `Llama 3.3 (70B)` — best quality on Groq free tier
- `Mixtral 8x7B` — very fast, good quality
- `Llama 3.1 (8B Fast)` — fastest responses

### Option C — Google Gemini (free tier available)

[aistudio.google.com](https://aistudio.google.com) → Get API Key (free tier: 60 req/min)

In the app: sidebar → **Gemini** → paste key → choose:
- `Gemini 2.0 Flash` — fastest, best free tier model
- `Gemini 1.5 Flash` — very fast, free
- `Gemini 1.5 Pro` — highest quality (paid)

### Option D — OpenAI

[platform.openai.com](https://platform.openai.com) → API keys → Create key

In the app: sidebar → **OpenAI** → paste key → choose:
- `GPT-4o Mini` — cheapest, great quality
- `GPT-4o` — best quality
- `GPT-3.5 Turbo` — fastest/cheapest

### Option E — Anthropic Claude

[console.anthropic.com](https://console.anthropic.com) → API Keys → Create key

In the app: sidebar → **Anthropic** → paste key → choose:
- `Claude 3 Haiku` — fastest, cheapest
- `Claude 3.5 Sonnet` — best quality

> **API keys are stored in your browser only (localStorage). They are forwarded to your backend on each request and never stored server-side.**

---

## Environment variables

```env
# backend/.env

# ── Database ──────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://quantai:quantai_pass@localhost:5432/quantai_db

# ── Redis (optional — app works without it, just no caching) ──────
REDIS_URL=redis://localhost:6379/0

# ── Ollama (optional — only needed for local LLM) ─────────────────
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

# ── Auth ──────────────────────────────────────────────────────────
JWT_SECRET_KEY=change-this-to-a-random-secret-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ── Optional: extend macro data ───────────────────────────────────
# Both are free — registration only
FRED_API_KEY=
DATA_GOV_IN_KEY=

# ── CORS (add your domain if hosting) ─────────────────────────────
CORS_ORIGINS=http://localhost:3000
```

---

## Deploying to production

### Frontend → GitHub Pages (automatic)

Every push to `master` auto-deploys via GitHub Actions.

Setup (one time):
1. GitHub repo → **Settings** → **Pages** → Source: **GitHub Actions**
2. Done — live at `https://goyal-harshit.github.io/quant-analyzer`

### Backend → Render (free tier)

1. [render.com](https://render.com) → Sign up with GitHub
2. **New** → **Blueprint** → select this repo
3. Render reads `render.yaml` and auto-creates the web service + PostgreSQL
4. Click **Apply** — backend live in ~5 min at `https://quant-analyzer-backend.onrender.com`

> **Note:** Render free tier sleeps after 15 min of inactivity. First request after sleep takes ~30s to wake. Upgrade to the $7/month plan for always-on.

---

## Features

| Feature | Description |
|---|---|
| **Dashboard** | Live NIFTY/SENSEX indices, top gainers/losers, sector heatmap, factor signals |
| **Screener** | Filter 500+ stocks by PE, PB, ROE, momentum, quality, value, growth scores |
| **Stock Detail** | Price chart, fundamentals, 52-week range, AI analysis with your chosen model |
| **Portfolio** | Track positions, P&L, sector allocation, performance vs benchmark |
| **Watchlists** | Multiple lists, live price updates every 15s |
| **Backtester** | Factor-based strategy backtesting with Sharpe, drawdown, win-rate metrics |
| **Macro** | RBI repo rate, CPI, IIP, FII/DII flows, GDP growth |
| **IPO Tracker** | Upcoming, open, and listed IPOs with GMP and subscription data |
| **Mutual Funds** | Search, compare, SIP calculator, risk metrics |
| **AI Chat** | Multi-provider AI tuned for Indian equities — works with any LLM you configure |

---

## Data sources (all free)

| Data | Source |
|---|---|
| Stock quotes & history | Yahoo Finance v8 API (direct, no library) |
| NSE live data | NseIndiaApi (cookie-managed, no key) |
| Mutual fund NAV | mfapi.in |
| Macro data | World Bank, FRED (optional free key), data.gov.in |
| Fundamentals | Screener.in (scraped) + Yahoo Finance |

---

## Troubleshooting

**Dashboard shows demo data**
→ Backend not connected. Either run locally or deploy to Render and check `NEXT_PUBLIC_API_URL` in the GitHub Actions workflow.

**Ollama shows "Unavailable" locally**
→ Run `ollama serve` in a terminal, then refresh. Pull a model first: `ollama pull llama3.2`

**"API key not set" in AI chat**
→ Go to sidebar → model selector → enter your API key for the chosen provider.

**Backend fails to start: "database not found"**
→ `psql -U postgres -c "CREATE DATABASE quantai_db;"` then restart the backend.

**Port 3000 already in use**
→ `npm run dev -- --port 3001` for the frontend.

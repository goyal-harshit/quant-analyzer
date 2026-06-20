# QuantAI — Comprehensive Investment Analyzer
## Full-Stack Indian Market Analytics Platform
### Personal Use · 100% Free · Open Source Only

---

## 1. Vision

A **Groww-like personal analytics platform** covering all Indian market asset classes:

| Asset Class | MVP | Phase 2 | Phase 3 |
|---|---|---|---|
| **Equities (NSE/BSE)** | ✅ | — | — |
| **Mutual Funds** | ✅ | — | — |
| **IPO / SME IPO Tracker** | ✅ | — | — |
| **Futures & Options** | — | ✅ | — |
| **Commodities (MCX)** | — | — | ✅ |
| **Indices & ETFs** | — | ✅ | — |

**Not a trading platform** — no order execution. Pure analytics, tracking, and research.

---

## 2. Current State (Revamp Baseline)

Existing `quant-analyzer/` codebase:
- **Backend**: Monolithic FastAPI, 11 routers, services for data/factors/AI
- **Frontend**: Next.js + TypeScript + Tailwind (scaffold only)
- **Infra**: Docker Compose (Postgres+TimescaleDB, Redis, Ollama, Celery)
- **Problems**: yfinance 429 blocked, high latency, no precomputation, incomplete modules, no real auth, messy architecture

**Revamp approach**: Keep the Docker Compose infra and FastAPI/Next.js stack. Restructure backend into clean domain modules. Rebuild frontend from scratch with proper component architecture.

---

## 3. Tech Stack (All Free)

### Backend

| Component | Tool | Why |
|---|---|---|
| Language | Python 3.11+ | Ecosystem for finance/data |
| Framework | FastAPI + Uvicorn | Async, fast, auto-docs |
| Task Queue | Celery + Redis | Background data ingestion |
| Cache | Redis | Response caching, rate limit |
| DB | PostgreSQL + TimescaleDB | Time-series hypertables for prices |
| ORM | SQLAlchemy 2.0 + Alembic | Async ORM + migrations |
| AI/LLM | Ollama (Llama 3.2 / Qwen2.5) | Local, free, no API key |

### Data Sources (All Free, No API Key Unless Noted)

| Asset | Primary Source | Fallback | Notes |
|---|---|---|---|
| **Stocks (Live)** | `jugaad-data` NSELive | `pnsea` / yfinance `.NS` | jugaad-data has caching, respects NSE |
| **Stocks (Historical)** | `jugaad-data` stock_df | yfinance | Up to 20yr daily OHLCV |
| **Options Chain** | `jugaad-data` option_chain | NSE website scrape | Live OI, Greeks, PCR |
| **Futures Data** | `jugaad-data` bhavcopy_fo | yfinance futures | Bhavcopy + live quotes |
| **Mutual Funds NAV** | `mfapi.in` REST API | `mfdata.in` API | 14k+ schemes, no auth, daily update |
| **MF Holdings/Ratios** | `mfdata.in` REST API | AMFI website scrape | Sector allocation, expense ratio |
| **IPO Data** | NSE/BSE corporate actions API | `ipoalerts.in` API | Upcoming, open, listed, GMP |
| **SME IPO** | NSE SME platform scrape | BSE SME scrape | Subscription data, allotment |
| **Commodities** | yfinance (MCX symbols) | `commodities-api.com` free tier | Gold, Silver, Crude — limited |
| **Indices** | `jugaad-data` index_df | yfinance `^NSEI` etc. | Nifty50, BankNifty, sectoral |
| **Macro Data** | RBI DBIE + FRED | data.gov.in | GDP, inflation, repo rate |
| **News** | GNews API (free) | Google News RSS scrape | 100 req/day free |

### Frontend

| Component | Tool |
|---|---|
| Framework | Next.js 14 (App Router) + TypeScript |
| Styling | Tailwind CSS + shadcn/ui |
| Charts | Lightweight Charts (TradingView OSS) + Recharts |
| State | Zustand |
| Data Fetching | TanStack Query (React Query) |
| Tables | TanStack Table |

### Infrastructure

| Component | Tool | Free Tier |
|---|---|---|
| Containers | Docker Compose | Unlimited (local) |
| DB | PostgreSQL + TimescaleDB | Self-hosted |
| Cache/Queue | Redis | Self-hosted |
| AI | Ollama | Self-hosted |
| Hosting (optional) | Railway / Render | 500hr/month free |

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────┐
│                    NEXT.JS FRONTEND                   │
│  Dashboard │ Stocks │ MF │ IPO │ F&O │ Portfolio     │
└──────────────────────┬──────────────────────────────┘
                       │ REST API
┌──────────────────────┴──────────────────────────────┐
│                   FASTAPI BACKEND                     │
│                                                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Stocks  │ │ Mutual  │ │  IPO    │ │ F&O     │   │
│  │ Module  │ │ Funds   │ │ Module  │ │ Module  │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   │
│       │           │           │           │          │
│  ┌────┴───────────┴───────────┴───────────┴────┐    │
│  │           SHARED SERVICES LAYER              │    │
│  │  DataService │ CacheService │ AIService      │    │
│  │  AlertEngine │ FactorEngine │ NewsService    │    │
│  └──────────────────┬──────────────────────────┘    │
│                     │                                │
│  ┌──────────────────┴──────────────────────────┐    │
│  │         INGESTION LAYER (Celery)             │    │
│  │  StockIngester │ MFIngester │ IPOIngester    │    │
│  │  FOIngester │ CommodityIngester              │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   PostgreSQL       Redis          Ollama
   +TimescaleDB    (cache+queue)   (local LLM)
```

### Backend Module Structure (Revamped)

```
backend/
├── main.py                     # FastAPI app, CORS, lifespan
├── config.py                   # Settings via pydantic-settings
├── database.py                 # Async SQLAlchemy engine + session
│
├── modules/
│   ├── stocks/
│   │   ├── router.py           # /api/stocks endpoints
│   │   ├── service.py          # Quote, history, fundamentals
│   │   ├── models.py           # Company, PriceOHLCV, Fundamentals
│   │   └── schemas.py          # Pydantic request/response
│   │
│   ├── mutual_funds/
│   │   ├── router.py           # /api/mf endpoints
│   │   ├── service.py          # NAV, holdings, returns calc
│   │   ├── models.py           # MFScheme, MFNav, MFHolding
│   │   └── schemas.py
│   │
│   ├── ipo/
│   │   ├── router.py           # /api/ipo endpoints
│   │   ├── service.py          # Upcoming, open, listed, GMP
│   │   ├── models.py           # IPO, IPOSubscription
│   │   └── schemas.py
│   │
│   ├── derivatives/            # Phase 2
│   │   ├── router.py           # /api/fno endpoints
│   │   ├── service.py          # Option chain, OI analysis
│   │   ├── models.py           # OptionContract, FutureContract
│   │   └── schemas.py
│   │
│   ├── commodities/            # Phase 3
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── portfolio/
│   │   ├── router.py           # /api/portfolio
│   │   ├── service.py          # Holdings, P&L, allocation
│   │   ├── models.py           # Portfolio, Position
│   │   └── schemas.py
│   │
│   ├── screener/
│   │   ├── router.py           # /api/screener
│   │   ├── service.py          # Filter stocks/MF by criteria
│   │   └── schemas.py
│   │
│   ├── watchlist/
│   │   ├── router.py           # /api/watchlists
│   │   ├── service.py
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── alerts/
│   │   ├── router.py           # /api/alerts
│   │   ├── service.py          # Price/signal alerts
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── ai/
│   │   ├── router.py           # /api/ai
│   │   └── service.py          # Ollama-powered research assistant
│   │
│   ├── news/
│   │   ├── router.py           # /api/news
│   │   ├── service.py          # Fetch + sentiment scoring
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   └── macro/
│       ├── router.py           # /api/macro
│       ├── service.py          # GDP, inflation, FII/DII flows
│       └── schemas.py
│
├── services/                   # Shared cross-module services
│   ├── data_service.py         # Unified data fetcher with fallback chain
│   ├── cache_service.py        # Redis cache wrapper
│   ├── factor_engine.py        # Quant factor scoring
│   ├── technical_engine.py     # TA indicators (pandas-ta)
│   ├── ingestion_service.py    # Celery tasks for background ingestion
│   └── notification_service.py # Email/push alerts
│
├── models/                     # Shared DB models
│   └── base.py                 # Base model, common mixins
│
├── alembic/                    # DB migrations
└── tests/
```

---

## 5. Database Schema

### Core Tables

```sql
-- STOCKS
companies (id, symbol, name, exchange, sector, industry, market_cap, is_index, is_etf, created_at)
price_ohlcv (time, symbol, open, high, low, close, volume, adj_close)  -- TimescaleDB hypertable
fundamentals (id, symbol, pe, pb, eps, roe, roce, dividend_yield, debt_equity, mcap, fetched_at)
factor_scores (id, symbol, momentum, value, quality, volatility, composite, computed_at)

-- MUTUAL FUNDS
mf_schemes (id, scheme_code, scheme_name, amc, category, sub_category, scheme_type, launch_date)
mf_nav (id, scheme_code, date, nav)  -- TimescaleDB hypertable
mf_holdings (id, scheme_code, stock_symbol, pct_holding, sector, as_of_date)
mf_metadata (id, scheme_code, expense_ratio, aum, benchmark, risk_grade, updated_at)

-- IPO
ipos (id, company_name, symbol, exchange, issue_size, price_band_low, price_band_high,
      lot_size, open_date, close_date, listing_date, listing_price, gmp, status, ipo_type)
      -- ipo_type: MAINBOARD | SME
ipo_subscriptions (id, ipo_id, category, subscription_times, day, fetched_at)

-- DERIVATIVES (Phase 2)
option_chain (id, symbol, expiry, strike, ce_oi, ce_ltp, ce_iv, pe_oi, pe_ltp, pe_iv, fetched_at)
futures_data (id, symbol, expiry, ltp, oi, volume, basis, fetched_at)

-- COMMODITIES (Phase 3)
commodity_prices (time, symbol, open, high, low, close, volume)  -- hypertable

-- PORTFOLIO & TRACKING
portfolios (id, name, created_at)
positions (id, portfolio_id, asset_type, symbol, quantity, avg_price, added_at)
    -- asset_type: STOCK | MF | COMMODITY
watchlists (id, name, created_at)
watchlist_items (id, watchlist_id, asset_type, symbol, added_at)

-- ALERTS
alerts (id, asset_type, symbol, condition, threshold, is_active, last_triggered, created_at)
    -- condition: PRICE_ABOVE | PRICE_BELOW | RSI_ABOVE | RSI_BELOW | VOLUME_SPIKE

-- NEWS
news_articles (id, title, url, source, symbols, sentiment_score, published_at, fetched_at)
```

---

## 6. Feature Specification

### 6.1 Dashboard (Home)
- Market overview: Nifty50, Sensex, BankNifty live with sparkline
- Top gainers/losers (NSE)
- Watchlist quick-view with live prices
- Portfolio summary (total value, day P&L, % change)
- Upcoming IPOs banner
- FII/DII flow indicator
- Market sentiment gauge (based on advance/decline ratio)

### 6.2 Stock Analysis
- **Quote**: LTP, day high/low, 52W high/low, volume, market cap
- **Chart**: TradingView Lightweight Charts — candlestick, line, area with volume overlay
- **Technicals**: RSI, MACD, Bollinger Bands, EMA(20/50/200), SuperTrend, VWAP
- **Fundamentals**: PE, PB, EPS, ROE, ROCE, D/E, dividend yield, revenue/profit trend
- **Factor Scores**: Momentum, Value, Quality, Volatility — composite quant score
- **Signal Engine**: Buy/Hold/Sell based on weighted technical + factor scores
- **Peer Comparison**: Same-sector stocks side-by-side
- **News & Sentiment**: Recent news with VADER sentiment scoring
- **AI Analysis**: Ollama-powered natural language summary of stock's position

### 6.3 Mutual Fund Analytics
- **Search & Filter**: By AMC, category (equity/debt/hybrid), sub-category, AUM, expense ratio
- **NAV Chart**: Historical NAV with configurable period (1M/3M/6M/1Y/3Y/5Y/Max)
- **Returns Calculator**: SIP vs Lumpsum comparison with XIRR
- **Returns Table**: 1Y, 3Y, 5Y, 10Y CAGR, rolling returns
- **Risk Metrics**: Standard deviation, Sharpe ratio, Sortino, max drawdown, beta vs benchmark
- **Holdings Analysis**: Top 10 holdings, sector allocation pie chart, overlap with other schemes
- **Peer Comparison**: Compare 2-4 funds in same category
- **SIP Calculator**: Monthly SIP → future value projection with inflation adjustment
- **AI Summary**: Plain-English fund analysis via Ollama

### 6.4 IPO / SME Tracker
- **Upcoming IPOs**: Issue size, price band, dates, lot size, type (Mainboard/SME)
- **Open IPOs**: Live subscription data (QIB, NII, RII, total) with auto-refresh
- **Recently Listed**: Listing price vs issue price, listing gain %, current price
- **IPO Calendar**: Month-view calendar of open/close/listing dates
- **GMP Tracker**: Grey market premium (scraped from aggregator sites)
- **SME IPO Section**: Dedicated section for BSE SME / NSE Emerge
- **Allotment Status Check**: Link/embed for checking allotment
- **IPO Performance History**: Historical listing gains analysis

### 6.5 Portfolio Tracker
- **Multi-portfolio support**: Separate portfolios for stocks, MF, etc.
- **Holdings view**: Current price, avg price, P&L (absolute + %), day change
- **Asset Allocation**: Pie chart — equity/debt/commodity split
- **Sector Allocation**: Pie chart based on holdings' sectors
- **Risk Metrics**: Portfolio beta, Sharpe, max drawdown, volatility
- **Performance Chart**: Portfolio value over time vs benchmark (Nifty50)
- **Dividend Tracker**: Expected dividends from holdings
- **Tax Helper**: Short-term vs long-term capital gains summary (based on holding period)

### 6.6 Screener
- **Stock Screener**: Filter by market cap, PE, PB, ROE, ROCE, sector, 52W proximity, RSI, volume
- **MF Screener**: Filter by category, AUM, expense ratio, returns, risk grade
- **Custom Filters**: Save and reuse filter combinations
- **Export**: Download filtered results as CSV

### 6.7 Watchlists
- Multiple named watchlists
- Live price updates (polling every 30s during market hours)
- Quick add from any asset page
- Drag-and-drop reorder

### 6.8 Alerts
- Price alerts (above/below threshold)
- Technical alerts (RSI overbought/oversold, MACD crossover)
- Volume spike alerts
- IPO open/close reminders
- Delivery: In-app notification + optional email (Resend, 3k/month free)

### 6.9 AI Research Assistant
- Natural language queries: "Compare HDFC Bank and ICICI Bank fundamentals"
- Stock summarization: "Give me a 2-minute summary of Reliance"
- MF recommendation: "Best large cap fund with low expense ratio"
- Powered by local Ollama — zero API cost
- Context-aware: feeds real data from DB into LLM prompt

### 6.10 Macro Dashboard
- India GDP, CPI inflation, repo rate, 10Y bond yield
- FII/DII daily/monthly flows
- USD/INR trend
- Global indices snapshot (S&P 500, NASDAQ, Nikkei)
- Crude oil, gold prices

---

## 7. Phased Implementation Plan

### Phase 1 — MVP: Stocks + Mutual Funds + IPO (Weeks 1-6)

#### Sprint 1 (Week 1-2): Foundation Revamp
1. Restructure backend into `modules/` pattern (move existing routers/services)
2. Set up proper `database.py` with async SQLAlchemy 2.0
3. Create all MVP database tables + Alembic migrations
4. Build `DataService` with fallback chain: jugaad-data → yfinance → seed data
5. Set up Redis caching layer with TTL strategy
6. Celery tasks: stock price ingestion (every 5 min market hours), daily EOD bhavcopy
7. Health check + basic error handling middleware

#### Sprint 2 (Week 2-3): Stock Analysis Module
1. `/api/stocks/{symbol}/quote` — live quote via jugaad-data NSELive
2. `/api/stocks/{symbol}/history` — OHLCV from DB (ingested by Celery)
3. `/api/stocks/{symbol}/fundamentals` — PE, PB, EPS, ROE etc.
4. `/api/stocks/{symbol}/technicals` — RSI, MACD, BB, EMA via pandas-ta
5. `/api/stocks/{symbol}/factors` — momentum, value, quality scores
6. `/api/stocks/{symbol}/signals` — composite buy/hold/sell
7. `/api/stocks/gainers-losers` — top movers
8. `/api/screener/stocks` — filterable stock screener

#### Sprint 3 (Week 3-4): Mutual Fund Module
1. Celery task: ingest all MF schemes from mfapi.in (one-time + daily delta)
2. Celery task: daily NAV update for tracked schemes
3. `/api/mf/search` — search schemes by name, AMC, category
4. `/api/mf/{scheme_code}/nav` — historical NAV data
5. `/api/mf/{scheme_code}/returns` — 1Y/3Y/5Y CAGR, rolling returns
6. `/api/mf/{scheme_code}/risk` — std dev, Sharpe, max drawdown
7. `/api/mf/{scheme_code}/holdings` — top holdings, sector allocation
8. `/api/mf/compare` — side-by-side comparison of 2-4 funds
9. `/api/mf/sip-calculator` — SIP projection endpoint

#### Sprint 4 (Week 4-5): IPO Module + Portfolio + Watchlist
1. Celery task: scrape NSE/BSE corporate actions for IPO data (daily)
2. `/api/ipo/upcoming` — upcoming IPOs with details
3. `/api/ipo/open` — currently open IPOs with subscription data
4. `/api/ipo/listed` — recently listed with performance
5. `/api/ipo/calendar` — month view
6. Revamp portfolio CRUD (fix existing bugs from CONTEXT.md)
7. Portfolio P&L calculation with live prices
8. Watchlist CRUD with live price polling
9. Alert engine: create, evaluate (Celery periodic task), notify

#### Sprint 5 (Week 5-6): Frontend MVP
1. Next.js App Router layout: sidebar nav + header
2. Dashboard page: market overview, watchlist, portfolio summary
3. Stock detail page: chart (TradingView Lightweight), technicals, fundamentals
4. MF search + detail page: NAV chart, returns, risk metrics, SIP calc
5. IPO tracker page: tabs (upcoming/open/listed), subscription bars
6. Portfolio page: holdings table, allocation charts, P&L
7. Watchlist page: live prices, quick actions
8. Screener page: stock + MF filters with results table
9. Responsive design (mobile-friendly)

#### Sprint 6 (Week 6): Polish + AI + Alerts
1. AI research assistant page (Ollama integration)
2. Alerts page: create/manage alerts
3. News feed with sentiment badges
4. Macro dashboard (static + FII/DII data)
5. Error states, loading skeletons, empty states
6. Performance optimization: API response caching, lazy loading

### Phase 2 — F&O + Indices + ETFs (Weeks 7-10)

1. Option chain viewer with OI analysis, PCR, max pain
2. Futures data: basis, rollover tracking
3. Options strategy builder (covered call, straddle, etc.) — payoff charts
4. IV surface / skew visualization
5. Index analysis module (Nifty50, BankNifty, sectoral indices)
6. ETF module (NAV vs price, tracking error)
7. Derivatives screener (by OI change, IV percentile)
8. Options Greeks calculator

### Phase 3 — Commodities + Advanced (Weeks 11-14)

1. Commodity module: Gold, Silver, Crude Oil via yfinance MCX symbols
2. Commodity-equity correlation dashboard
3. Backtesting engine: define strategy → run on historical data → report
4. Strategy builder UI: no-code rule composer
5. Advanced portfolio analytics: Monte Carlo simulation, VaR
6. PDF report generation: portfolio/stock report export
7. Data export: CSV/Excel for any data view

---

## 8. API Endpoint Reference

### Stocks
```
GET    /api/stocks/{symbol}/quote
GET    /api/stocks/{symbol}/history?period=1y&interval=1d
GET    /api/stocks/{symbol}/fundamentals
GET    /api/stocks/{symbol}/technicals
GET    /api/stocks/{symbol}/factors
GET    /api/stocks/{symbol}/signals
GET    /api/stocks/{symbol}/peers
GET    /api/stocks/gainers-losers
POST   /api/screener/stocks          body: {filters}
```

### Mutual Funds
```
GET    /api/mf/search?q=hdfc&category=equity&amc=HDFC
GET    /api/mf/{scheme_code}
GET    /api/mf/{scheme_code}/nav?period=3y
GET    /api/mf/{scheme_code}/returns
GET    /api/mf/{scheme_code}/risk
GET    /api/mf/{scheme_code}/holdings
POST   /api/mf/compare              body: {scheme_codes: [...]}
POST   /api/mf/sip-calculator       body: {monthly, years, expected_return}
POST   /api/screener/mf             body: {filters}
```

### IPO
```
GET    /api/ipo/upcoming
GET    /api/ipo/open
GET    /api/ipo/listed?days=30
GET    /api/ipo/calendar?month=2026-07
GET    /api/ipo/{id}/subscription
GET    /api/ipo/sme                  # SME IPOs only
```

### Portfolio
```
POST   /api/portfolio
GET    /api/portfolio/{id}
POST   /api/portfolio/{id}/positions
GET    /api/portfolio/{id}/pnl
GET    /api/portfolio/{id}/allocation
GET    /api/portfolio/{id}/performance?benchmark=NIFTY50
DELETE /api/portfolio/{id}/positions/{pos_id}
```

### Watchlist
```
POST   /api/watchlists
GET    /api/watchlists
GET    /api/watchlists/{id}
POST   /api/watchlists/{id}/items
DELETE /api/watchlists/{id}/items/{item_id}
```

### Alerts
```
POST   /api/alerts
GET    /api/alerts
PUT    /api/alerts/{id}
DELETE /api/alerts/{id}
```

### AI
```
POST   /api/ai/query               body: {question, context_symbols: [...]}
```

### News
```
GET    /api/news?symbols=RELIANCE,TCS&limit=20
GET    /api/news/sentiment?symbol=RELIANCE
```

### Macro
```
GET    /api/macro/india              # GDP, CPI, repo rate
GET    /api/macro/fii-dii?period=30d
GET    /api/macro/global-indices
GET    /api/macro/commodities        # Gold, crude summary
```

### Derivatives (Phase 2)
```
GET    /api/fno/{symbol}/option-chain?expiry=2026-07-31
GET    /api/fno/{symbol}/futures
GET    /api/fno/{symbol}/oi-analysis
POST   /api/fno/strategy-payoff     body: {legs: [...]}
GET    /api/fno/screener            query: {oi_change_min, iv_pct_min}
```

---

## 9. Data Ingestion Schedule (Celery Tasks)

| Task | Frequency | Source | Table |
|---|---|---|---|
| Stock prices (live) | Every 5 min (9:15-15:30 IST) | jugaad-data NSELive | price_ohlcv |
| Stock EOD bhavcopy | Daily 16:00 IST | jugaad-data bhavcopy | price_ohlcv |
| Fundamentals refresh | Weekly Sunday | jugaad-data / yfinance | fundamentals |
| Factor score compute | Daily 17:00 IST | Internal (from prices) | factor_scores |
| MF NAV update | Daily 22:00 IST | mfapi.in | mf_nav |
| MF scheme list sync | Weekly Sunday | mfapi.in | mf_schemes |
| MF holdings refresh | Monthly 1st | mfdata.in | mf_holdings |
| IPO data refresh | Every 2 hours | NSE corporate actions | ipos, ipo_subscriptions |
| News fetch | Every 30 min | GNews API | news_articles |
| Sentiment scoring | On news insert | VADER | news_articles.sentiment_score |
| FII/DII flows | Daily 19:00 IST | NSE website | macro cache |
| Option chain snapshot | Every 5 min (market hours) | jugaad-data (Phase 2) | option_chain |
| Alert evaluation | Every 1 min (market hours) | Internal | alerts |

---

## 10. Key Python Dependencies

```
# Core
fastapi==0.115.*
uvicorn[standard]
sqlalchemy[asyncio]==2.0.*
asyncpg
alembic
pydantic-settings
redis[hiredis]
celery[redis]
httpx[http2]

# Data Sources
jugaad-data
yfinance
pnsea

# Analysis
pandas
pandas-ta
numpy
scikit-learn

# Sentiment
vaderSentiment

# AI
ollama  # Python client for local Ollama

# Utils
python-dotenv
apscheduler
```

---

## 11. Frontend Pages & Components

```
/                        → Dashboard (market overview, portfolio summary)
/stocks                  → Stock screener
/stocks/[symbol]         → Stock detail (chart, technicals, fundamentals, AI)
/mutual-funds            → MF search + screener
/mutual-funds/[code]     → MF detail (NAV chart, returns, risk, holdings)
/ipo                     → IPO tracker (upcoming, open, listed tabs)
/portfolio               → Portfolio list
/portfolio/[id]          → Portfolio detail (holdings, P&L, allocation)
/watchlists              → Watchlist manager
/alerts                  → Alert manager
/screener                → Advanced screener (stocks + MF)
/news                    → News feed with sentiment
/macro                   → Macro dashboard
/ai                      → AI research assistant
/fno                     → F&O dashboard (Phase 2)
/fno/[symbol]            → Option chain + analysis (Phase 2)
/commodities             → Commodity prices (Phase 3)
/backtest                → Backtesting (Phase 3)
```

---

## 12. Development Workflow

### Running Locally
```bash
cd quant-analyzer
docker compose up --build
# Backend: http://localhost:8000/docs
# Frontend: http://localhost:3000
# Redis: localhost:6379
# Postgres: localhost:5432
# Ollama: http://localhost:11434
```

### Adding a New Module
1. Create `backend/modules/<name>/` with router.py, service.py, models.py, schemas.py
2. Register router in `main.py`
3. Create Alembic migration: `alembic revision --autogenerate -m "add <name> tables"`
4. Add Celery ingestion task in `services/ingestion_service.py`
5. Create frontend page in `frontend/app/<name>/page.tsx`

### Git Workflow
- `main` — stable, deployable
- `dev` — integration branch
- Feature branches: `feat/<module>-<feature>`
- Commit format: `feat(stocks): add fundamentals endpoint`

---

## 13. Success Metrics (MVP)

| Metric | Target |
|---|---|
| Stock quote response time | < 500ms (cached) |
| MF NAV data freshness | Same-day NAV by 22:30 IST |
| IPO data freshness | < 2 hours lag |
| Dashboard load time | < 2s |
| Screener query time | < 3s for 500+ stocks |
| Portfolio P&L accuracy | Within 0.1% of actual |
| Uptime (local Docker) | No crashes over 24hr run |

---

## 14. Risk & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| jugaad-data rate limited | No live data | Fallback chain: pnsea → yfinance → cached |
| mfapi.in downtime | No MF NAV | Cache last 30 days locally, use mfdata.in fallback |
| NSE blocks scraping | No IPO/option data | Use cached data, add ipoalerts.in as fallback |
| yfinance 429 (current issue) | No fallback data | jugaad-data as primary replaces yfinance dependency |
| Ollama OOM on small machines | AI features fail | Graceful degradation: rule-based analysis fallback |
| TimescaleDB complexity | Slow dev | Start with plain Postgres, add hypertables later for scale |

---

## 15. What This Is NOT

- **Not a trading terminal** — no order placement, no broker integration
- **Not real-time tick-by-tick** — 5-minute polling, not WebSocket streaming
- **Not multi-user SaaS** — single user, no auth, localhost
- **Not mobile app** — responsive web only
- **Not financial advice** — analytics tool, no recommendations guaranteed

---

*Last updated: 2026-06-20*
*Phase: Pre-MVP (Foundation Revamp)*

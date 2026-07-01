# QuantAI User & Admin Guides

This document provides a comprehensive operational guide for both users of the terminal interface and administrators managing the local self-hosted infrastructure.

---

## 1. User Guide

### 1.1 Using the Factor Screener
The Screener filters the Nifty 500 universe based on both fundamental metrics (P/E, P/B, ROE) and quantitative factor scores (Momentum, Quality, Value, Growth).
- **Fuzzy Search**: Filter by ticker code or company name using the search bar.
- **Sliders**: Drag sliders to filter stocks above or below specific parameters.
- **Blended Composite Score**: The final composite score represents a weighted average of momentum, quality, value, and growth factor rankings.
- **Sorting**: Click any column header to sort constituencies client-side.

### 1.2 Portfolio & Broker Imports
QuantAI allows you to track multiple custom portfolios. 

#### Creating Portfolios & Adding Positions
1. Navigate to the **Portfolio** tab.
2. Click **Create Portfolio** if no portfolio exists.
3. Click **Add Position** to manually input positions (Ticker, Qty, Average Buy Cost).

#### Ingesting Broker CSV / Excel Statements
QuantAI's import parser is highly flexible and features automatic header aliasing. You can import standard CSV, XLS, or XLSX files from brokerages (Zerodha, Groww, Upstox, etc.).
- **Header Aliasing**: The parser maps headers automatically. Your file columns should contain terms matching:
  - **Ticker / Symbol**: `ticker`, `symbol`, `scrip`, `instrument`, `stock_code`
  - **Quantity**: `qty`, `quantity`, `shares`, `units`, `holding`
  - **Average Cost**: `cost`, `avg_cost`, `buy_price`, `average_price`, `price`
- **Duplicate Merging**: If your statement has multiple transaction rows for the same ticker, the parser automatically calculates a **weighted average cost** and merges the rows into a single position.

#### Unrealized Capital Gains (Tax Planning)
Click **Tax Report** to view a breakdown of unrealized gains:
- **Short-Term Capital Gains (STCG)**: Position holding period is less than or equal to 365 days.
- **Long-Term Capital Gains (LTCG)**: Position holding period exceeds 365 days. (Enables tax planning before booking profits).

---

## 2. Administrator & Developer Guide

### 2.1 Local LLM & Embedding Setup
QuantAI runs entirely locally using Ollama. To start the AI features:
1. Install Ollama from [ollama.com](https://ollama.com).
2. Start the service:
   ```bash
   ollama serve
   ```
3. Pull the required models:
   ```bash
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```
4. Verify models are loaded at `http://localhost:11434/api/tags`.

### 2.2 Grounded AI Reindexing (RAG)
When fundamentals or sector constituents are updated in the database, you must rebuild the semantic RAG vector index so the AI chatbot picks up fresh context.
- **Trigger via Endpoint**: Run a POST request to reindex all equities:
  ```bash
  curl -X POST http://localhost:8000/api/v1/ai/rag/reindex -H "Authorization: Bearer <your_token>"
  ```
- This triggers `rag_ingest.ingest_stocks()`, generating embeddings using `nomic-embed-text` and writing them to the database's `embeddings` JSON table.

### 2.3 Monitoring Telemetry & Metrics
QuantAI exposes structured Prometheus metrics at `http://localhost:8000/metrics`.

Key metrics to scrape:
- `http_requests_total`: Counts incoming API calls.
- `http_request_duration_seconds`: API route latency distribution.
- `cache_requests_total{result="hit"|"miss"}`: Redis cache efficiency.
- `circuit_breaker_state{source="[name]",state="[closed|open|half_open]"}`: Circuit breaker state monitoring for live data providers.

### 2.4 Circuit Breaker Management & Health Checks
Query the `/health` endpoint to monitor overall system status:
```bash
curl http://localhost:8000/health
```
If a live provider (e.g., Yahoo, Screener.in, or NSE Live) experiences repeated 403, 429, or 5xx errors, the circuit breaker shifts to **OPEN**.
- **Cooldown Period**: The breaker remains OPEN for 120 seconds, during which all queries bypass the source and fall back to local seed data immediately to prevent server throttling.
- **Automatic Recovery**: After 120 seconds, the breaker enters **HALF-OPEN** and test-routes a single query. If it succeeds, the breaker resets to **CLOSED** (normal operation).

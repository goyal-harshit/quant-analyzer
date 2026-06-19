"""
AI Service — 100% Free, Open-Source LLM via Ollama
======================================================
No API keys. No payment. No external AI vendor. Runs entirely on your
own machine (or any free-tier VM) using Ollama (https://ollama.com),
which serves open-weight models like Llama 3.2, Mistral, Qwen2.5, or
Phi-3 — all free to download and use commercially.

Setup (one-time, free):
    1. Install Ollama:        curl -fsSL https://ollama.com/install.sh | sh
    2. Pull a model:          ollama pull llama3.2
    3. Ollama auto-serves at: http://localhost:11434

Recommended free models (pick based on your hardware):
    - llama3.2:3b      → fastest, runs on 8GB RAM laptops
    - qwen2.5:7b        → stronger reasoning, needs ~16GB RAM
    - mistral:7b        → good general-purpose balance
    - phi3:3.8b         → Microsoft's compact open model

All of these are open-source, Apache/MIT-family licensed, and free
for commercial use — no Anthropic/OpenAI bill, ever.
"""

import os
import logging

import httpx

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

DISCLAIMER = "\n\n⚠️ This analysis is generated for educational purposes only and does not constitute investment advice. Consult a SEBI-registered investment adviser before making investment decisions."

SYSTEM_PROMPT_RESEARCH = """You are QuantAI, an open-source research assistant specialising in Indian equity markets (NSE/BSE), running entirely on a free, self-hosted language model.

Your expertise covers:
- Nifty 50, Nifty 500, BSE 500 constituent companies and their fundamentals
- RBI monetary policy and its sector-specific transmission effects
- SEBI regulations, corporate governance norms, and Indian accounting standards (Ind AS)
- Factor investing: momentum, quality, value, growth, low-volatility — calibrated for Indian market behaviour
- India macroeconomic indicators: GDP growth, CPI, IIP, FII/DII flows, credit growth, INR/USD
- Sector dynamics: Banking/NBFC, IT Services, FMCG, Auto, Pharma, Capital Goods, Telecom, Energy, Utilities, Metals

Guidelines:
- Use ₹ (Rupee) for currency references
- Reference specific Indian regulatory bodies (SEBI, RBI, MOSPI, NSE, BSE) where relevant
- Keep analysis data-driven, structured, and concise
- Never give explicit buy/sell recommendations — provide analytical frameworks instead
- Always end responses with a brief disclaimer about educational purpose
"""

SYSTEM_PROMPT_ANALYST = """You are a quantitative equity analyst at QuantAI, specialising in factor-based analysis of NSE/BSE-listed companies.

For each analysis, provide:
1. A data-driven snapshot interpreting the given metrics
2. Key strengths visible in the quantitative profile
3. Key risks visible in the quantitative profile
4. What the composite factor score implies relative to sector peers
5. Comparable stocks for benchmarking

Be specific and reference the exact numbers provided. Do not invent data not given to you.
Never issue a buy/sell/hold recommendation — describe what the data shows, not what to do.
Always end with the disclaimer."""

SYSTEM_PROMPT_EARNINGS = """You are an earnings analyst summarising quarterly results for Indian companies.

Given raw or excerpted financial result data, produce a structured summary:
- Revenue & Profit (YoY and QoQ change)
- Margin trends (gross, EBITDA, net)
- Management commentary highlights (if transcript provided)
- Segment/geography performance (if available)
- Key risks flagged by management or analysts
- Guidance for upcoming quarters (if mentioned)

Be factual, structured, and avoid speculation beyond what's stated. Always end with the disclaimer."""


def _tier(v: int) -> str:
    return "top-tier" if v >= 70 else "mid-tier" if v >= 45 else "lower-tier"


def _pct(n: float) -> str:
    return f"{'+' if n >= 0 else ''}{n:.2f}%"


# Offline rule-based engine (fallback when Ollama is unreachable)
# Uses seed_data module — no external calls, no cost, always works.
def _build_stock_list():
    from services.seed_data import STOCK_MASTER
    stocks = []
    for r in STOCK_MASTER:
        if len(r) >= 13:
            ticker, name, sector, price, pe, pb, roe, rev, mom, qual, val, grw, mcap = r
            composite = round(mom * 0.25 + qual * 0.25 + val * 0.20 + grw * 0.20 + min(100, roe * 0.8) * 0.10)
            stocks.append({
                "ticker": ticker, "name": name, "sector": sector,
                "price": price, "pe": pe, "pb": pb, "roe": roe, "rev": rev,
                "mom": mom, "qual": qual, "val": val, "grw": grw,
                "mcap": mcap / 1000, "composite": composite,
            })
    return stocks


_STOCKS = _build_stock_list()

_MACRO_DATA = {
    "repo": [5.9, 6.25, 6.5, 6.5, 6.5, 6.5, 6.5, 6.5, 6.5, 6.25, 6.0, 5.75],
    "cpi_current": 2.6,
    "nifty_cagr": 16.2,
    "high_momentum_cagr": 22.5,
}


def buildOfflineReport(stock: dict) -> str:
    tiers = _tier
    score = stock.get("composite", 0)
    mom = stock.get("mom", 50)
    qual = stock.get("qual", 50)
    val = stock.get("val", 50)
    grw = stock.get("grw", 50)
    pe = stock.get("pe", 0)
    pb = stock.get("pb", 0)
    roe = stock.get("roe", 0)
    rev = stock.get("rev", 0)
    name = stock.get("name", stock["ticker"])
    sector = stock.get("sector", "Unknown")

    peers = [s for s in _STOCKS if s["sector"] == sector and s["ticker"] != stock["ticker"]]
    peers.sort(key=lambda x: x["composite"], reverse=True)
    peer_str = " · ".join(f"{p['ticker']} ({p['composite']})" for p in peers[:2]) or "No close sector peers"

    return (
        f"**Quick Snapshot**\n"
        f"{name} ({stock['ticker']}) trades at ₹{stock['price']:,.0f} "
        f"with a P/E of {pe:.1f}x and ROE of {roe:.1f}%. "
        f"Its composite factor score of {score}/100 places it in the "
        f"{tiers(score)} of the Nifty universe within {sector}.\n\n"
        f"**Strengths**\n"
        f"• {f'Strong Quality score ({qual}) — ROE of {roe:.1f}% signals efficient capital use' if qual >= 65 else f'Revenue growing at {rev:.1f}% YoY, a reasonable pace for {sector}'}\n"
        f"• {f'Momentum score of {mom} shows strong recent relative price strength' if mom >= 65 else f'Valuation looks measured at {pe:.1f}x earnings'}\n"
        f"• {f'Value score of {val} suggests the stock is not expensive relative to peers' if val >= 55 else f'Established scale within the {sector} sector'}\n\n"
        f"**Risks**\n"
        f"• {f'P/E of {pe:.1f}x is elevated — leaves limited room for multiple expansion' if pe > 40 else f'Momentum score of {mom} is muted — limited near-term price catalysts'}\n"
        f"• {f'P/B of {pb:.1f}x implies the market is pricing in a lot of future growth' if pb > 10 else f'Growth score of {grw} suggests topline momentum could be inconsistent'}\n\n"
        f"**Factor View**\n"
        f"A composite score of {score}/100 (Momentum {mom} · Quality {qual} · Value {val} · Growth {grw}) "
        f"places {stock['ticker']} in the {tiers(score)} of its peer set on a blended multi-factor basis.\n\n"
        f"**Peers**\n{peer_str}\n\n"
        f"⚠️ Offline rule-based engine (Ollama not reachable). "
        f"Self-host with `ollama serve` for full LLM analysis. "
        f"Educational purposes only — not investment advice."
    )


def buildOfflineChatReply(query: str) -> str:
    ql = query.lower()
    mentioned = [s for s in _STOCKS if ql.find(s["ticker"].lower()) != -1 or ql.find(s["name"].lower()) != -1]
    if len(mentioned) >= 2:
        a, b = mentioned[:2]
        return (
            f"Comparing {a['ticker']} vs {b['ticker']} on quantitative factors:\n\n"
            f"{a['ticker']}: Composite {a['composite']} (Quality {a['qual']}, Momentum {a['mom']}, Value {a['val']}) "
            f"· ROE {a['roe']:.1f}% · P/E {a['pe']:.1f}x\n"
            f"{b['ticker']}: Composite {b['composite']} (Quality {b['qual']}, Momentum {b['mom']}, Value {b['val']}) "
            f"· ROE {b['roe']:.1f}% · P/E {b['pe']:.1f}x\n\n"
            f"On this data, {a['ticker'] if a['composite'] > b['composite'] else b['ticker']} screens higher "
            f"on the blended composite factor, driven primarily by "
            f"{'Quality' if (a['qual'] if a['composite'] > b['composite'] else b['qual']) > (a['mom'] if a['composite'] > b['composite'] else b['mom']) else 'Momentum'}.\n\n"
            f"⚠️ Offline rule-based reply (Ollama not reachable). Self-host with Ollama for full LLM responses."
        )
    if len(mentioned) == 1:
        s = mentioned[0]
        return (
            f"{s['name']} ({s['ticker']}) — quick data view:\n"
            f"Price ₹{s['price']:,.0f} · Sector: {s['sector']}\n"
            f"P/E {s['pe']:.1f}x · P/B {s['pb']:.1f}x · ROE {s['roe']:.1f}%\n"
            f"Factor scores — Momentum {s['mom']} · Quality {s['qual']} · Value {s['val']} · Growth {s['grw']} · Composite {s['composite']}\n\n"
            f"Open the Screener or click this stock from the Dashboard for the full AI report.\n\n"
            f"⚠️ Offline rule-based reply (Ollama not reachable in this preview)."
        )
    if any(w in ql for w in ["rbi", "repo", "rate"]):
        latest_repo = _MACRO_DATA["repo"][-1]
        return (
            f"RBI's repo rate currently stands at {latest_repo}%, as part of an easing cycle. "
            f"Historically, falling rates benefit rate-sensitive sectors: Banking, NBFC, Real Estate, and Auto. "
            f"Check the Macro tab for full repo rate and CPI trend charts.\n\n"
            f"⚠️ Offline rule-based reply."
        )
    if "momentum" in ql:
        return (
            f"Momentum investing ranks stocks by relative price strength over the trailing 12 months. "
            f"In the Indian market, momentum has historically been one of the stronger factors. "
            f"The 'High Momentum' strategy shows a {_MACRO_DATA['high_momentum_cagr']}% CAGR "
            f"vs {_MACRO_DATA['nifty_cagr']}% for Nifty 50 over the same period.\n\n"
            f"⚠️ Offline rule-based reply."
        )
    return (
        f"I can discuss specific Nifty stocks (try mentioning a ticker like 'HDFCBANK' or 'TCS'), "
        f"RBI policy, or factor investing concepts. Try a quick prompt or ask about a specific stock.\n\n"
        f"⚠️ Offline rule-based reply (Ollama not reachable). "
        f"Run `ollama serve` on your host for full open-source LLM responses — free, no API key."
    )


class AIService:
    """
    Thin wrapper around Ollama's local REST API.
    No billing, no rate limits beyond your own hardware, no data leaves
    your machine (or your self-hosted server) unless you choose to deploy
    Ollama on a cloud VM yourself.
    """

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=120.0)

    async def _generate(self, system: str, messages: list[dict], max_tokens: int = 1000) -> dict:
        """
        Calls Ollama's /api/chat endpoint.
        Falls back gracefully with a clear setup message if Ollama isn't
        running — this is the only "failure mode" since there's no
        billing/auth layer to break.
        """
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "system", "content": system}] + messages,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0.4},
        }
        try:
            resp = await self.client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
            return {"content": content, "tokens": tokens, "source": "ollama"}
        except httpx.ConnectError:
            logger.error("Ollama is not running.")
            return {
                "content": (
                    f"⚠️ Local AI model unavailable. Ollama isn't running.\n\n"
                    f"Start it with: `ollama serve`\n"
                    f"Make sure the model is pulled: `ollama pull {OLLAMA_MODEL}`\n\n"
                    f"This app uses a 100% free, self-hosted LLM — no payment or API key needed, "
                    f"just Ollama running locally or on your own server."
                ),
                "tokens": 0, "source": "error",
            }
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return {"content": f"AI generation failed: {str(e)}", "tokens": 0, "source": "error"}

    # ── CHAT ─────────────────────────────────────────────────────
    async def chat(self, messages: list[dict], context_ticker: str | None = None) -> dict:
        system = SYSTEM_PROMPT_RESEARCH
        if context_ticker:
            system += f"\n\nThe user is currently viewing: {context_ticker}. Bias your answer toward this stock if relevant."

        result = await self._generate(system, messages, max_tokens=900)
        if result.get("source") == "ollama":
            return {
                "response": result["content"],
                "model": OLLAMA_MODEL,
                "tokens_used": result["tokens"],
                "source": "ollama",
            }
        # Fallback to offline rule-based engine
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        offline_reply = buildOfflineChatReply(last_user_msg)
        return {
            "response": offline_reply,
            "model": "offline-rule-engine",
            "tokens_used": 0,
            "source": "offline",
        }

    # ── STOCK REPORT ─────────────────────────────────────────────
    async def generate_stock_report(self, stock_data: dict, report_type: str = "full") -> str:
        system_prompt = SYSTEM_PROMPT_ANALYST
        max_tokens = 1200
        
        if report_type == "brief":
            system_prompt = """You are a quantitative equity analyst specializing in Indian equities.
Provide a very brief 4-bullet analysis.
You must output exactly 4 bullet points, one for each category: Valuation, Momentum, Risk, and Verdict.
Be concise, use numbers, and do not include headers or other text.
Format precisely as:
- Valuation: [details]
- Momentum: [details]
- Risk: [details]
- Verdict: [details]"""
            prompt = f"""Analyze {stock_data.get('name')} ({stock_data.get('ticker')}, NSE) with this data:
Price: ₹{stock_data.get('price')} | Change: {stock_data.get('change_pct')}%
PE: {stock_data.get('pe_ratio')}x | PB: {stock_data.get('pb_ratio')}x | ROE: {stock_data.get('roe')}% | Revenue Growth: {stock_data.get('revenue_growth')}%
Factor Scores (0-100): Momentum {stock_data.get('momentum_score')} | Quality {stock_data.get('quality_score')} | Value {stock_data.get('value_score')} | Growth {stock_data.get('growth_score')} | Composite {stock_data.get('composite_score')}"""
            max_tokens = 300
        else:
            prompt = f"""Analyze {stock_data.get('name')} ({stock_data.get('ticker')}, NSE):

Price: ₹{stock_data.get('price')} | Change: {stock_data.get('change_pct')}%
Sector: {stock_data.get('sector')} | Market Cap: ₹{stock_data.get('market_cap')} Cr

Valuation: PE {stock_data.get('pe_ratio')}x | PB {stock_data.get('pb_ratio')}x | EV/EBITDA {stock_data.get('ev_ebitda')}x
Profitability: ROE {stock_data.get('roe')}% | ROA {stock_data.get('roa')}% | Net Margin {stock_data.get('net_margin')}%
Growth: Revenue Growth {stock_data.get('revenue_growth')}% | Earnings Growth {stock_data.get('earnings_growth')}%
Leverage: Debt/Equity {stock_data.get('debt_equity')}

Factor Scores (0-100 percentile vs Nifty 500):
Momentum {stock_data.get('momentum_score')} | Quality {stock_data.get('quality_score')} | Value {stock_data.get('value_score')} | Growth {stock_data.get('growth_score')} | Composite {stock_data.get('composite_score')}

Report type requested: {report_type}"""

        result = await self._generate(system_prompt, [{"role": "user", "content": prompt}], max_tokens=max_tokens)
        if result.get("source") == "ollama":
            return result["content"]
        # Fallback to offline rule-based report
        ticker = stock_data.get("ticker", "").upper()
        stock = next((s for s in _STOCKS if s["ticker"] == ticker), None)
        if stock:
            return buildOfflineReport(stock)
        return result["content"]

    # ── EARNINGS SUMMARY ─────────────────────────────────────────
    async def summarise_earnings(self, ticker: str, raw_text: str) -> str:
        prompt = f"Summarise this quarterly earnings release/transcript for {ticker}:\n\n{raw_text[:6000]}"
        result = await self._generate(SYSTEM_PROMPT_EARNINGS, [{"role": "user", "content": prompt}], max_tokens=900)
        return result["content"]

    # ── INVESTMENT THESIS ────────────────────────────────────────
    async def generate_investment_thesis(self, stock_data: dict, portfolio_context: dict | None = None) -> str:
        context_str = f"\n\nUser's current portfolio context: {portfolio_context}" if portfolio_context else ""
        prompt = f"""Generate a structured bull case and bear case (NOT a recommendation) for {stock_data.get('name')} ({stock_data.get('ticker')}) based on this data:

{stock_data}
{context_str}

Format as:
**Bull Case** (3 data-driven points)
**Bear Case** (3 data-driven points)
**What Would Change The Picture** (catalysts to watch)"""

        result = await self._generate(SYSTEM_PROMPT_ANALYST, [{"role": "user", "content": prompt}], max_tokens=1000)
        return result["content"]

    # ── PORTFOLIO RISK NARRATIVE ─────────────────────────────────
    async def analyse_portfolio_risk(self, portfolio_data: dict) -> str:
        prompt = f"""Explain this Indian equity portfolio's risk profile in plain language for a retail investor:

Total Value: ₹{portfolio_data.get('total_value')}
Beta vs Nifty 50: {portfolio_data.get('beta')}
Sharpe Ratio: {portfolio_data.get('sharpe')}
Volatility (annualised): {portfolio_data.get('volatility')}%
Max Drawdown: {portfolio_data.get('max_drawdown')}%
Sector Concentration: {portfolio_data.get('sector_weights')}

Explain what these numbers mean practically, and flag any concentration or risk concerns visible in the data."""

        result = await self._generate(SYSTEM_PROMPT_RESEARCH, [{"role": "user", "content": prompt}], max_tokens=800)
        return result["content"]

    async def close(self):
        await self.client.aclose()


ai_service = AIService()

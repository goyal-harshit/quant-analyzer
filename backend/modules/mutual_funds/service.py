"""
Mutual Fund service.

Primary data source: mfapi.in (free, no API key, 14k+ Indian schemes, daily NAV).
  GET /mf/search?q=<query>   -> [{schemeCode, schemeName}]
  GET /mf/{code}             -> {meta, data:[{date:"dd-mm-yyyy", nav:"xx.xx"}], status}

Resilience: every network call is cached in Redis (cache_service) and falls
back to a small bundled seed list so the endpoints always return something
usable even offline / when mfapi.in is unreachable.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from statistics import mean, pstdev
from typing import Optional

import httpx

from services.cache_service import cache

logger = logging.getLogger(__name__)

MFAPI_BASE = "https://api.mfapi.in"
_TIMEOUT = httpx.Timeout(15.0, connect=8.0)

TTL_SEARCH = 6 * 3600
TTL_DETAIL = 6 * 3600
RISK_FREE_RATE = 0.065  # ~6.5% (RBI repo) for Sharpe/Sortino

# ── Seed fallback: a few popular schemes so search/detail work offline ──
SEED_SCHEMES = [
    {"scheme_code": 120503, "scheme_name": "Axis Bluechip Fund - Direct Plan - Growth",
     "fund_house": "Axis Mutual Fund", "category": "Equity Scheme - Large Cap Fund"},
    {"scheme_code": 119551, "scheme_name": "SBI Bluechip Fund - Direct Plan - Growth",
     "fund_house": "SBI Mutual Fund", "category": "Equity Scheme - Large Cap Fund"},
    {"scheme_code": 118989, "scheme_name": "HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth",
     "fund_house": "HDFC Mutual Fund", "category": "Equity Scheme - Mid Cap Fund"},
    {"scheme_code": 120465, "scheme_name": "Mirae Asset Large Cap Fund - Direct Plan - Growth",
     "fund_house": "Mirae Asset Mutual Fund", "category": "Equity Scheme - Large Cap Fund"},
    {"scheme_code": 122639, "scheme_name": "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
     "fund_house": "PPFAS Mutual Fund", "category": "Equity Scheme - Flexi Cap Fund"},
    {"scheme_code": 118834, "scheme_name": "ICICI Prudential Bluechip Fund - Direct Plan - Growth",
     "fund_house": "ICICI Prudential Mutual Fund", "category": "Equity Scheme - Large Cap Fund"},
    {"scheme_code": 125354, "scheme_name": "Quant Small Cap Fund - Direct Plan - Growth",
     "fund_house": "Quant Mutual Fund", "category": "Equity Scheme - Small Cap Fund"},
    {"scheme_code": 119598, "scheme_name": "Nippon India Small Cap Fund - Direct Plan - Growth",
     "fund_house": "Nippon India Mutual Fund", "category": "Equity Scheme - Small Cap Fund"},
]


async def _get_json(url: str):
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                return resp.json()
            logger.warning("mfapi %s -> HTTP %s", url, resp.status_code)
    except Exception as e:  # noqa: BLE001
        logger.warning("mfapi request failed %s: %s", url, e)
    return None


def _seed_search(q: str) -> list[dict]:
    ql = q.lower().strip()
    return [s for s in SEED_SCHEMES if ql in s["scheme_name"].lower() or ql in (s.get("fund_house") or "").lower()]


_ALL_SCHEMES: list[dict] = []  # in-process cache of the full mfapi scheme list


async def _all_schemes() -> list[dict]:
    """Full mfapi.in scheme list (~14k), cached in-process + Redis for a day.
    Enables local multi-term search that mfapi's own /mf/search can't do well."""
    global _ALL_SCHEMES
    if _ALL_SCHEMES:
        return _ALL_SCHEMES
    cached = await cache.get("mf:all")
    if cached:
        _ALL_SCHEMES = json.loads(cached)
        return _ALL_SCHEMES
    raw = await _get_json(f"{MFAPI_BASE}/mf")
    if isinstance(raw, list) and raw:
        _ALL_SCHEMES = [
            {"scheme_code": x.get("schemeCode"), "scheme_name": x.get("schemeName")}
            for x in raw if x.get("schemeName") and x.get("schemeCode")
        ]
        await cache.set("mf:all", json.dumps(_ALL_SCHEMES), 86400)
    return _ALL_SCHEMES


def _rank(name: str, terms: list[str]) -> float:
    """Higher = better. Prefer prefix match, Direct/Growth plans, shorter names."""
    score = 0.0
    if name.startswith(terms[0]):
        score += 100
    if "direct" in name:
        score += 6
    if "growth" in name:
        score += 4
    if "dividend" in name or "idcw" in name or "bonus" in name:
        score -= 3
    score -= len(name) * 0.01
    return score


async def search_schemes(q: str, limit: int = 25) -> list[dict]:
    q = (q or "").strip()
    if len(q) < 2:
        return []
    key = f"mf:search:{q.lower()}"
    cached = await cache.get(key)
    if cached:
        return json.loads(cached)[:limit]

    results: list[dict] = []
    schemes = await _all_schemes()
    if schemes:
        terms = [t for t in q.lower().split() if t]
        matched = [s for s in schemes if all(t in s["scheme_name"].lower() for t in terms)]
        matched.sort(key=lambda s: _rank(s["scheme_name"].lower(), terms), reverse=True)
        results = [
            {"scheme_code": s["scheme_code"], "scheme_name": s["scheme_name"],
             "fund_house": None, "category": None}
            for s in matched[:limit]
        ]

    # Fallback to mfapi's own search, then the bundled seed list.
    if not results:
        raw = await _get_json(f"{MFAPI_BASE}/mf/search?q={httpx.URL(q)}")
        if isinstance(raw, list) and raw:
            results = [{"scheme_code": i.get("schemeCode"), "scheme_name": i.get("schemeName"),
                        "fund_house": None, "category": None} for i in raw]
    if not results:
        results = _seed_search(q)

    if results:
        await cache.set(key, json.dumps(results), TTL_SEARCH)
    return results[:limit]


def _parse_nav_history(data: list[dict]) -> list[dict]:
    """mfapi returns newest-first; normalise to oldest-first ISO dates."""
    out = []
    for row in data or []:
        try:
            d = datetime.strptime(row["date"], "%d-%m-%Y").date()
            out.append({"date": d.isoformat(), "nav": float(row["nav"])})
        except (KeyError, ValueError, TypeError):
            continue
    out.sort(key=lambda r: r["date"])
    return out


async def get_scheme(code: int, refresh: bool = False) -> Optional[dict]:
    key = f"mf:detail:{code}"
    if not refresh:
        cached = await cache.get(key)
        if cached:
            return json.loads(cached)

    raw = await _get_json(f"{MFAPI_BASE}/mf/{code}")
    if not raw or raw.get("status") == "FAIL" or not raw.get("data"):
        return _seed_detail(code)

    meta = raw.get("meta", {}) or {}
    history = _parse_nav_history(raw.get("data", []))
    detail = {
        "meta": {
            "scheme_code": meta.get("scheme_code", code),
            "scheme_name": meta.get("scheme_name", f"Scheme {code}"),
            "fund_house": meta.get("fund_house"),
            "scheme_type": meta.get("scheme_type"),
            "scheme_category": meta.get("scheme_category"),
        },
        "latest_nav": history[-1]["nav"] if history else None,
        "latest_date": history[-1]["date"] if history else None,
        "nav_history": history,
    }
    await cache.set(key, json.dumps(detail), TTL_DETAIL)
    return detail


def _seed_detail(code: int) -> Optional[dict]:
    """Synthesise a plausible NAV series for a seed scheme so the UI still works."""
    seed = next((s for s in SEED_SCHEMES if s["scheme_code"] == code), None)
    if not seed:
        return None
    # Deterministic synthetic NAV: smooth ~13% CAGR growth with mild wobble.
    history = []
    base = 100.0
    days = 5 * 365
    for i in range(days):
        # ~13% annual drift; deterministic sinusoidal wobble (no randomness)
        drift = (1.13 ** (i / 365))
        wobble = 1 + 0.04 * math.sin(i / 18.0)
        nav = round(base * drift * wobble, 4)
        # Build dates going back `days` from today (not a fixed reference, which
        # would go stale and stop the chart at a past date).
        from datetime import date, timedelta
        d = date.today() - timedelta(days=(days - 1 - i))
        history.append({"date": d.isoformat(), "nav": nav})
    return {
        "meta": {
            "scheme_code": code,
            "scheme_name": seed["scheme_name"],
            "fund_house": seed.get("fund_house"),
            "scheme_type": "Open Ended",
            "scheme_category": seed.get("category"),
        },
        "latest_nav": history[-1]["nav"],
        "latest_date": history[-1]["date"],
        "nav_history": history,
        "_synthetic": True,
    }


# ── Analytics ────────────────────────────────────────────────────────────

def _nav_on_or_before(history: list[dict], target_iso: str) -> Optional[float]:
    """NAV at the closest available date <= target (history is oldest-first)."""
    chosen = None
    for row in history:
        if row["date"] <= target_iso:
            chosen = row["nav"]
        else:
            break
    return chosen


def _pct(curr: float, prev: Optional[float]) -> Optional[float]:
    if not prev:
        return None
    return round((curr / prev - 1.0) * 100, 2)


def _cagr(curr: float, prev: Optional[float], years: float) -> Optional[float]:
    if not prev or prev <= 0 or years <= 0:
        return None
    return round(((curr / prev) ** (1 / years) - 1.0) * 100, 2)


def compute_returns(detail: dict) -> dict:
    history = detail.get("nav_history", [])
    meta = detail.get("meta", {})
    out = {
        "scheme_code": meta.get("scheme_code"),
        "scheme_name": meta.get("scheme_name"),
        "latest_nav": detail.get("latest_nav"),
        "ret_1m": None, "ret_3m": None, "ret_6m": None, "ret_1y": None,
        "cagr_3y": None, "cagr_5y": None, "cagr_since_inception": None,
    }
    if not history:
        return out

    from datetime import date, timedelta
    curr = history[-1]["nav"]
    last_date = date.fromisoformat(history[-1]["date"])

    def back(days):
        return (last_date - timedelta(days=days)).isoformat()

    out["ret_1m"] = _pct(curr, _nav_on_or_before(history, back(30)))
    out["ret_3m"] = _pct(curr, _nav_on_or_before(history, back(91)))
    out["ret_6m"] = _pct(curr, _nav_on_or_before(history, back(182)))
    out["ret_1y"] = _pct(curr, _nav_on_or_before(history, back(365)))
    out["cagr_3y"] = _cagr(curr, _nav_on_or_before(history, back(365 * 3)), 3)
    out["cagr_5y"] = _cagr(curr, _nav_on_or_before(history, back(365 * 5)), 5)

    first = history[0]
    span_years = max((last_date - date.fromisoformat(first["date"])).days / 365.0, 0.01)
    out["cagr_since_inception"] = _cagr(curr, first["nav"], span_years)
    return out


def _daily_returns(history: list[dict]) -> list[float]:
    rets = []
    prev = None
    for row in history:
        nav = row["nav"]
        if prev and prev > 0:
            rets.append(nav / prev - 1.0)
        prev = nav
    return rets


def compute_risk(detail: dict, lookback_days: int = 365 * 3) -> dict:
    history = detail.get("nav_history", [])
    meta = detail.get("meta", {})
    out = {
        "scheme_code": meta.get("scheme_code"),
        "scheme_name": meta.get("scheme_name"),
        "volatility_pct": None, "sharpe_ratio": None, "sortino_ratio": None,
        "max_drawdown_pct": None, "risk_grade": None,
    }
    window = history[-lookback_days:] if len(history) > lookback_days else history
    if len(window) < 30:
        return out

    rets = _daily_returns(window)
    if not rets:
        return out

    vol_daily = pstdev(rets) if len(rets) > 1 else 0.0
    vol_ann = vol_daily * math.sqrt(252)
    out["volatility_pct"] = round(vol_ann * 100, 2)

    mean_daily = mean(rets)
    ann_return = (1 + mean_daily) ** 252 - 1
    if vol_ann > 0:
        out["sharpe_ratio"] = round((ann_return - RISK_FREE_RATE) / vol_ann, 2)

    downside = [r for r in rets if r < 0]
    if downside:
        dd_dev = pstdev(downside) * math.sqrt(252) if len(downside) > 1 else abs(downside[0]) * math.sqrt(252)
        if dd_dev > 0:
            out["sortino_ratio"] = round((ann_return - RISK_FREE_RATE) / dd_dev, 2)

    # Max drawdown
    peak = window[0]["nav"]
    max_dd = 0.0
    for row in window:
        peak = max(peak, row["nav"])
        if peak > 0:
            max_dd = min(max_dd, row["nav"] / peak - 1.0)
    out["max_drawdown_pct"] = round(max_dd * 100, 2)

    v = out["volatility_pct"]
    out["risk_grade"] = (
        "Low" if v is not None and v < 12 else
        "Moderate" if v is not None and v < 20 else
        "High" if v is not None and v < 30 else
        "Very High" if v is not None else None
    )
    return out


def sip_projection(monthly: float, years: float, annual_return: float, step_up: float = 0.0) -> dict:
    """Future value of a monthly SIP with optional annual step-up."""
    months = int(round(years * 12))
    r = (annual_return / 100.0) / 12.0
    fv = 0.0
    invested = 0.0
    amount = monthly
    for m in range(months):
        if m > 0 and step_up > 0 and m % 12 == 0:
            amount *= (1 + step_up / 100.0)
        invested += amount
        # each contribution compounds for the remaining months
        fv = (fv + amount) * (1 + r)
    fv = round(fv, 2)
    invested = round(invested, 2)
    return {
        "monthly_amount": monthly,
        "years": years,
        "expected_return": annual_return,
        "total_invested": invested,
        "future_value": fv,
        "estimated_gain": round(fv - invested, 2),
        "wealth_multiple": round(fv / invested, 2) if invested else 0.0,
    }


async def compare(scheme_codes: list[int]) -> list[dict]:
    out = []
    for code in scheme_codes[:4]:
        detail = await get_scheme(code)
        if not detail:
            continue
        ret = compute_returns(detail)
        risk = compute_risk(detail)
        out.append({
            "scheme_code": code,
            "scheme_name": detail["meta"]["scheme_name"],
            "fund_house": detail["meta"].get("fund_house"),
            "category": detail["meta"].get("scheme_category"),
            "latest_nav": detail.get("latest_nav"),
            "returns": ret,
            "risk": risk,
        })
    return out

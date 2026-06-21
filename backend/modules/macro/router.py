"""Macro Router — India macroeconomic indicators"""

import asyncio
import json

from fastapi import APIRouter
from services.data_service import data_service, _get_redis

router = APIRouter()

_MACRO_CACHE_KEY = "macro:dashboard:v1"
_MACRO_TTL = 600  # 10 min — macro series move slowly


@router.get("", response_model=dict)
async def get_macro_dashboard(refresh: bool = False):
    """
    Get full macro dashboard: repo rate, CPI, GDP, USD/INR, FII/DII flows.
    Live sources: World Bank (CPI/GDP), Yahoo (USD/INR), NSE (FII/DII).
    Sources are fetched concurrently AND individually bounded, so one slow source
    (e.g. NSE FII/DII, which blocks datacenter IPs) can't stall the dashboard past
    ~6s; the assembled response is cached so repeat loads are instant.
    """
    if not refresh:
        try:
            r = await _get_redis()
            if r:
                cached = await r.get(_MACRO_CACHE_KEY)
                if cached:
                    return json.loads(cached)
        except Exception:
            pass

    async def _bounded(coro, timeout: float = 6.0):
        """Cap any single source; on timeout/failure that source degrades to empty."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except Exception:
            return None

    repo, cpi, gdp, usd_inr, flows = await asyncio.gather(
        _bounded(data_service.get_repo_rate_history(refresh=refresh)),
        _bounded(data_service.get_cpi_history(refresh=refresh)),
        _bounded(data_service.get_gdp_growth_history(refresh=refresh)),
        _bounded(data_service.get_usd_inr_history(days=180, refresh=refresh)),
        _bounded(data_service.get_fii_dii_flows(refresh=refresh)),
    )
    repo = repo if isinstance(repo, list) else []
    cpi = cpi if isinstance(cpi, list) else []
    gdp = gdp if isinstance(gdp, list) else []
    usd_inr = usd_inr if isinstance(usd_inr, list) else []
    flows = flows if isinstance(flows, dict) else {}

    result = {
        "repo_rate": repo,
        "cpi": cpi,
        "gdp_growth": gdp,
        "usd_inr": usd_inr,
        "fii_flows": flows.get("fii", []),
        "dii_flows": flows.get("dii", []),
        "fii_dii_latest": flows.get("latest"),
        "current_indicators": [
            {"name": "RBI Repo Rate", "value": repo[-1]["value"] if repo else None, "unit": "%", "source": "RBI (last published)"},
            {"name": "CPI Inflation", "value": cpi[-1]["value"] if cpi else None, "unit": "%", "source": "World Bank", "as_of": cpi[-1]["date"] if cpi else None},
            {"name": "GDP Growth", "value": gdp[-1]["value"] if gdp else None, "unit": "%", "source": "World Bank", "as_of": gdp[-1]["quarter"] if gdp else None},
            {"name": "USD/INR", "value": usd_inr[-1]["value"] if usd_inr else None, "unit": "₹", "source": "Yahoo (live)"},
        ],
    }

    try:
        r = await _get_redis()
        if r:
            await r.setex(_MACRO_CACHE_KEY, _MACRO_TTL, json.dumps(result))
    except Exception:
        pass
    return result


@router.get("/regime")
async def get_macro_regime():
    """
    Classify current macro regime (simplified rule-based, replace with
    HMM/ML regime detection model in production) and suggest sector tilts.
    """
    repo = await data_service.get_repo_rate_history()
    cpi = await data_service.get_cpi_history()

    repo_trend = "easing" if len(repo) >= 2 and repo[-1]["value"] < repo[-2]["value"] else "stable"
    cpi_level = "controlled" if cpi and cpi[-1]["value"] < 4.0 else "elevated"

    sector_tilt = []
    if repo_trend == "easing":
        sector_tilt.extend(["Banking", "NBFC", "Real Estate", "Auto"])
    if cpi_level == "controlled":
        sector_tilt.append("Consumer Discretionary")

    return {
        "monetary_policy_regime": repo_trend,
        "inflation_regime": cpi_level,
        "favoured_sectors": sector_tilt,
        "rationale": f"RBI policy is {repo_trend} with repo rate at {repo[-1]['value'] if repo else 'N/A'}%. "
                     f"CPI inflation is {cpi_level} at {cpi[-1]['value'] if cpi else 'N/A'}%, "
                     f"{'creating room for further rate cuts' if cpi_level == 'controlled' else 'limiting RBI easing room'}.",
    }

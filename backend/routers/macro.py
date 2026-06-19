"""Macro Router — India macroeconomic indicators"""

from fastapi import APIRouter
from services.data_service import data_service

router = APIRouter()


@router.get("", response_model=dict)
async def get_macro_dashboard():
    """
    Get full macro dashboard: repo rate, CPI, USD/INR, FII/DII flows.
    Sources: RBI DBIE, MOSPI, FRED (India series), NSE provisional data.
    """
    repo = await data_service.get_repo_rate_history()
    cpi = await data_service.get_cpi_history()
    usd_inr = await data_service.get_usd_inr_history(days=180)
    flows = await data_service.get_fii_dii_flows()

    return {
        "repo_rate": repo,
        "cpi": cpi,
        "usd_inr": usd_inr,
        "fii_flows": flows.get("fii", []),
        "dii_flows": flows.get("dii", []),
        "current_indicators": [
            {"name": "RBI Repo Rate", "value": repo[-1]["value"] if repo else None, "unit": "%", "source": "RBI"},
            {"name": "CPI Inflation", "value": cpi[-1]["value"] if cpi else None, "unit": "%", "source": "MOSPI"},
            {"name": "USD/INR", "value": usd_inr[-1]["value"] if usd_inr else None, "unit": "₹", "source": "Market"},
        ],
    }


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

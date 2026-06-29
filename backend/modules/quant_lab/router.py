"""Quant Lab Router — Custom factor model builder"""

from fastapi import APIRouter, HTTPException
import pandas as pd

from services.data_service import data_service, _gather_limited
from services.seed_data import DEFAULT_TICKERS
from services.factor_engine import FactorEngine
from models.schemas import FactorModelRequest

router = APIRouter()
engine = FactorEngine()



@router.post("/score")
async def score_universe(request: FactorModelRequest):
    """
    Score a custom list of tickers using a custom factor model.
    Returns ranked results with composite and individual factor scores.
    """
    universe = request.tickers if request.tickers and len(request.tickers) > 0 else DEFAULT_TICKERS

    _all = await _gather_limited(
        [
            *[data_service.get_fundamentals(t) for t in universe],
            *[data_service.get_price_history(t, period="1y") for t in universe],
        ],
        limit=12,
    )
    n = len(universe)
    funds, hists = _all[:n], _all[n:]

    fund_list = []
    for ticker, fund in zip(universe, funds):
        if fund:
            f = dict(fund)
            f["ticker"] = ticker
            if not f.get("sector"):
                f["sector"] = data_service._SECTOR_MAP.get(ticker)
            fund_list.append(f)

    price_histories = {}
    for ticker, df in zip(universe, hists):
        if df is not None and not df.empty:
            price_histories[ticker] = df["close"]

    if not fund_list:
        raise HTTPException(status_code=503, detail="Unable to fetch universe data")

    fund_df = pd.DataFrame(fund_list).set_index("ticker")
    price_matrix = pd.DataFrame(price_histories)

    weights = request.factor_weights
    momentum = engine.compute_momentum_score(price_matrix) if not price_matrix.empty else pd.Series(dtype=float)
    quality = engine.compute_quality_score(fund_df)
    value = engine.compute_value_score(fund_df)
    growth = engine.compute_growth_score(fund_df)
    low_vol = engine.compute_low_vol_score(price_matrix) if not price_matrix.empty else pd.Series(dtype=float)

    composite = engine.compute_composite(momentum, quality, value, growth, low_vol, weights=weights)

    results = []
    for ticker in fund_df.index:
        def _safe(v):
            return None if (isinstance(v, float) and pd.isna(v)) else round(v, 1) if v is not None else None

        results.append({
            "ticker": ticker,
            "momentum": _safe(momentum.get(ticker)),
            "quality": _safe(quality.get(ticker)),
            "value": _safe(value.get(ticker)),
            "growth": _safe(growth.get(ticker)),
            "low_volatility": _safe(low_vol.get(ticker)),
            "composite": _safe(composite.get(ticker)),
        })

    results.sort(key=lambda x: x["composite"] or 0, reverse=True)
    return {"model_name": request.name, "results": results}


@router.get("/factor-definitions")
async def get_factor_definitions():
    """Get explanations of each factor for Quant Lab UI."""
    return {
        "momentum": {
            "description": "12-1 month price momentum (Jegadeesh & Titman 1993). Measures relative price strength over the past year excluding the most recent month.",
            "formula": "Return(t-252, t-21) cross-sectionally ranked",
        },
        "quality": {
            "description": "Composite of ROE, gross/EBITDA margins, leverage, and earnings quality (Piotroski/Novy-Marx framework).",
            "formula": "Rank(ROE, Gross Margin, Low Debt, Interest Coverage)",
        },
        "value": {
            "description": "Inverse-ranked valuation multiples: PE, PB, EV/EBITDA, plus FCF yield (Fama-French value factor).",
            "formula": "Rank(-PE, -PB, -EV/EBITDA, FCF Yield)",
        },
        "growth": {
            "description": "Revenue growth, EPS growth, and operating profit growth trends.",
            "formula": "Rank(Revenue Growth, EPS Growth, OpProfit Growth)",
        },
        "low_volatility": {
            "description": "Inverse-ranked 60-day realised volatility (low-vol anomaly: Ang et al. 2006).",
            "formula": "Rank(-σ_60d)",
        },
    }

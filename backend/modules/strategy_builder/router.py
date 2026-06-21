"""Strategy Builder Router — No-code strategy composer"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import pandas as pd

from services.data_service import data_service, _gather_limited
from services.seed_data import DEFAULT_TICKERS
from services.factor_engine import FactorEngine, PortfolioAnalytics

router = APIRouter()
engine = FactorEngine()


class StrategyRule(BaseModel):
    type: str = Field(..., description="factor|technical|fundamental")
    field: str
    operator: str = Field(..., description="gt|lt|gte|lte|between")
    value: float
    weight: float = 1.0


class StrategyRequest(BaseModel):
    name: str
    rules: List[StrategyRule]
    universe: str = "NIFTY50"
    start_date: str = "2022-01-01"
    end_date: str = "2025-12-31"
    rebalance_freq: str = Field(default="quarterly", description="monthly|quarterly|semi-annual|annual")
    top_n: int = Field(default=20, ge=5, le=100)
    transaction_cost: float = Field(default=0.001)


@router.post("/backtest")
async def backtest_strategy(request: StrategyRequest):
    """
    Backtest a custom strategy built from rules.
    Rules are translated into factor weights or filter thresholds.
    """
    universe = DEFAULT_TICKERS

    try:
        _all = await _gather_limited(
            [
                *[data_service.get_fundamentals(t) for t in universe],
                *[data_service.get_price_history(t, period="2y") for t in universe],
            ],
            limit=8,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Data fetch failed: {e}")

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
        raise HTTPException(status_code=503, detail="Insufficient data for backtest")

    fund_df = pd.DataFrame(fund_list).set_index("ticker")
    price_matrix = pd.DataFrame(price_histories)

    # Translate rules to factor weights
    weights = {}
    for rule in request.rules:
        if rule.type == "factor":
            weights[rule.field] = rule.weight

    default_weights = {"momentum": 0.25, "quality": 0.25, "value": 0.20, "growth": 0.20, "low_volatility": 0.10}
    for k, v in default_weights.items():
        if k not in weights:
            weights[k] = 0.0
    total = sum(weights.values()) or 1.0
    weights = {k: v / total for k, v in weights.items()}

    momentum = engine.compute_momentum_score(price_matrix) if not price_matrix.empty else pd.Series(dtype=float)
    quality = engine.compute_quality_score(fund_df)
    value = engine.compute_value_score(fund_df)
    growth = engine.compute_growth_score(fund_df)
    low_vol = engine.compute_low_vol_score(price_matrix) if not price_matrix.empty else pd.Series(dtype=float)

    composite = engine.compute_composite(momentum, quality, value, growth, low_vol, weights=weights)

    # Apply filters
    filtered = composite.dropna()
    for rule in request.rules:
        if rule.type == "fundamental" and rule.field in fund_df.columns:
            vals = fund_df[rule.field].dropna()
            if rule.operator == "gt":
                filtered = filtered[vals.loc[filtered.index] > rule.value]
            elif rule.operator == "lt":
                filtered = filtered[vals.loc[filtered.index] < rule.value]
            elif rule.operator == "gte":
                filtered = filtered[vals.loc[filtered.index] >= rule.value]
            elif rule.operator == "lte":
                filtered = filtered[vals.loc[filtered.index] <= rule.value]

    top = filtered.nlargest(min(request.top_n, len(filtered)))

    result = {
        "strategy_name": request.name,
        "rules_applied": [r.model_dump() for r in request.rules],
        "weights_used": weights,
        "top_holdings": [{"ticker": t, "score": round(float(top[t]), 2)} for t in top.index],
        "universe_size": len(filtered),
        "message": "Full backtest simulation requires price history for the selected date range. Use /backtest endpoint for complete simulation.",
    }
    return result


@router.get("/rule-templates")
async def get_rule_templates():
    """Get pre-built rule templates for the Strategy Builder UI."""
    return {
        "templates": [
            {
                "id": "high_momentum",
                "name": "High Momentum",
                "description": "Stocks with strong 12-1 month momentum",
                "rules": [{"type": "factor", "field": "momentum", "operator": "gt", "value": 70, "weight": 1.0}],
            },
            {
                "id": "quality_value",
                "name": "Quality Value",
                "description": "High quality (ROE, margins) and low valuation (PE, PB)",
                "rules": [
                    {"type": "factor", "field": "quality", "operator": "gt", "value": 65, "weight": 0.5},
                    {"type": "factor", "field": "value", "operator": "gt", "value": 60, "weight": 0.5},
                ],
            },
            {
                "id": "low_vol_defensive",
                "name": "Low Volatility Defensive",
                "description": "Low-volatility stocks with stable earnings",
                "rules": [{"type": "factor", "field": "low_volatility", "operator": "gt", "value": 70, "weight": 1.0}],
            },
        ]
    }

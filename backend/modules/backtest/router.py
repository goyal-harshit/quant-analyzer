"""Backtest Router — Factor strategy backtesting"""

from fastapi import APIRouter, HTTPException
import pandas as pd
import numpy as np
from datetime import datetime

from models.schemas import BacktestRequest, BacktestResponse, BacktestMetrics, BacktestDataPoint
from services.data_service import data_service, _gather_limited
from services.seed_data import DEFAULT_TICKERS
from services.factor_engine import FactorEngine, PortfolioAnalytics

router = APIRouter()
engine = FactorEngine()


@router.post("", response_model=dict)
async def run_backtest(request: BacktestRequest):
    universe = DEFAULT_TICKERS
    tickers_to_fetch = [t for t in universe if t != "^NSEI"] + ["^NSEI"]

    price_results = await _gather_limited(
        [data_service.get_price_history(t, period="2y") for t in tickers_to_fetch],
        limit=12,
    )
    price_data = {}
    for ticker, df in zip(tickers_to_fetch, price_results):
        if df is not None and not df.empty and len(df) > 60:
            price_data[ticker] = df["close"]

    if "^NSEI" not in price_data and price_data:
        price_data["^NSEI"] = pd.Series(
            sum(price_data.values()) / len(price_data),
            index=list(price_data.values())[0].index
        )
    if len(price_data) < 10:
        raise HTTPException(status_code=503, detail="Insufficient data for backtest")

    price_matrix = pd.DataFrame(price_data).dropna(how="all")
    benchmark_prices = price_data.get("^NSEI", price_matrix.mean(axis=1))

    # Determine rebalance dates
    freq_map = {"monthly": "ME", "quarterly": "QE", "semi-annual": "2QE", "annual": "YE"}
    rebal_freq = freq_map.get(request.rebalance_freq, "QE")
    rebalance_dates = pd.date_range(
        start=price_matrix.index.min(), end=price_matrix.index.max(), freq=rebal_freq
    )

    portfolio_value = 100.0
    benchmark_value = 100.0
    equity_curve = []
    prev_holdings = set()
    turnovers = []

    for i, rebal_date in enumerate(rebalance_dates):
        # Get prices up to this rebalance date
        window = price_matrix[price_matrix.index <= rebal_date]
        if len(window) < 60:
            continue

        # Compute factor scores using available history
        momentum = engine.compute_momentum_score(window)
        low_vol = engine.compute_low_vol_score(window)

        # Simplified: use momentum + low-vol as proxy composite (since
        # fundamentals require separate point-in-time data not modeled here)
        combined = (momentum.fillna(50) * 0.7 + low_vol.fillna(50) * 0.3)
        top_n = combined.nlargest(min(request.top_n, len(combined))).index.tolist()

        # Calculate turnover
        if prev_holdings:
            turnover = len(set(top_n) - prev_holdings) / len(top_n)
            turnovers.append(turnover)
        prev_holdings = set(top_n)

        # Hold period return (until next rebalance or end)
        next_date = rebalance_dates[i + 1] if i + 1 < len(rebalance_dates) else price_matrix.index.max()
        period_prices = price_matrix.loc[rebal_date:next_date, top_n]

        if len(period_prices) > 1 and not period_prices.empty:
            period_returns = period_prices.iloc[-1] / period_prices.iloc[0] - 1
            period_returns = period_returns.dropna()
            avg_return = period_returns.mean() if not period_returns.empty else 0

            # Apply transaction cost on turnover
            cost = (turnovers[-1] if turnovers else 0) * request.transaction_cost * 2
            portfolio_value *= (1 + avg_return - cost)

            bench_period = benchmark_prices.loc[rebal_date:next_date]
            if len(bench_period) > 1:
                bench_return = bench_period.iloc[-1] / bench_period.iloc[0] - 1
                benchmark_value *= (1 + bench_return)

            equity_curve.append(BacktestDataPoint(
                date=rebal_date.strftime("%Y-%m-%d"),
                portfolio_value=round(portfolio_value, 2),
                benchmark_value=round(benchmark_value, 2),
                active_return=round(avg_return - (bench_return if len(bench_period) > 1 else 0), 4),
            ))

    if not equity_curve:
        raise HTTPException(status_code=503, detail="Backtest produced no data points — check date range")

    # Compute final metrics
    values = pd.Series([p.portfolio_value for p in equity_curve])
    bench_values = pd.Series([p.benchmark_value for p in equity_curve])
    port_returns = values.pct_change().dropna()
    bench_returns = bench_values.pct_change().dropna()

    years = len(equity_curve) / (4 if rebal_freq == "QE" else 12 if rebal_freq == "ME" else 1)
    total_return = (values.iloc[-1] / 100 - 1) * 100
    ann_return = ((values.iloc[-1] / 100) ** (1 / max(years, 0.25)) - 1) * 100
    bench_total_return = (bench_values.iloc[-1] / 100 - 1) * 100

    metrics = BacktestMetrics(
        total_return=round(total_return, 2),
        annualised_return=round(ann_return, 2),
        benchmark_return=round(bench_total_return, 2),
        alpha=round(total_return - bench_total_return, 2),
        beta=round(PortfolioAnalytics.beta(port_returns, bench_returns), 2) if len(port_returns) > 3 else 1.0,
        sharpe_ratio=round(PortfolioAnalytics.sharpe_ratio(port_returns), 2) if len(port_returns) > 1 else 0,
        sortino_ratio=round(PortfolioAnalytics.sortino_ratio(port_returns), 2) if len(port_returns) > 1 else 0,
        max_drawdown=round(PortfolioAnalytics.max_drawdown(values) * 100, 2),
        calmar_ratio=round(PortfolioAnalytics.calmar_ratio(values), 2) if len(values) > 2 else 0,
        win_rate=round(float((port_returns > 0).mean() * 100), 1) if len(port_returns) > 0 else 0,
        avg_monthly_return=round(float(port_returns.mean() * 100), 2) if len(port_returns) > 0 else 0,
        volatility_ann=round(float(port_returns.std() * np.sqrt(4 if rebal_freq=='QE' else 12) * 100), 2) if len(port_returns) > 1 else 0,
    )

    # Per-rebalance period returns (period-over-period % change of the equity curve).
    monthly_returns = []
    for i in range(1, len(equity_curve)):
        prev_v = equity_curve[i - 1].portfolio_value
        cur_v = equity_curve[i].portfolio_value
        if prev_v:
            monthly_returns.append({
                "date": equity_curve[i].date,
                "return": round((cur_v / prev_v - 1) * 100, 2),
            })

    return BacktestResponse(
        request=request,
        metrics=metrics,
        equity_curve=equity_curve,
        monthly_returns=monthly_returns,
        top_holdings_last=[{"ticker": t} for t in list(prev_holdings)[:10]],
        turnover_avg=round(float(np.mean(turnovers)) * 100, 1) if turnovers else 0,
    )


@router.get("/strategies")
async def list_strategy_templates():
    """Pre-built strategy templates available for backtesting."""
    return {
        "templates": [
            {
                "name": "High Momentum",
                "description": "Top-decile 12-1 month price momentum, equal-weight, quarterly rebalance.",
                "factor_weights": {"momentum": 1.0},
            },
            {
                "name": "Quality Value",
                "description": "Intersection of top-quartile Quality and Value factors, semi-annual rebalance.",
                "factor_weights": {"quality": 0.5, "value": 0.5},
            },
            {
                "name": "Composite Multi-Factor",
                "description": "Blend of Momentum, Quality, Value, Growth, Low-Volatility, monthly rebalance.",
                "factor_weights": {"momentum": 0.25, "quality": 0.25, "value": 0.20, "growth": 0.20, "low_volatility": 0.10},
            },
            {
                "name": "Low Volatility Defensive",
                "description": "Bottom-quartile realised volatility, defensive tilt, quarterly rebalance.",
                "factor_weights": {"low_volatility": 1.0},
            },
        ]
    }

import pandas as pd
import numpy as np
from services.factor_engine import FactorEngine, PortfolioAnalytics

def test_factor_engine_momentum_computation():
    engine = FactorEngine()
    
    # Create fake prices for 10 stocks over 300 days
    dates = pd.date_range(start="2023-01-01", periods=300)
    tickers = ["AAPL", "MSFT", "GOOG", "AMZN", "META", "TSLA", "NFLX", "NVDA", "AMD", "INTC"]
    
    # Generate prices with upward trend for AAPL, downward for INTC
    data = {}
    for i, t in enumerate(tickers):
        trend = (i - 5) * 0.1  # Some positive, some negative
        data[t] = [100.0 + (trend * x) + np.random.normal(0, 2) for x in range(300)]
        
    prices = pd.DataFrame(data, index=dates)
    
    # AAPL (index 0) has negative trend, INTC (index 9) has positive trend
    mom_12_1 = engine.momentum_12_1(prices)
    assert len(mom_12_1) == 10
    
    mom_6_1 = engine.momentum_6_1(prices)
    assert len(mom_6_1) == 10

    # Test that compute_momentum_score returns rankings
    momentum_scores = engine.compute_momentum_score(prices)
    assert len(momentum_scores) == 10
    assert momentum_scores.min() >= 0
    assert momentum_scores.max() <= 100


# ── Regression tests for annualization fixes (period-aware risk metrics) ──

def _quarterly_returns():
    np.random.seed(1)
    return pd.Series(np.random.normal(0.03, 0.05, 12))


def test_sharpe_scales_with_periods():
    """Sharpe must scale by sqrt(periods); quarterly (4) != daily (252).
    Use risk_free=0 to isolate the pure annualization factor."""
    r = _quarterly_returns()
    s_q = PortfolioAnalytics.sharpe_ratio(r, risk_free=0.0, periods=4)
    s_d = PortfolioAnalytics.sharpe_ratio(r, risk_free=0.0, periods=252)
    assert abs(s_d / s_q - np.sqrt(252 / 4)) < 1e-6
    # With the real risk-free, the quarterly figure stays sane (not inflated ~8x)
    assert 0 < PortfolioAnalytics.sharpe_ratio(r, periods=4) < 2


def test_sharpe_guards_degenerate_input():
    assert PortfolioAnalytics.sharpe_ratio(pd.Series([0.01]), periods=4) == 0.0
    assert PortfolioAnalytics.sharpe_ratio(pd.Series([0.0, 0.0, 0.0]), periods=4) == 0.0


def test_calmar_periods_and_guard():
    vals = pd.Series([100, 110, 105, 120, 115, 130], dtype=float)
    c4 = PortfolioAnalytics.calmar_ratio(vals, periods=4)
    c252 = PortfolioAnalytics.calmar_ratio(vals, periods=252)
    assert c4 > 0 and c252 > c4  # higher annualization -> higher CAGR -> higher calmar
    assert PortfolioAnalytics.calmar_ratio(pd.Series([100.0]), periods=4) == 0.0


def test_sortino_only_penalises_downside():
    r = pd.Series([0.05, -0.02, 0.03, -0.04, 0.06])
    assert PortfolioAnalytics.sortino_ratio(r, periods=12) != 0.0
    # No downside -> 0 (cannot compute downside deviation)
    assert PortfolioAnalytics.sortino_ratio(pd.Series([0.01, 0.02, 0.03]), periods=12) == 0.0


def test_max_drawdown():
    vals = pd.Series([100, 120, 90, 110], dtype=float)
    assert abs(PortfolioAnalytics.max_drawdown(vals) - (-0.25)) < 1e-9


def test_rsi_wilder_edges():
    engine = FactorEngine()
    rising = pd.Series(np.arange(1, 40, dtype=float))
    assert engine.rsi(rising) == 100.0          # all gains
    assert engine.rsi(pd.Series([10.0] * 40)) == 50.0  # flat
    # Mixed series stays strictly within (0, 100)
    np.random.seed(2)
    mixed = pd.Series(100 + np.random.normal(0, 1, 60).cumsum())
    val = engine.rsi(mixed)
    assert 0 < val < 100

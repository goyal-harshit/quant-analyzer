"""
Quant correctness golden-master suite.

Every expected value here is computed by hand (shown in the comments) rather than
captured from the implementation, so these tests catch silent regressions in the
numbers users actually trade on — the audit's #2 priority.

Covers PortfolioAnalytics risk metrics, FactorEngine cross-sectional ranking /
helpers, and the single-stock compute_quant_factors pipeline.
"""

import numpy as np
import pandas as pd

from services.factor_engine import FactorEngine, PortfolioAnalytics
from services.fast_data import compute_quant_factors

TOL = 1e-4


# ── PortfolioAnalytics: risk metrics ──────────────────────────────

def test_sharpe_ratio_golden():
    # r=[.01,.02,.03,.04]: mean=.025, std(ddof=1)=0.01290994449,
    # ratio=1.93649167, *sqrt(252)=30.740852  (risk_free=0 isolates annualization)
    r = pd.Series([0.01, 0.02, 0.03, 0.04])
    val = PortfolioAnalytics.sharpe_ratio(r, risk_free=0.0, periods=252)
    assert abs(val - 30.740852) < 1e-4


def test_sharpe_scales_with_sqrt_periods():
    r = pd.Series([0.01, 0.02, 0.03, 0.04])
    s4 = PortfolioAnalytics.sharpe_ratio(r, risk_free=0.0, periods=4)
    s252 = PortfolioAnalytics.sharpe_ratio(r, risk_free=0.0, periods=252)
    assert abs(s252 / s4 - np.sqrt(252 / 4)) < TOL


def test_sharpe_degenerate_guards():
    assert PortfolioAnalytics.sharpe_ratio(pd.Series([0.01]), periods=252) == 0.0
    assert PortfolioAnalytics.sharpe_ratio(pd.Series([0.0, 0.0, 0.0]), periods=252) == 0.0


def test_sortino_ratio_golden():
    # r=[.05,-.02,.03,-.04,.06]: excess.mean()=.016 (rf=0).
    # downside=[-.02,-.04]: std(ddof=1)=0.01414214, *sqrt(12)=0.04898979.
    # sortino = .016*12/0.04898979 = 3.919184
    r = pd.Series([0.05, -0.02, 0.03, -0.04, 0.06])
    val = PortfolioAnalytics.sortino_ratio(r, risk_free=0.0, periods=12)
    assert abs(val - 3.919184) < 1e-4


def test_sortino_zero_without_downside():
    assert PortfolioAnalytics.sortino_ratio(pd.Series([0.01, 0.02, 0.03]), periods=12) == 0.0


def test_max_drawdown_golden():
    # peak=[100,120,120,120]; min dd = (90-120)/120 = -0.25
    vals = pd.Series([100, 120, 90, 110], dtype=float)
    assert abs(PortfolioAnalytics.max_drawdown(vals) - (-0.25)) < 1e-12


def test_calmar_ratio_golden():
    # vals=[100,110,105,120,115,130], periods=4, n=6:
    # CAGR=(130/100)^(4/6)-1=0.191139; maxDD=-0.0454545; calmar=4.20506
    vals = pd.Series([100, 110, 105, 120, 115, 130], dtype=float)
    val = PortfolioAnalytics.calmar_ratio(vals, periods=4)
    assert abs(val - 4.20506) < 1e-3


def test_calmar_guards_short_series():
    assert PortfolioAnalytics.calmar_ratio(pd.Series([100.0]), periods=4) == 0.0


def test_beta_golden():
    # portfolio = exactly 2x benchmark -> beta = cov(2b,b)/var(b) = 2.0
    bench = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02, 0.04, -0.03, 0.01, 0.02, -0.01, 0.03, 0.0])
    port = bench * 2.0
    assert abs(PortfolioAnalytics.beta(port, bench) - 2.0) < 1e-9


def test_beta_defaults_to_one_when_too_short():
    s = pd.Series([0.01, 0.02, 0.03])
    assert PortfolioAnalytics.beta(s, s) == 1.0


def test_alpha_zero_when_portfolio_equals_benchmark():
    # p=b -> beta=1; alpha = bench_ann - (0 + 1*(bench_ann-0)) = 0  (risk_free=0)
    b = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02, 0.04, -0.03, 0.01, 0.02, -0.01, 0.03, 0.0])
    assert abs(PortfolioAnalytics.alpha(b, b, risk_free=0.0)) < 1e-9


def test_information_ratio_golden():
    # same numbers as sharpe (no risk-free term): 30.740852
    active = pd.Series([0.01, 0.02, 0.03, 0.04])
    assert abs(PortfolioAnalytics.information_ratio(active) - 30.740852) < 1e-4


def test_var_and_cvar_golden():
    # sorted returns; np.percentile(.,5) linear: rank=0.45 between -0.10 and -0.05
    #   VaR = -0.10 + 0.45*0.05 = -0.0775
    #   CVaR = mean of returns <= VaR = mean([-0.10]) = -0.10
    r = pd.Series([-0.10, -0.05, -0.02, 0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06])
    var = PortfolioAnalytics.var_historical(r, confidence=0.95)
    assert abs(var - (-0.0775)) < 1e-9
    cvar = PortfolioAnalytics.cvar(r, confidence=0.95)
    assert abs(cvar - (-0.10)) < 1e-9


# ── FactorEngine: cross-sectional ranking & helpers ───────────────

def test_value_score_ranks_low_pe_highest():
    # -pe ranked pct: pe 10 -> highest value (100), 40 -> lowest (25)
    f = pd.DataFrame({"pe_ratio": [10.0, 20.0, 30.0, 40.0]}, index=["A", "B", "C", "D"])
    v = FactorEngine().compute_value_score(f)
    assert abs(v["A"] - 100.0) < TOL
    assert abs(v["B"] - 75.0) < TOL
    assert abs(v["C"] - 50.0) < TOL
    assert abs(v["D"] - 25.0) < TOL


def test_quality_score_ranks_high_roe_highest():
    f = pd.DataFrame({"roe": [10.0, 20.0, 30.0]}, index=["A", "B", "C"])
    q = FactorEngine().compute_quality_score(f)
    assert abs(q["A"] - (1 / 3 * 100)) < 1e-6
    assert abs(q["B"] - (2 / 3 * 100)) < 1e-6
    assert abs(q["C"] - 100.0) < 1e-6


def test_rank_is_percentile_0_to_100():
    s = pd.Series([5.0, 1.0, 3.0, 9.0])
    r = FactorEngine._rank(s)
    assert r.min() == 25.0 and r.max() == 100.0


def test_z_score_guards_constant_series():
    # std==0 must not divide-by-zero; returns all-zero deviations
    z = FactorEngine.z_score(pd.Series([5.0, 5.0, 5.0]))
    assert (z.abs() < 1e-12).all()


def test_winsorise_clips_to_quantiles():
    s = pd.Series(np.arange(0, 101, dtype=float))  # 0..100
    w = FactorEngine.winsorise(s, pct=0.05)
    assert w.max() == 95.0  # quantile(0.95)
    assert w.min() == 5.0   # quantile(0.05)


def test_rsi_edges():
    eng = FactorEngine()
    assert eng.rsi(pd.Series(np.arange(1.0, 40.0))) == 100.0   # all gains
    assert eng.rsi(pd.Series([10.0] * 40)) == 50.0             # flat
    np.random.seed(3)
    mixed = pd.Series(100 + np.random.normal(0, 1, 60).cumsum())
    assert 0 < eng.rsi(mixed) < 100


def test_max_drawdown_zero_for_monotonic_increase():
    assert PortfolioAnalytics.max_drawdown(pd.Series([1.0, 2.0, 3.0, 4.0])) == 0.0


# ── compute_quant_factors: single-stock pipeline ──────────────────

def _linear_history(n=260):
    # close[i] = 100 + i ; deterministic, monotonically rising
    idx = pd.date_range("2023-01-01", periods=n)
    close = pd.Series([100.0 + i for i in range(n)], index=idx)
    return pd.DataFrame({"open": close, "high": close, "low": close,
                         "close": close, "volume": [1000] * n}, index=idx)


def test_compute_quant_factors_momentum_golden():
    # momentum_12_1 = (close[-22]/close[-252]-1)*100
    # n=260 -> close[-22]=row238=338, close[-252]=row8=108 -> (338/108-1)*100=212.96
    df = _linear_history(260)
    factors = compute_quant_factors(df, fundamentals={})
    assert abs(factors["momentum_12_1"] - 212.96) < 0.01
    # rising series -> RSI saturates near 100
    assert factors["rsi_14"] > 99.0
    # golden cross present (sma50 > sma200) on a monotone uptrend
    assert factors["golden_cross"] is True


def test_compute_quant_factors_value_and_quality_from_fundamentals():
    df = _linear_history(60)
    # PE exactly 10 -> value component 100-(10-10)*2 = 100
    # ROE 40 -> quality component min(100, 40*2.5) = 100
    factors = compute_quant_factors(df, {"pe_ratio": 10.0, "roe": 40.0})
    assert abs(factors["value_score"] - 100.0) < TOL
    assert abs(factors["quality_score"] - 100.0) < TOL


def test_compute_quant_factors_empty_when_no_signal():
    # Too-short history and no fundamentals -> composite cannot be formed.
    df = _linear_history(5)
    factors = compute_quant_factors(df, fundamentals={})
    assert factors["composite_score"] is None

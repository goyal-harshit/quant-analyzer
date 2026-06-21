"""
Factor Engine — Quantitative Factor Computation
Computes Momentum, Quality, Value, Growth, Size, Low-Volatility scores
for the NSE/BSE universe using academic-grade methodologies.
"""

import numpy as np
import pandas as pd
from typing import Optional
from scipy import stats
import logging

logger = logging.getLogger(__name__)


# ── FACTOR WEIGHTS (default composite) ───────────────────────────
DEFAULT_WEIGHTS = {
    "momentum":      0.25,
    "quality":       0.25,
    "value":         0.20,
    "growth":        0.20,
    "low_volatility": 0.10,
}


class FactorEngine:
    """
    Computes factor scores for a universe of stocks.
    All scores are cross-sectional percentile ranks (0-100).
    """

    def __init__(self, universe: str = "NIFTY500"):
        self.universe = universe
        self.logger = logging.getLogger(__name__)

    # ── MOMENTUM FACTORS ─────────────────────────────────────────
    def momentum_12_1(self, prices: pd.DataFrame) -> pd.Series:
        """
        12-minus-1 month momentum (Jegadeesh & Titman 1993).
        Returns: cumulative return from t-252 to t-21 trading days.
        Skips last month to avoid short-term reversal.
        """
        if len(prices) < 252:
            return pd.Series(dtype=float)
        ret = (prices.iloc[-21] / prices.iloc[-252]) - 1
        return ret.fillna(0)

    def momentum_6_1(self, prices: pd.DataFrame) -> pd.Series:
        """6-minus-1 month momentum."""
        if len(prices) < 126:
            return pd.Series(dtype=float)
        return ((prices.iloc[-21] / prices.iloc[-126]) - 1).fillna(0)

    def momentum_3_1(self, prices: pd.DataFrame) -> pd.Series:
        """3-minus-1 month momentum."""
        if len(prices) < 63:
            return pd.Series(dtype=float)
        return ((prices.iloc[-21] / prices.iloc[-63]) - 1).fillna(0)

    def compute_momentum_score(
        self,
        prices: pd.DataFrame,
        weights: dict = {"12_1": 0.60, "6_1": 0.25, "3_1": 0.15}
    ) -> pd.Series:
        """
        Composite momentum score = weighted combination of time-period signals.
        Each component is ranked cross-sectionally then combined.
        """
        scores = pd.DataFrame()
        if len(prices) >= 252:
            scores["12_1"] = self._rank(self.momentum_12_1(prices))
        if len(prices) >= 126:
            scores["6_1"] = self._rank(self.momentum_6_1(prices))
        if len(prices) >= 63:
            scores["3_1"] = self._rank(self.momentum_3_1(prices))

        if scores.empty:
            return pd.Series(dtype=float)

        composite = sum(
            scores[k] * weights[k]
            for k in weights
            if k in scores.columns
        ) / sum(weights[k] for k in weights if k in scores.columns)
        return composite.clip(0, 100)

    # ── QUALITY FACTORS ──────────────────────────────────────────
    def compute_quality_score(self, fundamentals: pd.DataFrame) -> pd.Series:
        """
        Quality = f(ROE, Gross Profitability, Accruals, Debt/Equity, Interest Coverage)
        Based on Novy-Marx (2013) gross profitability and Piotroski F-Score framework.
        """
        scores = pd.DataFrame(index=fundamentals.index)

        # ROE component (higher = better quality)
        if "roe" in fundamentals.columns:
            scores["roe"] = self._rank(fundamentals["roe"].clip(-50, 150))

        # Gross profitability (higher = better)
        if "gross_margin" in fundamentals.columns:
            scores["gross_margin"] = self._rank(fundamentals["gross_margin"].clip(0, 100))

        # EBITDA margin
        if "ebitda_margin" in fundamentals.columns:
            scores["ebitda_margin"] = self._rank(fundamentals["ebitda_margin"].clip(0, 60))

        # Accruals (lower = better — signals earnings quality)
        if "accruals_ratio" in fundamentals.columns:
            scores["accruals"] = self._rank(-fundamentals["accruals_ratio"])

        # Debt/Equity (lower = better quality)
        if "debt_equity" in fundamentals.columns:
            scores["leverage"] = self._rank(-fundamentals["debt_equity"].clip(0, 20))

        # Interest coverage (higher = better)
        if "interest_coverage" in fundamentals.columns:
            scores["interest_cov"] = self._rank(
                fundamentals["interest_coverage"].clip(0, 50)
            )

        if scores.empty:
            return pd.Series(dtype=float)

        return scores.mean(axis=1).clip(0, 100)

    # ── VALUE FACTORS ────────────────────────────────────────────
    def compute_value_score(self, fundamentals: pd.DataFrame) -> pd.Series:
        """
        Value = f(EV/EBITDA, P/B, P/E, FCF Yield, Dividend Yield)
        Lower multiples = higher value score.
        Composite of inverse-ranked multiples.
        """
        scores = pd.DataFrame(index=fundamentals.index)

        if "pe_ratio" in fundamentals.columns:
            # Inverse — low PE = high value
            pe_clipped = fundamentals["pe_ratio"].clip(3, 100)
            scores["pe"] = self._rank(-pe_clipped)

        if "pb_ratio" in fundamentals.columns:
            pb_clipped = fundamentals["pb_ratio"].clip(0.2, 30)
            scores["pb"] = self._rank(-pb_clipped)

        if "ev_ebitda" in fundamentals.columns:
            ev_clipped = fundamentals["ev_ebitda"].clip(2, 50)
            scores["ev_ebitda"] = self._rank(-ev_clipped)

        if "fcf_yield" in fundamentals.columns:
            # Higher FCF yield = more value
            scores["fcf_yield"] = self._rank(fundamentals["fcf_yield"])

        if "ps_ratio" in fundamentals.columns:
            scores["ps"] = self._rank(-fundamentals["ps_ratio"].clip(0.2, 20))

        if scores.empty:
            return pd.Series(dtype=float)

        return scores.mean(axis=1).clip(0, 100)

    # ── GROWTH FACTORS ───────────────────────────────────────────
    def compute_growth_score(self, fundamentals: pd.DataFrame) -> pd.Series:
        """
        Growth = f(Revenue Growth, EPS Growth, Operating Profit Growth, Guidance Trend)
        """
        scores = pd.DataFrame(index=fundamentals.index)

        if "revenue_growth" in fundamentals.columns:
            scores["rev_growth"] = self._rank(
                fundamentals["revenue_growth"].clip(-30, 80)
            )

        if "eps_growth" in fundamentals.columns:
            scores["eps_growth"] = self._rank(
                fundamentals["eps_growth"].clip(-50, 100)
            )

        if "operating_profit_growth" in fundamentals.columns:
            scores["op_growth"] = self._rank(
                fundamentals["operating_profit_growth"].clip(-30, 80)
            )

        if scores.empty:
            return pd.Series(dtype=float)

        return scores.mean(axis=1).clip(0, 100)

    # ── LOW VOLATILITY FACTOR ────────────────────────────────────
    def compute_low_vol_score(self, prices: pd.DataFrame, window: int = 60) -> pd.Series:
        """
        Low Volatility anomaly (Ang et al. 2006, Baker et al. 2011).
        Lower realised volatility = higher score.
        Uses 60-day rolling annualised std deviation.
        """
        if len(prices) < window:
            return pd.Series(dtype=float)

        daily_rets = prices.pct_change().dropna()
        vol = daily_rets.tail(window).std() * np.sqrt(252)
        # Inverse rank — low vol stocks get high scores
        return self._rank(-vol).clip(0, 100)

    # ── SIZE FACTOR ──────────────────────────────────────────────
    def compute_size_score(self, market_caps: pd.Series) -> pd.Series:
        """
        Small-cap premium (Fama-French 1993).
        Note: In Indian context, size factor is weaker.
        Lower market cap = higher size score (small-cap tilt).
        """
        return self._rank(-market_caps.clip(0)).clip(0, 100)

    # ── COMPOSITE SCORE ──────────────────────────────────────────
    def compute_composite(
        self,
        momentum: pd.Series,
        quality: pd.Series,
        value: pd.Series,
        growth: pd.Series,
        low_volatility: pd.Series,
        weights: dict = DEFAULT_WEIGHTS,
    ) -> pd.Series:
        """
        Composite multi-factor score.
        Each factor is first normalised to percentile, then combined.
        """
        factors = pd.DataFrame({
            "momentum":      momentum,
            "quality":       quality,
            "value":         value,
            "growth":        growth,
            "low_volatility": low_volatility,
        })

        composite = pd.Series(0.0, index=factors.index)
        total_weight = 0.0

        for factor, weight in weights.items():
            if factor in factors.columns:
                col = factors[factor].dropna()
                if not col.empty:
                    composite[col.index] += col * weight
                    total_weight += weight

        if total_weight > 0:
            composite = composite / total_weight

        return composite.clip(0, 100)

    # ── PIOTROSKI F-SCORE ────────────────────────────────────────
    def piotroski_f_score(self, fundamentals: pd.DataFrame) -> pd.Series:
        """
        Piotroski F-Score (9-point fundamental strength checklist).
        Score 0-9: 0-2 weak, 3-6 neutral, 7-9 strong.
        """
        f = pd.Series(0, index=fundamentals.index)

        # Profitability signals
        if "roa" in fundamentals.columns:
            f += (fundamentals["roa"] > 0).astype(int)
        if "operating_cf" in fundamentals.columns:
            f += (fundamentals["operating_cf"] > 0).astype(int)
        if "roa_change" in fundamentals.columns:
            f += (fundamentals["roa_change"] > 0).astype(int)
        if "cf_to_assets" in fundamentals.columns and "roa" in fundamentals.columns:
            f += (fundamentals["cf_to_assets"] > fundamentals["roa"]).astype(int)

        # Leverage / liquidity signals
        if "debt_equity_change" in fundamentals.columns:
            f += (fundamentals["debt_equity_change"] < 0).astype(int)
        if "current_ratio_change" in fundamentals.columns:
            f += (fundamentals["current_ratio_change"] > 0).astype(int)
        if "shares_diluted" in fundamentals.columns:
            f += (fundamentals["shares_diluted"] == 0).astype(int)

        # Operating efficiency signals
        if "gross_margin_change" in fundamentals.columns:
            f += (fundamentals["gross_margin_change"] > 0).astype(int)
        if "asset_turnover_change" in fundamentals.columns:
            f += (fundamentals["asset_turnover_change"] > 0).astype(int)

        return f.clip(0, 9)

    # ── TECHNICAL INDICATORS ─────────────────────────────────────
    def rsi(self, prices: pd.Series, window: int = 14) -> float:
        """Relative Strength Index."""
        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(window).mean()
        loss = (-delta.clip(upper=0)).rolling(window).mean()
        rs = gain / loss.replace(0, np.nan)
        return float(100 - 100 / (1 + rs.iloc[-1]))

    def moving_average(self, prices: pd.Series, window: int) -> pd.Series:
        return prices.rolling(window).mean()

    def bollinger_bands(self, prices: pd.Series, window: int = 20, std: float = 2):
        ma = prices.rolling(window).mean()
        std_dev = prices.rolling(window).std()
        return {
            "upper": ma + std * std_dev,
            "middle": ma,
            "lower": ma - std * std_dev,
        }

    def atr(self, high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
        """Average True Range — volatility measure for position sizing."""
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low  - close.shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(window).mean()

    # ── HELPERS ──────────────────────────────────────────────────
    @staticmethod
    def _rank(series: pd.Series) -> pd.Series:
        """Cross-sectional percentile rank (0-100). Handles NaN gracefully."""
        return series.rank(pct=True, na_option="keep") * 100

    @staticmethod
    def winsorise(series: pd.Series, pct: float = 0.01) -> pd.Series:
        """Winsorise extremes to reduce outlier impact."""
        lo = series.quantile(pct)
        hi = series.quantile(1 - pct)
        return series.clip(lo, hi)

    @staticmethod
    def z_score(series: pd.Series) -> pd.Series:
        """Cross-sectional z-score normalisation."""
        std = series.std()
        # std() returns a scalar; guard against zero/NaN division (the old
        # `.replace(0, 1)` was a no-op on a float and didn't prevent div-by-zero).
        if not std or pd.isna(std) or std < 1e-10:
            std = 1.0
        return (series - series.mean()) / std


# ── PORTFOLIO ANALYTICS ───────────────────────────────────────────
class PortfolioAnalytics:

    @staticmethod
    def compute_returns(portfolio_values: pd.Series) -> pd.Series:
        return portfolio_values.pct_change().dropna()

    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free: float = 0.065) -> float:
        """Annualised Sharpe. India 10Y Gsec ≈ 6.5%."""
        excess = returns - risk_free / 252
        return float((excess.mean() / returns.std()) * np.sqrt(252)) if returns.std() > 0 else 0.0

    @staticmethod
    def sortino_ratio(returns: pd.Series, risk_free: float = 0.065) -> float:
        """Sortino ratio — only penalises downside volatility."""
        excess = returns - risk_free / 252
        downside_std = returns[returns < 0].std() * np.sqrt(252)
        return float(excess.mean() * 252 / downside_std) if downside_std > 0 else 0.0

    @staticmethod
    def max_drawdown(values: pd.Series) -> float:
        peak = values.cummax()
        drawdown = (values - peak) / peak
        return float(drawdown.min())

    @staticmethod
    def calmar_ratio(values: pd.Series) -> float:
        returns = values.pct_change().dropna()
        cagr = (values.iloc[-1] / values.iloc[0]) ** (252 / len(values)) - 1
        mdd = abs(PortfolioAnalytics.max_drawdown(values))
        return float(cagr / mdd) if mdd > 0 else 0.0

    @staticmethod
    def beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
        aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < 10:
            return 1.0
        cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
        return float(cov[0, 1] / cov[1, 1]) if cov[1, 1] > 0 else 1.0

    @staticmethod
    def alpha(portfolio_returns: pd.Series, benchmark_returns: pd.Series, risk_free: float = 0.065) -> float:
        b = PortfolioAnalytics.beta(portfolio_returns, benchmark_returns)
        port_ann = portfolio_returns.mean() * 252
        bench_ann = benchmark_returns.mean() * 252
        return float(port_ann - (risk_free + b * (bench_ann - risk_free)))

    @staticmethod
    def information_ratio(active_returns: pd.Series) -> float:
        if active_returns.std() == 0:
            return 0.0
        return float(active_returns.mean() / active_returns.std() * np.sqrt(252))

    @staticmethod
    def var_historical(returns: pd.Series, confidence: float = 0.95) -> float:
        """Historical Value at Risk."""
        return float(np.percentile(returns, (1 - confidence) * 100))

    @staticmethod
    def cvar(returns: pd.Series, confidence: float = 0.95) -> float:
        """Conditional VaR (Expected Shortfall)."""
        var = PortfolioAnalytics.var_historical(returns, confidence)
        return float(returns[returns <= var].mean())

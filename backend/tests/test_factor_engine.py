import pytest
import pandas as pd
import numpy as np
from services.factor_engine import FactorEngine

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

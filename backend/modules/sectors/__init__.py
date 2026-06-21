"""Sector analytics module — aggregate the NSE universe into sector tiles.

Reuses get_universe_overview (per-stock sector/change/composite/momentum) and
get_sector_performance (1d/1w/1m) plus fundamentals for avg P/E and ROE, so the
heatmap and sector cards stay consistent with the dashboard and screener.
"""

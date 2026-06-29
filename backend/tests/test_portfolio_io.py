"""Unit tests for the Phase C portfolio file I/O (parse + export + tax helper).

Pure functions only — no DB / async, so these run in any environment.
"""

import io
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from services.portfolio_io import (
    parse_positions,
    positions_to_csv,
    positions_to_xlsx,
    rows_to_csv,
    portfolio_to_pdf,
    build_tax_report,
)


# ── Import / parse ──────────────────────────────────────────────────────────

def test_parse_basic_csv():
    csv = b"ticker,quantity,avg_cost\nTCS,10,3500\nINFY,5,1500\n"
    res = parse_positions(csv, "holdings.csv")
    assert res.ok
    assert {p.ticker for p in res.positions} == {"TCS", "INFY"}
    tcs = next(p for p in res.positions if p.ticker == "TCS")
    assert tcs.quantity == 10 and tcs.avg_cost == 3500


def test_parse_aliased_headers_and_currency_symbols():
    # broker-style headers + ₹ symbols + thousands separators
    csv = 'Symbol,Qty,Buy Price\nRELIANCE,2,"₹ 2,450.50"\n'.encode("utf-8")
    res = parse_positions(csv, "broker.csv")
    assert res.ok
    p = res.positions[0]
    assert p.ticker == "RELIANCE"
    assert p.quantity == 2
    assert p.avg_cost == 2450.50


def test_parse_merges_duplicate_tickers_weighted():
    csv = b"ticker,qty,price\nTCS,10,100\nTCS,10,200\n"
    res = parse_positions(csv, "x.csv")
    assert len(res.positions) == 1
    p = res.positions[0]
    assert p.quantity == 20
    assert p.avg_cost == 150  # weighted average of 100 and 200


def test_parse_skips_invalid_rows_but_keeps_valid():
    csv = b"ticker,quantity,avg_cost\nTCS,10,3500\nBAD,-3,100\n,5,50\nINFY,abc,1500\n"
    res = parse_positions(csv, "x.csv")
    assert {p.ticker for p in res.positions} == {"TCS"}
    assert res.skipped >= 2
    assert any("BAD" in e for e in res.errors)


def test_parse_missing_required_column_reports_error():
    csv = b"ticker,quantity\nTCS,10\n"
    res = parse_positions(csv, "x.csv")
    assert not res.ok
    assert any("avg_cost" in e for e in res.errors)


def test_parse_excel_roundtrip():
    df = pd.DataFrame({"Ticker": ["HDFCBANK"], "Shares": [7], "Average Cost": [1600]})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    res = parse_positions(buf.getvalue(), "holdings.xlsx")
    assert res.ok
    assert res.positions[0].ticker == "HDFCBANK"
    assert res.positions[0].quantity == 7
    assert res.positions[0].avg_cost == 1600


def test_parse_empty_file():
    res = parse_positions(b"", "empty.csv")
    assert not res.ok
    assert res.errors


# ── Export ──────────────────────────────────────────────────────────────────

_SAMPLE = [
    {"ticker": "TCS", "quantity": 10, "avg_cost": 3500, "current_price": 3800,
     "current_value": 38000, "cost_basis": 35000, "pnl": 3000, "pnl_pct": 8.57, "sector": "IT"},
]


def test_positions_to_csv_has_header_and_data():
    out = positions_to_csv(_SAMPLE).decode("utf-8")
    assert "Ticker" in out and "TCS" in out
    assert "3500" in out


def test_positions_to_xlsx_is_valid_workbook():
    data = positions_to_xlsx(_SAMPLE, sheet_name="My Port:folio*")  # illegal chars stripped
    assert data[:2] == b"PK"  # xlsx is a zip
    back = pd.read_excel(io.BytesIO(data))
    assert "TCS" in back["Ticker"].values


def test_rows_to_csv_generic():
    out = rows_to_csv([{"a": 1, "b": 2}]).decode("utf-8")
    assert "a,b" in out and "1,2" in out
    assert rows_to_csv([]) == b""


def test_portfolio_to_pdf_produces_pdf():
    portfolio = {
        "name": "Growth", "currency": "INR",
        "total_value": 38000, "total_cost": 35000, "total_pnl": 3000, "total_pnl_pct": 8.57,
        "sharpe": 1.2, "positions": _SAMPLE,
    }
    pdf = portfolio_to_pdf(portfolio)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 800


def test_portfolio_to_pdf_empty_positions():
    pdf = portfolio_to_pdf({"name": "Empty", "positions": []})
    assert pdf[:5] == b"%PDF-"


# ── Tax helper ──────────────────────────────────────────────────────────────

def test_tax_report_classifies_long_and_short():
    now = datetime(2026, 6, 29, tzinfo=timezone.utc)
    positions = [
        {"ticker": "TCS", "quantity": 10, "avg_cost": 100, "current_price": 150,
         "date_added": (now - timedelta(days=400)).isoformat()},   # long term
        {"ticker": "INFY", "quantity": 10, "avg_cost": 100, "current_price": 90,
         "date_added": (now - timedelta(days=100)).isoformat()},   # short term, loss
    ]
    rep = build_tax_report(positions, as_of=now)
    assert rep["long_term"]["positions"] == 1
    assert rep["long_term"]["unrealized_gain"] == 500   # (150-100)*10
    assert rep["short_term"]["positions"] == 1
    assert rep["short_term"]["unrealized_gain"] == -100  # (90-100)*10
    assert rep["total_unrealized_gain"] == 400


def test_tax_report_holding_days_direct_and_missing_date():
    now = datetime(2026, 6, 29, tzinfo=timezone.utc)
    positions = [
        {"ticker": "A", "quantity": 1, "avg_cost": 10, "current_price": 20, "holding_days": 500},
        {"ticker": "B", "quantity": 1, "avg_cost": 10, "current_price": 20},  # no date → short
    ]
    rep = build_tax_report(positions, as_of=now)
    assert rep["long_term"]["positions"] == 1
    assert rep["short_term"]["positions"] == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

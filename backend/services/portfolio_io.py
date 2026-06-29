"""Portfolio file I/O — import (broker CSV/Excel → positions) and export
(CSV / Excel / PDF) for portfolios, screener results, and a capital-gains tax helper.

Phase C of PROJECT_MASTER_PLAN. Everything here is **pure** (bytes in → bytes /
dataclasses out) with no DB or network access, so it is fully unit-testable
without the async-SQLAlchemy stack. The router layer wires these into endpoints.

All dependencies are free / open-source: pandas (parse), openpyxl (xlsx),
reportlab (pdf).
"""

from __future__ import annotations

import io
import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

# ── Column aliasing ─────────────────────────────────────────────────────────
# Broker statements use wildly inconsistent headers. Map a normalized key to the
# set of header spellings we accept (compared case-insensitively, stripped of
# spaces/underscores/punctuation).
_ALIASES: dict[str, set[str]] = {
    "ticker": {
        "ticker", "symbol", "scrip", "scripname", "stock", "instrument",
        "tradingsymbol", "name", "security", "isin",
    },
    "quantity": {"quantity", "qty", "units", "shares", "holdings", "noofshares", "balance"},
    "avg_cost": {
        "avgcost", "avgprice", "averageprice", "averagecost", "buyprice",
        "price", "cost", "avg", "buyavg", "costprice", "purchaseprice",
    },
    "notes": {"notes", "note", "remark", "remarks", "comment"},
}

_MAX_ROWS = 5000  # guardrail against absurd uploads


def _norm_header(h: object) -> str:
    return "".join(ch for ch in str(h).strip().lower() if ch.isalnum())


def _build_column_map(columns: list[object]) -> dict[str, str]:
    """Return {normalized_key: original_column} for the columns we recognise."""
    resolved: dict[str, str] = {}
    for col in columns:
        key = _norm_header(col)
        for target, spellings in _ALIASES.items():
            if target in resolved:
                continue
            if key in spellings:
                resolved[target] = col
                break
    return resolved


def _to_float(value: object) -> float | None:
    """Parse a number that may carry currency symbols, commas, or be blank."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        return None if pd.isna(f) else f
    s = str(value).strip()
    if not s:
        return None
    # strip currency symbols / thousands separators / stray spaces
    cleaned = (
        s.replace(",", "")
        .replace("₹", "")  # ₹
        .replace("Rs.", "")
        .replace("Rs", "")
        .replace("$", "")
        .strip()
    )
    try:
        return float(cleaned)
    except ValueError:
        return None


@dataclass
class ParsedPosition:
    ticker: str
    quantity: float
    avg_cost: float
    notes: str | None = None


@dataclass
class ImportResult:
    positions: list[ParsedPosition] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # human-readable, row-scoped
    skipped: int = 0

    @property
    def ok(self) -> bool:
        return bool(self.positions)


def _read_dataframe(content: bytes, filename: str) -> pd.DataFrame:
    """Load CSV or Excel bytes into a DataFrame, dtype=object (we coerce later)."""
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xlsm", ".xls")):
        return pd.read_excel(io.BytesIO(content), dtype=object)
    # default to CSV; sniff the delimiter so tab/semicolon exports also work
    text = content.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        sep = dialect.delimiter
    except csv.Error:
        sep = ","
    # index_col=False keeps the first column as data even when a trailing
    # unquoted field sneaks in; skipinitialspace tolerates ", " separators.
    return pd.read_csv(
        io.StringIO(text), sep=sep, dtype=object,
        index_col=False, skipinitialspace=True,
    )


def parse_positions(content: bytes, filename: str = "") -> ImportResult:
    """Parse a broker CSV/Excel file into normalized positions.

    - flexible header matching (see `_ALIASES`)
    - currency-symbol / comma tolerant number parsing
    - rows missing ticker/quantity/avg_cost are reported and skipped, never fatal
    - duplicate tickers are merged (quantity summed, cost = weighted average)
    """
    result = ImportResult()
    try:
        df = _read_dataframe(content, filename)
    except Exception as exc:  # noqa: BLE001 — surface any parser failure to the user
        result.errors.append(f"Could not read file: {exc}")
        return result

    if df.empty:
        result.errors.append("File contains no data rows.")
        return result

    colmap = _build_column_map(list(df.columns))
    missing = [c for c in ("ticker", "quantity", "avg_cost") if c not in colmap]
    if missing:
        result.errors.append(
            "Missing required column(s): "
            + ", ".join(missing)
            + f". Found headers: {', '.join(str(c) for c in df.columns)}"
        )
        return result

    if len(df) > _MAX_ROWS:
        result.errors.append(f"File has {len(df)} rows; limit is {_MAX_ROWS}.")
        return result

    merged: dict[str, ParsedPosition] = {}
    for pos, (_, row) in enumerate(df.iterrows()):
        rownum = pos + 2  # +1 for 0-index, +1 for header → spreadsheet row number
        raw_ticker = row.get(colmap["ticker"])
        ticker = ("" if raw_ticker is None else str(raw_ticker)).strip().upper()
        if not ticker or ticker == "NAN":
            result.skipped += 1
            continue
        # An ISIN-only column still gives us *a* symbol; keep alphanumerics + dots.
        ticker = "".join(ch for ch in ticker if ch.isalnum() or ch in ".-&")

        qty = _to_float(row.get(colmap["quantity"]))
        cost = _to_float(row.get(colmap["avg_cost"]))
        if qty is None or qty <= 0:
            result.errors.append(f"Row {rownum} ({ticker}): invalid quantity — skipped.")
            result.skipped += 1
            continue
        if cost is None or cost <= 0:
            result.errors.append(f"Row {rownum} ({ticker}): invalid avg cost — skipped.")
            result.skipped += 1
            continue

        notes = None
        if "notes" in colmap:
            nv = row.get(colmap["notes"])
            notes = None if nv is None or str(nv).strip().lower() in ("", "nan") else str(nv).strip()

        if ticker in merged:
            ex = merged[ticker]
            total_qty = ex.quantity + qty
            ex.avg_cost = round((ex.avg_cost * ex.quantity + cost * qty) / total_qty, 4)
            ex.quantity = total_qty
        else:
            merged[ticker] = ParsedPosition(ticker=ticker, quantity=qty, avg_cost=cost, notes=notes)

    result.positions = list(merged.values())
    if not result.positions and not result.errors:
        result.errors.append("No valid positions found in file.")
    return result


# ── Export builders ─────────────────────────────────────────────────────────

def _positions_records(positions: list[dict]) -> list[dict]:
    """Normalize a list of position dicts (from the API/DB) into export rows."""
    rows = []
    for p in positions:
        rows.append(
            {
                "Ticker": p.get("ticker"),
                "Quantity": p.get("quantity"),
                "Avg Cost": p.get("avg_cost"),
                "Current Price": p.get("current_price"),
                "Current Value": p.get("current_value"),
                "Cost Basis": p.get("cost_basis"),
                "P&L": p.get("pnl"),
                "P&L %": p.get("pnl_pct"),
                "Sector": p.get("sector"),
            }
        )
    return rows


def positions_to_csv(positions: list[dict]) -> bytes:
    df = pd.DataFrame(_positions_records(positions))
    return df.to_csv(index=False).encode("utf-8")


def positions_to_xlsx(positions: list[dict], sheet_name: str = "Positions") -> bytes:
    df = pd.DataFrame(_positions_records(positions))
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Excel caps sheet names at 31 chars and forbids a few characters.
        safe = "".join(c for c in sheet_name if c not in r"[]:*?/\\")[:31] or "Sheet1"
        df.to_excel(writer, index=False, sheet_name=safe)
    return buf.getvalue()


def rows_to_csv(rows: list[dict]) -> bytes:
    """Generic CSV export for any list of flat dicts (e.g. screener results)."""
    if not rows:
        return b""
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")


def portfolio_to_pdf(portfolio: dict) -> bytes:
    """Render a one-page portfolio report PDF (holdings + summary metrics)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Portfolio Report — {portfolio.get('name', '')}",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Portfolio Report — {portfolio.get('name', 'Untitled')}", styles["Title"]))
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Generated {generated}", styles["Normal"]))
    story.append(Spacer(1, 8 * mm))

    cur = portfolio.get("currency", "INR")
    summary = [
        ["Total Value", f"{cur} {portfolio.get('total_value', 0):,.2f}"],
        ["Total Cost", f"{cur} {portfolio.get('total_cost', 0):,.2f}"],
        ["Total P&L", f"{cur} {portfolio.get('total_pnl', 0):,.2f}"],
        ["Total P&L %", f"{portfolio.get('total_pnl_pct', 0):,.2f}%"],
    ]
    for label, key in (("Beta", "beta"), ("Sharpe", "sharpe"),
                       ("Volatility %", "volatility"), ("Max Drawdown %", "max_drawdown")):
        v = portfolio.get(key)
        if v is not None:
            summary.append([label, f"{v}"])
    st = Table(summary, colWidths=[60 * mm, 60 * mm])
    st.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(st)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Holdings", styles["Heading2"]))
    header = ["Ticker", "Qty", "Avg Cost", "Price", "Value", "P&L", "P&L %"]
    data = [header]
    for p in portfolio.get("positions", []):
        data.append([
            str(p.get("ticker", "")),
            f"{p.get('quantity', 0):g}",
            f"{p.get('avg_cost', 0):,.2f}",
            f"{(p.get('current_price') or 0):,.2f}",
            f"{(p.get('current_value') or 0):,.2f}",
            f"{(p.get('pnl') or 0):,.2f}",
            f"{(p.get('pnl_pct') or 0):,.2f}%",
        ])
    if len(data) == 1:
        data.append(["—"] * len(header))
    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tbl)

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Generated by QuantAI. For analysis only — not investment advice.",
        styles["Italic"],
    ))
    doc.build(story)
    return buf.getvalue()


# ── Tax helper (Indian equity capital gains) ────────────────────────────────
# Equity/equity-MF holdings: gains on units held > 12 months are Long-Term,
# else Short-Term. We classify *unrealized* gains on current holdings by holding
# period — a planning aid, not a filed computation.

_LTCG_THRESHOLD_DAYS = 365


@dataclass
class TaxLot:
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    holding_days: int
    term: str            # "LONG" | "SHORT"
    cost_basis: float
    market_value: float
    unrealized_gain: float


def build_tax_report(positions: list[dict], as_of: datetime | None = None) -> dict:
    """Classify current holdings into long/short term unrealized gains.

    `positions` items need: ticker, quantity, avg_cost, current_price, and either
    `date_added` (datetime or ISO str) or `holding_days` (int). Missing dates →
    treated as short-term (conservative).
    """
    now = as_of or datetime.now(timezone.utc)
    lots: list[TaxLot] = []
    for p in positions:
        qty = float(p.get("quantity") or 0)
        avg = float(p.get("avg_cost") or 0)
        price = float(p.get("current_price") or avg)
        days = p.get("holding_days")
        if days is None:
            da = p.get("date_added")
            if isinstance(da, str):
                try:
                    da = datetime.fromisoformat(da.replace("Z", "+00:00"))
                except ValueError:
                    da = None
            if isinstance(da, datetime):
                if da.tzinfo is None:
                    da = da.replace(tzinfo=timezone.utc)
                days = (now - da).days
            else:
                days = 0
        days = int(days)
        term = "LONG" if days > _LTCG_THRESHOLD_DAYS else "SHORT"
        cost_basis = round(avg * qty, 2)
        market_value = round(price * qty, 2)
        lots.append(TaxLot(
            ticker=str(p.get("ticker", "")),
            quantity=qty, avg_cost=avg, current_price=price,
            holding_days=days, term=term,
            cost_basis=cost_basis, market_value=market_value,
            unrealized_gain=round(market_value - cost_basis, 2),
        ))

    def _summarize(term: str) -> dict:
        sub = [lot for lot in lots if lot.term == term]
        gain = round(sum(lot.unrealized_gain for lot in sub), 2)
        return {
            "positions": len(sub),
            "cost_basis": round(sum(lot.cost_basis for lot in sub), 2),
            "market_value": round(sum(lot.market_value for lot in sub), 2),
            "unrealized_gain": gain,
        }

    return {
        "as_of": now.strftime("%Y-%m-%d"),
        "threshold_days": _LTCG_THRESHOLD_DAYS,
        "long_term": _summarize("LONG"),
        "short_term": _summarize("SHORT"),
        "total_unrealized_gain": round(sum(lot.unrealized_gain for lot in lots), 2),
        "lots": [
            {
                "ticker": lot.ticker,
                "quantity": lot.quantity,
                "avg_cost": lot.avg_cost,
                "current_price": lot.current_price,
                "holding_days": lot.holding_days,
                "term": lot.term,
                "cost_basis": lot.cost_basis,
                "market_value": lot.market_value,
                "unrealized_gain": lot.unrealized_gain,
            }
            for lot in lots
        ],
        "disclaimer": "Unrealized estimate for planning only — not tax advice.",
    }

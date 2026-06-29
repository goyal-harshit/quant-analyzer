"""
providers.py — unified market-data access with an ordered fallback chain.

The audit's top-leverage recommendation: replace data-access logic scattered
across data_service / fast_data / screener_service with a single ``DataProvider``
interface and one orchestrating call site that decides the source.

A ``FallbackChain`` tries each provider in priority order and returns the first
healthy, non-empty result — tagging every value with the source that produced it
and an ``as_of`` timestamp (so the UI can always say *where* a number came from
and *how fresh* it is). Each provider sits behind the per-source circuit breakers
in ``reliability.py``, so a blocked source is skipped fast instead of stalling
the whole chain.

Default order (per audit §3.1):   Yahoo v8  →  seed fixtures

NSE-direct and cached-DB providers are designed to slot into this same list once
scheduled ingestion lands (the "ingest-then-serve" item) — they just need to
implement the ``DataProvider`` protocol and be inserted at the right priority.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Optional, Protocol, runtime_checkable

import pandas as pd

from services.reliability import guard_call

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@runtime_checkable
class DataProvider(Protocol):
    """A source of market data. All methods return None/empty when this provider
    has no data (or is unavailable) so the chain can fall through to the next."""

    name: str

    async def get_quote(self, ticker: str) -> Optional[dict]: ...

    async def get_history(self, ticker: str, period: str = "1y") -> Optional[pd.DataFrame]: ...

    async def get_fundamentals(self, ticker: str) -> Optional[dict]: ...


# ── Validity checks: what counts as a usable (non-empty) result ───
def _quote_ok(q: Optional[dict]) -> bool:
    return bool(q) and bool(q.get("price"))


def _history_ok(df: Optional[pd.DataFrame]) -> bool:
    return df is not None and not df.empty


def _fundamentals_ok(f: Optional[dict]) -> bool:
    return bool(f) and (f.get("pe_ratio") is not None or f.get("roe") is not None)


# ── Concrete providers ────────────────────────────────────────────
class YahooProvider:
    """Live data via the direct Yahoo v8 API (already circuit-broken in fast_data)."""

    name = "yahoo"

    def __init__(self, service=None):
        if service is None:
            from services.fast_data import fast_data_service
            service = fast_data_service
        self._svc = service

    async def get_quote(self, ticker: str) -> Optional[dict]:
        return await self._svc.get_quote(ticker)

    async def get_history(self, ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
        return await self._svc.get_price_history(ticker, period)

    async def get_fundamentals(self, ticker: str) -> Optional[dict]:
        return await self._svc.get_fundamentals(ticker)


_PERIOD_DAYS = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}


class SeedProvider:
    """Deterministic offline fixtures — the always-available last resort.

    Results are tagged ``source="seed"`` so callers (and the UI) never mistake a
    fallback for live data; cache layers cache seed values only briefly so a
    transient miss self-heals (see CONTEXT.md "seed-cache poisoning" fix)."""

    name = "seed"

    def __init__(self, module=None):
        if module is None:
            from services import seed_data as module
        self._seed = module

    async def get_quote(self, ticker: str) -> Optional[dict]:
        q = self._seed.get_seed_quote(ticker)
        if q:
            q.setdefault("source", "seed")
        return q

    async def get_history(self, ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
        days = _PERIOD_DAYS.get(period, 365)
        rows = self._seed.get_seed_price_history(ticker, days=days)
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        if "date" in df.columns:
            df.index = pd.to_datetime(df["date"])
            df = df.drop(columns=["date"])
        return df

    async def get_fundamentals(self, ticker: str) -> Optional[dict]:
        f = self._seed.get_seed_fundamentals(ticker)
        if f:
            f.setdefault("source", "seed")
        return f


# ── NSE-direct providers (nsepython / jugaad-data) ────────────────
# These libraries call NSE's public APIs directly. They are authoritative for
# Indian equities but block from many hosts (HTTP 403 / JSON-decode), so they sit
# behind their own circuit breakers and only contribute when they actually work —
# adding redundancy without reintroducing the 429/403 "storm" fragility.

def _normalize_nse_quote(raw: Optional[dict], ticker: str) -> Optional[dict]:
    """Map the NSE quote-equity JSON (shared by nsepython.nse_eq and
    jugaad NSELive.stock_quote) into the standard quote schema."""
    if not isinstance(raw, dict):
        return None
    pi = raw.get("priceInfo") or {}
    info = raw.get("info") or {}
    price = pi.get("lastPrice")
    if not price:
        return None
    hl = pi.get("intraDayHighLow") or {}
    whl = pi.get("weekHighLow") or {}
    return {
        "ticker": ticker.upper(),
        "name": info.get("companyName") or info.get("symbol") or ticker.upper(),
        "price": price,
        "prev_close": pi.get("previousClose"),
        "change": pi.get("change"),
        "change_pct": pi.get("pChange"),
        "open": pi.get("open"),
        "day_high": hl.get("max"),
        "day_low": hl.get("min"),
        "fifty_two_week_high": whl.get("max"),
        "fifty_two_week_low": whl.get("min"),
        "exchange": "NSE",
        "currency": "INR",
    }


def _normalize_ohlc_df(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    """Normalize a jugaad/nse history DataFrame to lowercase OHLCV + DatetimeIndex."""
    if df is None or getattr(df, "empty", True):
        return None
    cols = {str(c).strip().upper(): c for c in df.columns}
    needed = ["OPEN", "HIGH", "LOW", "CLOSE"]
    if not all(k in cols for k in needed):
        return None
    date_col = cols.get("DATE") or cols.get("CH_TIMESTAMP") or cols.get("TIMESTAMP")
    out = pd.DataFrame({
        "open": pd.to_numeric(df[cols["OPEN"]], errors="coerce"),
        "high": pd.to_numeric(df[cols["HIGH"]], errors="coerce"),
        "low": pd.to_numeric(df[cols["LOW"]], errors="coerce"),
        "close": pd.to_numeric(df[cols["CLOSE"]], errors="coerce"),
        "volume": pd.to_numeric(df[cols["VOLUME"]], errors="coerce") if "VOLUME" in cols else 0,
    })
    if date_col is not None:
        out.index = pd.to_datetime(df[date_col], errors="coerce")
        out = out[out.index.notna()].sort_index()
    return out.dropna(subset=["close"]) if not out.empty else None


class _LazyLibProvider:
    """Base for sync-library-backed providers: lazy import, thread offload, breaker.

    A blocking library call (it uses ``requests`` under the hood) is run in a
    worker thread so it never stalls the event loop, and wrapped in the named
    circuit breaker so persistent failures stop being retried."""

    name = "lib"
    breaker = "lib"

    def __init__(self):
        self._available: Optional[bool] = None  # resolved on first use

    def _load(self) -> bool:
        """Import the backing library; return False (and disable) if unavailable."""
        raise NotImplementedError

    def _ensure(self) -> bool:
        if self._available is None:
            try:
                self._available = self._load()
            except Exception as e:  # ImportError or any init failure
                logger.info("provider '%s' unavailable: %s", self.name, e)
                self._available = False
        return self._available

    async def _guarded(self, fn: Callable, *args):
        async def _call():
            return await asyncio.to_thread(fn, *args)
        return await guard_call(self.breaker, _call)


class NsePythonProvider(_LazyLibProvider):
    """Live NSE quotes via the ``nsepython`` library (``nse_eq``)."""

    name = "nsepython"
    breaker = "nsepython"

    def __init__(self, quote_fn: Optional[Callable] = None):
        super().__init__()
        self._quote_fn = quote_fn
        if quote_fn is not None:
            self._available = True

    def _load(self) -> bool:
        from nsepython import nse_eq
        self._quote_fn = nse_eq
        return True

    async def get_quote(self, ticker: str) -> Optional[dict]:
        if not self._ensure():
            return None
        try:
            raw = await self._guarded(self._quote_fn, ticker.upper())
        except Exception as e:
            logger.info("nsepython quote failed for %s: %s", ticker, e)
            return None
        q = _normalize_nse_quote(raw, ticker)
        if q:
            q["source"] = "nsepython"
        return q

    async def get_history(self, ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
        return None  # nsepython history schema is messy; leave to jugaad/Yahoo

    async def get_fundamentals(self, ticker: str) -> Optional[dict]:
        return None  # not a fundamentals source — fall through to screener/Yahoo


class JugaadProvider(_LazyLibProvider):
    """Live NSE quotes + history via ``jugaad-data`` (``NSELive`` + ``stock_df``)."""

    name = "jugaad"
    breaker = "jugaad"

    def __init__(self, quote_fn: Optional[Callable] = None, history_fn: Optional[Callable] = None):
        super().__init__()
        self._quote_fn = quote_fn
        self._history_fn = history_fn
        if quote_fn is not None or history_fn is not None:
            self._available = True

    def _load(self) -> bool:
        from jugaad_data.nse import NSELive, stock_df
        live = NSELive()
        self._quote_fn = live.stock_quote
        self._history_fn = stock_df
        return True

    async def get_quote(self, ticker: str) -> Optional[dict]:
        if not self._ensure() or self._quote_fn is None:
            return None
        try:
            raw = await self._guarded(self._quote_fn, ticker.upper())
        except Exception as e:
            logger.info("jugaad quote failed for %s: %s", ticker, e)
            return None
        q = _normalize_nse_quote(raw, ticker)
        if q:
            q["source"] = "jugaad"
        return q

    async def get_history(self, ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
        if not self._ensure() or self._history_fn is None:
            return None
        days = _PERIOD_DAYS.get(period, 365)
        to_d = date.today()
        from_d = to_d - timedelta(days=days)
        try:
            raw = await self._guarded(self._history_fn, ticker.upper(), from_d, to_d, "EQ")
        except Exception as e:
            logger.info("jugaad history failed for %s: %s", ticker, e)
            return None
        return _normalize_ohlc_df(raw)

    async def get_fundamentals(self, ticker: str) -> Optional[dict]:
        return None


# ── DB-first provider (ingest-then-serve) ─────────────────────────
class DBProvider:
    """Serves data from the ingest-then-serve store (`market_*` tables).

    Placed first in the read chain so endpoints read fresh DB rows instead of
    live-scraping. A freshness gate (per data class) means stale rows are treated
    as a miss, so the chain falls through to a live source — which the background
    refresh job then writes back. Any DB error degrades to None (never raises),
    so the app keeps working if the DB is down."""

    name = "db"

    def __init__(self, session_factory=None, quote_max_age=None, fundamentals_max_age=None):
        self._session_factory = session_factory
        self._quote_max_age = quote_max_age
        self._fundamentals_max_age = fundamentals_max_age

    def _factory(self):
        if self._session_factory is not None:
            return self._session_factory
        from models.database import AsyncSessionLocal
        return AsyncSessionLocal

    async def get_quote(self, ticker: str) -> Optional[dict]:
        from services import market_store
        kw = {} if self._quote_max_age is None else {"max_age": self._quote_max_age}
        try:
            async with self._factory()() as db:
                return await market_store.read_quote(db, ticker, **kw)
        except Exception as e:
            logger.info("DB quote read failed for %s: %s", ticker, e)
            return None

    async def get_history(self, ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
        from services import market_store
        try:
            async with self._factory()() as db:
                return await market_store.read_bars(db, ticker, period)
        except Exception as e:
            logger.info("DB history read failed for %s: %s", ticker, e)
            return None

    async def get_fundamentals(self, ticker: str) -> Optional[dict]:
        from services import market_store
        kw = {} if self._fundamentals_max_age is None else {"max_age": self._fundamentals_max_age}
        try:
            async with self._factory()() as db:
                return await market_store.read_fundamentals(db, ticker, **kw)
        except Exception as e:
            logger.info("DB fundamentals read failed for %s: %s", ticker, e)
            return None


# ── The orchestrating chain ───────────────────────────────────────
class FallbackChain:
    """Tries providers in order; first non-empty result wins."""

    def __init__(self, providers: list[DataProvider]):
        if not providers:
            raise ValueError("FallbackChain needs at least one provider")
        self.providers = providers

    async def _first_ok(self, method: str, validate, *args):
        """Call ``method`` on each provider until one returns a valid result."""
        last_empty = None
        for provider in self.providers:
            try:
                result = await getattr(provider, method)(*args)
            except Exception as e:  # a provider error must not break the chain
                logger.info("provider '%s'.%s failed: %s", provider.name, method, e)
                continue
            if validate(result):
                return provider.name, result
            last_empty = result
        # Nothing usable — return the last (empty) shape so callers get a stable type.
        return None, last_empty

    async def get_quote(self, ticker: str) -> dict:
        source, result = await self._first_ok("get_quote", _quote_ok, ticker)
        result = result or {}
        if source:
            result["source"] = result.get("source") or source
            result.setdefault("as_of", _now_iso())
        return result

    async def get_history(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        _, result = await self._first_ok("get_history", _history_ok, ticker, period)
        return result if result is not None else pd.DataFrame()

    async def get_fundamentals(self, ticker: str) -> dict:
        source, result = await self._first_ok("get_fundamentals", _fundamentals_ok, ticker)
        result = result or {}
        if source:
            result["source"] = result.get("source") or source
            result.setdefault("as_of", _now_iso())
        return result


# Registry of available providers by name, for order-driven chain assembly.
_PROVIDER_FACTORIES: dict[str, Callable[[], DataProvider]] = {
    "db": DBProvider,
    "yahoo": YahooProvider,
    "nsepython": NsePythonProvider,
    "jugaad": JugaadProvider,
    "seed": SeedProvider,
}

_DEFAULT_ORDER = ["db", "yahoo", "nsepython", "jugaad", "seed"]


def build_chain(order: list[str]) -> FallbackChain:
    """Assemble a FallbackChain from an ordered list of provider names.

    Unknown names are skipped with a warning. ``seed`` is always appended as the
    last-resort provider if not already present, so the chain can never come up
    empty-handed."""
    providers: list[DataProvider] = []
    for name in order:
        factory = _PROVIDER_FACTORIES.get(name.strip().lower())
        if factory is None:
            logger.warning("unknown data provider '%s' — skipping", name)
            continue
        providers.append(factory())
    if not any(getattr(p, "name", None) == "seed" for p in providers):
        providers.append(SeedProvider())
    return FallbackChain(providers)


def _configured_order() -> list[str]:
    try:
        from config import get_settings
        order = get_settings().data_provider_order_list
        return order or list(_DEFAULT_ORDER)
    except Exception:
        return list(_DEFAULT_ORDER)


def build_default_chain() -> FallbackChain:
    """Production READ chain, order from settings (``DATA_PROVIDER_ORDER``).

    Default ``db → yahoo → nsepython → jugaad → seed``: read fresh rows from the
    ingest-then-serve store first; on a stale/empty DB miss, fall through to live
    sources (which the refresh job writes back), then seed. Set
    ``DATA_PROVIDER_ORDER`` to reorder (e.g. ``nsepython,jugaad,yahoo,seed``)."""
    return build_chain(_configured_order())


def build_live_chain() -> FallbackChain:
    """LIVE-only chain (DB excluded) used by ingestion to refresh the store —
    fetching through the DB here would read our own writes instead of going live."""
    return build_chain([p for p in _configured_order() if p.strip().lower() != "db"])


# Process-wide singletons.
#   market_data — the DB-first READ chain endpoints should use.
#   live_data   — the live-only chain the ingestion jobs use to refresh the store.
market_data = build_default_chain()
live_data = build_live_chain()

"""
Tests for the data-provider fallback chain (services/providers.py).

Uses in-memory fake providers so the orchestration logic is verified without any
network access.
"""

import pandas as pd
import pytest

import services.reliability as reliability
from services.providers import (
    FallbackChain,
    JugaadProvider,
    NsePythonProvider,
    SeedProvider,
    YahooProvider,
    _fundamentals_ok,
    _history_ok,
    _normalize_nse_quote,
    _normalize_ohlc_df,
    _quote_ok,
    build_chain,
)


@pytest.fixture(autouse=True)
def _reset_guards():
    # Each test starts with fresh per-source breakers / rate limiters so circuit
    # state never leaks between tests.
    reliability._guards.clear()
    yield
    reliability._guards.clear()


# A realistic NSE quote-equity payload (shape shared by nse_eq / NSELive).
NSE_QUOTE = {
    "info": {"symbol": "RELIANCE", "companyName": "Reliance Industries Limited"},
    "priceInfo": {
        "lastPrice": 2850.5, "previousClose": 2838.2, "change": 12.3, "pChange": 0.43,
        "open": 2840.0, "intraDayHighLow": {"min": 2835.0, "max": 2860.0},
        "weekHighLow": {"min": 2200.0, "max": 3000.0},
    },
}


class FakeProvider:
    def __init__(self, name, *, quote=None, history=None, fundamentals=None, raises=False):
        self.name = name
        self._quote = quote
        self._history = history
        self._fundamentals = fundamentals
        self._raises = raises
        self.quote_calls = 0

    async def get_quote(self, ticker):
        self.quote_calls += 1
        if self._raises:
            raise ConnectionError("source down")
        return self._quote

    async def get_history(self, ticker, period="1y"):
        if self._raises:
            raise ConnectionError("source down")
        return self._history

    async def get_fundamentals(self, ticker):
        if self._raises:
            raise ConnectionError("source down")
        return self._fundamentals


# ── Validity predicates ───────────────────────────────────────────

def test_quote_ok_requires_price():
    assert _quote_ok({"price": 100}) is True
    assert _quote_ok({"price": 0}) is False
    assert _quote_ok({}) is False
    assert _quote_ok(None) is False


def test_history_ok_requires_rows():
    assert _history_ok(pd.DataFrame({"close": [1, 2]})) is True
    assert _history_ok(pd.DataFrame()) is False
    assert _history_ok(None) is False


def test_fundamentals_ok_requires_pe_or_roe():
    assert _fundamentals_ok({"pe_ratio": 20}) is True
    assert _fundamentals_ok({"roe": 15}) is True
    assert _fundamentals_ok({"market_cap": 1}) is False
    assert _fundamentals_ok({}) is False


# ── Chain ordering & fallthrough ──────────────────────────────────

async def test_first_provider_wins_and_is_tagged():
    primary = FakeProvider("primary", quote={"price": 101})
    backup = FakeProvider("backup", quote={"price": 999})
    chain = FallbackChain([primary, backup])

    q = await chain.get_quote("RELIANCE")
    assert q["price"] == 101
    assert q["source"] == "primary"
    assert "as_of" in q
    assert backup.quote_calls == 0  # short-circuited at the first healthy source


async def test_falls_through_on_empty_result():
    primary = FakeProvider("primary", quote={})          # empty
    backup = FakeProvider("backup", quote={"price": 50})
    chain = FallbackChain([primary, backup])

    q = await chain.get_quote("X")
    assert q["price"] == 50
    assert q["source"] == "backup"


async def test_falls_through_on_provider_exception():
    primary = FakeProvider("primary", raises=True)        # source down
    backup = FakeProvider("backup", quote={"price": 7})
    chain = FallbackChain([primary, backup])

    q = await chain.get_quote("X")
    assert q["price"] == 7
    assert q["source"] == "backup"


async def test_all_empty_returns_empty_dict():
    chain = FallbackChain([FakeProvider("a", quote={}), FakeProvider("b", quote=None)])
    q = await chain.get_quote("X")
    assert q == {}


async def test_existing_source_tag_is_preserved():
    # A provider that already labelled its data (e.g. seed) keeps that label
    # rather than being overwritten by the provider name.
    primary = FakeProvider("primary", quote={"price": 12, "source": "seed"})
    chain = FallbackChain([primary])
    q = await chain.get_quote("X")
    assert q["source"] == "seed"


async def test_history_returns_dataframe_and_falls_through():
    primary = FakeProvider("primary", history=pd.DataFrame())   # empty
    backup = FakeProvider("backup", history=pd.DataFrame({"close": [1, 2, 3]}))
    chain = FallbackChain([primary, backup])

    df = await chain.get_history("X", "1y")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3


async def test_empty_chain_rejected():
    with pytest.raises(ValueError):
        FallbackChain([])


# ── SeedProvider behaves as a real last-resort provider ───────────

async def test_seed_provider_quote_and_history_shapes():
    sp = SeedProvider()
    q = await sp.get_quote("RELIANCE")
    assert q and q["price"] > 0
    assert q["source"] == "seed"

    df = await sp.get_history("RELIANCE", "6mo")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert {"open", "high", "low", "close"}.issubset(df.columns)


# ── NSE-direct providers (nsepython / jugaad) ─────────────────────

def test_normalize_nse_quote_maps_fields():
    q = _normalize_nse_quote(NSE_QUOTE, "RELIANCE")
    assert q["price"] == 2850.5
    assert q["prev_close"] == 2838.2
    assert q["change_pct"] == 0.43
    assert q["day_high"] == 2860.0
    assert q["fifty_two_week_low"] == 2200.0
    assert q["name"] == "Reliance Industries Limited"
    assert q["exchange"] == "NSE"


def test_normalize_nse_quote_rejects_empty():
    assert _normalize_nse_quote(None, "X") is None
    assert _normalize_nse_quote({"priceInfo": {}}, "X") is None  # no lastPrice


def test_normalize_ohlc_df_lowercases_and_indexes():
    raw = pd.DataFrame({
        "DATE": ["2026-01-01", "2026-01-02"],
        "OPEN": [10, 11], "HIGH": [12, 13], "LOW": [9, 10],
        "CLOSE": [11, 12], "VOLUME": [100, 200],
    })
    out = _normalize_ohlc_df(raw)
    assert list(out.columns) == ["open", "high", "low", "close", "volume"]
    assert isinstance(out.index, pd.DatetimeIndex)
    assert out["close"].tolist() == [11, 12]


def test_normalize_ohlc_df_rejects_missing_columns():
    assert _normalize_ohlc_df(pd.DataFrame({"DATE": [1], "OPEN": [1]})) is None
    assert _normalize_ohlc_df(pd.DataFrame()) is None


async def test_nsepython_provider_normalizes_injected_quote():
    prov = NsePythonProvider(quote_fn=lambda t: NSE_QUOTE)
    q = await prov.get_quote("RELIANCE")
    assert q["price"] == 2850.5
    assert q["source"] == "nsepython"
    # not a history/fundamentals source
    assert await prov.get_history("RELIANCE") is None
    assert await prov.get_fundamentals("RELIANCE") is None


async def test_nsepython_provider_returns_none_on_lib_error():
    def boom(_t):
        raise ConnectionError("NSE 403")

    prov = NsePythonProvider(quote_fn=boom)
    assert await prov.get_quote("X") is None  # swallowed -> chain falls through


async def test_jugaad_provider_quote_and_history_injected():
    hist = pd.DataFrame({
        "DATE": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "OPEN": [10, 11, 12], "HIGH": [12, 13, 14], "LOW": [9, 10, 11],
        "CLOSE": [11, 12, 13], "VOLUME": [100, 200, 300],
    })
    prov = JugaadProvider(quote_fn=lambda t: NSE_QUOTE, history_fn=lambda t, f, to, s: hist)
    q = await prov.get_quote("RELIANCE")
    assert q["source"] == "jugaad"
    df = await prov.get_history("RELIANCE", "6mo")
    assert len(df) == 3 and "close" in df.columns


async def test_nse_provider_unavailable_yields_none():
    # Simulate a failed/absent library load (deterministic — never touches the
    # network, so it's safe in CI where the lib may actually be installed). The
    # provider must disable itself and yield None rather than raise.
    prov = NsePythonProvider()
    prov._available = False
    assert await prov.get_quote("RELIANCE") is None


async def test_nse_provider_in_chain_falls_through_to_yahoo():
    nse = NsePythonProvider(quote_fn=lambda t: None)        # blocked / empty
    yahoo = FakeProvider("yahoo", quote={"price": 123})
    chain = FallbackChain([nse, yahoo])
    q = await chain.get_quote("RELIANCE")
    assert q["price"] == 123
    assert q["source"] == "yahoo"


# ── Order-driven chain assembly ───────────────────────────────────

def test_build_chain_respects_order_and_appends_seed():
    chain = build_chain(["yahoo"])
    names = [p.name for p in chain.providers]
    assert names[0] == "yahoo"
    assert names[-1] == "seed"  # always appended as backstop


def test_build_chain_skips_unknown_and_keeps_seed_once():
    chain = build_chain(["yahoo", "bogus", "seed"])
    names = [p.name for p in chain.providers]
    assert "bogus" not in names
    assert names.count("seed") == 1


def test_build_chain_full_order():
    chain = build_chain(["nsepython", "jugaad", "yahoo", "seed"])
    assert [p.name for p in chain.providers] == ["nsepython", "jugaad", "yahoo", "seed"]


async def test_default_chain_falls_back_to_seed_when_live_empty():
    # A YahooProvider whose underlying service yields nothing should fall through
    # to seed, proving the production wiring degrades gracefully offline.
    class DeadSvc:
        async def get_quote(self, t):
            return {}

        async def get_price_history(self, t, p):
            return pd.DataFrame()

        async def get_fundamentals(self, t):
            return {}

    chain = FallbackChain([YahooProvider(service=DeadSvc()), SeedProvider()])
    q = await chain.get_quote("RELIANCE")
    assert q["source"] == "seed"
    assert q["price"] > 0

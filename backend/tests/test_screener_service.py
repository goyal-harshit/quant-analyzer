"""
Tests for services/screener_service.py scrape resilience.

Network-free: `guard_call`, `_fetch_html`, and `_parse_screener_page` are patched
so we exercise the URL-fallback and cache-TTL logic deterministically.
"""
import time

import services.screener_service as ss
from services.screener_service import ScreenerService, _has_real_data


async def _passthrough_guard(name, fn):
    return await fn()


async def test_falls_back_to_standalone_when_consolidated_empty(monkeypatch):
    monkeypatch.setattr(ss, "guard_call", _passthrough_guard)
    s = ScreenerService()

    urls = []

    async def fake_fetch(url, ticker):
        urls.append(url)
        return "<html></html>"

    calls = {"n": 0}

    def fake_parse(soup, ticker):
        calls["n"] += 1
        if calls["n"] == 1:  # consolidated page is a stub (no real metrics)
            return {"ticker": ticker, "source": "screener.in"}
        return {"ticker": ticker, "source": "screener.in", "pe_ratio": 25.0, "roe": 18.0}

    monkeypatch.setattr(s, "_fetch_html", fake_fetch)
    monkeypatch.setattr(s, "_parse_screener_page", fake_parse)

    r = await s.get_fundamentals("FOO")
    assert r.get("pe_ratio") == 25.0
    assert len(urls) == 2  # tried consolidated, then standalone
    assert "/consolidated/" in urls[0]
    assert "/consolidated/" not in urls[1]


async def test_empty_result_negative_cached_with_short_ttl(monkeypatch):
    monkeypatch.setattr(ss, "guard_call", _passthrough_guard)
    s = ScreenerService()

    async def fake_fetch(url, ticker):
        return "<html></html>"

    monkeypatch.setattr(s, "_fetch_html", fake_fetch)
    monkeypatch.setattr(s, "_parse_screener_page", lambda soup, t: {"ticker": t, "source": "screener.in"})

    r = await s.get_fundamentals("BAR")
    assert r == {}
    ts, data = s._cache["BAR"]
    assert data == {}
    assert not _has_real_data(data)

    # A miss must expire after the short negative TTL, not the 30-min success TTL.
    s._cache["BAR"] = (time.time() - (s._neg_ttl + 1), {})
    hit_before = "BAR" in s._cache
    r2 = await s.get_fundamentals("BAR")  # stale negative entry → re-fetches (still empty)
    assert hit_before and r2 == {}
    assert s._neg_ttl < s._cache_ttl


async def test_real_hit_is_cached_and_not_refetched(monkeypatch):
    monkeypatch.setattr(ss, "guard_call", _passthrough_guard)
    s = ScreenerService()

    fetches = {"n": 0}

    async def fake_fetch(url, ticker):
        fetches["n"] += 1
        return "<html></html>"

    monkeypatch.setattr(s, "_fetch_html", fake_fetch)
    monkeypatch.setattr(s, "_parse_screener_page", lambda soup, t: {"ticker": t, "pe_ratio": 10.0})

    r1 = await s.get_fundamentals("QUX")
    r2 = await s.get_fundamentals("QUX")
    assert r1.get("pe_ratio") == 10.0 and r2.get("pe_ratio") == 10.0
    assert fetches["n"] == 1  # second call served from the 30-min cache


async def test_circuit_open_negative_caches_and_stops(monkeypatch):
    from services.reliability import CircuitOpenError

    async def open_guard(name, fn):
        raise CircuitOpenError("screener circuit open")

    monkeypatch.setattr(ss, "guard_call", open_guard)
    s = ScreenerService()

    r = await s.get_fundamentals("BAZ")
    assert r == {}
    assert s._cache["BAZ"][1] == {}

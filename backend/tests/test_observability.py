"""
Tests for the observability layer (services/observability.py): JSON logging,
request-id context, the metrics registry, and the request middleware end-to-end.
"""

import json
import logging

import pytest

from services.observability import (
    JsonFormatter,
    Metrics,
    breaker_gauges,
    get_request_id,
    new_request_id,
    render_metrics,
    request_id_var,
)


# ── JSON logging ──────────────────────────────────────────────────

def _record(msg, **extra):
    rec = logging.LogRecord("test", logging.INFO, __file__, 1, msg, (), None)
    for k, v in extra.items():
        setattr(rec, k, v)
    return rec


def test_json_formatter_emits_parseable_json():
    line = JsonFormatter().format(_record("hello"))
    obj = json.loads(line)
    assert obj["msg"] == "hello"
    assert obj["level"] == "INFO"
    assert obj["logger"] == "test"
    assert "ts" in obj


def test_json_formatter_includes_extra_and_request_id():
    line = JsonFormatter().format(_record("req", request_id="abc123", route="/x", status=200))
    obj = json.loads(line)
    assert obj["request_id"] == "abc123"
    assert obj["route"] == "/x"
    assert obj["status"] == 200


def test_json_formatter_includes_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        rec = logging.LogRecord("t", logging.ERROR, __file__, 1, "failed", (), sys.exc_info())
    obj = json.loads(JsonFormatter().format(rec))
    assert "ValueError" in obj["exc"]


def test_request_id_contextvar():
    assert get_request_id() == "-"
    token = request_id_var.set("xyz")
    try:
        assert get_request_id() == "xyz"
    finally:
        request_id_var.reset(token)
    assert len(new_request_id()) == 16


# ── Metrics registry ──────────────────────────────────────────────

def test_counter_increments_and_renders():
    m = Metrics()
    m.inc("http_requests_total", {"method": "GET", "status": "200"})
    m.inc("http_requests_total", {"method": "GET", "status": "200"})
    m.inc("http_requests_total", {"method": "POST", "status": "500"})
    assert m.get_counter("http_requests_total", {"method": "GET", "status": "200"}) == 2.0
    text = m.render()
    assert "# TYPE http_requests_total counter" in text
    assert 'http_requests_total{method="GET",status="200"} 2.0' in text


def test_summary_tracks_sum_and_count():
    m = Metrics()
    m.observe("http_request_duration_seconds", 0.1, {"route": "/a"})
    m.observe("http_request_duration_seconds", 0.3, {"route": "/a"})
    text = m.render()
    assert 'http_request_duration_seconds_sum{route="/a"} 0.4' in text
    assert 'http_request_duration_seconds_count{route="/a"} 2' in text


def test_render_includes_extra_gauges():
    m = Metrics()
    text = m.render(extra_gauges={"my_gauge": {(("source", "yahoo"),): 1.0}})
    assert "# TYPE my_gauge gauge" in text
    assert 'my_gauge{source="yahoo"} 1.0' in text


def test_label_values_are_escaped():
    m = Metrics()
    m.inc("c", {"path": 'a"b\\c'})
    text = m.render()
    assert 'a\\"b\\\\c' in text


def test_reset_clears_metrics():
    m = Metrics()
    m.inc("c")
    m.reset()
    assert m.get_counter("c") == 0.0


def test_breaker_gauges_reflect_state():
    import asyncio

    import services.reliability as reliability
    reliability._guards.clear()

    async def trip():
        g = await reliability.get_guard("yahoo")
        for _ in range(g.breaker.failure_threshold):
            await g.breaker.record_failure()

    asyncio.run(trip())
    gauges = breaker_gauges()["circuit_breaker_state"]
    # The 'open' series for yahoo should be 1.0 after tripping.
    assert gauges[(("source", "yahoo"), ("state", "open"))] == 1.0
    assert gauges[(("source", "yahoo"), ("state", "closed"))] == 0.0
    reliability._guards.clear()


def test_render_metrics_smoke():
    # render_metrics() merges counters + breaker gauges without raising.
    assert isinstance(render_metrics(), str)


# ── Middleware end-to-end (full app) ──────────────────────────────

async def test_request_id_header_and_metrics(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")          # middleware stamped it
    # The request was counted; /metrics exposes it.
    m = await client.get("/metrics")
    assert m.status_code == 200
    assert "http_requests_total" in m.text


async def test_incoming_request_id_is_propagated(client):
    resp = await client.get("/", headers={"X-Request-ID": "trace-42"})
    assert resp.headers.get("X-Request-ID") == "trace-42"

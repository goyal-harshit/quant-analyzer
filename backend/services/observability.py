"""
observability.py — structured logging, request IDs, metrics, error tracking.

Audit §3.5 (observability) in one dependency-light module:

  * JSON logs with a per-request ``request_id`` (correlate every log line of a
    request) via a contextvar — no external logging library.
  * RequestContextMiddleware — assigns/propagates ``X-Request-ID``, times each
    request, emits a structured access log, and records metrics.
  * A tiny in-process metrics registry exposed in Prometheus text format at
    ``/metrics`` (counters + summaries) — no prometheus-client dependency.
  * Optional Sentry init, active only when ``SENTRY_DSN`` is set and the SDK is
    installed (graceful no-op otherwise).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from threading import Lock
from typing import Optional

# ── Request-id context ────────────────────────────────────────────
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return request_id_var.get()


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


# ── JSON logging ──────────────────────────────────────────────────
# Standard LogRecord attributes we don't want to duplicate into the JSON "extra".
_RESERVED = set(vars(logging.makeLogRecord({})).keys()) | {
    "message", "asctime", "taskName",
}


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON, including the request id and any
    structured ``extra={...}`` fields passed to the logger."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
                  + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
        }
        # Merge any user-supplied structured fields.
        for k, v in record.__dict__.items():
            if k not in _RESERVED and k not in payload:
                payload[k] = v
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """Install a single root handler with the chosen formatter (idempotent)."""
    root = logging.getLogger()
    root.setLevel(level.upper())
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler()
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        ))
    root.addHandler(handler)


# ── Metrics registry (Prometheus text exposition, no dependency) ──
def _labels_key(labels: Optional[dict]) -> tuple:
    return tuple(sorted((labels or {}).items()))


def _fmt_labels(labels: tuple) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{k}="{_escape(str(v))}"' for k, v in labels)
    return "{" + inner + "}"


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


class Metrics:
    """Minimal thread-safe metrics: counters + summaries (sum/count)."""

    def __init__(self):
        self._counters: dict[tuple[str, tuple], float] = {}
        self._summaries: dict[tuple[str, tuple], tuple[float, int]] = {}
        self._lock = Lock()

    def inc(self, name: str, labels: Optional[dict] = None, value: float = 1.0) -> None:
        key = (name, _labels_key(labels))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def observe(self, name: str, value: float, labels: Optional[dict] = None) -> None:
        key = (name, _labels_key(labels))
        with self._lock:
            total, count = self._summaries.get(key, (0.0, 0))
            self._summaries[key] = (total + value, count + 1)

    def get_counter(self, name: str, labels: Optional[dict] = None) -> float:
        return self._counters.get((name, _labels_key(labels)), 0.0)

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._summaries.clear()

    def render(self, extra_gauges: Optional[dict] = None) -> str:
        """Render Prometheus text. ``extra_gauges`` maps name -> {labels_tuple: value}
        for values computed at scrape time (e.g. circuit-breaker state)."""
        lines: list[str] = []
        with self._lock:
            counters = dict(self._counters)
            summaries = dict(self._summaries)

        by_name: dict[str, list] = {}
        for (name, labels), val in counters.items():
            by_name.setdefault(name, []).append((labels, val))
        for name, series in by_name.items():
            lines.append(f"# TYPE {name} counter")
            for labels, val in series:
                lines.append(f"{name}{_fmt_labels(labels)} {val}")

        for (name, labels), (total, count) in summaries.items():
            lines.append(f"# TYPE {name} summary")
            lines.append(f"{name}_sum{_fmt_labels(labels)} {total}")
            lines.append(f"{name}_count{_fmt_labels(labels)} {count}")

        for name, series in (extra_gauges or {}).items():
            lines.append(f"# TYPE {name} gauge")
            for labels, val in series.items():
                lines.append(f"{name}{_fmt_labels(labels)} {val}")

        return "\n".join(lines) + "\n"


metrics = Metrics()


def breaker_gauges() -> dict:
    """Circuit-breaker state as a Prometheus gauge (1 = in that state)."""
    try:
        from services.reliability import CircuitState, breaker_states
    except Exception:
        return {}
    series: dict[tuple, float] = {}
    for source, st in breaker_states().items():
        for state in CircuitState:
            labels = _labels_key({"source": source, "state": state.value})
            series[labels] = 1.0 if st["state"] == state.value else 0.0
        series[_labels_key({"source": source, "state": "consecutive_failures"})] = \
            float(st["consecutive_failures"])
    return {"circuit_breaker_state": series}


def render_metrics() -> str:
    return metrics.render(extra_gauges=breaker_gauges())


# ── Request middleware ────────────────────────────────────────────
def install_request_context(app) -> None:
    """Add the request-id + timing + metrics middleware to a FastAPI app."""
    from starlette.middleware.base import BaseHTTPMiddleware

    logger = logging.getLogger("access")

    class RequestContextMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            rid = request.headers.get("x-request-id") or new_request_id()
            token = request_id_var.set(rid)
            start = time.perf_counter()
            route = _route_template(request)
            status = 500
            try:
                response = await call_next(request)
                status = response.status_code
                response.headers["X-Request-ID"] = rid
                return response
            finally:
                dur = time.perf_counter() - start
                labels = {"method": request.method, "route": route}
                metrics.observe("http_request_duration_seconds", dur, labels)
                metrics.inc("http_requests_total", {**labels, "status": str(status)})
                logger.info(
                    "request",
                    extra={"request_id": rid, "method": request.method,
                           "route": route, "status": status,
                           "duration_ms": round(dur * 1000, 1)},
                )
                request_id_var.reset(token)

    app.add_middleware(RequestContextMiddleware)


def _route_template(request) -> str:
    """Matched route pattern (bounded cardinality), else the raw path."""
    route = request.scope.get("route")
    return getattr(route, "path", None) or request.url.path


# ── Sentry (optional) ─────────────────────────────────────────────
def init_sentry(dsn: str, environment: str = "development", traces_sample_rate: float = 0.0) -> bool:
    """Initialise Sentry if a DSN is configured and the SDK is installed."""
    if not dsn:
        return False
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=dsn, environment=environment, traces_sample_rate=traces_sample_rate)
        logging.getLogger(__name__).info("Sentry error tracking enabled")
        return True
    except Exception as e:  # SDK absent or bad DSN — don't block startup
        logging.getLogger(__name__).warning("Sentry not enabled: %s", e)
        return False

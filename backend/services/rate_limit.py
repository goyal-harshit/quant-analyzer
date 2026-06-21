"""
rate_limit.py — shared API rate limiter (slowapi).

Protects against resource abuse on compute/LLM-heavy endpoints and brute-force
on login. Degrades gracefully to a no-op if slowapi isn't installed, so the app
still boots in minimal environments.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    SLOWAPI_AVAILABLE = True
    # Generous global default — blocks scripted abuse without hurting normal use.
    limiter = Limiter(key_func=get_remote_address, default_limits=["240/minute"])
except Exception:  # pragma: no cover - optional dependency
    SLOWAPI_AVAILABLE = False
    logger.warning("slowapi not installed — rate limiting disabled")

    class _NoopLimiter:
        """Stand-in so @limiter.limit(...) decorators are harmless no-ops."""

        def limit(self, *_args, **_kwargs):
            def _decorator(func):
                return func
            return _decorator

    limiter = _NoopLimiter()


def install_rate_limiting(app) -> None:
    """Wire the limiter into a FastAPI app (no-op if slowapi is unavailable)."""
    if not SLOWAPI_AVAILABLE:
        return
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

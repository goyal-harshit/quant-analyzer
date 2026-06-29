"""
config.py — typed application settings (pydantic-settings).

Single source of truth for configuration, replacing scattered ``os.getenv`` reads
(audit §3.3). Values come from environment variables (or a local ``.env``), are
validated/типed once at import, and are accessed via ``get_settings()``.

Adopt incrementally: new code should read ``get_settings()``; existing modules can
migrate off raw ``os.getenv`` over time without a big-bang change.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://quant:quant@localhost:5432/quantai",
        alias="DATABASE_URL",
    )

    # ── Cache / queue ─────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str | None = Field(default=None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(default=None, alias="CELERY_RESULT_BACKEND")

    # ── Auth ──────────────────────────────────────────────────────
    jwt_secret_key: str | None = Field(default=None, alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    # httpOnly auth cookies. Cross-site prod (GH Pages frontend → Render backend)
    # needs samesite="none" + secure=True; same-site local dev defaults to "lax".
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")
    cookie_samesite: str = Field(default="lax", alias="COOKIE_SAMESITE")

    # ── CORS ──────────────────────────────────────────────────────
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    # ── Market-data provider fallback order ───────────────────────
    # Comma-separated provider names tried in order (first non-empty wins).
    # Known: yahoo, nsepython, jugaad, seed. seed is always appended as backstop.
    data_provider_order: str = Field(
        default="db,yahoo,nsepython,jugaad,seed", alias="DATA_PROVIDER_ORDER"
    )

    # ── AI / Ollama ───────────────────────────────────────────────
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    ollama_model: str = Field(default="llama3.2", alias="OLLAMA_MODEL")

    # ── Optional external data keys (free tiers; blank = disabled) ─
    fred_api_key: str = Field(default="", alias="FRED_API_KEY")
    data_gov_in_key: str = Field(default="", alias="DATA_GOV_IN_KEY")

    # ── Email / notifications ─────────────────────────────────────
    # Backend: "console" (logs, dev default), "memory" (tests), or "smtp" (prod).
    email_backend: str = Field(default="console", alias="EMAIL_BACKEND")
    email_from: str = Field(default="QuantAI <no-reply@quantai.local>", alias="EMAIL_FROM")
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_starttls: bool = Field(default=True, alias="SMTP_STARTTLS")
    # Base URL of the frontend, used to build links in emails (reset/verify).
    frontend_base_url: str = Field(default="http://localhost:3000", alias="FRONTEND_BASE_URL")
    # Token lifetimes (minutes) for reset / email-verification links.
    reset_token_expire_minutes: int = Field(default=30, alias="RESET_TOKEN_EXPIRE_MINUTES")
    verify_token_expire_minutes: int = Field(default=1440, alias="VERIFY_TOKEN_EXPIRE_MINUTES")

    # ── Observability ─────────────────────────────────────────────
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")       # JSON logs (set false for plain dev logs)
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")      # blank = Sentry disabled
    sentry_traces_sample_rate: float = Field(default=0.0, alias="SENTRY_TRACES_SAMPLE_RATE")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def data_provider_order_list(self) -> list[str]:
        return [p.strip() for p in self.data_provider_order.split(",") if p.strip()]

    @property
    def celery_broker(self) -> str:
        if self.celery_broker_url:
            return self.celery_broker_url
        base = self.redis_url.rsplit("/", 1)[0]
        return f"{base}/1"

    @property
    def celery_backend(self) -> str:
        if self.celery_result_backend:
            return self.celery_result_backend
        base = self.redis_url.rsplit("/", 1)[0]
        return f"{base}/2"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton (read once per process)."""
    return Settings()

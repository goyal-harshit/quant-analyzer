"""Tests for typed settings (config.py) and the response envelope (envelope.py)."""

import importlib

from config import Settings
from services.envelope import envelope


# ── Settings ──────────────────────────────────────────────────────

def test_settings_defaults():
    s = Settings(_env_file=None)
    assert s.redis_url.startswith("redis://")
    assert s.jwt_algorithm == "HS256"
    assert s.access_token_expire_minutes == 1440


def test_cors_origin_list_parsing():
    s = Settings(_env_file=None, CORS_ORIGINS="http://a.com, http://b.com ,")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]


def test_celery_urls_derive_from_redis():
    s = Settings(_env_file=None, REDIS_URL="redis://host:6379/0")
    assert s.celery_broker == "redis://host:6379/1"
    assert s.celery_backend == "redis://host:6379/2"


def test_celery_urls_explicit_override():
    s = Settings(_env_file=None, CELERY_BROKER_URL="redis://x/9")
    assert s.celery_broker == "redis://x/9"


def test_env_var_typed_coercion(monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    s = Settings(_env_file=None)
    assert s.access_token_expire_minutes == 30  # coerced str -> int


# ── Envelope ──────────────────────────────────────────────────────

def test_envelope_basic_shape():
    env = envelope({"price": 100}, source="yahoo", cached=False)
    assert env["data"] == {"price": 100}
    assert env["source"] == "yahoo"
    assert env["cached"] is False
    assert "as_of" in env


def test_envelope_reuses_payload_as_of_and_source():
    payload = {"price": 1, "as_of": "2026-06-27T00:00:00Z", "source": "seed"}
    env = envelope(payload)
    assert env["as_of"] == "2026-06-27T00:00:00Z"
    assert env["source"] == "seed"


def test_envelope_handles_list_payload():
    env = envelope([1, 2, 3], source="cache", cached=True)
    assert env["data"] == [1, 2, 3]
    assert env["cached"] is True
    assert env["source"] == "cache"


def test_config_module_importable_singleton():
    cfg = importlib.import_module("config")
    assert cfg.get_settings() is cfg.get_settings()  # lru_cache singleton

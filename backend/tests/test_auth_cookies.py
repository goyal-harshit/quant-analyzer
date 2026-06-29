"""
Tests for httpOnly-cookie auth + refresh tokens (the audit's auth-hardening).

The httpx test client keeps a cookie jar, so login's Set-Cookie flows to later
requests — letting us exercise the real cookie-based flow end-to-end.
"""

import pytest

from services.auth_service import create_access_token, create_refresh_token, decode_token

PW = "securepass123"


async def _register_login(client, email):
    await client.post("/api/v1/auth/register", json={"email": email, "password": PW})
    return await client.post("/api/v1/auth/login", data={"username": email, "password": PW})


# ── Token type enforcement (unit, no DB) ──────────────────────────

def test_access_token_has_type_and_rejected_as_refresh():
    tok = create_access_token({"sub": "a@b.com"})
    assert decode_token(tok, expected_type="access")["sub"] == "a@b.com"
    assert decode_token(tok, expected_type="refresh") is None  # wrong type


def test_refresh_token_rejected_as_access():
    tok = create_refresh_token({"sub": "a@b.com"})
    assert decode_token(tok, expected_type="refresh") is not None
    assert decode_token(tok, expected_type="access") is None


def test_legacy_token_without_type_treated_as_access():
    # A token carrying no "type" claim (pre-upgrade) still validates as access.
    from datetime import timedelta

    from jose import jwt
    from services import auth_service as a
    legacy = jwt.encode(
        {"sub": "old@b.com"}, a.SECRET_KEY, algorithm=a.ALGORITHM,
    )
    assert decode_token(legacy, expected_type="access")["sub"] == "old@b.com"
    del timedelta  # silence unused in case of refactor


# ── Cookie flow (integration) ─────────────────────────────────────

async def test_login_sets_httponly_cookies(client):
    r = await _register_login(client, "c1@example.com")
    assert r.status_code == 200
    assert "access_token" in r.json()                       # body still returned (back-compat)
    assert r.cookies.get("access_token") is not None        # and cookies set
    assert r.cookies.get("refresh_token") is not None


async def test_me_works_via_cookie_without_authorization_header(client):
    await _register_login(client, "c2@example.com")
    # No Authorization header — auth rides the httpOnly cookie in the jar.
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "c2@example.com"


async def test_me_works_via_bearer_header_backward_compat(client):
    login = await _register_login(client, "c3@example.com")
    token = login.json()["access_token"]
    client.cookies.clear()                                  # drop cookies → header-only path
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "c3@example.com"


async def test_refresh_rotates_and_issues_new_access(client):
    await _register_login(client, "c4@example.com")
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert r.cookies.get("access_token") is not None        # rotated cookies set
    # The refreshed cookie still authenticates /me.
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200


async def test_refresh_without_cookie_is_401(client):
    client.cookies.clear()
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


async def test_logout_clears_cookies_and_blocks_me(client):
    await _register_login(client, "c5@example.com")
    out = await client.post("/api/v1/auth/logout")
    assert out.status_code == 200
    # Cookies cleared → /me (no header) is now unauthorized.
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401


async def test_access_token_cannot_be_used_as_refresh(client):
    login = await _register_login(client, "c6@example.com")
    access = login.json()["access_token"]
    client.cookies.clear()
    client.cookies.set("refresh_token", access)             # plant access token as refresh
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 401                             # type mismatch rejected


async def test_refresh_token_cannot_be_used_as_access(client):
    await _register_login(client, "c7@example.com")
    refresh_val = client.cookies.get("refresh_token")
    client.cookies.clear()
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_val}"})
    assert r.status_code == 401


async def test_protected_route_still_401_without_auth(client):
    client.cookies.clear()
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


# ── CSRF (double-submit) ──────────────────────────────────────────

async def test_login_returns_csrf_token_and_cookie(client):
    r = await _register_login(client, "csrf1@example.com")
    assert r.json().get("csrf_token")
    assert r.cookies.get("csrf_token") is not None


async def test_cookie_mutation_without_csrf_header_is_403(client):
    await _register_login(client, "csrf2@example.com")
    # A cookie-authenticated POST to a watchlist (mutating) with NO X-CSRF-Token.
    r = await client.post("/api/v1/watchlists", json={"name": "x"})
    assert r.status_code == 403
    assert "csrf" in r.json()["detail"].lower()


async def test_cookie_mutation_with_csrf_header_passes_csrf(client):
    login = await _register_login(client, "csrf3@example.com")
    csrf = login.json()["csrf_token"]
    r = await client.post("/api/v1/watchlists", json={"name": "My List"},
                          headers={"X-CSRF-Token": csrf})
    # CSRF passed → request reaches the handler (created, not a 403).
    assert r.status_code != 403


async def test_bearer_auth_is_exempt_from_csrf(client):
    login = await _register_login(client, "csrf4@example.com")
    token = login.json()["access_token"]
    client.cookies.clear()  # no cookies → header-only auth path
    r = await client.post("/api/v1/watchlists", json={"name": "Hdr"},
                          headers={"Authorization": f"Bearer {token}"})
    assert r.status_code != 403  # Bearer header is CSRF-immune


async def test_get_requests_not_csrf_checked(client):
    await _register_login(client, "csrf5@example.com")
    r = await client.get("/api/v1/watchlists")  # safe method, cookie auth, no CSRF header
    assert r.status_code != 403

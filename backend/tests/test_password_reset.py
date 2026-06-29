"""
Tests for password reset + email verification (uses the in-memory email backend
so the emailed token can be captured and the flow completed end-to-end).
"""

import re

import pytest

PW = "securepass123"


@pytest.fixture
def outbox(monkeypatch):
    # Switch the email service to the in-memory backend for this test.
    from config import get_settings
    from services import email_service

    monkeypatch.setenv("EMAIL_BACKEND", "memory")
    get_settings.cache_clear()
    email_service.clear_outbox()
    yield email_service.outbox
    email_service.clear_outbox()
    get_settings.cache_clear()  # restore default-config settings for other tests


def _token_from(body: str) -> str:
    m = re.search(r"token=([A-Za-z0-9_\-.]+)", body)
    assert m, f"no token in email body: {body!r}"
    return m.group(1)


async def _register(client, email):
    await client.post("/api/v1/auth/register", json={"email": email, "password": PW})


async def test_password_reset_end_to_end(client, outbox):
    email = "reset-flow@example.com"
    await _register(client, email)

    r = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    assert len(outbox) == 1
    token = _token_from(outbox[0].body)

    new_pw = "brandnew123"
    rr = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": new_pw})
    assert rr.status_code == 200

    # Old password rejected, new one works.
    old = await client.post("/api/v1/auth/login", data={"username": email, "password": PW})
    assert old.status_code == 401
    new = await client.post("/api/v1/auth/login", data={"username": email, "password": new_pw})
    assert new.status_code == 200


async def test_forgot_password_no_user_enumeration(client, outbox):
    r = await client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})
    assert r.status_code == 200                      # same response as a real account
    assert len(outbox) == 0                          # but no email actually sent


async def test_reset_with_invalid_token_rejected(client):
    r = await client.post("/api/v1/auth/reset-password",
                          json={"token": "not-a-real-token", "new_password": PW})
    assert r.status_code == 400


async def test_reset_rejects_weak_password(client, outbox):
    email = "reset-weak@example.com"
    await _register(client, email)
    await client.post("/api/v1/auth/forgot-password", json={"email": email})
    token = _token_from(outbox[0].body)
    r = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "short"})
    assert r.status_code == 400


async def test_access_token_cannot_reset_password(client, outbox):
    # An access token must not be usable as a reset token (type enforcement).
    email = "reset-type@example.com"
    await _register(client, email)
    login = await client.post("/api/v1/auth/login", data={"username": email, "password": PW})
    access = login.json()["access_token"]
    r = await client.post("/api/v1/auth/reset-password",
                          json={"token": access, "new_password": "brandnew123"})
    assert r.status_code == 400


async def test_email_verification_flow(client, outbox):
    email = "verify-flow@example.com"
    await _register(client, email)
    await client.post("/api/v1/auth/login", data={"username": email, "password": PW})

    sent = await client.post("/api/v1/auth/send-verification")  # /auth/* is CSRF-exempt
    assert sent.status_code == 200
    assert len(outbox) == 1
    token = _token_from(outbox[0].body)

    v = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert v.status_code == 200

    me = await client.get("/api/v1/auth/me")
    assert me.json()["is_verified"] is True

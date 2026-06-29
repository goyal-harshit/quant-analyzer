"""Tests for role-based access control (require_role / require_admin)."""

from sqlalchemy import select

PW = "securepass123"


async def _register_login(client, email):
    await client.post("/api/v1/auth/register", json={"email": email, "password": PW})
    await client.post("/api/v1/auth/login", data={"username": email, "password": PW})


async def _set_role(email, role):
    from models.database import AsyncSessionLocal, User
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one()
        user.role = role
        await db.commit()


async def test_new_users_default_to_user_role(client):
    await _register_login(client, "role-default@example.com")
    me = await client.get("/api/v1/auth/me")
    assert me.json()["role"] == "user"
    assert me.json()["is_verified"] is False


async def test_admin_route_forbidden_for_regular_user(client):
    await _register_login(client, "regular@example.com")
    r = await client.get("/api/v1/auth/admin/ping")  # GET → no CSRF; cookie auth
    assert r.status_code == 403


async def test_admin_route_allowed_for_admin(client):
    email = "boss@example.com"
    await _register_login(client, email)
    await _set_role(email, "admin")
    r = await client.get("/api/v1/auth/admin/ping")
    assert r.status_code == 200
    assert r.json()["admin"] == email


async def test_admin_route_requires_auth(client):
    client.cookies.clear()
    r = await client.get("/api/v1/auth/admin/ping")
    assert r.status_code == 401

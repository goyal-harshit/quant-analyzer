import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_auth_flow(client: AsyncClient):
    # Test registration
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "testuser@example.com", "password": "securepassword123"}
    )
    assert reg_response.status_code == 200
    assert "access_token" in reg_response.json()
    
    # Test duplicate registration
    dup_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "testuser@example.com", "password": "securepassword123"}
    )
    assert dup_response.status_code == 400

    # Test login
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "testuser@example.com", "password": "securepassword123"}
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # Test authenticated route /me
    headers = {"Authorization": f"Bearer {token}"}
    me_response = await client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "testuser@example.com"

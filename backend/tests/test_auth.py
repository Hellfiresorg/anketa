import pytest
from httpx import AsyncClient

from app.models.manager import Manager


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, manager: Manager):
    resp = await client.post("/api/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, manager: Manager):
    resp = await client.post("/api/auth/login", json={"email": "test@example.com", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_wrong_email(client: AsyncClient, manager: Manager):
    resp = await client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient, manager: Manager, auth_headers: dict):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test Manager"


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code in (401, 403)  # HTTPBearer returns 403 in older FastAPI, 401 in newer


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, manager: Manager):
    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 200

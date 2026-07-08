import pytest
from httpx import AsyncClient


class TestLogin:

    async def test_valid_credentials_return_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "changeme"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    async def test_wrong_password_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_wrong_username_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "hacker", "password": "changeme"},
        )
        assert resp.status_code == 401

    async def test_token_is_valid_jwt_format(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "changeme"},
        )
        token = resp.json()["access_token"]
        # JWT has exactly 3 dot-separated parts: header.payload.signature
        assert len(token.split(".")) == 3


class TestProtectedEndpoints:

    async def test_post_prices_without_token_returns_401(self, client: AsyncClient):
        resp = await client.post("/api/v1/prices", json={})
        assert resp.status_code == 401

    async def test_post_bulk_without_token_returns_401(self, client: AsyncClient):
        resp = await client.post("/api/v1/prices/bulk", json=[])
        assert resp.status_code == 401

    async def test_post_prices_with_valid_token_passes_auth(
        self, client: AsyncClient, auth_headers: dict
    ):
        # 422 means auth passed, request body was invalid — that's fine here
        resp = await client.post("/api/v1/prices", json={}, headers=auth_headers)
        assert resp.status_code in (201, 422)

    async def test_get_endpoints_are_public(self, client: AsyncClient):
        for path in [
            "/api/v1/prices/latest",
            "/api/v1/anomalies/overview",
            "/api/v1/health",
        ]:
            resp = await client.get(path)
            assert resp.status_code != 401, f"{path} should be public"

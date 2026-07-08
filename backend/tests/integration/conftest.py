import asyncio

import httpx
import pytest
import pytest_asyncio

BASE_URL = "http://localhost:8000"
ADMIN_CREDS = {"username": "admin", "password": "changeme"}


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def client():
    ac = httpx.AsyncClient(base_url=BASE_URL, timeout=10.0)
    yield ac
    try:
        await ac.aclose()
    except RuntimeError:
        pass


@pytest.fixture(scope="session")
def auth_headers() -> dict:
    resp = httpx.post(f"{BASE_URL}/api/v1/auth/token", data=ADMIN_CREDS, timeout=10.0)
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

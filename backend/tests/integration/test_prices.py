from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient


class TestGetLatestPrices:

    async def test_returns_200(self, client: AsyncClient):
        resp = await client.get("/api/v1/prices/latest")
        assert resp.status_code == 200

    async def test_each_item_has_required_fields(self, client: AsyncClient):
        resp = await client.get("/api/v1/prices/latest")
        for item in resp.json():
            assert "component" in item
            assert "price_value" in item
            assert "recorded_at" in item

    async def test_second_call_hits_cache(self, client: AsyncClient):
        resp1 = await client.get("/api/v1/prices/latest")
        resp2 = await client.get("/api/v1/prices/latest")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()


class TestGetPriceSummary:

    async def test_valid_component_returns_summary(self, client: AsyncClient):
        resp = await client.get("/api/v1/prices/summary/DDR5?days=30")
        assert resp.status_code == 200
        body = resp.json()
        assert "avg_price" in body
        assert "min_price" in body
        assert "max_price" in body
        assert "data_points" in body

    async def test_invalid_component_returns_404_or_422(self, client: AsyncClient):
        resp = await client.get("/api/v1/prices/summary/NONEXISTENT?days=30")
        assert resp.status_code in (404, 422)

    async def test_component_name_is_case_insensitive(self, client: AsyncClient):
        resp = await client.get("/api/v1/prices/summary/ddr5?days=30")
        assert resp.status_code == 200


class TestCreatePrice:

    async def test_create_with_auth_returns_201(
        self, client: AsyncClient, auth_headers: dict
    ):
        unique_ts = datetime.now(timezone.utc) - timedelta(seconds=60)
        payload = {
            "component": "DDR5",
            "market_segment": "CONSUMER",
            "price_value": "3.75",
            "price_unit": "USD_PER_GB",
            "currency": "USD",
            "data_source": "NEWEGG",
            "recorded_at": unique_ts.isoformat(),
        }
        resp = await client.post("/api/v1/prices", json=payload, headers=auth_headers)
        assert resp.status_code in (201, 409)
        if resp.status_code == 201:
            body = resp.json()
            assert body["component"] == "DDR5"
            assert Decimal(body["price_value"]) == Decimal("3.75")

    async def test_create_without_auth_returns_401(self, client: AsyncClient):
        payload = {
            "component": "DDR5",
            "market_segment": "CONSUMER",
            "price_value": "3.75",
            "price_unit": "USD_PER_GB",
            "currency": "USD",
            "data_source": "NEWEGG",
            "recorded_at": "2099-01-02T00:00:00Z",
        }
        resp = await client.post("/api/v1/prices", json=payload)
        assert resp.status_code == 401

    async def test_bulk_too_many_records_returns_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        payload = [
            {
                "component": "DDR5",
                "market_segment": "CONSUMER",
                "price_value": "3.75",
                "price_unit": "USD_PER_GB",
                "currency": "USD",
                "data_source": "NEWEGG",
                "recorded_at": "2024-02-01T00:00:00Z",
            }
        ] * 501
        resp = await client.post("/api/v1/prices/bulk", json=payload, headers=auth_headers)
        assert resp.status_code == 400


class TestGetPriceHistory:

    async def test_returns_paginated_response(self, client: AsyncClient):
        resp = await client.get("/api/v1/prices?limit=10&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert len(body["items"]) <= 10

    async def test_component_filter_works(self, client: AsyncClient):
        resp = await client.get("/api/v1/prices?component=DDR5&limit=5")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["component"] == "DDR5"

from httpx import AsyncClient


class TestHealthEndpoints:

    async def test_health_returns_200(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200

    async def test_readiness_returns_200(self, client: AsyncClient):
        resp = await client.get("/api/v1/health/ready")
        assert resp.status_code == 200

    async def test_metrics_endpoint_returns_prometheus_format(self, client: AsyncClient):
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        # Prometheus format always starts with # HELP or a metric name
        assert b"http_requests_total" in resp.content or b"# HELP" in resp.content

    async def test_root_endpoint_returns_service_info(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert "name" in body
        assert "version" in body

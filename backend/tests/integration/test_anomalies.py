from httpx import AsyncClient


class TestAnomalyOverview:

    async def test_returns_200(self, client: AsyncClient):
        resp = await client.get("/api/v1/anomalies/overview")
        assert resp.status_code == 200

    async def test_response_has_reports_list(self, client: AsyncClient):
        resp = await client.get("/api/v1/anomalies/overview")
        body = resp.json()
        assert "reports" in body
        assert "generated_at" in body
        assert "period_days" in body
        assert isinstance(body["reports"], list)

    async def test_each_report_has_risk_fields(self, client: AsyncClient):
        resp = await client.get("/api/v1/anomalies/overview")
        for report in resp.json()["reports"]:
            assert "component" in report
            assert "risk_score" in report
            assert "risk_level" in report
            assert 0.0 <= report["risk_score"] <= 100.0

    async def test_days_parameter_accepted(self, client: AsyncClient):
        for days in [7, 30, 90]:
            resp = await client.get(f"/api/v1/anomalies/overview?days={days}")
            assert resp.status_code == 200

    async def test_reports_sorted_by_risk_score_desc(self, client: AsyncClient):
        resp = await client.get("/api/v1/anomalies/overview")
        scores = [r["risk_score"] for r in resp.json()["reports"]]
        assert scores == sorted(scores, reverse=True)


class TestComponentAnomaly:

    async def test_valid_component_returns_report(self, client: AsyncClient):
        resp = await client.get("/api/v1/anomalies/DDR5")
        assert resp.status_code == 200
        body = resp.json()
        assert body["component"] == "DDR5"
        assert "risk_score" in body
        assert "anomaly_status" in body

    async def test_invalid_component_returns_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/anomalies/INVALID_COMPONENT")
        assert resp.status_code == 404

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.exceptions import PriceNotFoundError
from app.services.forecast_service import MIN_DATA_POINTS, ForecastService


def _synthetic_records(
    days: int, start_price: float = 10.0, daily_drift: float = 0.02
) -> list[dict]:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "recorded_at": base + timedelta(days=i),
            "price_value": start_price + daily_drift * i,
        }
        for i in range(days)
    ]


@pytest.fixture
def mock_price_repository():
    mock = MagicMock()
    mock.get_time_series = AsyncMock()
    return mock


@pytest.fixture
def forecast_service(mock_price_repository):
    return ForecastService(price_repository=mock_price_repository)


class TestGenerateForecast:

    async def test_unknown_component_raises_not_found(
        self, forecast_service, mock_price_repository
    ):
        with pytest.raises(PriceNotFoundError):
            await forecast_service.generate_forecast("NOT_A_COMPONENT", horizon_days=7)
        mock_price_repository.get_time_series.assert_not_called()

    async def test_one_point_short_of_minimum_raises_not_found(
        self, forecast_service, mock_price_repository
    ):
        mock_price_repository.get_time_series.return_value = _synthetic_records(MIN_DATA_POINTS - 1)
        with pytest.raises(PriceNotFoundError):
            await forecast_service.generate_forecast("DDR5", horizon_days=7)

    async def test_exactly_minimum_points_succeeds(self, forecast_service, mock_price_repository):
        mock_price_repository.get_time_series.return_value = _synthetic_records(MIN_DATA_POINTS)

        result = await forecast_service.generate_forecast("DDR5", horizon_days=7)

        assert len(result.forecast) == 7

    async def test_sufficient_data_returns_forecast(self, forecast_service, mock_price_repository):
        mock_price_repository.get_time_series.return_value = _synthetic_records(60)

        result = await forecast_service.generate_forecast("DDR5", horizon_days=14)

        assert result.component == "DDR5"
        assert result.horizon_days == 14
        assert result.historical_days == 180
        assert result.model == "prophet"
        assert len(result.forecast) == 14

    async def test_forecast_points_are_chronological_and_positive(
        self, forecast_service, mock_price_repository
    ):
        mock_price_repository.get_time_series.return_value = _synthetic_records(60)

        result = await forecast_service.generate_forecast("DDR5", horizon_days=10)

        dates = [point.date for point in result.forecast]
        assert dates == sorted(dates)
        assert len(set(dates)) == len(dates)
        for point in result.forecast:
            assert point.predicted > 0
            assert point.lower > 0
            assert point.upper > 0

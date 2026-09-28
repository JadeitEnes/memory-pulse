from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.exceptions import PriceNotFoundError
from app.services.forecast_comparison_service import ForecastComparisonService


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
def comparison_service(mock_price_repository):
    return ForecastComparisonService(price_repository=mock_price_repository)


class TestForecastComparison:

    async def test_unknown_component_raises_not_found(
        self, comparison_service, mock_price_repository
    ):
        with pytest.raises(PriceNotFoundError):
            await comparison_service.compare("NOT_A_COMPONENT", horizon_days=7, backtest_days=14)
        mock_price_repository.get_time_series.assert_not_called()

    async def test_insufficient_data_raises_not_found(
        self, comparison_service, mock_price_repository
    ):
        mock_price_repository.get_time_series.return_value = _synthetic_records(10)
        with pytest.raises(PriceNotFoundError):
            await comparison_service.compare("DDR5", horizon_days=7, backtest_days=14)

    async def test_sufficient_data_returns_full_comparison(
        self, comparison_service, mock_price_repository
    ):
        mock_price_repository.get_time_series.return_value = _synthetic_records(60)

        result = await comparison_service.compare("DDR5", horizon_days=7, backtest_days=14)

        assert result.component == "DDR5"
        assert result.horizon_days == 7
        assert result.backtest_days == 14
        assert len(result.prophet.forecast) == 7
        assert len(result.xgboost.forecast) == 7
        assert result.prophet.backtest.compared_points > 0
        assert result.xgboost.backtest.compared_points > 0
        assert result.prophet.backtest.mae >= 0
        assert result.xgboost.backtest.mae >= 0
        assert result.better_model in {"prophet", "xgboost", "tie"}

    async def test_forecast_points_are_chronological_and_positive(
        self, comparison_service, mock_price_repository
    ):
        mock_price_repository.get_time_series.return_value = _synthetic_records(60)

        result = await comparison_service.compare("DDR5", horizon_days=10, backtest_days=14)

        for model_result in (result.prophet, result.xgboost):
            dates = [point.date for point in model_result.forecast]
            assert dates == sorted(dates)
            assert len(set(dates)) == len(dates)
            for point in model_result.forecast:
                assert point.predicted > 0
                assert point.lower > 0
                assert point.upper > 0

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from app.core.logging import get_logger
from app.domain.exceptions import PriceNotFoundError
from app.repositories.interfaces.price_repository import IPriceRepository
from app.schemas.forecast import (
    BacktestMetrics,
    ForecastComparisonResponse,
    ForecastPoint,
    ModelForecast,
)
from app.services.forecast_service import HISTORICAL_DAYS, _run_prophet
from app.services.historical_data import fetch_historical_records, resolve_component
from app.services.xgboost_forecast_service import _run_xgboost

logger = get_logger(__name__)

BACKTEST_DAYS = 14
MIN_DATA_POINTS = 30


def _daily_series(records: list[dict]):
    import pandas as pd

    df = pd.DataFrame([{"ds": r["recorded_at"], "y": float(r["price_value"])} for r in records])
    df["ds"] = pd.to_datetime(df["ds"])
    if df["ds"].dt.tz is not None:
        df["ds"] = df["ds"].dt.tz_localize(None)
    df["ds"] = df["ds"].dt.normalize()
    df = df.groupby("ds", as_index=False)["y"].mean()
    return df.sort_values("ds").reset_index(drop=True)


def _to_records(daily) -> list[dict]:
    return [{"recorded_at": row.ds, "price_value": row.y} for row in daily.itertuples()]


def _score(predicted_points: list[dict], actual_daily) -> dict:
    actual_by_date = {row.ds.date().isoformat(): float(row.y) for row in actual_daily.itertuples()}
    errors = [
        abs(p["predicted"] - actual_by_date[p["date"]])
        for p in predicted_points
        if p["date"] in actual_by_date
    ]
    if not errors:
        return {"mae": None, "rmse": None, "compared_points": 0}
    mae = float(sum(errors) / len(errors))
    rmse = float((sum(e**2 for e in errors) / len(errors)) ** 0.5)
    return {"mae": round(mae, 4), "rmse": round(rmse, 4), "compared_points": len(errors)}


def _run_comparison(records: list[dict], horizon_days: int, backtest_days: int) -> dict:
    daily = _daily_series(records)
    if len(daily) < MIN_DATA_POINTS + backtest_days:
        raise PriceNotFoundError(component="insufficient-daily-coverage")

    train_daily = daily.iloc[:-backtest_days].reset_index(drop=True)
    test_daily = daily.iloc[-backtest_days:].reset_index(drop=True)
    train_records = _to_records(train_daily)

    prophet_backtest_points = _run_prophet(train_records, backtest_days)
    xgboost_backtest_points = _run_xgboost(train_records, backtest_days)

    full_records = _to_records(daily)
    prophet_forecast = _run_prophet(full_records, horizon_days)
    xgboost_forecast = _run_xgboost(full_records, horizon_days)

    return {
        "prophet": {
            "forecast": prophet_forecast,
            "backtest": _score(prophet_backtest_points, test_daily),
        },
        "xgboost": {
            "forecast": xgboost_forecast,
            "backtest": _score(xgboost_backtest_points, test_daily),
        },
    }


def _to_forecast_points(raw: list[dict]) -> list[ForecastPoint]:
    return [
        ForecastPoint(
            date=p["date"],
            predicted=Decimal(str(max(p["predicted"], 0.0001))),
            lower=Decimal(str(max(p["lower"], 0.0001))),
            upper=Decimal(str(max(p["upper"], 0.0001))),
        )
        for p in raw
    ]


class ForecastComparisonService:
    def __init__(self, price_repository: IPriceRepository) -> None:
        self._repo = price_repository

    async def compare(
        self,
        component: str,
        horizon_days: int = 30,
        backtest_days: int = BACKTEST_DAYS,
    ) -> ForecastComparisonResponse:
        component_enum = resolve_component(component)
        records = await fetch_historical_records(self._repo, component_enum, HISTORICAL_DAYS)

        if len(records) < MIN_DATA_POINTS + backtest_days:
            raise PriceNotFoundError(component=component)

        logger.info(
            "forecast_comparison_running",
            component=component,
            data_points=len(records),
            horizon_days=horizon_days,
            backtest_days=backtest_days,
        )

        result = await asyncio.to_thread(_run_comparison, records, horizon_days, backtest_days)

        prophet = ModelForecast(
            model="prophet",
            forecast=_to_forecast_points(result["prophet"]["forecast"]),
            backtest=BacktestMetrics(**result["prophet"]["backtest"]),
        )
        xgboost = ModelForecast(
            model="xgboost",
            forecast=_to_forecast_points(result["xgboost"]["forecast"]),
            backtest=BacktestMetrics(**result["xgboost"]["backtest"]),
        )

        if prophet.backtest.mae is None or xgboost.backtest.mae is None:
            better_model = "undetermined"
        elif prophet.backtest.mae < xgboost.backtest.mae:
            better_model = "prophet"
        elif xgboost.backtest.mae < prophet.backtest.mae:
            better_model = "xgboost"
        else:
            better_model = "tie"

        logger.info(
            "forecast_comparison_complete",
            component=component,
            better_model=better_model,
            prophet_mae=prophet.backtest.mae,
            xgboost_mae=xgboost.backtest.mae,
        )

        return ForecastComparisonResponse(
            component=component.upper(),
            generated_at=datetime.now(timezone.utc),
            horizon_days=horizon_days,
            historical_days=HISTORICAL_DAYS,
            backtest_days=backtest_days,
            prophet=prophet,
            xgboost=xgboost,
            better_model=better_model,
        )

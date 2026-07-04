import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from app.core.logging import get_logger
from app.domain.entities.enums import MemoryComponent
from app.domain.exceptions import DatabaseError, PriceNotFoundError
from app.repositories.interfaces.price_repository import IPriceRepository
from app.schemas.forecast import ForecastPoint, ForecastResponse
from app.schemas.price import PriceFilterSchema

logger = get_logger(__name__)

HISTORICAL_DAYS = 180
MIN_DATA_POINTS = 30


def _run_prophet(records: list[dict], horizon_days: int) -> list[dict]:
    """CPU-bound: fit Prophet and return forecast rows. Runs in thread pool."""
    import pandas as pd
    from prophet import Prophet

    df = pd.DataFrame(
        [
            {
                "ds": r["recorded_at"],
                "y": float(r["price_value"]),
            }
            for r in records
        ]
    )

    # Aggregate to daily averages — Prophet works on daily granularity
    df["ds"] = pd.to_datetime(df["ds"]).dt.tz_localize(None).dt.normalize()
    df = df.groupby("ds", as_index=False)["y"].mean()
    df = df.sort_values("ds").reset_index(drop=True)

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.1,
        interval_width=0.80,
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=horizon_days, freq="D")
    forecast = model.predict(future)

    last_historical = df["ds"].max()
    future_rows = forecast[forecast["ds"] > last_historical]

    return [
        {
            "date": row.ds.date().isoformat(),
            "predicted": round(float(row.yhat), 4),
            "lower": round(float(row.yhat_lower), 4),
            "upper": round(float(row.yhat_upper), 4),
        }
        for _, row in future_rows.iterrows()
    ]


class ForecastService:
    def __init__(self, price_repository: IPriceRepository) -> None:
        self._repo = price_repository

    async def generate_forecast(
        self,
        component: str,
        horizon_days: int = 30,
    ) -> ForecastResponse:
        try:
            component_enum = MemoryComponent(component.upper())
        except ValueError:
            raise PriceNotFoundError(component=component)

        filters = PriceFilterSchema(
            component=component_enum,
            days=HISTORICAL_DAYS,
            limit=5000,
            offset=0,
        )

        try:
            records = await self._repo.get_time_series(filters)
        except Exception as e:
            raise DatabaseError(f"Failed to fetch historical data: {e}") from e

        if len(records) < MIN_DATA_POINTS:
            raise PriceNotFoundError(component=component)

        logger.info(
            "forecast_fitting",
            component=component,
            data_points=len(records),
            horizon_days=horizon_days,
        )

        # Prophet.fit() is synchronous + CPU-bound — run in thread pool
        # so we don't block the async event loop
        raw_points = await asyncio.to_thread(_run_prophet, records, horizon_days)

        forecast_points = [
            ForecastPoint(
                date=p["date"],
                predicted=Decimal(str(max(p["predicted"], 0.0001))),
                lower=Decimal(str(max(p["lower"], 0.0001))),
                upper=Decimal(str(max(p["upper"], 0.0001))),
            )
            for p in raw_points
        ]

        logger.info(
            "forecast_complete",
            component=component,
            points=len(forecast_points),
        )

        return ForecastResponse(
            component=component.upper(),
            generated_at=datetime.now(timezone.utc),
            horizon_days=horizon_days,
            historical_days=HISTORICAL_DAYS,
            forecast=forecast_points,
        )

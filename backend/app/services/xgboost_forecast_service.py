import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from app.core.logging import get_logger
from app.domain.exceptions import PriceNotFoundError
from app.repositories.interfaces.price_repository import IPriceRepository
from app.schemas.forecast import ForecastPoint, ForecastResponse
from app.services.historical_data import fetch_historical_records, resolve_component

logger = get_logger(__name__)

HISTORICAL_DAYS = 180
MIN_DATA_POINTS = 30

_LAGS = (1, 7, 14)
_ROLLING_WINDOW = 7
_FEATURE_COLUMNS = [
    "day_index",
    "day_of_week",
    "day_of_month",
    "month",
    "lag_1",
    "lag_7",
    "lag_14",
    "rolling_mean_7",
]
_QUANTILES = {"lower": 0.1, "predicted": 0.5, "upper": 0.9}


def _daily_series(records: list[dict]):
    import pandas as pd

    df = pd.DataFrame([{"ds": r["recorded_at"], "y": float(r["price_value"])} for r in records])
    df["ds"] = pd.to_datetime(df["ds"])
    if df["ds"].dt.tz is not None:
        df["ds"] = df["ds"].dt.tz_localize(None)
    df["ds"] = df["ds"].dt.normalize()
    df = df.groupby("ds", as_index=False)["y"].mean()
    return df.sort_values("ds").reset_index(drop=True)


def _with_features(df):
    out = df.copy()
    out["day_index"] = range(len(out))
    out["day_of_week"] = out["ds"].dt.dayofweek
    out["day_of_month"] = out["ds"].dt.day
    out["month"] = out["ds"].dt.month
    for lag in _LAGS:
        out[f"lag_{lag}"] = out["y"].shift(lag)
    out["rolling_mean_7"] = out["y"].shift(1).rolling(_ROLLING_WINDOW).mean()
    return out


def _fit_quantile_models(train_df) -> dict:
    from xgboost import XGBRegressor

    features = _with_features(train_df).dropna().reset_index(drop=True)
    models = {}
    for name, alpha in _QUANTILES.items():
        model = XGBRegressor(
            objective="reg:quantileerror",
            quantile_alpha=alpha,
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
        model.fit(features[_FEATURE_COLUMNS], features["y"])
        models[name] = model
    return models


def _recursive_forecast(history_df, models: dict, steps: int) -> list[dict]:
    import pandas as pd

    series_by_key = {key: history_df.copy() for key in models}
    results = []

    for _ in range(steps):
        row_result: dict = {}
        for key, model in models.items():
            series = series_by_key[key]
            next_date = series["ds"].max() + pd.Timedelta(days=1)
            candidate = pd.concat(
                [series, pd.DataFrame({"ds": [next_date], "y": [float("nan")]})],
                ignore_index=True,
            )
            feats = _with_features(candidate).iloc[[-1]]
            pred = float(model.predict(feats[_FEATURE_COLUMNS])[0])
            candidate.loc[candidate.index[-1], "y"] = pred
            series_by_key[key] = candidate
            row_result[key] = round(pred, 4)
        row_result["date"] = next_date.date().isoformat()
        results.append(row_result)

    return results


def _run_xgboost(records: list[dict], horizon_days: int) -> list[dict]:
    """CPU-bound: fit three quantile XGBoost models and forecast forward. Runs in thread pool."""
    df = _daily_series(records)
    models = _fit_quantile_models(df)
    return _recursive_forecast(df, models, horizon_days)


class XGBoostForecastService:
    def __init__(self, price_repository: IPriceRepository) -> None:
        self._repo = price_repository

    async def generate_forecast(
        self,
        component: str,
        horizon_days: int = 30,
    ) -> ForecastResponse:
        component_enum = resolve_component(component)
        records = await fetch_historical_records(self._repo, component_enum, HISTORICAL_DAYS)

        if len(records) < MIN_DATA_POINTS:
            raise PriceNotFoundError(component=component)

        logger.info(
            "xgboost_forecast_fitting",
            component=component,
            data_points=len(records),
            horizon_days=horizon_days,
        )

        raw_points = await asyncio.to_thread(_run_xgboost, records, horizon_days)

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
            "xgboost_forecast_complete",
            component=component,
            points=len(forecast_points),
        )

        return ForecastResponse(
            component=component.upper(),
            generated_at=datetime.now(timezone.utc),
            horizon_days=horizon_days,
            historical_days=HISTORICAL_DAYS,
            model="xgboost",
            forecast=forecast_points,
        )

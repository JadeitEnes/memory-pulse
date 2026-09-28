from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.api.dependencies import (
    CacheDep,
    ForecastComparisonServiceDep,
    ForecastServiceDep,
)
from app.core.logging import get_logger
from app.domain.exceptions import DatabaseError, PriceNotFoundError
from app.schemas.forecast import ForecastComparisonResponse, ForecastResponse

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])
logger = get_logger(__name__)

_CACHE_TTL = 3600  # 1 hour — model fitting is expensive


@router.get(
    "/{component}",
    response_model=ForecastResponse,
    summary="Generate price forecast for a component",
    description=(
        "Uses Prophet time-series model trained on the last 180 days of historical data. "
        "Forecast is cached for 1 hour. First request takes 3-8 seconds (model fitting)."
    ),
)
async def get_forecast(
    component: str,
    service: ForecastServiceDep,
    cache: CacheDep,
    horizon: int = Query(default=30, ge=7, le=90, description="Forecast horizon in days"),
) -> Any:
    cache_key = f"mp:forecast:{component.upper()}:{horizon}"

    cached = await cache.get(cache_key)
    if cached is not None:
        logger.debug("forecast_cache_hit", component=component, horizon=horizon)
        return JSONResponse(content=cached)

    try:
        result = await service.generate_forecast(component, horizon)
    except PriceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No historical data found for component: {component.upper()}",
        )
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))

    await cache.set(cache_key, result.model_dump(mode="json"), ttl_seconds=_CACHE_TTL)
    return result


@router.get(
    "/{component}/compare",
    response_model=ForecastComparisonResponse,
    summary="Compare Prophet and XGBoost forecasts for a component",
    description=(
        "Fits both models, backtests each against the most recent held-out days "
        "(actual MAE/RMSE, not in-sample fit), then forecasts the requested horizon "
        "with both. Cached for 1 hour — fitting four models takes 5-15 seconds."
    ),
)
async def compare_forecasts(
    component: str,
    service: ForecastComparisonServiceDep,
    cache: CacheDep,
    horizon: int = Query(default=30, ge=7, le=90, description="Forecast horizon in days"),
    backtest_days: int = Query(default=14, ge=7, le=30, description="Held-out days to backtest"),
) -> Any:
    cache_key = f"mp:forecast:compare:{component.upper()}:{horizon}:{backtest_days}"

    cached = await cache.get(cache_key)
    if cached is not None:
        logger.debug("forecast_comparison_cache_hit", component=component, horizon=horizon)
        return JSONResponse(content=cached)

    try:
        result = await service.compare(component, horizon, backtest_days)
    except PriceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Not enough historical data to backtest component: {component.upper()} "
                f"(need at least 30 daily points plus {backtest_days} held-out days)"
            ),
        )
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))

    await cache.set(cache_key, result.model_dump(mode="json"), ttl_seconds=_CACHE_TTL)
    return result

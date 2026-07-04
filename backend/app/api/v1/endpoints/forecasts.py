from typing import Any

from app.api.dependencies import CacheDep, ForecastServiceDep
from app.core.logging import get_logger
from app.domain.exceptions import DatabaseError, PriceNotFoundError
from app.schemas.forecast import ForecastResponse
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])
logger = get_logger(__name__)

_CACHE_TTL = 3600  # 1 hour — Prophet fit is expensive


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

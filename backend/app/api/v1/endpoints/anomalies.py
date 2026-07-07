from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.api.dependencies import AnomalyServiceDep, CacheDep
from app.core.logging import get_logger
from app.domain.exceptions import DatabaseError, PriceNotFoundError
from app.schemas.anomaly import AnomalyOverview, ComponentRiskReport

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])
logger = get_logger(__name__)

_CACHE_TTL = 300  # 5 minutes


@router.get(
    "/overview",
    response_model=AnomalyOverview,
    summary="Risk report for all tracked components",
    description="Returns Z-score anomaly status and composite risk score (0-100) for every "
    "component, sorted by risk descending. Cached 5 minutes.",
)
async def get_anomaly_overview(
    service: AnomalyServiceDep,
    cache: CacheDep,
    days: int = Query(default=30, ge=7, le=90, description="Lookback window in days"),
) -> Any:
    cache_key = f"mp:anomaly:overview:{days}"
    cached = await cache.get(cache_key)
    if cached is not None:
        logger.debug("anomaly_cache_hit", key=cache_key)
        return JSONResponse(content=cached)

    try:
        result = await service.analyze_all(days)
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))

    await cache.set(cache_key, result.model_dump(mode="json"), ttl_seconds=_CACHE_TTL)
    return result


@router.get(
    "/{component}",
    response_model=ComponentRiskReport,
    summary="Risk report for a single component",
)
async def get_component_risk(
    component: str,
    service: AnomalyServiceDep,
    cache: CacheDep,
    days: int = Query(default=30, ge=7, le=90),
) -> Any:
    cache_key = f"mp:anomaly:{component.upper()}:{days}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return JSONResponse(content=cached)

    try:
        result = await service.analyze_component(component, days)
    except PriceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for component: {component.upper()}",
        )
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))

    await cache.set(cache_key, result.model_dump(mode="json"), ttl_seconds=_CACHE_TTL)
    return result

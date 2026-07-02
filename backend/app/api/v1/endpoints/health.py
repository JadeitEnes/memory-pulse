from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.database import check_db_connection
from app.core.logging import get_logger

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)
settings = get_settings()


async def _check_redis(url: str) -> bool:
    try:
        client = aioredis.from_url(url, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        return True
    except Exception:
        return False


@router.get("/health", summary="Basic liveness check")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/ready", summary="Readiness check with dependencies")
async def readiness_check():
    checks = {}
    overall_healthy = True

    db_healthy = await check_db_connection()
    checks["database"] = {
        "status": "healthy" if db_healthy else "unhealthy",
        "type": "postgresql+timescaledb",
    }
    if not db_healthy:
        overall_healthy = False
        logger.warning("readiness_check_db_failed")

    broker_healthy = await _check_redis(settings.REDIS_BROKER_URL)
    checks["redis_broker"] = {
        "status": "healthy" if broker_healthy else "unhealthy",
        "type": "redis",
        "role": "celery-broker",
    }
    if not broker_healthy:
        overall_healthy = False
        logger.warning("readiness_check_redis_broker_failed")

    cache_healthy = await _check_redis(settings.REDIS_CACHE_URL)
    checks["redis_cache"] = {
        "status": "healthy" if cache_healthy else "unhealthy",
        "type": "redis",
        "role": "api-cache",
    }
    if not cache_healthy:
        overall_healthy = False
        logger.warning("readiness_check_redis_cache_failed")

    response = {
        "status": "ready" if overall_healthy else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }

    if not overall_healthy:
        raise HTTPException(status_code=503, detail=response)
    return response

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.database import check_db_connection
from app.core.logging import get_logger

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)
settings = get_settings()


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

    checks["redis"] = {"status": "not_checked", "type": "redis"}

    response = {
        "status": "ready" if overall_healthy else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }

    if not overall_healthy:
        raise HTTPException(status_code=503, detail=response)
    return response

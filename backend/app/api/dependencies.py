from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import RedisCache, get_redis_client
from app.core.database import get_db
from app.core.security import decode_access_token
from app.repositories.implementations.postgres_price_repository import (
    PostgresPriceRepository,
)
from app.repositories.interfaces.price_repository import IPriceRepository
from app.services.anomaly_service import AnomalyService
from app.services.forecast_service import ForecastService
from app.services.price_service import PriceService

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_price_repository(
    db: AsyncSession = Depends(get_db),
) -> IPriceRepository:
    return PostgresPriceRepository(session=db)


def get_price_service(
    repository: IPriceRepository = Depends(get_price_repository),
) -> PriceService:
    return PriceService(price_repository=repository)


def get_forecast_service(
    repository: IPriceRepository = Depends(get_price_repository),
) -> ForecastService:
    return ForecastService(price_repository=repository)


def get_anomaly_service(
    repository: IPriceRepository = Depends(get_price_repository),
) -> AnomalyService:
    return AnomalyService(price_repository=repository)


def get_cache() -> RedisCache:
    return RedisCache(client=get_redis_client())


async def get_current_user(token: str = Depends(_oauth2_scheme)) -> str:
    username = decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


PriceServiceDep = Annotated[PriceService, Depends(get_price_service)]
ForecastServiceDep = Annotated[ForecastService, Depends(get_forecast_service)]
AnomalyServiceDep = Annotated[AnomalyService, Depends(get_anomaly_service)]
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
CacheDep = Annotated[RedisCache, Depends(get_cache)]
CurrentUserDep = Annotated[str, Depends(get_current_user)]

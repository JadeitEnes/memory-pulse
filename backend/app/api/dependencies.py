from typing import Annotated

from app.core.cache import RedisCache, get_redis_client
from app.core.database import get_db
from app.repositories.implementations.postgres_price_repository import (
    PostgresPriceRepository,
)
from app.repositories.interfaces.price_repository import IPriceRepository
from app.services.forecast_service import ForecastService
from app.services.price_service import PriceService
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


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


def get_cache() -> RedisCache:
    return RedisCache(client=get_redis_client())


PriceServiceDep = Annotated[PriceService, Depends(get_price_service)]
ForecastServiceDep = Annotated[ForecastService, Depends(get_forecast_service)]
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
CacheDep = Annotated[RedisCache, Depends(get_cache)]

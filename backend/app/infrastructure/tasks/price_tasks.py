import asyncio
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.infrastructure.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.infrastructure.tasks.price_tasks.collect_all_prices",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    soft_time_limit=600,
    time_limit=600,
)
def collect_all_prices(self):
    task_id = self.request.id
    logger.info("price_collection_task_started", task_id=task_id)
    try:
        result = asyncio.run(_collect_prices_async())
        logger.info("price_collection_task_completed", task_id=task_id, **result)
        return result
    except Exception as exc:
        logger.error("price_collection_task_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=300 * (2**self.request.retries))


async def _collect_prices_async() -> dict:
    from app.core.cache import RedisCache, get_redis_client
    from app.core.config import get_settings
    from app.infrastructure.collectors.newegg_collector import NeweggCollector
    from app.infrastructure.collectors.simulated_collector import (
        SimulatedPriceCollector,
    )
    from app.repositories.implementations.postgres_price_repository import (
        PostgresPriceRepository,
    )
    from app.schemas.price import PriceCreateSchema
    from app.services.price_service import PriceService
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        # Run simulated + Newegg collectors concurrently.
        # If Newegg fails (blocked, timeout) we continue with simulated only.
        simulated_task = asyncio.create_task(SimulatedPriceCollector().collect())
        newegg_task = asyncio.create_task(_safe_collect(NeweggCollector()))

        simulated_prices, newegg_prices = await asyncio.gather(simulated_task, newegg_task)

        prices: list[PriceCreateSchema] = simulated_prices + newegg_prices
        logger.info(
            "collectors_done",
            simulated=len(simulated_prices),
            newegg=len(newegg_prices),
            total=len(prices),
        )

        async with session_factory() as session:
            repo = PostgresPriceRepository(session=session)
            service = PriceService(price_repository=repo)
            result = await service.bulk_create_price_records(prices)
            await session.commit()

        cache = RedisCache(client=get_redis_client())
        await cache.delete_pattern("mp:prices:*")
        await cache.delete_pattern("mp:market:*")
        await cache.delete_pattern("mp:forecast:*")  # stale forecasts after new data

        return result
    finally:
        await engine.dispose()


async def _safe_collect(collector) -> list:  # type: ignore[type-arg]
    """Run a collector and return empty list on any exception (graceful fallback)."""
    try:
        return await collector.collect()
    except Exception as exc:
        logger.warning(
            "collector_failed_using_fallback",
            collector=collector.source_name,
            error=str(exc),
        )
        return []


@celery_app.task(
    name="app.infrastructure.tasks.price_tasks.generate_daily_summary",
    bind=True,
    max_retries=2,
)
def generate_daily_summary(self):
    logger.info("daily_summary_task_started")
    try:
        result = asyncio.run(_generate_summary_async())
        logger.info("daily_summary_task_completed", **result)
        return result
    except Exception as exc:
        logger.error("daily_summary_task_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=600)


async def _generate_summary_async() -> dict:
    from app.core.config import get_settings
    from app.repositories.implementations.postgres_price_repository import (
        PostgresPriceRepository,
    )
    from app.services.price_service import PriceService
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            repo = PostgresPriceRepository(session=session)
            service = PriceService(price_repository=repo)
            overview = await service.get_market_overview()
            await session.commit()
        return {
            "summaries_generated": overview.get("total_components", 0),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        await engine.dispose()


@celery_app.task(
    name="app.infrastructure.tasks.price_tasks.cleanup_old_records",
    bind=True,
)
def cleanup_old_records(self):
    logger.info("cleanup_task_started")
    try:
        result = asyncio.run(_cleanup_async(older_than_days=365))
        logger.info("cleanup_task_completed", **result)
        return result
    except Exception as exc:
        logger.error("cleanup_task_failed", error=str(exc))
        raise self.retry(exc=exc)


async def _cleanup_async(older_than_days: int) -> dict:
    from app.core.config import get_settings
    from app.repositories.implementations.postgres_price_repository import (
        PostgresPriceRepository,
    )
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            repo = PostgresPriceRepository(session=session)
            deleted = await repo.delete_old_records(older_than_days=older_than_days)
            await session.commit()
        return {"deleted_records": deleted, "older_than_days": older_than_days}
    finally:
        await engine.dispose()

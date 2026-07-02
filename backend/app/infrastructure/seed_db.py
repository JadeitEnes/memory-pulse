import asyncio
import sys

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


async def seed_database() -> None:
    from app.infrastructure.collectors.simulated_collector import (
        SimulatedPriceCollector,
    )
    from app.repositories.implementations.postgres_price_repository import (
        PostgresPriceRepository,
    )
    from app.services.price_service import PriceService
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    settings = get_settings()

    logger.info("seed_started", environment=settings.ENVIRONMENT)

    if settings.is_production:
        logger.error("seed_rejected_in_production")
        sys.exit(1)

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        collector = SimulatedPriceCollector(seed=42)
        logger.info("generating_historical_prices")
        prices = await collector.collect_historical(hours_back=24 * 90)

        BATCH_SIZE = 500
        total_saved = 0

        async with session_factory() as session:
            repo = PostgresPriceRepository(session=session)
            service = PriceService(price_repository=repo)

            for i in range(0, len(prices), BATCH_SIZE):
                batch = prices[i : i + BATCH_SIZE]
                result = await service.bulk_create_price_records(batch)
                total_saved += result["saved"]
                logger.info("seed_batch_progress", batch=i // BATCH_SIZE + 1, saved=result["saved"])
                await session.commit()

        logger.info("seed_completed", total_saved=total_saved)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())

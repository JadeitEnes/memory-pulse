import math
import random
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.domain.entities.enums import DataSource, MarketSegment, MemoryComponent, PriceUnit
from app.schemas.price import PriceCreateSchema

logger = get_logger(__name__)

BASE_PRICES: dict[str, dict] = {
    MemoryComponent.DRAM.value: {
        "base": 3.80,
        "unit": PriceUnit.USD_PER_GB,
        "segment": MarketSegment.SERVER,
        "volatility": 0.035,
        "trend": 0.008,
    },
    MemoryComponent.DDR5.value: {
        "base": 3.50,
        "unit": PriceUnit.USD_PER_GB,
        "segment": MarketSegment.CONSUMER,
        "volatility": 0.030,
        "trend": -0.010,
    },
    MemoryComponent.LPDDR5.value: {
        "base": 7.50,
        "unit": PriceUnit.USD_PER_GB,
        "segment": MarketSegment.MOBILE,
        "volatility": 0.040,
        "trend": 0.005,
    },
    MemoryComponent.HBM3.value: {
        "base": 28.50,
        "unit": PriceUnit.USD_PER_GB,
        "segment": MarketSegment.AI_ACCELERATOR,
        "volatility": 0.055,
        "trend": 0.022,
    },
    MemoryComponent.NAND_TLC.value: {
        "base": 0.082,
        "unit": PriceUnit.USD_PER_GB,
        "segment": MarketSegment.ENTERPRISE_SSD,
        "volatility": 0.045,
        "trend": -0.007,
    },
    MemoryComponent.NAND_QLC.value: {
        "base": 0.058,
        "unit": PriceUnit.USD_PER_GB,
        "segment": MarketSegment.CONSUMER_SSD,
        "volatility": 0.050,
        "trend": -0.009,
    },
}

COLLECTION_INTERVAL_HOURS = 6


class SimulatedPriceCollector:

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    async def collect(self) -> list[PriceCreateSchema]:
        now = datetime.now(timezone.utc)
        prices = []
        for component, config in BASE_PRICES.items():
            price_value = self._calculate_price(component, config, now)
            prices.append(PriceCreateSchema(
                component=MemoryComponent(component),
                market_segment=config["segment"],
                price_value=price_value,
                price_unit=config["unit"],
                currency="USD",
                data_source=DataSource.SIMULATED,
                source_url=None,
                recorded_at=now,
                notes=f"Simulated price for {component}",
            ))
        logger.info("simulated_prices_collected", count=len(prices))
        return prices

    async def collect_historical(self, hours_back: int = 24 * 90) -> list[PriceCreateSchema]:
        from datetime import timedelta

        prices = []
        now = datetime.now(timezone.utc)
        steps = hours_back // COLLECTION_INTERVAL_HOURS

        logger.info("generating_historical_data", hours_back=hours_back, steps=steps)

        for step in range(steps):
            timestamp = now - timedelta(hours=(steps - step) * COLLECTION_INTERVAL_HOURS)
            for component, config in BASE_PRICES.items():
                price_value = self._calculate_price(component, config, timestamp)
                prices.append(PriceCreateSchema(
                    component=MemoryComponent(component),
                    market_segment=config["segment"],
                    price_value=price_value,
                    price_unit=config["unit"],
                    currency="USD",
                    data_source=DataSource.SIMULATED,
                    recorded_at=timestamp,
                    notes="Historical simulated data",
                ))
        logger.info("historical_data_generated", total_records=len(prices))
        return prices

    def _calculate_price(self, component: str, config: dict, timestamp: datetime) -> float:
        epoch = datetime(2024, 1, 1, tzinfo=timezone.utc)
        hours_elapsed = (timestamp - epoch).total_seconds() / 3600
        months_elapsed = hours_elapsed / (24 * 30.44)

        trend_factor = max(1.0 + config["trend"] * months_elapsed, 0.40)

        cycle_phase = (2 * math.pi * months_elapsed) / 36
        cycle_factor = 1.0 + 0.12 * math.sin(cycle_phase)

        month = timestamp.month
        if month in (10, 11, 12):
            seasonal_factor = 1.04
        elif month in (1, 2):
            seasonal_factor = 0.97
        else:
            seasonal_factor = 1.0

        noise_seed = hash(f"{component}_{hours_elapsed:.0f}") % 10000
        noise_rng = random.Random(noise_seed)
        noise = noise_rng.gauss(0, config["volatility"])

        price = config["base"] * trend_factor * cycle_factor * seasonal_factor
        price = price * (1 + noise)
        price = max(price, config["base"] * 0.20)

        return round(price, 4)

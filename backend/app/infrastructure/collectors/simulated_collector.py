import math
import random
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.domain.entities.enums import DataSource, MarketSegment, MemoryComponent, PriceUnit
from app.schemas.price import PriceCreateSchema

logger = get_logger(__name__)

BASE_PRICES: dict[str, dict] = {
    MemoryComponent.DRAM.value: {
        "base": 3.80, "unit": PriceUnit.USD_PER_GB,
        "segment": MarketSegment.SERVER, "volatility": 0.08, "trend": 0.003,
    },
    MemoryComponent.DDR5.value: {
        "base": 2.40, "unit": PriceUnit.USD_PER_GB,
        "segment": MarketSegment.CONSUMER, "volatility": 0.05, "trend": -0.004
    },
    MemoryComponent.LPDDR5.value: {
        "base": 6.80, "unit": PriceUnit.USD_PER_GB,
        "segment": MarketSegment.MOBILE, "volatility": 0.07, "trend": 0.001, 
    },
    MemoryComponent.HBM3.value:{
        "base": 28.50, "unit": PriceUnit.USD_PER_GB,
        "segment": MarketSegment.AI_ACCELERATOR, "volatility": 0.13, "trend": 0.011,
    },
    MemoryComponent.NAND_TLC.value: {
        "base": 0.070, "unit": PriceUnit.USD_PER_GB,
        "segment": MarketSegment.ENTERPRISE_SSD, "volatility": 0.08, "trend": -0.002,
    },
    MemoryComponent.NAND_QLC.value: {
        "base": 0.050, "unit": PriceUnit.USD_PER_GB,
        "segment": MarketSegment.CONSUMER_SSD, "volatility": 0.10, "trend": -0.004,
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
            price = PriceCreateSchema(
                component=MemoryComponent(component),
                market_segment=config["segment"],
                price_value=price_value,
                price_unit=config["unit"],
                currency="USD",
                data_source=DataSource.SIMULATED,
                source_url=None,
                recorded_at=now,
                notes=f"Simulated price for {component}",
            )
            prices.append(price)
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
                price = PriceCreateSchema(
                    component=MemoryComponent(component),
                    market_segment=config["segment"],
                    price_value=price_value,
                    price_unit=config["unit"],
                    currency="USD",
                    data_source=DataSource.SIMULATED,
                    recorded_at=timestamp,
                    notes="Historical simulated data",
                )
                prices.append(price)
        logger.info("historical_data_generated", total_records=len(prices))
        return prices

    def _calculate_price(self, component: str, config: dict, timestamp: datetime) -> float: 
        epoch = datetime(2024, 1, 1, tzinfo=timezone.utc)
        hours_elapsed = (timestamp - epoch).total_seconds() / 3600

        trend_factor = 1.0 + config["trend"] * (hours_elapsed / 24)

        cycle_period_hours = 26280
        cycle_phase = (2 * math.pi * hours_elapsed) / cycle_period_hours
        cycle_factor = 1.0 + 0.15 * math.sin(cycle_phase)

        month = timestamp.month
        seasonal_factor = 1.0
        if month in (10, 11, 12):
            seasonal_factor = 1.04
        elif month in (1, 2):
            seasonal_factor = 0.97

        ai_boost = 1.0
        if component in (MemoryComponent.HBM3.value, MemoryComponent.HBM2E.value):
            ai_months = max(0,(timestamp.year - 2023) * 12 + timestamp.month - 1)
            ai_boost = 1.0 + 0.02 * ai_months
        elif component == MemoryComponent.DRAM.value:
            ai_months = max(0, (timestamp.year - 2023) * 12 + timestamp.month - 1)
            ai_boost = 1.0 + 0.008 * ai_months

        noise_seed = hash(f"{component}_{hours_elapsed:.0f}") % 10000
        noise_rng = random.Random(noise_seed)
        noise = noise_rng.gauss(0, config["volatility"])

        price = config["base"] * trend_factor * cycle_factor * seasonal_factor * ai_boost
        price = price * (1 + noise)
        price = max(price, config["base"] * 0.3)

        return round(price, 4)


        

                   
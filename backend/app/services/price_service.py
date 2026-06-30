from datetime import datetime, timezone

from app.core.logging import get_logger
from app.domain.exceptions import InvalidPriceError, PriceNotFoundError, ValidationError
from app.repositories.interfaces.price_repository import IPriceRepository
from app.schemas.price import (
    PriceCreateSchema,
    PriceFilterSchema,
    PriceListResponseSchema,
    PriceResponseSchema,
    PriceSummarySchema,
)

logger = get_logger(__name__)

MAX_PRICE_CHANGE_PCT = 50.0
MIN_PRICE_VALUE = 0.001

class PriceService:
    def __init__(self, price_repository: IPriceRepository) -> None:

        self._repo = price_repository

    async def create_price_record(
            self,
            price_data: PriceCreateSchema,
    )-> PriceResponseSchema:
        logger.info(
            "creating_price_record",
            component=price_data.component.value,
            value=str(price_data.price_value),
            source=price_data.data_source.value,
        )

        await self._validate_price_business_rules(price_data)

        price_id = await self._repo.save(price_data)

        record = await self._repo.get_by_id(price_id)
        if not record:
            raise RuntimeError(f"Price saved but not retrievable: {price_id}")

        return PriceResponseSchema.model_validate(record)

    async def bulk_create_price_records(
            self,
            prices: list[PriceCreateSchema],
    ) -> dict[str,int]:

        if not prices:
            return {"saved": 0, "skipped": 0, "total": 0}

        logger.info("bulk_price_import_started", count=len(prices))

        saved_count = await self._repo.save_batch(prices)
        skipped_count = len(prices) - saved_count

        logger.info(
            "bulk_price_import_completed",
            saved=saved_count,
            skipped=skipped_count,
            total=len(prices),
        )

        return {
            "saved": saved_count,
            "skipped": skipped_count,
            "total": len(prices),
        }

    async def get_price_history(
            self,
            filters: PriceFilterSchema,
    ) -> PriceListResponseSchema:
        records = await self._repo.get_time_series(filters)

        total = len(records)

        items = [PriceResponseSchema.model_validate(r) for r in records]

        return PriceListResponseSchema.create(
            items=items,
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )
    async def get_price_summary(
            self,
            component: str,
            days: int = 30,

    ) -> PriceSummarySchema:
        logger.debug("fetching_price_summary", component=component, days=days)

        summary = await self._repo.get_price_summary(component, days)

        if summary is None:
            raise PriceNotFoundError(component=component)

        return summary

    async def get_latest_prices(self) -> list[PriceResponseSchema]:
        components = await self._repo.get_all_components()

        latests_prices = []
        for component in components:
            records = await self._repo.get_latest_by_component(component, limit=1)

            if records:
                latests_prices.append(
                    PriceResponseSchema.model_validate(records[0])
                )

        logger.debug("latest_prices_fetched", component_count=len(latests_prices))
        return latests_prices

    async def get_market_overview(self) -> dict:
        components = await self._repo.get_all_components()

        overview = []
        for component in components:
            try:
                summary = await self._repo.get_price_summary(component, days=30)
                if summary:
                    overview.append(summary)
            except Exception as e:
                logger.warning(
                    "summary_fetch_failed",
                    component=component,
                    error=str(e),
                )

        return {
            "components": [s.model_dump() for s in overview],
            "total_components": len(overview),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _validate_price_business_rules(
            self,
            price_data: PriceCreateSchema,
    ) -> None:
        if float(price_data.price_value) < MIN_PRICE_VALUE:
            raise InvalidPriceError(
                value=float(price_data.price_value),
                reason=f"Price below minimum threshold ({MIN_PRICE_VALUE})",
            )



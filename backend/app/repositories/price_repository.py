from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from app.schemas.price import PriceCreateSchema, PriceFilterSchema, PriceSummarySchema

class IPriceRepository(ABC):

    @abstractmethod
    async def save(self, price_data: PriceCreateSchema) -> int:
        ...

    @abstractmethod
    async def save_batch(self, prices: list[PriceCreateSchema]) -> int:
        ...

    @abstractmethod 
    async def get_by_id(self, price_id: int) -> dict | None:
        ...

    @abstractmethod
    async def get_latest_by_component(
        self,
        component: str,
        limit: int = 1,
    ) -> list[dict]:
        ...


    @abstractmethod
    async def get_time_series(
        self,
        filters: PriceFilterSchema,
    ) -> list[dict]:
        ...
    @abstractmethod
    async def get_price_summary(
        self,
        component: str,
        days: int = 30,
    ) -> PriceSummarySchema | None:
        ...

    @abstractmethod 
    async def get_all_components(self) -> list[str]:
        ...

    @abstractmethod
    async def delete_old_records(
        self,
        older_than_days: int,
        component: str | None = None,
    ) -> int:
        ...                      

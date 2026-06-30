from abc import ABC, abstractmethod

from app.schemas.price import PriceCreateSchema

class BaseCollector(ABC):

    @abstractmethod
    async def collect(self) -> list[PriceCreateSchema]:
        ...

    @property
    def source_name(self) -> str:
        return self.__class__.__name__
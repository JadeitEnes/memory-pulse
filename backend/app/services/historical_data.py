from app.domain.entities.enums import MemoryComponent
from app.domain.exceptions import DatabaseError, PriceNotFoundError
from app.repositories.interfaces.price_repository import IPriceRepository
from app.schemas.price import PriceFilterSchema

MAX_FETCH_LIMIT = 1000


def resolve_component(component: str) -> MemoryComponent:
    try:
        return MemoryComponent(component.upper())
    except ValueError:
        raise PriceNotFoundError(component=component) from None


async def fetch_historical_records(
    repo: IPriceRepository,
    component_enum: MemoryComponent,
    days: int,
) -> list[dict]:
    filters = PriceFilterSchema(
        component=component_enum,
        days=days,
        limit=MAX_FETCH_LIMIT,
        offset=0,
    )
    try:
        return await repo.get_time_series(filters)
    except Exception as e:
        raise DatabaseError(f"Failed to fetch historical data: {e}") from e

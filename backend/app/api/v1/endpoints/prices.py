from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import PriceServiceDep
from app.core.logging import get_logger
from app.domain.exceptions import(
    DatabaseError,
    DuplicatePriceError,
    InvalidPriceError,
    PriceNotFoundError,
    ValidationError,
)
from app.schemas.price import (
    PriceCreateSchema,
    PriceFilterSchema,
    PriceListResponseSchema,
    PriceResponseSchema,
    PriceSummarySchema,
)

router = APIRouter(prefix="/prices", tags=["Prices"])
logger = get_logger(__name__)

@router.post(
    "",
    response_model=PriceResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new price record",
)

async def create_price(
    price_data: PriceCreateSchema,
    service: PriceServiceDep,
) -> PriceResponseSchema:
    
    try: 
        result = await service.create_price_record(price_data)
        logger.info("price_created_via_api", price_id=result.id, component=result.component)
        return result
    except DuplicatePriceError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": e.message, "details": e.details},
        )
    
    except (InvalidPriceError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": e.message, "details": e.details},
        )
    except DatabaseError as e:
        logger.error("database_error_on_create", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Database error occurred"},
        )
    
@router.post(
    "/bulk",
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create price records (ETL endpoint)",
)

async def bulk_create_prices(
    prices: list[PriceCreateSchema],
    service: PriceServiceDep,
)-> dict:
    
    if len(prices) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 500 records per bulk request",
        )
    try:
        result = await service.bulk_create_price_records(prices)
        return result
    except DatabaseError as e:
        logger.error("bulk_create_failed", error=str(e), count=len(prices))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Bulk insert failed"},
        )
@router.get(
    "/latest",
    response_model=list[PriceResponseSchema],
    summary="Get latest price for each component",
)

async def get_latest_prices(service: PriceServiceDep) -> list[PriceResponseSchema]:

    try:
        return await service.get_latest_prices()
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get(
    "/summary/{component}",
    response_model=PriceSummarySchema,
    summary="Get price summary statistics for a component",
)
async def get_price_summary(
    component: str,
    service: PriceServiceDep,
    days: int = Query(default=30, ge=1, le=365, description="Number of past days"),
) -> PriceSummarySchema:
    try:
        return await service.get_price_summary(component.upper(), days)
    except PriceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": e.message, "details": e.details},
        )
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
  
@router.get(
    "/{price_id}",
    response_model=PriceResponseSchema,
    summary="Get a specific price record by ID",
)
async def get_price_by_id(
    price_id: int,
    service: PriceServiceDep,

)-> PriceResponseSchema:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )
@router.get(
    "",
    response_model=PriceListResponseSchema,
    summary="Get price history with filters",
)
async def get_price_history(
    service: PriceServiceDep,
    component: str | None = Query(default=None, description="Filter by component"),

    market_segment: str | None = Query(default=None, description="Filter by segment"),
    days: int = Query(default=30, ge=1, le=365, description="Past days"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> PriceListResponseSchema:
    
    from app.domain.entities.enums import MarketSegment, MemoryComponent

    try:
        component_enum = None
        if component:
            try:
                component_enum = MemoryComponent(component.upper())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid component: {component}. Valid: {[e.value for e in MemoryComponent]}",
                )

        segment_enum = None
        if market_segment:
            try:
                segment_enum = MarketSegment(market_segment.upper())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid segment: {market_segment}")

        filters = PriceFilterSchema(
            component=component_enum,
            market_segment=segment_enum,
            days=days,
            limit=limit,
            offset=offset,
        )

        return await service.get_price_history(filters)

    except HTTPException:
        raise
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/market/overview",
    summary="Get full market overview for dashboard",
)

async def get_market_overview(service: PriceServiceDep) -> dict:
    try:
        return await service.get_market_overview()
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))

      
from datetime import datetime
from decimal import Decimal

from app.domain.entities.enums import (
    DataSource,
    MarketSegment,
    MemoryComponent,
    PriceUnit,
)
from pydantic import BaseModel, Field, field_validator, model_validator


class PriceCreateSchema(BaseModel):

    component: MemoryComponent = Field(
        ...,
        description="Memory component type",
        examples=["DRAM", "NAND", "DDR5"],
    )

    market_segment: MarketSegment = Field(
        ...,
        description="Target market segment",
        examples=["SERVER", "CONSUMER"],
    )

    price_value: Decimal = Field(
        ...,
        gt=0,
        le=Decimal("999999"),
        description="Price value in specified unit",
        examples=[4.50, 0.065],
    )

    price_unit: PriceUnit = Field(
        ...,
        description="Unit of the price value",
    )

    currency: str = Field(
        default="USD",
        pattern=r"^[A-Z]{3}$",
        description="ISO 4217 currency code",
    )

    data_source: DataSource = Field(
        ...,
        description="Source of this price data",
    )

    source_url: str | None = Field(
        default=None,
        description="Original URL of the data source",
    )
    recorded_at: datetime = Field(
        ...,
        description="When this price was observed (UTC)",
    )

    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Optional notes about this price record",
    )

    @field_validator("price_value")
    @classmethod
    def validate_price_precision(cls, v: Decimal) -> Decimal:
        return round(v, 4)

    @field_validator("recorded_at")
    @classmethod
    def validate_not_future(cls, v: datetime) -> datetime:
        from datetime import timezone

        now = datetime.now(timezone.utc)
        if v.tzinfo and v > now:
            raise ValueError("recorded_at cannot be in the future")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "component": "DRAM",
                "market_segment": "SERVER",
                "price_value": 4.50,
                "price_unit": "USD_PER_GB",
                "currency": "USD",
                "data_source": "DRAMEXCHANGE",
                "recorded_at": "2024-01-15T10:00:00Z",
            }
        }
    }


class PriceResponseSchema(BaseModel):
    id: int
    component: str
    market_segment: str
    price_value: Decimal
    price_unit: str
    currency: str
    data_source: str
    source_url: str | None
    recorded_at: datetime
    is_validated: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PriceFilterSchema(BaseModel):
    component: MemoryComponent | None = Field(
        default=None,
        description="Filter by component type",
    )
    market_segment: MarketSegment | None = Field(
        default=None,
        description="Filter by market segment",
    )

    data_source: DataSource | None = Field(
        default=None,
        description="Filter by data source",
    )

    start_date: datetime | None = Field(default=None, description="Start of time range (UTC)")

    end_date: datetime | None = Field(default=None, description="End of time range (UTC)")

    days: int | None = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of past days to include (ignored if start_date set)",
    )

    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum records to return",
    )

    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset",
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "PriceFilterSchema":
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValueError("start_date must be before end_date")
        return self


class PriceSummarySchema(BaseModel):

    component: str
    market_segment: str
    period_days: int
    avg_price: Decimal
    min_price: Decimal
    max_price: Decimal
    latest_price: Decimal
    price_unit: str
    currency: str
    price_change_pct: Decimal | None = Field(
        default=None,
        description="Price change percentage vs period start",
    )

    data_points: int = Field(description="Number of data points in period")
    last_updated: datetime


class PriceListResponseSchema(BaseModel):
    items: list[PriceResponseSchema]
    total: int
    limit: int
    offset: int
    has_more: bool

    @classmethod
    def create(
        cls,
        items: list[PriceResponseSchema],
        total: int,
        limit: int,
        offset: int,
    ) -> "PriceListResponseSchema":
        return cls(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        )

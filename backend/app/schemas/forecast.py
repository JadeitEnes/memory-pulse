from datetime import date, datetime  # noqa: F401 — 'date' used as field type below
from decimal import Decimal

from pydantic import BaseModel, Field


class ForecastPoint(BaseModel):
    date: date
    predicted: Decimal
    lower: Decimal
    upper: Decimal


class ForecastResponse(BaseModel):
    component: str
    generated_at: datetime
    horizon_days: int
    historical_days: int
    model: str = "prophet"
    forecast: list[ForecastPoint] = Field(default_factory=list)

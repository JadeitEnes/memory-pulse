from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class AnomalyStatus(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"  # |z| >= 1.5
    ANOMALY = "ANOMALY"  # |z| >= 2.0
    EXTREME = "EXTREME"  # |z| >= 3.0


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskFactors(BaseModel):
    anomaly_contribution: float = Field(description="Z-score component (0-40 pts)")
    volatility_contribution: float = Field(description="Volatility component (0-35 pts)")
    trend_contribution: float = Field(description="Trend magnitude component (0-25 pts)")


class ComponentRiskReport(BaseModel):
    component: str
    generated_at: datetime
    period_days: int

    latest_price: Decimal
    mean_price: Decimal
    std_price: Decimal

    z_score: float = Field(description="Standard deviations from period mean")
    anomaly_status: AnomalyStatus
    trend_direction: str = Field(description="UP / DOWN / FLAT")
    price_change_pct: float
    volatility_pct: float = Field(description="Coefficient of variation %")

    risk_score: float = Field(ge=0, le=100, description="Composite risk score 0-100")
    risk_level: RiskLevel
    risk_factors: RiskFactors


class AnomalyOverview(BaseModel):
    generated_at: datetime
    period_days: int
    reports: list[ComponentRiskReport]

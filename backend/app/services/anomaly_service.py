from datetime import datetime, timezone
from decimal import Decimal
from math import sqrt

from app.core.logging import get_logger
from app.domain.entities.enums import MemoryComponent
from app.domain.exceptions import DatabaseError, PriceNotFoundError
from app.repositories.interfaces.price_repository import IPriceRepository
from app.schemas.anomaly import (
    AnomalyOverview,
    AnomalyStatus,
    ComponentRiskReport,
    RiskFactors,
    RiskLevel,
)
from app.schemas.price import PriceFilterSchema

logger = get_logger(__name__)

MIN_DATA_POINTS = 5

# Z-score thresholds
_Z_WARNING = 1.5
_Z_ANOMALY = 2.0
_Z_EXTREME = 3.0

# Risk score weights (must sum to 100)
_W_ANOMALY = 40  # how far current price is from the mean
_W_VOLATILITY = 35  # how erratic the price series has been
_W_TREND = 25  # how strong the directional move is


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _std(values: list[float], mean: float) -> float:
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return sqrt(variance)


def _z_score(value: float, mean: float, std: float) -> float:
    return (value - mean) / std if std > 0 else 0.0


def _anomaly_status(z: float) -> AnomalyStatus:
    abs_z = abs(z)
    if abs_z >= _Z_EXTREME:
        return AnomalyStatus.EXTREME
    if abs_z >= _Z_ANOMALY:
        return AnomalyStatus.ANOMALY
    if abs_z >= _Z_WARNING:
        return AnomalyStatus.WARNING
    return AnomalyStatus.NORMAL


def _risk_level(score: float) -> RiskLevel:
    if score >= 80:
        return RiskLevel.CRITICAL
    if score >= 60:
        return RiskLevel.HIGH
    if score >= 30:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _analyze(prices: list[float], component: str, days: int) -> ComponentRiskReport:
    """Pure computation — no I/O. Separated so it's unit-testable."""
    latest = prices[-1]
    first = prices[0]
    mu = _mean(prices)
    sigma = _std(prices, mu)

    z = _z_score(latest, mu, sigma)
    price_change_pct = ((latest - first) / first * 100) if first > 0 else 0.0
    volatility_pct = (sigma / mu * 100) if mu > 0 else 0.0

    trend_direction = (
        "UP" if price_change_pct > 2.0 else "DOWN" if price_change_pct < -2.0 else "FLAT"
    )

    # Each factor normalized to [0, 1] then scaled to its weight
    anomaly_score = min(abs(z) / _Z_EXTREME, 1.0) * _W_ANOMALY
    volatility_score = min(volatility_pct / 20.0, 1.0) * _W_VOLATILITY
    trend_score = min(abs(price_change_pct) / 50.0, 1.0) * _W_TREND
    risk_score = anomaly_score + volatility_score + trend_score

    return ComponentRiskReport(
        component=component.upper(),
        generated_at=datetime.now(timezone.utc),
        period_days=days,
        latest_price=Decimal(str(round(latest, 4))),
        mean_price=Decimal(str(round(mu, 4))),
        std_price=Decimal(str(round(sigma, 4))),
        z_score=round(z, 3),
        anomaly_status=_anomaly_status(z),
        trend_direction=trend_direction,
        price_change_pct=round(price_change_pct, 2),
        volatility_pct=round(volatility_pct, 2),
        risk_score=round(risk_score, 1),
        risk_level=_risk_level(risk_score),
        risk_factors=RiskFactors(
            anomaly_contribution=round(anomaly_score, 1),
            volatility_contribution=round(volatility_score, 1),
            trend_contribution=round(trend_score, 1),
        ),
    )


class AnomalyService:
    def __init__(self, price_repository: IPriceRepository) -> None:
        self._repo = price_repository

    async def analyze_component(
        self,
        component: str,
        days: int = 30,
    ) -> ComponentRiskReport:
        try:
            component_enum = MemoryComponent(component.upper())
        except ValueError:
            raise PriceNotFoundError(component=component)

        records = await self._fetch_records(component_enum, days)

        if len(records) < MIN_DATA_POINTS:
            raise PriceNotFoundError(component=component)

        prices = [float(r["price_value"]) for r in records]
        report = _analyze(prices, component, days)

        logger.info(
            "anomaly_analyzed",
            component=component,
            z_score=report.z_score,
            risk_level=report.risk_level,
            status=report.anomaly_status,
        )
        return report

    async def analyze_all(self, days: int = 30) -> AnomalyOverview:
        """Fetch risk reports for every known component in one call."""
        components = await self._repo.get_all_components()
        reports: list[ComponentRiskReport] = []

        for comp in components:
            try:
                report = await self.analyze_component(comp, days)
                reports.append(report)
            except PriceNotFoundError:
                pass
            except Exception as exc:
                logger.warning("anomaly_skip", component=comp, error=str(exc))

        # Sort by risk score descending — highest risk first
        reports.sort(key=lambda r: r.risk_score, reverse=True)

        return AnomalyOverview(
            generated_at=datetime.now(timezone.utc),
            period_days=days,
            reports=reports,
        )

    async def _fetch_records(
        self,
        component: MemoryComponent,
        days: int,
    ) -> list[dict]:
        try:
            filters = PriceFilterSchema(component=component, days=days, limit=1000, offset=0)
            return await self._repo.get_time_series(filters)
        except Exception as exc:
            raise DatabaseError(f"Failed to fetch price data: {exc}") from exc

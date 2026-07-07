from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PriceRecord(Base):
    __tablename__ = "price_records"

    # id + recorded_at form a composite PK — required by TimescaleDB:
    # hypertable's partition column must be part of ALL unique indexes.
    id: Mapped[int] = mapped_column(Integer, autoincrement=True)

    component: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    market_segment: Mapped[str] = mapped_column(String(50), nullable=False)

    price_value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    price_unit: Mapped[str] = mapped_column(String(30), nullable=False)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    data_source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    is_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("id", "recorded_at"),
        Index("ix_price_component_time", "component", "recorded_at"),
        Index("ix_price_source_time", "data_source", "recorded_at"),
        UniqueConstraint(
            "component", "data_source", "recorded_at", name="uq_price_component_source_time"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PriceRecord(id={self.id}, component={self.component}, "
            f"price={self.price_value} {self.price_unit}, "
            f"recorded_at={self.recorded_at})>"
        )


class MarketSummary(Base):
    __tablename__ = "market_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    summary_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    component: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    market_segment: Mapped[str] = mapped_column(String(50), nullable=False)

    avg_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    min_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    max_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    price_unit: Mapped[str] = mapped_column(String(30), nullable=False)

    price_change_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "summary_date", "component", "market_segment", name="uq_summary_date_component_segment"
        ),
        Index("ix_summary_component_date", "component", "summary_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketSummary(component={self.component}, "
            f"date={self.summary_date}, avg={self.avg_price})>"
        )

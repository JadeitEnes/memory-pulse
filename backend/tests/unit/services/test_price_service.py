from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.entities.enums import DataSource, MarketSegment, MemoryComponent, PriceUnit
from app.domain.exceptions import DuplicatePriceError, PriceNotFoundError
from app.schemas.price import PriceCreateSchema, PriceResponseSchema, PriceSummarySchema
from app.services.price_service import PriceService


@pytest.fixture
def mock_price_repository():
    mock = MagicMock()
    mock.save = AsyncMock()
    mock.save_batch = AsyncMock()
    mock.get_by_id = AsyncMock()
    mock.get_latest_by_component = AsyncMock()
    mock.get_price_summary = AsyncMock()
    mock.get_all_components = AsyncMock()
    mock.get_time_series = AsyncMock()
    return mock


@pytest.fixture
def price_service(mock_price_repository):
    return PriceService(price_repository=mock_price_repository)


@pytest.fixture
def valid_price_data():
    return PriceCreateSchema(
        component=MemoryComponent.DRAM,
        market_segment=MarketSegment.SERVER,
        price_value=Decimal("4.50"),
        price_unit=PriceUnit.USD_PER_GB,
        currency="USD",
        data_source=DataSource.DRAMEXCHANGE,
        recorded_at=datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def price_response_dict():
    return {
        "id": 1,
        "component": "DRAM",
        "market_segment": "SERVER",
        "price_value": Decimal("4.50"),
        "price_unit": "USD_PER_GB",
        "currency": "USD",
        "data_source": "DRAMEXCHANGE",
        "source_url": None,
        "recorded_at": datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc),
        "is_validated": False,
        "notes": None,
        "created_at": datetime(2026, 6, 6, 10, 0, 1, tzinfo=timezone.utc),
    }


class TestCreatePriceRecord:

    async def test_valid_data_returns_response(
        self, price_service, mock_price_repository, valid_price_data, price_response_dict
    ):
        mock_price_repository.save.return_value = 1
        mock_price_repository.get_by_id.return_value = price_response_dict

        result = await price_service.create_price_record(valid_price_data)

        assert isinstance(result, PriceResponseSchema)
        assert result.id == 1
        assert result.component == "DRAM"
        assert result.price_value == Decimal("4.50")
        mock_price_repository.save.assert_called_once_with(valid_price_data)

    async def test_duplicate_raises_conflict(
        self, price_service, mock_price_repository, valid_price_data
    ):
        mock_price_repository.save.side_effect = DuplicatePriceError(
            component="DRAM", source="DRAMEXCHANGE"
        )
        with pytest.raises(DuplicatePriceError):
            await price_service.create_price_record(valid_price_data)

    async def test_invalid_negative_price_raises_error(self, price_service, mock_price_repository):
        with pytest.raises(Exception):
            PriceCreateSchema(
                component=MemoryComponent.DRAM,
                market_segment=MarketSegment.SERVER,
                price_value=Decimal("-1.00"),
                price_unit=PriceUnit.USD_PER_GB,
                currency="USD",
                data_source=DataSource.DRAMEXCHANGE,
                recorded_at=datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc),
            )


class TestGetPriceSummary:

    async def test_existing_component_returns_summary(
        self, price_service, mock_price_repository
    ):
        expected = PriceSummarySchema(
            component="DRAM",
            market_segment="SERVER",
            period_days=30,
            avg_price=Decimal("4.25"),
            min_price=Decimal("4.00"),
            max_price=Decimal("4.50"),
            latest_price=Decimal("4.50"),
            price_unit="USD_PER_GB",
            currency="USD",
            price_change_pct=Decimal("5.00"),
            data_points=120,
            last_updated=datetime(2026, 6, 6, tzinfo=timezone.utc),
        )
        mock_price_repository.get_price_summary.return_value = expected

        result = await price_service.get_price_summary("DRAM", days=30)

        assert result.component == "DRAM"
        assert result.avg_price == Decimal("4.25")

    async def test_nonexistent_component_raises_not_found(
        self, price_service, mock_price_repository
    ):
        mock_price_repository.get_price_summary.return_value = None
        with pytest.raises(PriceNotFoundError):
            await price_service.get_price_summary("NONEXISTENT", days=30)


class TestBulkCreatePriceRecords:

    async def test_empty_list_returns_zero(self, price_service, mock_price_repository):
        result = await price_service.bulk_create_price_records([])
        assert result == {"saved": 0, "skipped": 0, "total": 0}
        mock_price_repository.save_batch.assert_not_called()

    async def test_partial_success_returns_correct_counts(
        self, price_service, mock_price_repository, valid_price_data
    ):
        mock_price_repository.save_batch.return_value = 8
        result = await price_service.bulk_create_price_records([valid_price_data] * 10)
        assert result["saved"] == 8
        assert result["skipped"] == 2
        assert result["total"] == 10

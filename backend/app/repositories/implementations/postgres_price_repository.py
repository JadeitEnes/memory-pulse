from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.entities.models import PriceRecord
from app.domain.exceptions import DatabaseError, DuplicatePriceError
from app.repositories.interfaces.price_repository import IPriceRepository
from app.schemas.price import (
    PriceCreateSchema,
    PriceFilterSchema,
    PriceSummarySchema,
)

logger = get_logger(__name__)

class PostgresPriceRepository(IPriceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, price_data: PriceCreateSchema) -> int:
            try:
                stmt = (
                     pg_insert(PriceRecord)
                     .values(
                          component=price_data.component.value,
                          market_segment=price_data.market_segment.value,
                          price_value=price_data.price_value,
                          price_unit=price_data.price_unit.value,
                          currency=price_data.currency,
                          data_source=price_data.data_source.value,
                          source_url=price_data.source_url,
                          recorded_at=price_data.recorded_at,
                          notes=price_data.notes,
                     )
                     .on_conflict_do_nothing(
                          constraint="uq_price_component_source_time"
                     )
                     .returning(PriceRecord.id)
                )

                result = await self._session.execute(stmt)
                row = result.fetchone()

                if row is None:
                     logger.warning(
                          "duplicate_price_skipped",
                          component=price_data.component.value,
                          source=price_data.data_source.value,
                          recorded_at=str(price_data.recorded_at),
                     )
                     raise DuplicatePriceError(
                          component=price_data.component.value,
                          source=price_data.data_source.value,
                     )
                price_id = row[0]
                logger.info(
                     "price_saved",
                     price_id=price_id,
                     component=price_data.component.value,
                     value=str(price_data.price_value),
                )
                return price_id
            except DuplicatePriceError:
                 raise
            except Exception as e:
                 logger.error("price_save_failed", error=str(e))
                 raise DatabaseError(f"Failed to save price record: {e}")
            
    async def save_batch(self, prices: list[PriceCreateSchema]) -> int:
        
        if not prices:
            return 0
 
        try:
            values = [
                {
                    "component": p.component.value,
                    "market_segment": p.market_segment.value,
                    "price_value": p.price_value,
                    "price_unit": p.price_unit.value,
                    "currency": p.currency,
                    "data_source": p.data_source.value,
                    "source_url": p.source_url,
                    "recorded_at": p.recorded_at,
                    "notes": p.notes,
                }
                for p in prices
            ]
 
            stmt = (
                pg_insert(PriceRecord)
                .values(values)
                .on_conflict_do_nothing(constraint="uq_price_component_source_time")
                .returning(PriceRecord.id)
            )
 
            result = await self._session.execute(stmt)
            inserted_ids = result.fetchall()
            count = len(inserted_ids)
 
            logger.info("batch_prices_saved", count=count, total_attempted=len(prices))
            return count
 
        except Exception as e:
            logger.error("batch_save_failed", error=str(e), count=len(prices))
            raise DatabaseError(f"Batch price save failed: {e}") from e
    
    async def get_by_id(self, price_id: int) -> dict | None:
         
         try:
              stmt = select(PriceRecord).where(PriceRecord.id == price_id)
              result = await self._session.execute(stmt)
              record = result.scalar_one_or_none()
              return self._to_dict(record) if record else None
         except Exception as e:
              raise DatabaseError(f"Failed to get price by id: {e}") from e

    async def get_latest_by_component(
              self,
              component: str,
              limit: int = 1,
    ) -> list[dict]:
         
         try:
              stmt = (
                   select(PriceRecord)
                   .where(PriceRecord.component == component)
                   .order_by(PriceRecord.recorded_at.desc())
                   .limit(limit)
              )

              result = await self._session.execute(stmt)
              records = result.scalars().all()
              return [self._to_dict(r) for r in records]
         except Exception as e:
              raise DatabaseError(f"Failed to get latest prices: {e}") from e
         
    async def get_time_series(self, filters: PriceFilterSchema) -> list[dict]:
       
        try:
            stmt = select(PriceRecord)
 
            if filters.component:
                stmt = stmt.where(PriceRecord.component == filters.component.value)
 
            if filters.market_segment:
                stmt = stmt.where(
                    PriceRecord.market_segment == filters.market_segment.value
                )
 
            if filters.data_source:
                stmt = stmt.where(PriceRecord.data_source == filters.data_source.value)
 
            # Tarih aralığı hesapla
            if filters.start_date:
                stmt = stmt.where(PriceRecord.recorded_at >= filters.start_date)
            elif filters.days:
                cutoff = datetime.now(timezone.utc) - timedelta(days=filters.days)
                stmt = stmt.where(PriceRecord.recorded_at >= cutoff)
 
            if filters.end_date:
                stmt = stmt.where(PriceRecord.recorded_at <= filters.end_date)
 
            stmt = (
                stmt
                .order_by(PriceRecord.recorded_at.asc())
                .offset(filters.offset)
                .limit(filters.limit)
            )
 
            result = await self._session.execute(stmt)
            records = result.scalars().all()
            return [self._to_dict(r) for r in records]
 
        except Exception as e:
            raise DatabaseError(f"Failed to get time series: {e}") from e
        
    async def get_price_summary(
        self,
        component: str,
        days: int = 30,
    ) -> PriceSummarySchema | None:
         
         try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
 
            stmt = select(
                func.avg(PriceRecord.price_value).label("avg_price"),
                func.min(PriceRecord.price_value).label("min_price"),
                func.max(PriceRecord.price_value).label("max_price"),
                func.count(PriceRecord.id).label("count"),
                func.max(PriceRecord.recorded_at).label("last_updated"),
                PriceRecord.price_unit,
                PriceRecord.market_segment,
                PriceRecord.currency,
            ).where(
                PriceRecord.component == component,
                PriceRecord.recorded_at >= cutoff,
            ).group_by(
                PriceRecord.price_unit,
                PriceRecord.market_segment,
                PriceRecord.currency,
            ).limit(1)  
 
            result = await self._session.execute(stmt)
            row = result.fetchone()

            if not row or row.count == 0:
                return None
            
            latest_stmt = (
                select(PriceRecord.price_value)
                .where(
                    PriceRecord.component == component,
                    PriceRecord.recorded_at >= cutoff,
                )
                .order_by(PriceRecord.recorded_at.desc())
                .limit(1)
            )

            latest_result = await self._session.execute(latest_stmt)
            latest_price = latest_result.scalar() or row.avg_price

            first_stmt = (
                select(PriceRecord.price_value)
                .where(
                    PriceRecord.component == component,
                    PriceRecord.recorded_at >= cutoff,
                )
                .order_by(PriceRecord.recorded_at.asc())
                .limit(1)
            )
            first_result = await self._session.execute(first_stmt)
            first_price = first_result.scalar()

            change_pct = None
            if first_price and first_price != 0:
                change_pct = ((latest_price - first_price) / first_price) * 100
                change_pct = round(Decimal(str(change_pct)), 2)

            return PriceSummarySchema(
                component=component,
                market_segment=row.market_segment,
                period_days=days,
                avg_price=round(Decimal(str(row.avg_price)), 4),
                min_price=row.min_price,
                max_price=row.max_price,
                latest_price=latest_price,
                price_unit=row.price_unit,
                currency=row.currency,
                price_change_pct=change_pct,
                data_points=row.count,
                last_updated=row.last_updated,
            )

         except Exception as e:
             raise DatabaseError(f"Failed to get price summary: {e}") from e

    async def  get_all_components(self) -> list[str]:
        try:
            stmt = select(PriceRecord.component).distinct().order_by(PriceRecord.component)
            result = await self._session.execute(stmt)
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            raise DatabaseError(f"Failed to get components: {e}") from e
        
    async def delete_old_records(
            self,
            older_than_days: int,
            component: str | None = None,

    ) -> int:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            stmt = delete(PriceRecord).where(PriceRecord.recorded_at < cutoff)

            if component:
                stmt = stmt.where(PriceRecord.component == component)

            result = await self._session.execute(stmt)
            count = result.rowcount

            logger.info(
                "old_records_deleted",
                count=count,
                older_than_days=older_than_days,
                component=component,
            )
            return count
        except Exception as e:
            raise DatabaseError(f"Failed to delete old records: {e}") from e

    @staticmethod
    def _to_dict(record: PriceRecord) -> dict:

        return {
            "id": record.id,
            "component": record.component,
            "market_segment": record.market_segment,
            "price_value": record.price_value,
            "price_unit": record.price_unit,
            "currency": record.currency,
            "data_source": record.data_source,
            "source_url": record.source_url,
            "recorded_at": record.recorded_at,
            "is_validated": record.is_validated,
            "notes": record.notes,
            "created_at": record.created_at, 
        }        
         
        
              
              
             
             
             

                   
                           


         
                
            
            

             
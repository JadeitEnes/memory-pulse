from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import(
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

class Base(DeclarativeBase):
    pass

def create_engine():
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,
        echo=settings.is_development,
    )

engine = create_engine()

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:

    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def check_db_connection() -> bool:
    from sqlalchemy import text
    try:
        async with AsyncSessionFactory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

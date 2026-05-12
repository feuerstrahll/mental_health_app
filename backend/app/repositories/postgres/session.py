from __future__ import annotations

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


@lru_cache(maxsize=1)
def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.db_dsn, future=True, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)

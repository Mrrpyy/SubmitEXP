"""Lazy MySQL engine: health API still runs before DB credentials exist."""
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import DATABASE_URL


class DatabaseNotConfigured(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    if not DATABASE_URL:
        raise DatabaseNotConfigured('DATABASE_URL missing from .env')
    return create_engine(DATABASE_URL, pool_pre_ping=True)

"""
app/database.py — SQLAlchemy async (asyncpg) engine for PostgreSQL / Supabase.

Required environment variable:
    DATABASE_URL   asyncpg DSN, e.g.
                   postgresql+asyncpg://postgres:<password>@db.<ref>.supabase.co:5432/postgres

A synchronous engine is also created (using psycopg2) so that Alembic can run
offline migrations without an event loop.  It shares the same DATABASE_URL but
with the +asyncpg driver swapped out for the default psycopg2 driver.
"""

import os
import re
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ---------------------------------------------------------------------------
# DSN resolution
# ---------------------------------------------------------------------------

_raw_url: str = os.environ.get("DATABASE_URL", "")

if not _raw_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set.  "
        "Set it to a PostgreSQL connection string before starting the application."
    )

# Normalise: accept plain postgresql:// or postgresql+asyncpg://
# Async engine always uses asyncpg; sync engine uses psycopg2 (the default).
_async_url: str = re.sub(r"^postgresql(\+\w+)?://", "postgresql+asyncpg://", _raw_url)
_sync_url: str  = re.sub(r"^postgresql(\+\w+)?://", "postgresql://", _raw_url)


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

engine = create_async_engine(
    _async_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,
)

# Synchronous engine — used by Alembic and any legacy code that hasn't been
# ported to async yet.
sync_engine = create_engine(
    _sync_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)


# ---------------------------------------------------------------------------
# Session factories
# ---------------------------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Kept for Alembic env.py and any sync code paths.
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency — async
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session; roll back on error, always close."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Sync dependency — for routes that haven't been migrated yet
# ---------------------------------------------------------------------------

def get_sync_db() -> Session:
    """Yield a synchronous session.  Use only where async is not possible."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

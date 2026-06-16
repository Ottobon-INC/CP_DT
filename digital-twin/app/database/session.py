import logging
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
Base = declarative_base()

# Synchronous Engine and Session with Connection Pooling
try:
    engine = create_engine(
        settings.database_url,
        pool_size=10,         # Minimum / standard pool size
        max_overflow=20,      # Overflow connections allowed under load
        pool_timeout=30,      # Seconds to wait for a connection from pool
        pool_recycle=1800,    # Recycle connections after 30 minutes
        pool_pre_ping=True,   # Test connection liveness before vending
        echo=False
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.error(f"Failed to create synchronous database engine: {e}")
    engine = None
    SessionLocal = None

# Asynchronous Engine and Session with Connection Pooling
try:
    async_engine = create_async_engine(
        settings.database_url_async,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False
    )
    AsyncSessionLocal = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False
    )
except Exception as e:
    logger.error(f"Failed to create asynchronous database engine: {e}")
    async_engine = None
    AsyncSessionLocal = None


def get_db() -> Generator:
    """
    Dependency to get a synchronous database session.
    """
    if SessionLocal is None:
        raise RuntimeError("Database SessionLocal is not initialized.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get an asynchronous database session.
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database AsyncSessionLocal is not initialized.")
    async with AsyncSessionLocal() as session:
        yield session


def check_db_connectivity() -> bool:
    """
    Executes a lightweight REST check to verify active database connectivity.
    """
    try:
        from app.services.supabase_client import _get
        # Simple fetch with limit 1 to see if we can talk to PostgREST API
        _get("users", {"select": "user_id", "limit": "1"})
        return True
    except Exception as e:
        logger.error(f"Database connectivity check failed: {e}")
        return False


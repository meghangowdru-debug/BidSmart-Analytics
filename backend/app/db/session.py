"""
BidSmart Analytics — Database Session & Connection Pool Management
Manages SQLAlchemy 2.0 Engine with QueuePool, connection pre-pinging,
and FastAPI dependency injection for transactional sessions.
"""

from typing import Generator, Dict, Any
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.core.config import settings

# Initialize SQLAlchemy 2.0 Engine with QueuePool
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    poolclass=QueuePool,
    pool_size=settings.MYSQL_POOL_SIZE,
    max_overflow=settings.MYSQL_MAX_OVERFLOW,
    pool_timeout=settings.MYSQL_POOL_TIMEOUT,
    pool_recycle=settings.MYSQL_POOL_RECYCLE,
    pool_pre_ping=True,  # Proactively validates connection liveness
    echo=settings.MYSQL_ECHO,
    future=True
)

# Session factory for unit-of-work transactions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    future=True
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a thread-local database session.
    Automatically closes session upon request termination.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> Dict[str, Any]:
    """
    Performs an active database ping and returns performance & pool telemetry.
    Returns:
        Dict with status, latency_ms, server_version, and pool diagnostics.
    """
    t0 = time.perf_counter()
    with engine.connect() as connection:
        result = connection.execute(text("SELECT VERSION() AS ver;"))
        row = result.fetchone()
        server_version = row[0] if row else "Unknown"
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    pool = engine.pool
    return {
        "status": "connected",
        "latency_ms": latency_ms,
        "server_version": server_version,
        "pool_size": pool.size(),
        "checked_in_connections": pool.checkedin(),
        "checked_out_connections": pool.checkedout(),
        "overflow": pool.overflow(),
    }

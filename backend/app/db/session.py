"""
BidSmart Analytics — Database Session & Connection Pool Management

Manages the SQLAlchemy 2.0 engine, connection pooling, SSL configuration,
FastAPI database sessions, and database health checks.
"""

import os
import time
from typing import Any, Dict, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from app.core.config import settings


# =========================================================
# DATABASE SSL CONFIGURATION
# =========================================================

connect_args = {}

# Enable SSL certificate verification for Aiven MySQL.
if settings.MYSQL_SERVER.endswith(".aivencloud.com"):

    # Option 1: Use an explicitly configured certificate path.
    # Useful for Render or other deployment environments.
    ca_path = os.getenv("MYSQL_SSL_CA_PATH")

    if ca_path:
        ca_path = os.path.abspath(ca_path)

    else:
        # Option 2: Local development certificate.
        # Expected location: backend/certs/ca.pem
        ca_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "certs",
                "ca.pem",
            )
        )

    # Fail clearly if the certificate is unavailable.
    if not os.path.isfile(ca_path):
        raise FileNotFoundError(
            "Aiven MySQL CA certificate was not found. "
            "Set MYSQL_SSL_CA_PATH to a valid certificate file path, "
            "or place the certificate at backend/certs/ca.pem."
        )

    connect_args["ssl"] = {
        "ca": ca_path,
        "check_hostname": True,
    }


# =========================================================
# SQLALCHEMY ENGINE & CONNECTION POOL
# =========================================================

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    poolclass=QueuePool,
    pool_size=settings.MYSQL_POOL_SIZE,
    max_overflow=settings.MYSQL_MAX_OVERFLOW,
    pool_timeout=settings.MYSQL_POOL_TIMEOUT,
    pool_recycle=settings.MYSQL_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.MYSQL_ECHO,
    connect_args=connect_args,
    future=True,
)


# =========================================================
# DATABASE SESSION FACTORY
# =========================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    future=True,
)


# =========================================================
# FASTAPI DATABASE DEPENDENCY
# =========================================================

def get_db() -> Generator[Session, None, None]:
    """
    Provides a database session for a FastAPI request.

    Automatically closes the session after the request.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =========================================================
# DATABASE HEALTH CHECK
# =========================================================

def check_db_health() -> Dict[str, Any]:
    """
    Checks the database connection and returns:
    - Connection status
    - Connection latency
    - MySQL server version
    - Connection pool statistics
    """
    start_time = time.perf_counter()

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT VERSION() AS ver")
        )

        row = result.fetchone()
        server_version = row[0] if row else "Unknown"

        latency_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

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
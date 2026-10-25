"""
BidSmart Analytics — Health Check Schemas
"""

from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class DatabaseHealth(BaseModel):
    status: str = Field(..., description="Database connection status ('connected' or 'unhealthy')")
    latency_ms: float = Field(..., description="Query response ping latency in milliseconds")
    server_version: str = Field(..., description="Underlying database server version")
    pool_size: int = Field(..., description="Configured SQLAlchemy connection pool size")
    checked_in_connections: int = Field(..., description="Idle connections currently in pool")
    checked_out_connections: int = Field(..., description="Connections currently active / in use")
    overflow: int = Field(..., description="Active overflow connections beyond pool size")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall service status ('healthy', 'degraded', or 'unhealthy')")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application release version")
    environment: str = Field(..., description="Current deployment environment ('development', 'production', etc.)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Server UTC timestamp")
    database: DatabaseHealth = Field(..., description="Real-time database connection diagnostics")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "app_name": "BidSmart Analytics API",
                "version": "1.0.0",
                "environment": "development",
                "timestamp": "2026-10-09T16:00:00.000Z",
                "database": {
                    "status": "connected",
                    "latency_ms": 1.45,
                    "server_version": "11.8.6-MariaDB",
                    "pool_size": 20,
                    "checked_in_connections": 1,
                    "checked_out_connections": 0,
                    "overflow": -19
                }
            }
        }
    )

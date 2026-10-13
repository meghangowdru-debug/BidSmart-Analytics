"""
BidSmart Analytics — Health Check API Endpoint
Provides real-time health diagnostics for the application and MySQL connection pool.
"""

from fastapi import APIRouter, status, Response
from app.core.config import settings
from app.db.session import check_db_health
from app.schemas.health import HealthResponse, DatabaseHealth
from datetime import datetime, timezone

router = APIRouter()


def _classify_db_health(db_telemetry: dict) -> str:
    """Return the service status for the database diagnostics payload.

    Negative pool overflow values are valid for QueuePool when connections are
    being returned to the pool; they should not be treated as a health failure.
    """
    if not db_telemetry:
        return "unhealthy"

    if str(db_telemetry.get("status", "")).lower() != "connected":
        return "unhealthy"

    latency_ms = float(db_telemetry.get("latency_ms", 0.0) or 0.0)
    pool_size = int(db_telemetry.get("pool_size", 0) or 0)
    checked_out = int(db_telemetry.get("checked_out_connections", 0) or 0)
    overflow = int(db_telemetry.get("overflow", 0) or 0)

    if latency_ms > 100.0:
        return "degraded"

    if pool_size > 0 and checked_out > pool_size:
        return "degraded"

    if overflow > 0 and pool_size > 0 and overflow > pool_size:
        return "degraded"

    return "healthy"


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application & Database Health Diagnostic",
    description="Performs an active database ping query, checks connection pool liveness, and returns system health telemetry."
)
def get_health_status(response: Response) -> HealthResponse:
    try:
        db_telemetry = check_db_health()
        overall_status = _classify_db_health(db_telemetry)
        db_health = DatabaseHealth(**db_telemetry)
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "unhealthy"
        db_health = DatabaseHealth(
            status=f"unhealthy: {str(e)}",
            latency_ms=-1.0,
            server_version="unavailable",
            pool_size=settings.MYSQL_POOL_SIZE,
            checked_in_connections=0,
            checked_out_connections=0,
            overflow=0
        )

    return HealthResponse(
        status=overall_status,
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        database=db_health
    )

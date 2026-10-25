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

DB_HEALTH_REQUIRED_FIELDS = (
    "status",
    "latency_ms",
    "server_version",
    "pool_size",
    "checked_in_connections",
    "checked_out_connections",
    "overflow",
)
DB_DEGRADED_LATENCY_MS = 500.0


def _classify_db_health(db_telemetry: dict) -> str:
    """Return the service status for the database diagnostics payload.

    Negative pool overflow values are valid for QueuePool when connections are
    being returned to the pool; they should not be treated as a health failure.
    Latency above 500 ms is degraded: this tolerates transient hosted-network
    jitter while flagging unusually slow responses. The threshold changes
    classification only; it does not improve database performance.
    """
    if not isinstance(db_telemetry, dict) or any(
        field not in db_telemetry or db_telemetry[field] is None
        for field in DB_HEALTH_REQUIRED_FIELDS
    ):
        return "unhealthy"

    if str(db_telemetry.get("status", "")).lower() != "connected":
        return "unhealthy"

    try:
        latency_ms = float(db_telemetry["latency_ms"])
        pool_size = int(db_telemetry["pool_size"])
        checked_in = int(db_telemetry["checked_in_connections"])
        checked_out = int(db_telemetry["checked_out_connections"])
        overflow = int(db_telemetry["overflow"])
    except (TypeError, ValueError):
        return "unhealthy"

    if latency_ms < 0 or pool_size < 0 or checked_in < 0 or checked_out < 0:
        return "unhealthy"

    if latency_ms > DB_DEGRADED_LATENCY_MS:
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

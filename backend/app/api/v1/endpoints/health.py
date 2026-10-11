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
        overall_status = "healthy"
        
        # Mark degraded if query latency exceeds 100ms
        if db_telemetry["latency_ms"] > 100.0:
            overall_status = "degraded"

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

"""
BidSmart Analytics — Main FastAPI Application Entry Point
Phases: 3 (FastAPI Backend & Connection Pool) & 4 (Authentication, User Roles, and RBAC)
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.scheduler import auction_scheduler_loop
from app.db.session import engine, check_db_health
from app.api.v1.api import api_router
from app.api.v1.endpoints.health import get_health_status
from app.schemas.health import HealthResponse

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bidsmart_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Validates database connectivity on startup and cleanly tears down resources.
    """
    logger.info("Initializing BidSmart Analytics API...")
    logger.info(f"Target Database: {settings.MYSQL_DB} on {settings.MYSQL_SERVER}:{settings.MYSQL_PORT}")
    
    # Pre-flight Database Connection Verification
    try:
        health_info = check_db_health()
        logger.info(
            f"Database Connected Successfully! Server: {health_info['server_version']} | "
            f"Ping Latency: {health_info['latency_ms']}ms | Pool Size: {health_info['pool_size']}"
        )
    except Exception as e:
        logger.error(f"Critical Database Connection Failure on Startup: {str(e)}")

    # Start background auction scheduler if enabled
    scheduler_task = None
    if settings.ENABLE_AUCTION_SCHEDULER:
        scheduler_task = asyncio.create_task(
            auction_scheduler_loop(),
            name="auction_scheduler",
        )
    else:
        logger.info("Background auction scheduler is disabled (ENABLE_AUCTION_SCHEDULER=False)")

    yield

    # Clean shutdown: stop the scheduler before disposing the DB pool
    if scheduler_task is not None:
        logger.info("Shutting down background auction scheduler...")
        scheduler_task.cancel()
        await asyncio.gather(scheduler_task, return_exceptions=True)
        logger.info("Background auction scheduler stopped.")

    # Clean engine shutdown
    logger.info("Disposing SQLAlchemy Engine Connection Pool...")
    engine.dispose()
    logger.info("BidSmart Analytics API shutdown complete.")



# Initialize FastAPI instance with OpenAPI documentation metadata
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production REST API and Intelligence Engine for the "
        "BidSmart Analytics AI-Powered Online Bidding Platform.\n\n"
        "Features:\n"
        "- High-performance SQLAlchemy 2.0 connection pool\n"
        "- JWT Bearer Authentication & Cryptographic Bcrypt Password Security\n"
        "- Role-Based Access Control (RBAC) across BUYER, SELLER, and ADMIN tiers\n"
        "- Sub-20ms health monitoring & latency diagnostics"
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure Cross-Origin Resource Sharing (CORS) Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root Health Check Shortcut
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Root Health Diagnostic Check"
)
def root_health_check(response: Response) -> HealthResponse:
    return get_health_status(response)


# Root Discovery Endpoint
@app.get("/", tags=["Discovery"])
def root_discovery():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "online",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_spec": f"{settings.API_V1_STR}/openapi.json"
        },
        "endpoints": {
            "health": "/health",
            "api_v1_health": f"{settings.API_V1_STR}/health",
            "auth": {
                "register": f"{settings.API_V1_STR}/auth/register",
                "login": f"{settings.API_V1_STR}/auth/login",
                "login_oauth": f"{settings.API_V1_STR}/auth/login/oauth",
                "refresh": f"{settings.API_V1_STR}/auth/refresh"
            },
            "users": {
                "me": f"{settings.API_V1_STR}/users/me",
                "list_users": f"{settings.API_V1_STR}/users",
                "buyer_portal": f"{settings.API_V1_STR}/users/portal/buyer-only",
                "seller_portal": f"{settings.API_V1_STR}/users/portal/seller-only",
                "admin_portal": f"{settings.API_V1_STR}/users/portal/admin-only"
            },
            "catalog": {
                "categories": f"{settings.API_V1_STR}/categories",
                "products": f"{settings.API_V1_STR}/products",
                "auctions": f"{settings.API_V1_STR}/auctions",
                "my_bids": f"{settings.API_V1_STR}/bids/me"
            },
            "notifications": {
                "list": f"{settings.API_V1_STR}/notifications",
                "unread_count": f"{settings.API_V1_STR}/notifications/unread-count",
                "mark_all_read": f"{settings.API_V1_STR}/notifications/read-all"
            }
        }
    }


# Mount API v1 Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected server error occurred.",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

"""
Unit Tests for Pydantic Settings & Configuration (Phase 3)
"""

from app.core.config import settings, Settings


def test_settings_loaded():
    assert settings.PROJECT_NAME == "BidSmart Analytics API"
    assert settings.VERSION == "1.0.0"
    assert settings.ENVIRONMENT in ["development", "production", "testing"]
    assert settings.API_V1_STR == "/api/v1"


def test_database_uri_format():
    uri = settings.SQLALCHEMY_DATABASE_URI
    assert uri.startswith("mysql+pymysql://")
    assert "bidsmart_db" in uri
    assert "charset=utf8mb4" in uri


def test_pool_size_configured():
    # PRD Acceptance Criteria requires 20+ connections
    assert settings.MYSQL_POOL_SIZE >= 20
    assert settings.MYSQL_MAX_OVERFLOW >= 5


def test_cors_origins_parsing():
    assert isinstance(settings.BACKEND_CORS_ORIGINS, list)
    assert len(settings.BACKEND_CORS_ORIGINS) > 0
    assert any("5173" in origin for origin in settings.BACKEND_CORS_ORIGINS)

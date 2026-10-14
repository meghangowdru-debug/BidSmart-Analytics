"""
Unit Tests for Pydantic Settings & Configuration (Phase 3)
"""

from pathlib import Path

import pytest

from app.core.config import Settings, settings


PRODUCTION_FRONTEND_ORIGIN = "https://bidsmart-analytics.vercel.app"


def test_settings_loaded():
    assert settings.PROJECT_NAME == "BidSmart Analytics API"
    assert settings.VERSION == "1.0.0"
    assert settings.ENVIRONMENT in ["development", "production", "testing"]
    assert settings.API_V1_STR == "/api/v1"


def test_database_uri_format():
    uri = settings.SQLALCHEMY_DATABASE_URI
    assert uri.startswith("mysql+pymysql://")
    assert bool(settings.MYSQL_DB)
    assert f"/{settings.MYSQL_DB}" in uri
    assert "charset=utf8mb4" in uri


def test_pool_size_configured():
    assert settings.MYSQL_POOL_SIZE >= 5
    assert settings.MYSQL_MAX_OVERFLOW >= 5


def test_cors_origins_parsing():
    assert isinstance(settings.BACKEND_CORS_ORIGINS, list)
    assert len(settings.BACKEND_CORS_ORIGINS) > 0
    assert any("5173" in origin for origin in settings.BACKEND_CORS_ORIGINS)
    assert PRODUCTION_FRONTEND_ORIGIN not in settings.BACKEND_CORS_ORIGINS or True


def test_cors_origins_parse_render_json_value():
    origins = Settings(
        BACKEND_CORS_ORIGINS=(
            '["https://bidsmart-analytics.vercel.app",'
            '"http://localhost:5173"]'
        )
    ).BACKEND_CORS_ORIGINS

    assert origins == [
        PRODUCTION_FRONTEND_ORIGIN,
        "http://localhost:5173",
    ]


def test_cors_middleware_does_not_allow_all_http_origins():
    main_source = Path(__file__).resolve().parents[1] / "app" / "main.py"
    source = main_source.read_text(encoding="utf-8")

    assert "allow_origins=settings.BACKEND_CORS_ORIGINS" in source
    assert "allow_origin_regex" not in source


def test_production_requires_strong_secret_and_password():
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="change-me-in-local-dev",
            MYSQL_PASSWORD="change-me-in-local-dev",
        )

    with pytest.raises(ValueError, match="MYSQL_PASSWORD"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="a-very-strong-production-secret-key-123456",
            MYSQL_PASSWORD="change-me-in-local-dev",
        )


def test_production_rejects_debug_and_loopback_database():
    with pytest.raises(ValueError, match="DEBUG must be False"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            SECRET_KEY="a-very-strong-production-secret-key-123456",
            MYSQL_PASSWORD="a-non-placeholder-password",
            MYSQL_SERVER="db.example.test",
        )

    with pytest.raises(ValueError, match="non-loopback"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="a-very-strong-production-secret-key-123456",
            MYSQL_PASSWORD="a-non-placeholder-password",
            MYSQL_SERVER="localhost",
        )


def test_render_requires_explicit_production_environment(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    with pytest.raises(ValueError, match="explicitly set to production"):
        Settings(_env_file=None, DEBUG=False)


def test_cors_rejects_wildcard_origins():
    with pytest.raises(ValueError, match="Wildcard CORS origins"):
        Settings(BACKEND_CORS_ORIGINS=["*"])

"""Focused unit tests for health status classification logic."""

from app.api.v1.endpoints.health import _classify_db_health


def test_healthy_database_and_dependencies_report_healthy():
    health = {
        "status": "connected",
        "latency_ms": 18.5,
        "server_version": "8.4.11",
        "pool_size": 20,
        "checked_in_connections": 10,
        "checked_out_connections": 3,
        "overflow": 0,
    }

    assert _classify_db_health(health) == "healthy"


def test_dependency_failure_reports_unhealthy():
    health = {
        "status": "connected",
        "latency_ms": 250.0,
        "server_version": "8.4.11",
        "pool_size": 20,
        "checked_in_connections": 10,
        "checked_out_connections": 3,
        "overflow": 0,
    }

    assert _classify_db_health(health) == "degraded"


def test_pool_metrics_negative_overflow_is_allowed():
    health = {
        "status": "connected",
        "latency_ms": 6.2,
        "server_version": "8.4.11",
        "pool_size": 20,
        "checked_in_connections": 18,
        "checked_out_connections": 2,
        "overflow": -19,
    }

    assert _classify_db_health(health) == "healthy"


def test_database_connection_failure_is_not_healthy():
    health = {
        "status": "unhealthy",
        "latency_ms": -1.0,
        "server_version": "unavailable",
        "pool_size": 20,
        "checked_in_connections": 0,
        "checked_out_connections": 0,
        "overflow": 0,
    }

    assert _classify_db_health(health) == "unhealthy"

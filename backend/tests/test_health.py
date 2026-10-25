"""
API Integration Tests for Health Endpoints & Documentation (Phase 3)
"""

import time
from fastapi import status


def test_root_discovery(client):
    """Verify root endpoint returns API discovery metadata."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["project"] == "BidSmart Analytics API"
    assert data["status"] == "online"
    assert "documentation" in data
    assert data["documentation"]["swagger_ui"] == "/docs"


def test_root_health_endpoint(client):
    """Verify /health diagnostic endpoint responds with valid schema and latency under 20ms."""
    t0 = time.perf_counter()
    response = client.get("/health")
    request_duration_ms = (time.perf_counter() - t0) * 1000

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "BidSmart Analytics API"
    assert "database" in data
    assert data["database"]["status"] == "connected"
    assert data["database"]["pool_size"] == 20
    assert data["database"]["latency_ms"] < 20.0
    assert request_duration_ms < 50.0  # Overall HTTP client roundtrip


def test_api_v1_health_endpoint(client):
    """Verify versioned /api/v1/health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["database"]["status"] == "connected"
    assert data["database"]["latency_ms"] < 20.0


def test_openapi_documentation_accessible(client):
    """Verify Swagger UI and OpenAPI 3.1 JSON schema are generated."""
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == status.HTTP_200_OK
    assert "swagger-ui" in docs_resp.text.lower()

    openapi_resp = client.get("/api/v1/openapi.json")
    assert openapi_resp.status_code == status.HTTP_200_OK
    schema = openapi_resp.json()
    assert "paths" in schema
    assert "/health" in schema["paths"]
    assert f"/api/v1/health" in schema["paths"]

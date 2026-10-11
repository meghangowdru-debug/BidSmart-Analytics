"""
BidSmart Analytics — Pytest Configuration & Fixtures
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on Python module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.session import SessionLocal


@pytest.fixture(scope="session")
def client():
    """Provides a thread-safe test client with application lifespan management."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def db():
    """Provides a transactional database session for test execution."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session", autouse=True)
def clean_test_artifacts():
    """Restores database seed state at the start and end of the test session."""
    from sqlalchemy import text
    from app.db.session import engine

    def _cleanup():
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM transactions WHERE auction_id > 40 OR id > 18"))
            conn.execute(text("DELETE FROM bids WHERE auction_id > 40"))
            conn.execute(text("DELETE FROM watchlist WHERE auction_id > 40"))
            conn.execute(text("DELETE FROM audit_logs WHERE entity_type = 'AUCTION' AND entity_id > 40"))
            conn.execute(text("DELETE FROM auctions WHERE id > 40"))
            conn.execute(text("DELETE FROM products WHERE id > 40"))

    _cleanup()
    yield
    _cleanup()


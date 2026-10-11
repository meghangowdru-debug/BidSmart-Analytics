"""
Integration Tests for Database Connectivity & SQLAlchemy Connection Pooling (Phase 3)
Verifies PRD Acceptance Criteria:
- Connection pool manages 20+ simultaneous connections cleanly.
- Health check returns database ping in under 20ms.
"""

import time
import threading
from sqlalchemy import text
from app.db.session import engine, check_db_health, SessionLocal
from app.core.config import settings


def test_database_connection_and_latency():
    """
    Verify database ping responds with latency under 20ms.
    Pre-warms connection pool and measures operational query latency.
    """
    # Warm engine connection in pool
    with engine.connect() as conn:
        conn.execute(text("SELECT 1;"))

    # Measure pooled connection execution latency
    t0 = time.perf_counter()
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1 AS alive;")).fetchone()
        assert res[0] == 1
    latency_ms = (time.perf_counter() - t0) * 1000
    print(f"\nMeasured Pooled Ping Latency: {latency_ms:.2f}ms")
    # PRD Acceptance Criteria: < 20ms
    assert latency_ms < 20.0, f"Database ping latency {latency_ms:.2f}ms exceeded 20ms threshold"


def test_check_db_health_helper():
    """Verify the diagnostic telemetry helper returns valid structure and sub-20ms latency."""
    telemetry = check_db_health()
    assert telemetry["status"] == "connected"
    assert telemetry["latency_ms"] < 20.0, f"Latency {telemetry['latency_ms']}ms exceeded 20ms"
    assert "MariaDB" in telemetry["server_version"] or "MySQL" in telemetry["server_version"]
    assert telemetry["pool_size"] >= 20


def test_concurrent_pool_capacity_20_plus_connections():
    """
    PRD Acceptance Criteria: Connection pool manages 20+ simultaneous connections cleanly.
    Spawns 25 concurrent threads, each checking out a connection from the pool,
    executing a lightweight query, and holding it briefly to guarantee simultaneous concurrency.
    """
    concurrency_target = 25
    active_barrier = threading.Barrier(concurrency_target)
    results = []
    errors = []

    def connection_worker(worker_id: int):
        try:
            with engine.connect() as connection:
                # Wait for all 25 workers to reach the barrier so they hold connections concurrently
                active_barrier.wait(timeout=10)
                res = connection.execute(text("SELECT CONNECTION_ID() AS cid;")).fetchone()
                time.sleep(0.05)  # Hold connection briefly
                results.append((worker_id, res[0]))
        except Exception as e:
            errors.append((worker_id, str(e)))

    threads = [threading.Thread(target=connection_worker, args=(i,)) for i in range(concurrency_target)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Connection pool failures encountered: {errors}"
    assert len(results) == concurrency_target, f"Expected {concurrency_target} successful connections, got {len(results)}"

    # Verify distinct connection IDs were utilized across threads
    cids = set(cid for _, cid in results)
    assert len(cids) >= 20, f"Expected at least 20 distinct database connections, got {len(cids)}"

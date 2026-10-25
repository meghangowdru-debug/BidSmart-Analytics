"""Explicit MySQL integration tests using the guarded disposable test database."""

import threading
import time

import pytest
from sqlalchemy import text


@pytest.mark.mysql
def test_database_connection_and_latency(mysql_concurrency):
    """Verify a pooled ping on the explicitly configured test database."""
    engine = mysql_concurrency["engine"]
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    started = time.perf_counter()
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1 AS alive")).fetchone()
    latency_ms = (time.perf_counter() - started) * 1000

    assert result[0] == 1
    assert latency_ms < 20.0, (
        f"Database ping latency {latency_ms:.2f}ms exceeded 20ms threshold"
    )


@pytest.mark.mysql
def test_check_db_health_helper(mysql_concurrency):
    """Verify MySQL server information and pool capacity on the test engine."""
    engine = mysql_concurrency["engine"]
    with engine.connect() as connection:
        server_version = connection.execute(text("SELECT VERSION()")).scalar_one()

    assert "MariaDB" in server_version or "MySQL" in server_version
    assert engine.pool.size() >= 20


@pytest.mark.mysql
def test_concurrent_pool_capacity_20_plus_connections(mysql_concurrency):
    """Verify at least 20 dedicated test-database connections work concurrently."""
    engine = mysql_concurrency["engine"]
    concurrency_target = 25
    active_barrier = threading.Barrier(concurrency_target)
    results = []
    errors = []

    def connection_worker(worker_id: int):
        try:
            with engine.connect() as connection:
                active_barrier.wait(timeout=10)
                result = connection.execute(
                    text("SELECT CONNECTION_ID() AS cid")
                ).fetchone()
                time.sleep(0.05)
                results.append((worker_id, result[0]))
        except Exception as exc:
            errors.append((worker_id, type(exc).__name__))

    threads = [
        threading.Thread(target=connection_worker, args=(index,))
        for index in range(concurrency_target)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors, f"MySQL connection pool failures: {errors}"
    assert len(results) == concurrency_target
    assert len({connection_id for _, connection_id in results}) >= 20

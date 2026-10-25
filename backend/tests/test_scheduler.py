"""
Isolated scheduler lifecycle tests.

These tests patch out database work and do not connect to the configured database.
"""

import asyncio
import time

import pytest

from app.core import scheduler
from app.core.config import settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_scheduler_waits_for_active_close_cycle_before_cancel(monkeypatch):
    original_interval = settings.SCHEDULER_INTERVAL_SECONDS
    settings.SCHEDULER_INTERVAL_SECONDS = 3600

    loop = asyncio.get_running_loop()
    started = asyncio.Event()
    release = asyncio.Event()
    completed = False

    def fake_run_close_cycle():
        nonlocal completed
        loop.call_soon_threadsafe(started.set)
        while not release.is_set():
            time.sleep(0.01)
        completed = True

    monkeypatch.setattr(scheduler, "_run_close_cycle", fake_run_close_cycle)

    task = asyncio.create_task(scheduler.auction_scheduler_loop())
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        task.cancel()
        await asyncio.sleep(0.05)

        assert not task.done()
        assert completed is False

        release.set()

        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=1)

        assert completed is True
    finally:
        settings.SCHEDULER_INTERVAL_SECONDS = original_interval
        if not task.done():
            task.cancel()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task

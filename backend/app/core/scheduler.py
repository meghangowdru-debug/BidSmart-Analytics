"""
BidSmart Analytics — Background Auction Scheduler

Periodically closes expired auctions using the existing
close_all_expired_auctions service. Designed to run as a
long-lived asyncio task inside the FastAPI lifespan context manager.

Design notes:
- Uses asyncio.to_thread() so that the synchronous SQLAlchemy DB calls
  never block the Uvicorn event loop.
- Opens its own DB session (cannot reuse the request-scoped get_db dependency).
- Fully idempotent: close_single_auction() uses SELECT ... FOR UPDATE and
  checks terminal status, so duplicate calls are safe.
- Multi-worker safe: InnoDB row-level locking in close_single_auction()
  ensures only one worker completes a close even if Render scales up.
"""

import asyncio
import logging

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.auction_closing import close_all_expired_auctions
from app.services.auction_lifecycle import activate_due_scheduled_auctions

logger = logging.getLogger("bidsmart_api.scheduler")


def _run_close_cycle() -> None:
    """
    Synchronous worker that opens its own DB session, runs the
    close-expired-auctions service, then closes the session.

    Intended to be called via asyncio.to_thread() — never called
    directly from an async context, as it makes blocking SQLAlchemy calls.
    """
    db = SessionLocal()
    try:
        activated_count = activate_due_scheduled_auctions(db)
        if activated_count:
            logger.info("Scheduler cycle: activated=%d scheduled auctions", activated_count)

        # close_all_expired_auctions returns a BatchCloseResponse Pydantic model,
        # not a dict — access fields via attribute access, not .get().
        result = close_all_expired_auctions(db=db, closing_user_id=None)
        if result.processed_count > 0:
            logger.info(
                "Scheduler cycle: processed=%d | completed=%d | unsold=%d"
                " | reserve_not_met=%d | already_closed=%d",
                result.processed_count,
                result.completed_count,
                result.unsold_count,
                result.reserve_failed_count,
                result.already_closed_count,
            )
    except Exception:
        logger.exception("Auction scheduler encountered an error during close cycle")
    finally:
        db.close()  # Always return the connection to the pool


async def auction_scheduler_loop() -> None:
    """
    Async loop that runs _run_close_cycle every SCHEDULER_INTERVAL_SECONDS.

    Lifecycle:
      - Started via asyncio.create_task() inside the FastAPI lifespan.
      - Stopped cleanly by cancelling the task on application shutdown;
        CancelledError is caught, logged, and re-raised so asyncio.gather()
        sees a clean termination.
    """
    interval: int = settings.SCHEDULER_INTERVAL_SECONDS
    logger.info("Auction scheduler started (interval=%ds)", interval)

    try:
        while True:
            close_task = asyncio.create_task(asyncio.to_thread(_run_close_cycle))
            try:
                await asyncio.shield(close_task)
            except asyncio.CancelledError:
                logger.info("Auction scheduler shutdown requested; waiting for active close cycle")
                await close_task
                logger.info("Auction scheduler stopped cleanly (shutdown signal received)")
                raise
            except Exception:
                # _run_close_cycle logs its own errors; catch here to prevent
                # an unexpected exception from killing the entire loop.
                logger.exception("Unexpected error in scheduler loop body")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        raise  # Re-raise so asyncio.gather() records clean cancellation

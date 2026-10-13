"""Shared scheduled-auction lifecycle transitions."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.auction import Auction, AuctionStatus


def activate_due_scheduled_auctions(
    db: Session,
    now: datetime | None = None,
) -> int:
    """Activate scheduled auctions whose start has arrived and end is future."""
    current_time = now or datetime.now(timezone.utc)
    now_utc = (
        current_time.astimezone(timezone.utc)
        if current_time.tzinfo
        else current_time.replace(tzinfo=timezone.utc)
    )
    now_naive = now_utc.replace(tzinfo=None)

    activated = db.query(Auction).filter(
        Auction.status == AuctionStatus.SCHEDULED,
        Auction.start_time <= now_naive,
        Auction.end_time > now_naive,
    ).update(
        {Auction.status: AuctionStatus.ACTIVE},
        synchronize_session=False,
    )
    if activated:
        db.commit()
    return activated

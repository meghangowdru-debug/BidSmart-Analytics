"""
BidSmart Analytics — Secure Bidding Engine & Bid History Router
Features:
- Atomic database concurrency control with row locking
- Strict BUYER role enforcement (Admins & Sellers prohibited)
- Anti-self-bidding prevention
- Anti-sniping countdown extension
- Anonymized / masked bid history for public/buyers
- Audit logging of accepted bids
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, text

from app.api.deps import (
    get_db,
    get_optional_current_user,
    require_active_buyer
)
from app.models.user import User, UserStatus
from app.models.product import Product
from app.models.auction import Auction, AuctionStatus
from app.models.bid import Bid
from app.models.notification import Notification, NotificationType
from app.models.audit_log import AuditLog
from app.schemas.bid import (
    BidCreate,
    BidOut,
    BidHistoryOut,
    BidHistoryListResponse,
    BuyerBidSummary
)

router = APIRouter()


def mask_username(username: str) -> str:
    """
    Anonymizes bidder usernames for public and competing buyer displays.
    Example: 'elena_r' -> 'e***r', 'collector_dan' -> 'c***n'.
    """
    if not username:
        return "Anonymous"
    u = username.strip()
    if len(u) <= 2:
        return u[0] + "***"
    return u[0] + "***" + u[-1]


def _place_bid_sqlalchemy_fallback(
    db: Session,
    auction_id: int,
    bidder: User,
    bid_amount: Decimal,
    ip_address: str
) -> Dict[str, Any]:
    """
    Pure SQLAlchemy ORM pessimistic locking fallback.
    Used if stored procedure execution is unavailable in the environment.
    """
    # 1. Exclusive pessimistic row lock on auction
    auction = db.query(Auction).join(Product, Auction.product_id == Product.id)\
        .options(joinedload(Auction.product))\
        .filter(Auction.id == auction_id)\
        .with_for_update()\
        .first()

    if not auction:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction listing not found.")

    # 2. Anti-Self-Bidding Enforcement
    if auction.product.seller_id == bidder.id:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Marketplace rule violation: Sellers cannot bid on their own listings."
        )

    # 3. Status Verification
    if auction.status != AuctionStatus.ACTIVE:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot bid: Auction status is {auction.status.value}."
        )

    now_utc = datetime.now(timezone.utc)
    now_naive = now_utc.replace(tzinfo=None)
    start_comp = auction.start_time.astimezone(timezone.utc).replace(tzinfo=None) if auction.start_time.tzinfo else auction.start_time
    end_comp = auction.end_time.astimezone(timezone.utc).replace(tzinfo=None) if auction.end_time.tzinfo else auction.end_time

    # 4. Temporal Window Checks
    if now_naive < start_comp:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Auction has not started yet.")

    if now_naive > end_comp:
        auction.status = AuctionStatus.COMPLETED
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Auction deadline has passed and listing is now closed.")

    # 5. Required Minimum Bid Calculation
    if auction.total_bids == 0 or auction.current_highest_bid is None:
        required_min = auction.starting_price
    else:
        required_min = auction.current_highest_bid + auction.minimum_increment

    if bid_amount < required_min:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bid ${bid_amount:.2f} is below required minimum ${required_min:.2f}"
        )

    # 6. Insert Bid Record
    new_bid = Bid(
        auction_id=auction_id,
        bidder_id=bidder.id,
        bid_amount=bid_amount,
        is_winning_bid=True,
        is_flagged_anomaly=False,
        ip_address=ip_address
    )
    db.add(new_bid)
    db.flush()

    # 7. Demote Previous Winning Bids for this Auction
    db.query(Bid).filter(Bid.auction_id == auction_id, Bid.id != new_bid.id).update({"is_winning_bid": False})

    # 8. Anti-Sniping Rule: If bid within final 30 seconds, extend by 60 seconds
    anti_snipe_extended = False
    seconds_remaining = (end_comp - now_naive).total_seconds()
    if seconds_remaining <= 30:
        auction.end_time = auction.end_time + timedelta(seconds=60)
        anti_snipe_extended = True

    # 9. Update Auction State
    prev_winner = auction.winner_id
    prev_bid = auction.current_highest_bid
    prev_total = auction.total_bids
    auction.current_highest_bid = bid_amount
    auction.winner_id = bidder.id
    auction.winning_bid_id = new_bid.id
    auction.total_bids = auction.total_bids + 1

    # 10. Audit Log
    audit = AuditLog(
        user_id=bidder.id,
        action="BID_ACCEPTED",
        entity_type="AUCTION",
        entity_id=auction_id,
        old_values={"previous_highest_bid": str(prev_bid) if prev_bid else None, "previous_total_bids": prev_total},
        new_values={"new_highest_bid": str(bid_amount), "bid_id": new_bid.id, "anti_snipe_extended": anti_snipe_extended},
        ip_address=ip_address
    )
    db.add(audit)

    # 11. Outbid Notification: notify previous winner if outbid by someone else
    if prev_winner and prev_winner != bidder.id:
        outbid_notif = Notification(
            user_id=prev_winner,
            type=NotificationType.OUTBID,
            title="You Have Been Outbid!",
            message=f"Another bidder placed a higher bid of ${float(bid_amount):.2f} on '{auction.product.title}'.",
            is_read=False,
            link_url=f"/auctions/{auction.id}"
        )
        db.add(outbid_notif)

    db.commit()
    db.refresh(new_bid)
    db.refresh(auction)

    return {
        "bid": new_bid,
        "auction": auction,
        "anti_snipe_extended": anti_snipe_extended
    }


def place_atomic_bid(
    db: Session,
    auction_id: int,
    bidder: User,
    bid_amount: Decimal,
    ip_address: str
) -> Dict[str, Any]:
    """
    Executes an atomic bid placement with database row locking, race-condition protection,
    anti-snipe countdown extensions, and audit logging.
    Delegates to MariaDB's sp_place_bid stored procedure with automatic rollback on conflict.
    """
    # Capture previous winner for outbid notification
    prev_winner_id = db.query(Auction.winner_id).filter(Auction.id == auction_id).scalar()

    try:
        db.execute(
            text("CALL sp_place_bid(:auction_id, :bidder_id, :bid_amount, :ip_address, @bid_id, @code, @msg);"),
            {
                "auction_id": auction_id,
                "bidder_id": bidder.id,
                "bid_amount": float(bid_amount),
                "ip_address": ip_address
            }
        )
        res = db.execute(text("SELECT @bid_id AS bid_id, @code AS code, @msg AS msg;")).mappings().first()
        code = res["code"]
        msg = res["msg"]
        bid_id = res["bid_id"]
    except Exception:
        db.rollback()
        return _place_bid_sqlalchemy_fallback(db, auction_id, bidder, bid_amount, ip_address)

    if code == "NOT_FOUND":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction listing not found.")
    elif code == "FORBIDDEN_SELF_BID":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Marketplace rule violation: Sellers cannot bid on their own listings."
        )
    elif code == "AUCTION_NOT_ACTIVE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg or "Cannot bid: Auction is not active.")
    elif code == "AUCTION_NOT_STARTED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Auction has not started yet.")
    elif code == "AUCTION_EXPIRED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Auction deadline has passed and listing is now closed.")
    elif code == "OUTBID_CONFLICT":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    elif code != "SUCCESS" or bid_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg or "Bid could not be accepted.")

    # Successfully placed via stored procedure
    bid = db.query(Bid).options(joinedload(Bid.bidder)).filter(Bid.id == int(bid_id)).first()
    auction = db.query(Auction).options(joinedload(Auction.product)).filter(Auction.id == auction_id).first()

    # Retrieve anti-sniping status from audit log
    audit_entry = db.query(AuditLog).filter(
        AuditLog.action == "BID_ACCEPTED",
        AuditLog.entity_id == auction_id,
        AuditLog.user_id == bidder.id
    ).order_by(AuditLog.id.desc()).first()

    anti_snipe_extended = False
    if audit_entry and audit_entry.new_values and isinstance(audit_entry.new_values, dict):
        anti_snipe_extended = bool(audit_entry.new_values.get("anti_snipe_extended", False))

    # Outbid notification if another bidder held the previous highest bid
    if prev_winner_id and prev_winner_id != bidder.id:
        p_title = auction.product.title if (auction and auction.product) else "Auction Listing"
        outbid_notif = Notification(
            user_id=prev_winner_id,
            type=NotificationType.OUTBID,
            title="You Have Been Outbid!",
            message=f"Another bidder placed a higher bid of ${float(bid_amount):.2f} on '{p_title}'.",
            is_read=False,
            link_url=f"/auctions/{auction.id}"
        )
        db.add(outbid_notif)
        db.commit()

    return {
        "bid": bid,
        "auction": auction,
        "anti_snipe_extended": anti_snipe_extended
    }


# -----------------------------------------------------------------------------
# 1. ATOMIC BID SUBMISSION ENDPOINT
# -----------------------------------------------------------------------------

@router.post(
    "/auctions/{auction_id}/bids",
    response_model=BidOut,
    status_code=status.HTTP_201_CREATED,
    summary="[Buyer] Submit an atomic bid on an active auction"
)
def submit_bid(
    auction_id: int,
    bid_in: BidCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_buyer: User = Depends(require_active_buyer)
) -> Any:
    """
    Submits a new bid on an auction with strict concurrency and rule enforcements:
    - Only active, authenticated BUYER accounts permitted (Admins & Sellers rejected).
    - Cannot bid on own listings.
    - Auction must be ACTIVE and within start/end time.
    - First bid must meet starting_price. Subsequent bids must meet highest_bid + minimum_increment.
    - Pessimistic row locking ensures serialized concurrency without race conditions.
    - Automatically extends auction by 60 seconds if bid placed in final 30 seconds (Anti-Sniping).
    """
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "127.0.0.1")
    client_ip = client_ip.split(",")[0].strip()

    result = place_atomic_bid(
        db=db,
        auction_id=auction_id,
        bidder=current_buyer,
        bid_amount=bid_in.bid_amount,
        ip_address=client_ip
    )

    bid = result["bid"]
    auction = result["auction"]
    anti_snipe = result["anti_snipe_extended"]

    minimum_next_bid = auction.current_highest_bid + auction.minimum_increment

    return BidOut(
        id=bid.id,
        auction_id=auction.id,
        bidder_id=current_buyer.id,
        bidder_username=current_buyer.username,
        bid_amount=bid.bid_amount,
        bid_time=bid.bid_time,
        is_winning_bid=bid.is_winning_bid,
        anti_snipe_extended=anti_snipe,
        new_end_time=auction.end_time,
        new_highest_bid=auction.current_highest_bid,
        new_total_bids=auction.total_bids,
        minimum_next_bid=minimum_next_bid
    )


# -----------------------------------------------------------------------------
# 2. BID HISTORY ENDPOINT WITH IDENTITY PRIVACY MASKING
# -----------------------------------------------------------------------------

@router.get(
    "/auctions/{auction_id}/bids",
    response_model=BidHistoryListResponse,
    summary="Get chronological bid history for an auction"
)
def get_auction_bid_history(
    auction_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    optional_user: Optional[User] = Depends(get_optional_current_user)
) -> Any:
    """
    Retrieves the chronological bid history for an auction (newest first).
    Privacy Rules:
    - Public / Other Buyers: Bidder usernames are masked (e.g. 'e***r') and bidder_id is omitted.
    - Auction Seller / Admin: Full bidder usernames and IDs are revealed.
    - Current Bidder: Unmasked for their own bids with 'is_own_bid: true'.
    """
    auction = db.query(Auction).options(
        joinedload(Auction.product).joinedload(Product.seller)
    ).filter(Auction.id == auction_id).first()

    if not auction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auction with ID {auction_id} not found."
        )

    # Determine if viewer has privileged access to bidder identities
    is_privileged = False
    if optional_user:
        if optional_user.role and optional_user.role.name == "ADMIN":
            is_privileged = True
        elif auction.product and auction.product.seller_id == optional_user.id:
            is_privileged = True

    bids_query = db.query(Bid).options(joinedload(Bid.bidder))\
        .filter(Bid.auction_id == auction_id)\
        .order_by(desc(Bid.bid_time))

    total = bids_query.count()
    bids = bids_query.offset(skip).limit(limit).all()

    formatted_items = []
    for b in bids:
        is_self = optional_user and optional_user.id == b.bidder_id
        show_full_identity = is_privileged or is_self

        bidder_username = b.bidder.username if (b.bidder and show_full_identity) else mask_username(b.bidder.username if b.bidder else "bidder")
        bidder_id = b.bidder_id if show_full_identity else None

        formatted_items.append(
            BidHistoryOut(
                id=b.id,
                auction_id=b.auction_id,
                bid_amount=b.bid_amount,
                bid_time=b.bid_time,
                is_winning_bid=b.is_winning_bid,
                bidder_id=bidder_id,
                bidder_username=bidder_username,
                is_own_bid=bool(is_self)
            )
        )

    next_min = auction.starting_price if (auction.total_bids == 0 or auction.current_highest_bid is None) else (auction.current_highest_bid + auction.minimum_increment)

    return BidHistoryListResponse(
        items=formatted_items,
        total=total,
        auction_id=auction.id,
        starting_price=auction.starting_price,
        current_highest_bid=auction.current_highest_bid,
        minimum_increment=auction.minimum_increment,
        next_minimum_bid=next_min,
        status=auction.status.value if hasattr(auction.status, "value") else str(auction.status),
        end_time=auction.end_time
    )


# -----------------------------------------------------------------------------
# 3. BUYER PERSONAL BID ACTIVITY ENDPOINT
# -----------------------------------------------------------------------------

@router.get(
    "/bids/me",
    response_model=List[BuyerBidSummary],
    summary="[Buyer] List current user's personal bid activity"
)
def list_my_bids(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_buyer: User = Depends(require_active_buyer)
) -> Any:
    """Returns the authenticated buyer's personal bidding activity across all auctions."""
    bids = db.query(Bid)\
        .join(Auction, Bid.auction_id == Auction.id)\
        .join(Product, Auction.product_id == Product.id)\
        .options(
            joinedload(Bid.auction).joinedload(Auction.product)
        )\
        .filter(Bid.bidder_id == current_buyer.id)\
        .order_by(desc(Bid.bid_time))\
        .offset(skip).limit(limit).all()

    results = []
    for b in bids:
        p = b.auction.product if b.auction else None
        results.append(
            BuyerBidSummary(
                id=b.id,
                auction_id=b.auction_id,
                product_title=p.title if p else "Auction Listing",
                product_image_url=p.image_url if p else "",
                bid_amount=b.bid_amount,
                bid_time=b.bid_time,
                is_winning_bid=b.is_winning_bid,
                current_highest_bid=b.auction.current_highest_bid if b.auction else None,
                auction_status=b.auction.status.value if b.auction else "UNKNOWN",
                auction_end_time=b.auction.end_time if b.auction else datetime.now(timezone.utc)
            )
        )
    return results

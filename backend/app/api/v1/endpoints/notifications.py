"""
BidSmart Analytics — Notifications Router
Provides in-app notification retrieval, unread badge counts, and read-status management.
"""

from math import ceil
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.deps import (
    get_db,
    get_current_active_user
)
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import (
    NotificationOut,
    NotificationListResponse,
    NotificationUnreadCount
)

router = APIRouter()


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List in-app notifications for the current user"
)
def list_user_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Retrieves paginated notifications for the authenticated user."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read == False)

    total = query.count()
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()

    pages = max(1, ceil(total / page_size)) if total > 0 else 1
    offset = (page - 1) * page_size
    items = query.order_by(desc(Notification.created_at)).offset(offset).limit(page_size).all()

    return NotificationListResponse(
        items=[
            NotificationOut(
                id=n.id,
                user_id=n.user_id,
                type=n.type.value if hasattr(n.type, "value") else str(n.type),
                title=n.title,
                message=n.message,
                is_read=n.is_read,
                link_url=n.link_url,
                created_at=n.created_at
            )
            for n in items
        ],
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCount,
    summary="Get count of unread notifications for badge"
)
def get_unread_notification_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Returns number of unread notifications for badge indicators."""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    return NotificationUnreadCount(unread_count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationOut,
    summary="Mark a single notification as read"
)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Marks a specific notification as read. Ownership enforced."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification #{notification_id} not found."
        )

    notification.is_read = True
    db.commit()
    db.refresh(notification)

    return NotificationOut(
        id=notification.id,
        user_id=notification.user_id,
        type=notification.type.value if hasattr(notification.type, "value") else str(notification.type),
        title=notification.title,
        message=notification.message,
        is_read=notification.is_read,
        link_url=notification.link_url,
        created_at=notification.created_at
    )


@router.post(
    "/read-all",
    summary="Mark all user notifications as read"
)
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Marks all unread notifications for the authenticated user as read."""
    updated = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read.", "count": updated}

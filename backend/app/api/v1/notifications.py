"""Notification REST API — list, read, dismiss notifications."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.notifications import NotificationType
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.services.notification_service import notification_service

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: UUID
    type: NotificationType
    title: str
    message: str
    link_url: Optional[str]
    extra_data: dict
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    page: int
    page_size: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get count of unread notifications (lightweight, for polling)."""
    count = await notification_service.get_unread_count(db=db, user_id=current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user."""
    notifications, total = await notification_service.list_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )
    unread_count = await notification_service.get_unread_count(db=db, user_id=current_user.id)
    return NotificationListResponse(
        items=notifications,
        total=total,
        page=page,
        page_size=page_size,
        unread_count=unread_count,
    )


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    notification = await notification_service.mark_read(
        db=db, notification_id=notification_id, user_id=current_user.id
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}


@router.post("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    count = await notification_service.mark_all_read(db=db, user_id=current_user.id)
    return {"message": f"Marked {count} notifications as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete (dismiss) a notification."""
    deleted = await notification_service.delete_notification(
        db=db, notification_id=notification_id, user_id=current_user.id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted"}

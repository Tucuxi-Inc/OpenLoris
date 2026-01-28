"""
SQLAlchemy model for in-app notifications.

Notifications are created by the system at key workflow points
(question answered, auto-answer, GUD expiry, etc.) and delivered
to users via polling on GET /api/v1/notifications/unread-count.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class NotificationType(str, Enum):
    """Types of notifications sent to users."""
    # Question lifecycle
    QUESTION_ANSWERED = "question_answered"
    AUTO_ANSWER_AVAILABLE = "auto_answer_available"
    QUESTION_ASSIGNED = "question_assigned"
    CLARIFICATION_REQUESTED = "clarification_requested"
    CLARIFICATION_RECEIVED = "clarification_received"
    AUTO_ANSWER_REJECTED = "auto_answer_rejected"

    # GUD expiry — Automation rules
    RULE_EXPIRING_SOON = "rule_expiring_soon"
    RULE_EXPIRING_URGENT = "rule_expiring_urgent"
    RULE_EXPIRED = "rule_expired"

    # GUD expiry — Documents
    DOCUMENT_EXPIRING_SOON = "document_expiring_soon"
    DOCUMENT_EXPIRED = "document_expired"

    # GUD expiry — Knowledge facts
    FACT_EXPIRING_SOON = "fact_expiring_soon"
    FACT_EXPIRED = "fact_expired"

    # Sub-domain routing
    QUESTION_ROUTED = "question_routed"
    SLA_BREACH = "sla_breach"
    REASSIGNMENT_REQUESTED = "reassignment_requested"
    REASSIGNMENT_APPROVED = "reassignment_approved"
    REASSIGNMENT_REJECTED = "reassignment_rejected"


class Notification(Base, UUIDMixin, TimestampMixin):
    """In-app notification for a user."""
    __tablename__ = "notifications"

    # Organization & user
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Content
    type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Read status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<Notification {self.type.value} to={self.user_id} read={self.is_read}>"


# Composite indexes for common queries
Index("idx_notifications_user_unread", Notification.user_id, Notification.is_read, Notification.created_at)

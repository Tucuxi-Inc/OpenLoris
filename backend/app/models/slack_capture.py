"""
SQLAlchemy model for Slack-captured Q&A pairs.

When MoltenLoris escalates a question and an expert answers in Slack,
the Loris Web App captures these Q&A pairs for review and potential
addition to the knowledge base.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, Float
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class SlackCaptureStatus(str, Enum):
    """Status of a Slack-captured Q&A pair."""
    PENDING = "pending"        # Awaiting expert review
    APPROVED = "approved"      # Approved and converted to WisdomFact
    REJECTED = "rejected"      # Rejected by expert
    DUPLICATE = "duplicate"    # Duplicate of existing knowledge


class SlackCapture(Base, UUIDMixin, TimestampMixin):
    """
    Q&A pairs captured from Slack where MoltenLoris escalated
    and an expert responded.
    """
    __tablename__ = "slack_captures"

    # Organization scope
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True
    )

    # Slack context
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    thread_ts: Mapped[str] = mapped_column(String(50), nullable=False)
    message_ts: Mapped[str] = mapped_column(String(50), nullable=False)

    # Q&A content
    original_question: Mapped[str] = mapped_column(Text, nullable=False)
    expert_answer: Mapped[str] = mapped_column(Text, nullable=False)
    expert_name: Mapped[str] = mapped_column(String(200), nullable=False)
    expert_slack_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps from Slack
    question_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    answer_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # AI-suggested classification
    suggested_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    suggested_subdomain_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)

    # Review status
    status: Mapped[SlackCaptureStatus] = mapped_column(
        SAEnum(SlackCaptureStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=SlackCaptureStatus.PENDING,
        nullable=False,
        index=True
    )
    reviewed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # If approved, link to created wisdom fact
    created_fact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wisdom_facts.id"),
        nullable=True
    )

    # Extra metadata from Slack
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<SlackCapture channel={self.channel} status={self.status.value}>"

    @property
    def slack_link(self) -> str:
        """Generate a Slack link to the thread."""
        # Note: This is a simplified version; actual implementation
        # would need workspace info
        return f"slack://channel?id={self.channel}&message={self.thread_ts}"

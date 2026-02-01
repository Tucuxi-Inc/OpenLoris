"""
MoltenLoris Activity Model

Tracks Q&A activity from the MoltenLoris Slack bot, including
expert corrections for continuous improvement.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class MoltenLorisActivity(Base, UUIDMixin, TimestampMixin):
    """
    Tracks MoltenLoris Slack bot Q&A activity.

    Each record represents a question asked in Slack and the
    automated answer provided by MoltenLoris. Experts can
    review and correct answers to improve the knowledge base.

    Attributes:
        organization_id: Multi-tenant isolation
        channel_id: Slack channel ID where question was asked
        channel_name: Human-readable channel name
        thread_ts: Slack thread timestamp for threading
        user_slack_id: Slack user ID who asked
        user_name: Display name of asker

        question_text: The original question text
        answer_text: MoltenLoris's automated answer
        confidence_score: How confident the system was (0.0-1.0)
        source_facts: List of fact IDs that contributed to the answer

        was_corrected: Whether an expert corrected this answer
        corrected_by_id: Expert who made the correction
        corrected_at: When the correction was made
        correction_text: The corrected answer text
        correction_reason: Why the correction was needed

        created_question_id: If user's question was captured to main queue
        created_fact_id: If correction was promoted to knowledge fact
    """

    __tablename__ = "molten_loris_activities"

    # Organization (multi-tenant)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Slack context
    channel_id: Mapped[str] = mapped_column(String(100), nullable=False)
    channel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    thread_ts: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_slack_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Q&A content
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Source attribution - list of fact IDs and similarity scores
    source_facts: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )

    # Correction tracking
    was_corrected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    corrected_by_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    corrected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    correction_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correction_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Links to main Loris system
    created_question_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_fact_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("wisdom_facts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization = relationship("Organization", back_populates="molten_activities")
    corrected_by = relationship("User", foreign_keys=[corrected_by_id])
    created_question = relationship("Question", foreign_keys=[created_question_id])
    created_fact = relationship("WisdomFact", foreign_keys=[created_fact_id])

    def __repr__(self) -> str:
        return f"<MoltenLorisActivity {self.id} channel={self.channel_name}>"

    @property
    def is_high_confidence(self) -> bool:
        """Check if this was a high-confidence answer (>0.8)."""
        return self.confidence_score >= 0.8

    @property
    def needs_review(self) -> bool:
        """Check if this low-confidence answer should be reviewed."""
        return self.confidence_score < 0.6 and not self.was_corrected

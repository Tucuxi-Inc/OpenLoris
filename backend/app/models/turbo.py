"""
TurboAttribution model — tracks which knowledge sources contributed to a Turbo answer.
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.questions import Question
    from app.models.user import User


class TurboAttribution(Base, UUIDMixin, TimestampMixin):
    """
    Tracks which knowledge sources (facts, documents, automation rules)
    contributed to a Turbo Loris answer, along with confidence metrics.
    """
    __tablename__ = "turbo_attributions"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source identification
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "fact", "document", "automation_rule"
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Who contributed this knowledge (may be null for AI-generated)
    attributed_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Display name for the source (e.g., fact summary, document title)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # How the attributed user contributed
    contribution_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "authored", "uploaded", "approved"

    # Match quality metrics
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_similarity: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="turbo_attributions")
    attributed_user: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:
        return f"<TurboAttribution q={self.question_id} source={self.source_type}:{self.source_id}>"

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.questions import Question
    from app.models.user import User


class AnswerSource(str, Enum):
    """How the answer was created"""
    EXPERT = "expert"               # Human expert wrote it
    AI_APPROVED = "ai_approved"     # AI proposed, expert approved as-is
    AI_EDITED = "ai_edited"         # AI proposed, expert edited
    AUTOMATION = "automation"       # Delivered by automation rule


class Answer(Base, UUIDMixin, TimestampMixin):
    """Expert's answer to a question"""
    __tablename__ = "answers"

    # Question reference (one-to-one)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id"),
        unique=True,
        nullable=False,
        index=True
    )

    # Who created it
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Answer content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[AnswerSource] = mapped_column(
        ENUM(AnswerSource, name="answer_source", create_type=False),
        nullable=False
    )

    # If AI-assisted
    original_ai_proposal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Knowledge citations
    cited_knowledge: Mapped[dict] = mapped_column(
        JSONB,
        default=list,
        nullable=False
    )  # [{fact_id, document_id, excerpt}, ...]

    # Delivery tracking
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="answer")
    created_by: Mapped["User"] = relationship("User", back_populates="answers_given")

    def __repr__(self) -> str:
        return f"<Answer {self.id} [{self.source.value}]>"

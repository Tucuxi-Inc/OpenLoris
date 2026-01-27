import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.answers import Answer


class QuestionStatus(str, Enum):
    """Question lifecycle status"""
    SUBMITTED = "submitted"                 # Just received
    PROCESSING = "processing"               # Checking for automation
    AUTO_ANSWERED = "auto_answered"         # Automated answer delivered
    HUMAN_REQUESTED = "human_requested"     # User rejected auto-answer
    EXPERT_QUEUE = "expert_queue"           # Waiting for expert
    IN_PROGRESS = "in_progress"             # Expert working on it
    NEEDS_CLARIFICATION = "needs_clarification"
    ANSWERED = "answered"                   # Expert answered
    RESOLVED = "resolved"                   # User confirmed satisfied
    CLOSED = "closed"                       # Closed without resolution


class QuestionPriority(str, Enum):
    """Question priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageType(str, Enum):
    """Types of question messages"""
    QUESTION = "question"                       # Original or follow-up question
    CLARIFICATION_REQUEST = "clarification_request"   # Expert asks for more info
    CLARIFICATION_RESPONSE = "clarification_response" # User provides info
    SYSTEM = "system"                           # System-generated message


class Question(Base, UUIDMixin, TimestampMixin):
    """Question model - core of the Q&A workflow"""
    __tablename__ = "questions"

    # Organization
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True
    )

    # Who asked
    asked_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Question content
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String(50)), default=list, nullable=False)

    # File attachments as JSON array
    attachments: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)

    # Status & Priority
    status: Mapped[QuestionStatus] = mapped_column(
        ENUM(QuestionStatus, name="question_status", create_type=True),
        default=QuestionStatus.SUBMITTED,
        nullable=False,
        index=True
    )
    priority: Mapped[QuestionPriority] = mapped_column(
        ENUM(QuestionPriority, name="question_priority", create_type=True),
        default=QuestionPriority.NORMAL,
        nullable=False
    )

    # Assignment
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    # Automation tracking
    automation_rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True  # FK will be added when automation model is created
    )
    auto_answer_accepted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Gap analysis results (stored for expert view)
    gap_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Metrics
    response_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resolution_time_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    satisfaction_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5

    # Timestamps
    first_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="questions")
    asked_by: Mapped["User"] = relationship(
        "User",
        back_populates="questions_asked",
        foreign_keys=[asked_by_id]
    )
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="questions_assigned",
        foreign_keys=[assigned_to_id]
    )
    messages: Mapped[List["QuestionMessage"]] = relationship(
        "QuestionMessage",
        back_populates="question",
        order_by="QuestionMessage.created_at"
    )
    answer: Mapped[Optional["Answer"]] = relationship("Answer", back_populates="question", uselist=False)

    def __repr__(self) -> str:
        return f"<Question {self.id} [{self.status.value}]>"


class QuestionMessage(Base, UUIDMixin, TimestampMixin):
    """Messages/clarifications on a question"""
    __tablename__ = "question_messages"

    # Question reference
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id"),
        nullable=False,
        index=True
    )

    # Who sent it
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )

    # Message content
    message_type: Mapped[MessageType] = mapped_column(
        ENUM(MessageType, name="message_type", create_type=True),
        nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="messages")
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<QuestionMessage {self.id} [{self.message_type.value}]>"

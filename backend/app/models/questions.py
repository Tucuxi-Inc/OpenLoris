import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Integer, Boolean, DateTime, Enum as SAEnum, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.answers import Answer
    from app.models.subdomain import SubDomain


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
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # File attachments as JSON array
    attachments: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)

    # Status & Priority
    status: Mapped[QuestionStatus] = mapped_column(
        SAEnum(QuestionStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=QuestionStatus.SUBMITTED,
        nullable=False,
        index=True
    )
    priority: Mapped[QuestionPriority] = mapped_column(
        SAEnum(QuestionPriority, values_callable=lambda obj: [e.value for e in obj]),
        default=QuestionPriority.NORMAL,
        nullable=False
    )

    # Sub-domain routing
    subdomain_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subdomains.id"),
        nullable=True,
        index=True,
    )
    ai_classified_subdomain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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
    subdomain: Mapped[Optional["SubDomain"]] = relationship("SubDomain")
    routing_records: Mapped[List["QuestionRouting"]] = relationship(
        "QuestionRouting", back_populates="question", cascade="all, delete-orphan"
    )
    reassignment_requests: Mapped[List["ReassignmentRequest"]] = relationship(
        "ReassignmentRequest", back_populates="question", cascade="all, delete-orphan"
    )

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
        SAEnum(MessageType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="messages")
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<QuestionMessage {self.id} [{self.message_type.value}]>"


class QuestionRouting(Base, UUIDMixin, TimestampMixin):
    """Tracks which experts were notified about a question and who claimed it."""
    __tablename__ = "question_routings"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id"),
        nullable=False,
        index=True,
    )
    expert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    notified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="routing_records")
    expert: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<QuestionRouting q={self.question_id} expert={self.expert_id}>"


class ReassignmentStatus(str, Enum):
    """Status of a reassignment request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReassignmentRequest(Base, UUIDMixin, TimestampMixin):
    """Expert requests reassignment of a question to a different sub-domain."""
    __tablename__ = "reassignment_requests"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id"),
        nullable=False,
        index=True,
    )
    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    current_subdomain_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subdomains.id"),
        nullable=True,
    )
    suggested_subdomain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subdomains.id"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ReassignmentStatus] = mapped_column(
        SAEnum(ReassignmentStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ReassignmentStatus.PENDING,
        nullable=False,
        index=True,
    )
    reviewed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="reassignment_requests")
    requested_by: Mapped["User"] = relationship("User", foreign_keys=[requested_by_id])
    current_subdomain: Mapped[Optional["SubDomain"]] = relationship(
        "SubDomain", foreign_keys=[current_subdomain_id]
    )
    suggested_subdomain: Mapped["SubDomain"] = relationship(
        "SubDomain", foreign_keys=[suggested_subdomain_id]
    )
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id])

    def __repr__(self) -> str:
        return f"<ReassignmentRequest q={self.question_id} status={self.status.value}>"

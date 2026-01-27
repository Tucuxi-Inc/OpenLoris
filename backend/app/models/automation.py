import uuid
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Integer, Float, Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.questions import Question


class AutomationRule(Base, UUIDMixin, TimestampMixin):
    """Automation rule for auto-answering similar questions"""
    __tablename__ = "automation_rules"

    # Organization
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True
    )

    # Who created this rule
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Rule definition
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source question/answer (if created from a Q&A)
    source_question_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id"),
        nullable=True
    )

    # The canonical Q&A pair
    canonical_question: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_answer: Mapped[str] = mapped_column(Text, nullable=False)

    # Matching configuration
    similarity_threshold: Mapped[float] = mapped_column(
        Float, default=0.85, nullable=False
    )
    category_filter: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    exclude_keywords: Mapped[List[str]] = mapped_column(
        ARRAY(String(100)), default=list, nullable=False
    )

    # GUD (Good Until Date)
    good_until_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Metrics
    times_triggered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    times_accepted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    times_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    created_by: Mapped["User"] = relationship("User")
    source_question: Mapped[Optional["Question"]] = relationship("Question")
    embedding: Mapped[Optional["AutomationRuleEmbedding"]] = relationship(
        "AutomationRuleEmbedding", back_populates="rule", uselist=False
    )
    logs: Mapped[List["AutomationLog"]] = relationship(
        "AutomationLog", back_populates="rule", order_by="AutomationLog.created_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<AutomationRule {self.name} [{'enabled' if self.is_enabled else 'disabled'}]>"

    @property
    def acceptance_rate(self) -> Optional[float]:
        total = self.times_accepted + self.times_rejected
        if total == 0:
            return None
        return self.times_accepted / total

    @property
    def is_expired(self) -> bool:
        if self.good_until_date is None:
            return False
        return self.good_until_date < date.today()


class AutomationRuleEmbedding(Base, UUIDMixin, TimestampMixin):
    """Vector embedding for an automation rule's canonical question"""
    __tablename__ = "automation_rule_embeddings"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automation_rules.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    # Store embedding as JSONB array (pgvector column added via raw SQL)
    # The actual vector column is created in init.sql
    embedding_data: Mapped[List] = mapped_column(JSONB, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationship
    rule: Mapped["AutomationRule"] = relationship(
        "AutomationRule", back_populates="embedding"
    )

    def __repr__(self) -> str:
        return f"<AutomationRuleEmbedding rule={self.rule_id}>"


class AutomationLogAction(str, Enum):
    """Actions tracked in automation logs"""
    MATCHED = "matched"         # Rule matched a question
    DELIVERED = "delivered"     # Auto-answer delivered to user
    ACCEPTED = "accepted"       # User accepted auto-answer
    REJECTED = "rejected"       # User rejected auto-answer
    SUGGESTED = "suggested"     # Suggested to expert (medium confidence)


class AutomationLog(Base, UUIDMixin, TimestampMixin):
    """Log of automation events for auditing and metrics"""
    __tablename__ = "automation_logs"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automation_rules.id"),
        nullable=False,
        index=True
    )

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id"),
        nullable=False,
        index=True
    )

    action: Mapped[AutomationLogAction] = mapped_column(
        SAEnum(AutomationLogAction, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )

    similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    user_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    rule: Mapped["AutomationRule"] = relationship("AutomationRule", back_populates="logs")
    question: Mapped["Question"] = relationship("Question")

    def __repr__(self) -> str:
        return f"<AutomationLog {self.action.value} rule={self.rule_id}>"

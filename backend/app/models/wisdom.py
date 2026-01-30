"""
SQLAlchemy models for the Wisdom/Knowledge database.
Ported from CounselScope, adapted to Loris conventions (async, Mapped, UUIDMixin).

WisdomFacts are validated organizational knowledge that power:
- Gap analysis (finding relevant knowledge for incoming questions)
- Proposed answers (AI drafts using knowledge base context)
- Knowledge compounding (expert answers become reusable knowledge)
"""

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    String, Integer, Float, Boolean, Date, DateTime,
    Enum as SAEnum, ForeignKey, Text, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.answers import Answer


class WisdomTier(str, Enum):
    """Knowledge validation tiers based on confidence and expert validation."""
    TIER_0A = "tier_0a"     # >95% confidence, expert validated, actively maintained
    TIER_0B = "tier_0b"     # 85-95% confidence, validated, reliable
    TIER_0C = "tier_0c"     # <85% confidence, needs validation or review
    PENDING = "pending"      # Newly extracted, awaiting initial validation
    ARCHIVED = "archived"    # Outdated, superseded, or no longer applicable


class WisdomFact(Base, UUIDMixin, TimestampMixin):
    """
    Core wisdom facts - validated organizational knowledge.
    Each fact represents a piece of verified knowledge used for
    gap analysis, proposed answers, and knowledge compounding.
    """
    __tablename__ = "wisdom_facts"

    # Organization scope
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True
    )

    # Core content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Classification
    domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    tier: Mapped[WisdomTier] = mapped_column(
        SAEnum(WisdomTier, values_callable=lambda obj: [e.value for e in obj]),
        default=WisdomTier.PENDING,
        nullable=False,
        index=True
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    importance: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # 1-10

    # Source tracking
    source_answer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("answers.id"),
        nullable=True
    )
    source_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="SET NULL"),
        nullable=True
    )

    # GUD (Good Until Date) temporal system
    good_until_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_perpetual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Responsible contact
    contact_person_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )

    # Validation
    validated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    validated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )

    # Usage analytics
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Metadata
    jurisdiction: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    source_answer: Mapped[Optional["Answer"]] = relationship("Answer")
    contact_person: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[contact_person_id]
    )
    validated_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[validated_by_id]
    )
    embedding: Mapped[Optional["WisdomEmbedding"]] = relationship(
        "WisdomEmbedding", back_populates="fact", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<WisdomFact {self.id} [{self.tier.value}]>"

    @property
    def is_expired(self) -> bool:
        if self.is_perpetual or self.good_until_date is None:
            return False
        return self.good_until_date < date.today()


class WisdomEmbedding(Base, UUIDMixin, TimestampMixin):
    """Vector embedding for semantic search of wisdom facts."""
    __tablename__ = "wisdom_embeddings"

    wisdom_fact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wisdom_facts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    # Embedding data stored as JSONB (768 dims for nomic-embed-text)
    embedding_data: Mapped[list] = mapped_column(JSONB, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationship
    fact: Mapped["WisdomFact"] = relationship(
        "WisdomFact", back_populates="embedding"
    )

    def __repr__(self) -> str:
        return f"<WisdomEmbedding fact={self.wisdom_fact_id}>"


# Performance indexes
Index('idx_wisdom_facts_org_tier', WisdomFact.organization_id, WisdomFact.tier)
Index('idx_wisdom_facts_domain', WisdomFact.domain)
Index('idx_wisdom_facts_gud', WisdomFact.good_until_date)
Index('idx_wisdom_facts_active', WisdomFact.is_active)

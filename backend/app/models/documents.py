"""
SQLAlchemy models for Knowledge Document management.
Ported from CounselScope, adapted to Loris conventions (async, Mapped, UUIDMixin).

Handles document upload, parsing, chunking, fact extraction, and GUD expiration.
Documents are source material from which WisdomFacts are extracted.
"""

import uuid
from datetime import date, datetime
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


class DocumentType(str, Enum):
    """Types of knowledge documents that can be ingested."""
    LEGAL_MEMO = "legal_memo"
    OUTSIDE_COUNSEL_OPINION = "outside_counsel_opinion"
    INTERNAL_GUIDANCE = "internal_guidance"
    CONTRACT_PLAYBOOK = "contract_playbook"
    POLICY_DOCUMENT = "policy_document"
    REGULATORY_GUIDANCE = "regulatory_guidance"
    BOARD_RESOLUTION = "board_resolution"
    MEETING_NOTES = "meeting_notes"
    TRAINING_MATERIAL = "training_material"
    TEMPLATE = "template"
    FAQ = "faq"
    OTHER = "other"


class ParsingStatus(str, Enum):
    """Status of document parsing process."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExtractionStatus(str, Enum):
    """Status of fact extraction from document."""
    PENDING = "pending"
    EXTRACTING = "extracting"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ValidationStatus(str, Enum):
    """Status of extracted fact candidate validation."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class Department(Base, UUIDMixin, TimestampMixin):
    """Reference table for departments/teams."""
    __tablename__ = "departments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")

    def __repr__(self) -> str:
        return f"<Department {self.name}>"


class KnowledgeDocument(Base, UUIDMixin, TimestampMixin):
    """
    Source documents containing organizational knowledge.
    Documents are uploaded, parsed into chunks, and facts are extracted
    for expert validation before becoming WisdomFacts.
    """
    __tablename__ = "knowledge_documents"

    # Organization scope
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True
    )

    # Who uploaded
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )

    # File information
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, docx, txt
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Document metadata
    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, values_callable=lambda obj: [e.value for e in obj]),
        default=DocumentType.OTHER,
        nullable=False
    )
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Classification
    domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    topics: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Parsing status
    parsing_status: Mapped[ParsingStatus] = mapped_column(
        SAEnum(ParsingStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ParsingStatus.PENDING,
        nullable=False
    )
    parsing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    parsing_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    parsing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extraction status
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        SAEnum(ExtractionStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ExtractionStatus.PENDING,
        nullable=False
    )
    extracted_facts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validated_facts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Content statistics
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Quality metrics
    content_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    needs_manual_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # GUD (Good Until Date) temporal system
    good_until_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_perpetual: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_delete_on_expiry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expiry_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Department/responsibility
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    responsible_person: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    responsible_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Review
    reviewed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    uploaded_by: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by_id])
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id])
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
    fact_candidates: Mapped[List["ExtractedFactCandidate"]] = relationship(
        "ExtractedFactCandidate", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<KnowledgeDocument {self.original_filename}>"

    @property
    def is_expired(self) -> bool:
        if self.is_perpetual or self.good_until_date is None:
            return False
        return self.good_until_date < date.today()


class DocumentChunk(Base, UUIDMixin, TimestampMixin):
    """Parsed sections/chunks of documents for AI processing."""
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Position
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Processing
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    facts_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    document: Mapped["KnowledgeDocument"] = relationship(
        "KnowledgeDocument", back_populates="chunks"
    )
    embedding: Mapped[Optional["ChunkEmbedding"]] = relationship(
        "ChunkEmbedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk doc={self.document_id} idx={self.chunk_index}>"


class ChunkEmbedding(Base, UUIDMixin, TimestampMixin):
    """Vector embedding for document chunks."""
    __tablename__ = "chunk_embeddings"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    embedding_data: Mapped[list] = mapped_column(JSONB, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationship
    chunk: Mapped["DocumentChunk"] = relationship(
        "DocumentChunk", back_populates="embedding"
    )

    def __repr__(self) -> str:
        return f"<ChunkEmbedding chunk={self.chunk_id}>"


class ExtractedFactCandidate(Base, UUIDMixin, TimestampMixin):
    """
    AI-extracted facts pending expert validation.
    Once approved, they become WisdomFacts.
    """
    __tablename__ = "extracted_fact_candidates"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id"),
        nullable=True
    )

    # Extracted content
    fact_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI classification
    suggested_domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    suggested_importance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    suggested_tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    # Validation
    validation_status: Mapped[ValidationStatus] = mapped_column(
        SAEnum(ValidationStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ValidationStatus.PENDING,
        nullable=False,
        index=True
    )
    validated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # If approved, link to created wisdom fact
    created_wisdom_fact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wisdom_facts.id"),
        nullable=True
    )

    # Rejection tracking
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    document: Mapped["KnowledgeDocument"] = relationship(
        "KnowledgeDocument", back_populates="fact_candidates"
    )

    def __repr__(self) -> str:
        return f"<ExtractedFactCandidate doc={self.document_id} status={self.validation_status.value}>"


# Performance indexes
Index('idx_knowledge_docs_org', KnowledgeDocument.organization_id)
Index('idx_knowledge_docs_type', KnowledgeDocument.document_type)
Index('idx_knowledge_docs_parsing', KnowledgeDocument.parsing_status)
Index('idx_knowledge_docs_extraction', KnowledgeDocument.extraction_status)
Index('idx_knowledge_docs_gud', KnowledgeDocument.good_until_date)
Index('idx_doc_chunks_doc', DocumentChunk.document_id)
Index('idx_fact_candidates_doc', ExtractedFactCandidate.document_id)
Index('idx_fact_candidates_status', ExtractedFactCandidate.validation_status)

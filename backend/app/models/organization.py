import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Integer, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.questions import Question


class Organization(Base, UUIDMixin, TimestampMixin):
    """Organization model for multi-tenant support"""
    __tablename__ = "organizations"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Settings stored as JSON
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Branding
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color

    # Limits
    max_users: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_questions_per_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="organization")
    questions: Mapped[List["Question"]] = relationship("Question", back_populates="organization")

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"

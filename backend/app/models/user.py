import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.questions import Question
    from app.models.answers import Answer


class UserRole(str, Enum):
    """User roles for RBAC"""
    BUSINESS_USER = "business_user"     # Can ask questions, view own history
    DOMAIN_EXPERT = "domain_expert"     # Can answer, manage knowledge, automate
    ADMIN = "admin"                     # Full access including user management


class User(Base, UUIDMixin, TimestampMixin):
    """User model with role-based access control"""
    __tablename__ = "users"

    # Organization
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True
    )

    # Identity
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Authentication
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Role & Status
    role: Mapped[UserRole] = mapped_column(
        ENUM(UserRole, name="user_role", create_type=True),
        default=UserRole.BUSINESS_USER,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Metadata
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Preferences
    notification_preferences: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {"email": True, "in_app": True},
        nullable=False
    )

    # Last login
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")
    questions_asked: Mapped[List["Question"]] = relationship(
        "Question",
        back_populates="asked_by",
        foreign_keys="Question.asked_by_id"
    )
    questions_assigned: Mapped[List["Question"]] = relationship(
        "Question",
        back_populates="assigned_to",
        foreign_keys="Question.assigned_to_id"
    )
    answers_given: Mapped[List["Answer"]] = relationship("Answer", back_populates="created_by")

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def is_expert(self) -> bool:
        return self.role in (UserRole.DOMAIN_EXPERT, UserRole.ADMIN)

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

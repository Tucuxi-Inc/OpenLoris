"""
SubDomain models for expert routing.

SubDomains represent question categories (e.g., Contracts, Employment)
that admins manage and assign domain experts to. When a question is
submitted with a sub-domain, all experts assigned to that sub-domain
are notified. First to claim wins.
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class SubDomain(Base, UUIDMixin, TimestampMixin):
    """A question sub-domain/category managed by admins."""
    __tablename__ = "subdomains"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_subdomain_org_name"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sla_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    expert_assignments: Mapped[list["ExpertSubDomainAssignment"]] = relationship(
        "ExpertSubDomainAssignment",
        back_populates="subdomain",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SubDomain {self.name} org={self.organization_id}>"


class ExpertSubDomainAssignment(Base, UUIDMixin, TimestampMixin):
    """Maps experts to sub-domains they handle."""
    __tablename__ = "expert_subdomain_assignments"
    __table_args__ = (
        UniqueConstraint("expert_id", "subdomain_id", name="uq_expert_subdomain"),
    )

    expert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    subdomain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subdomains.id"),
        nullable=False,
        index=True,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    expert: Mapped["User"] = relationship("User")
    subdomain: Mapped["SubDomain"] = relationship("SubDomain", back_populates="expert_assignments")

    def __repr__(self) -> str:
        return f"<ExpertSubDomainAssignment expert={self.expert_id} subdomain={self.subdomain_id}>"

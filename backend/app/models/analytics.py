"""
SQLAlchemy model for aggregated daily metrics.

DailyMetrics stores pre-computed daily snapshots per organization.
Currently unused (metrics are computed on-the-fly), but the table
exists for future optimization when query volume warrants it.
"""

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class DailyMetrics(Base, UUIDMixin, TimestampMixin):
    """Pre-aggregated daily metrics per organization."""
    __tablename__ = "daily_metrics"
    __table_args__ = (
        UniqueConstraint("organization_id", "metric_date", name="uq_daily_metrics_org_date"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Question metrics
    questions_submitted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    questions_resolved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    questions_auto_answered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    questions_expert_answered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Performance metrics
    avg_response_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_resolution_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_satisfaction_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Automation metrics
    automation_triggers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    automation_accepted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    automation_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Knowledge metrics
    knowledge_facts_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    knowledge_facts_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    knowledge_facts_expired: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<DailyMetrics org={self.organization_id} date={self.metric_date}>"

"""
Document Expiration Service — manages GUD (Good Until Date) tracking,
expiration processing, and department management.

Ported from CounselScope's document_expiration_service.py,
adapted to Loris async patterns (AsyncSession passed in, UUIDs, Mapped models).
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.documents import Department, KnowledgeDocument

logger = logging.getLogger(__name__)


class DocumentExpirationService:
    """Manages document GUD enforcement, expiry processing, and departments."""

    # ------------------------------------------------------------------
    # Expiration status computation (pure function)
    # ------------------------------------------------------------------

    @staticmethod
    def compute_expiration_status(
        is_perpetual: bool,
        good_until_date: Optional[date],
    ) -> Tuple[bool, Optional[int], str]:
        """
        Returns (is_expired, days_until_expiry, status_label).
        status_label is one of: "perpetual", "expired", "expiring_soon", "active".
        """
        if is_perpetual or good_until_date is None:
            return (False, None, "perpetual")
        days_until = (good_until_date - date.today()).days
        if days_until < 0:
            return (True, days_until, "expired")
        elif days_until <= 30:
            return (False, days_until, "expiring_soon")
        return (False, days_until, "active")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_expired_documents(
        self,
        db: AsyncSession,
        organization_id: UUID,
        limit: int = 100,
    ) -> List[KnowledgeDocument]:
        """Documents past their GUD (excludes perpetual)."""
        today = date.today()
        result = await db.execute(
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.organization_id == organization_id,
                KnowledgeDocument.is_perpetual == False,
                KnowledgeDocument.good_until_date.isnot(None),
                KnowledgeDocument.good_until_date < today,
                KnowledgeDocument.is_active == True,
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_expiring_soon(
        self,
        db: AsyncSession,
        organization_id: UUID,
        days: int = 30,
        limit: int = 100,
    ) -> List[KnowledgeDocument]:
        """Documents expiring within *days* days."""
        today = date.today()
        future = today + timedelta(days=days)
        result = await db.execute(
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.organization_id == organization_id,
                KnowledgeDocument.is_perpetual == False,
                KnowledgeDocument.good_until_date.isnot(None),
                KnowledgeDocument.good_until_date >= today,
                KnowledgeDocument.good_until_date <= future,
                KnowledgeDocument.is_active == True,
            )
            .order_by(KnowledgeDocument.good_until_date)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Expiration processing
    # ------------------------------------------------------------------

    async def check_and_process_expirations(
        self,
        db: AsyncSession,
        organization_id: UUID,
    ) -> Dict[str, int]:
        """
        Process expired documents:
        - auto_delete_on_expiry=True → deactivate
        - auto_delete_on_expiry=False → flag for manual review
        """
        today = date.today()
        result = await db.execute(
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.organization_id == organization_id,
                KnowledgeDocument.is_perpetual == False,
                KnowledgeDocument.good_until_date.isnot(None),
                KnowledgeDocument.good_until_date < today,
                KnowledgeDocument.is_active == True,
            )
        )
        expired = list(result.scalars().all())

        deleted = 0
        flagged = 0
        for doc in expired:
            if doc.auto_delete_on_expiry:
                doc.is_active = False
                deleted += 1
            else:
                doc.needs_manual_review = True
                flagged += 1

        await db.commit()
        return {"deactivated": deleted, "flagged_for_review": flagged}

    # ------------------------------------------------------------------
    # GUD extension
    # ------------------------------------------------------------------

    async def extend_validity(
        self,
        db: AsyncSession,
        document_id: UUID,
        new_gud: Optional[date] = None,
        is_perpetual: bool = False,
    ) -> Optional[KnowledgeDocument]:
        """Extend a document's GUD or mark it perpetual."""
        result = await db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return None

        if is_perpetual:
            doc.is_perpetual = True
            doc.good_until_date = None
        else:
            doc.is_perpetual = False
            doc.good_until_date = new_gud

        doc.expiry_notified = False
        doc.needs_manual_review = False
        await db.commit()
        await db.refresh(doc)
        return doc

    # ------------------------------------------------------------------
    # Department management
    # ------------------------------------------------------------------

    async def get_departments(
        self,
        db: AsyncSession,
        organization_id: UUID,
    ) -> List[Department]:
        result = await db.execute(
            select(Department)
            .where(
                Department.organization_id == organization_id,
                Department.is_active == True,
            )
            .order_by(Department.name)
        )
        return list(result.scalars().all())

    async def create_department(
        self,
        db: AsyncSession,
        organization_id: UUID,
        name: str,
        contact_email: Optional[str] = None,
    ) -> Department:
        dept = Department(
            organization_id=organization_id,
            name=name,
            contact_email=contact_email,
        )
        db.add(dept)
        await db.commit()
        await db.refresh(dept)
        return dept


# Global singleton
document_expiration_service = DocumentExpirationService()

"""
Notification Service — manages in-app notifications for users.

Responsibilities:
- Create notifications for workflow events
- Query unread counts and paginated lists
- Mark notifications as read (single / bulk)
- Helper methods for common notification scenarios
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import Notification, NotificationType

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing user notifications."""

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def create_notification(
        self,
        db: AsyncSession,
        user_id: UUID,
        organization_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        link_url: Optional[str] = None,
        extra_data: Optional[dict] = None,
    ) -> Notification:
        """Create a new notification for a user."""
        notification = Notification(
            user_id=user_id,
            organization_id=organization_id,
            type=notification_type,
            title=title,
            message=message,
            link_url=link_url,
            extra_data=extra_data or {},
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        logger.debug(f"Notification created: {notification_type.value} for user {user_id}")
        return notification

    async def get_unread_count(self, db: AsyncSession, user_id: UUID) -> int:
        """Get count of unread notifications for a user."""
        result = await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
        )
        return result.scalar() or 0

    async def list_notifications(
        self,
        db: AsyncSession,
        user_id: UUID,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Notification], int]:
        """List notifications for a user with pagination."""
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        query = query.order_by(Notification.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        notifications = list(result.scalars().all())

        return notifications, total

    async def mark_read(
        self, db: AsyncSession, notification_id: UUID, user_id: UUID
    ) -> Optional[Notification]:
        """Mark a single notification as read."""
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return None

        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(notification)
        return notification

    async def mark_all_read(self, db: AsyncSession, user_id: UUID) -> int:
        """Mark all unread notifications as read. Returns count updated."""
        result = await db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return result.rowcount or 0

    async def delete_notification(
        self, db: AsyncSession, notification_id: UUID, user_id: UUID
    ) -> bool:
        """Delete a notification. Returns True if deleted."""
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return False

        await db.delete(notification)
        await db.commit()
        return True

    # ------------------------------------------------------------------
    # Workflow helpers — question lifecycle
    # ------------------------------------------------------------------

    async def notify_question_answered(
        self,
        db: AsyncSession,
        user_id: UUID,
        organization_id: UUID,
        question_id: UUID,
        question_text: str,
    ) -> Notification:
        """Notify user that their question has been answered by an expert."""
        short = question_text[:100] + ("..." if len(question_text) > 100 else "")
        return await self.create_notification(
            db=db,
            user_id=user_id,
            organization_id=organization_id,
            notification_type=NotificationType.QUESTION_ANSWERED,
            title="Your question has been answered",
            message=f'An expert answered: "{short}"',
            link_url=f"/questions/{question_id}",
            extra_data={"question_id": str(question_id)},
        )

    async def notify_auto_answer(
        self,
        db: AsyncSession,
        user_id: UUID,
        organization_id: UUID,
        question_id: UUID,
        question_text: str,
    ) -> Notification:
        """Notify user that their question was auto-answered (TransWarp)."""
        short = question_text[:100] + ("..." if len(question_text) > 100 else "")
        return await self.create_notification(
            db=db,
            user_id=user_id,
            organization_id=organization_id,
            notification_type=NotificationType.AUTO_ANSWER_AVAILABLE,
            title="Instant answer available",
            message=f'Loris found an answer for: "{short}"',
            link_url=f"/questions/{question_id}",
            extra_data={"question_id": str(question_id)},
        )

    async def notify_question_assigned(
        self,
        db: AsyncSession,
        expert_id: UUID,
        organization_id: UUID,
        question_id: UUID,
        question_text: str,
    ) -> Notification:
        """Notify expert that a question was assigned to them."""
        short = question_text[:100] + ("..." if len(question_text) > 100 else "")
        return await self.create_notification(
            db=db,
            user_id=expert_id,
            organization_id=organization_id,
            notification_type=NotificationType.QUESTION_ASSIGNED,
            title="Question assigned to you",
            message=f'New question: "{short}"',
            link_url=f"/expert/questions/{question_id}",
            extra_data={"question_id": str(question_id)},
        )

    async def notify_clarification_requested(
        self,
        db: AsyncSession,
        user_id: UUID,
        organization_id: UUID,
        question_id: UUID,
        clarification_text: str,
    ) -> Notification:
        """Notify user that an expert requested clarification."""
        short = clarification_text[:150] + ("..." if len(clarification_text) > 150 else "")
        return await self.create_notification(
            db=db,
            user_id=user_id,
            organization_id=organization_id,
            notification_type=NotificationType.CLARIFICATION_REQUESTED,
            title="Expert needs more information",
            message=short,
            link_url=f"/questions/{question_id}",
            extra_data={"question_id": str(question_id)},
        )

    async def notify_auto_answer_rejected(
        self,
        db: AsyncSession,
        expert_id: UUID,
        organization_id: UUID,
        question_id: UUID,
        question_text: str,
        rejection_reason: Optional[str] = None,
    ) -> Notification:
        """Notify rule creator that a user rejected an auto-answer."""
        short = question_text[:100] + ("..." if len(question_text) > 100 else "")
        msg = f'User rejected auto-answer for: "{short}"'
        if rejection_reason:
            msg += f" Reason: {rejection_reason[:100]}"
        return await self.create_notification(
            db=db,
            user_id=expert_id,
            organization_id=organization_id,
            notification_type=NotificationType.AUTO_ANSWER_REJECTED,
            title="Auto-answer rejected by user",
            message=msg,
            link_url=f"/expert/questions/{question_id}",
            extra_data={
                "question_id": str(question_id),
                "rejection_reason": rejection_reason,
            },
        )

    # ------------------------------------------------------------------
    # Workflow helpers — GUD expiry
    # ------------------------------------------------------------------

    async def notify_rule_expiring(
        self,
        db: AsyncSession,
        expert_id: UUID,
        organization_id: UUID,
        rule_id: UUID,
        rule_name: str,
        days_until_expiry: int,
    ) -> Notification:
        """Notify expert that an automation rule is approaching its GUD."""
        ntype = (
            NotificationType.RULE_EXPIRING_URGENT
            if days_until_expiry <= 7
            else NotificationType.RULE_EXPIRING_SOON
        )
        title = (
            "Automation rule expiring soon!"
            if days_until_expiry <= 7
            else "Automation rule expiring"
        )
        return await self.create_notification(
            db=db,
            user_id=expert_id,
            organization_id=organization_id,
            notification_type=ntype,
            title=title,
            message=f'Rule "{rule_name}" expires in {days_until_expiry} days',
            link_url="/expert/automation",
            extra_data={"rule_id": str(rule_id), "days_until_expiry": days_until_expiry},
        )

    async def notify_rule_expired(
        self,
        db: AsyncSession,
        expert_id: UUID,
        organization_id: UUID,
        rule_id: UUID,
        rule_name: str,
    ) -> Notification:
        """Notify expert that an automation rule has expired and been deactivated."""
        return await self.create_notification(
            db=db,
            user_id=expert_id,
            organization_id=organization_id,
            notification_type=NotificationType.RULE_EXPIRED,
            title="Automation rule expired",
            message=f'Rule "{rule_name}" has expired and been deactivated',
            link_url="/expert/automation",
            extra_data={"rule_id": str(rule_id)},
        )

    async def notify_document_expiring(
        self,
        db: AsyncSession,
        expert_id: UUID,
        organization_id: UUID,
        document_id: UUID,
        document_title: str,
        days_until_expiry: int,
    ) -> Notification:
        """Notify expert that a document is approaching its GUD."""
        return await self.create_notification(
            db=db,
            user_id=expert_id,
            organization_id=organization_id,
            notification_type=NotificationType.DOCUMENT_EXPIRING_SOON,
            title="Document expiring soon",
            message=f'"{document_title}" expires in {days_until_expiry} days',
            link_url="/expert/documents",
            extra_data={"document_id": str(document_id), "days_until_expiry": days_until_expiry},
        )

    async def notify_document_expired(
        self,
        db: AsyncSession,
        expert_id: UUID,
        organization_id: UUID,
        document_id: UUID,
        document_title: str,
    ) -> Notification:
        """Notify expert that a document has expired."""
        return await self.create_notification(
            db=db,
            user_id=expert_id,
            organization_id=organization_id,
            notification_type=NotificationType.DOCUMENT_EXPIRED,
            title="Document expired",
            message=f'"{document_title}" has expired',
            link_url="/expert/documents",
            extra_data={"document_id": str(document_id)},
        )

    async def notify_fact_expiring(
        self,
        db: AsyncSession,
        expert_id: UUID,
        organization_id: UUID,
        fact_id: UUID,
        fact_summary: str,
        days_until_expiry: int,
    ) -> Notification:
        """Notify expert that a knowledge fact is approaching its GUD."""
        short = fact_summary[:100] + ("..." if len(fact_summary) > 100 else "")
        return await self.create_notification(
            db=db,
            user_id=expert_id,
            organization_id=organization_id,
            notification_type=NotificationType.FACT_EXPIRING_SOON,
            title="Knowledge fact expiring soon",
            message=f'"{short}" expires in {days_until_expiry} days',
            link_url="/expert/knowledge",
            extra_data={"fact_id": str(fact_id), "days_until_expiry": days_until_expiry},
        )


# Global singleton
notification_service = NotificationService()

"""
Scheduler Service — runs background jobs for GUD enforcement and MoltenLoris sync.

Uses APScheduler to run periodic tasks:
- Daily check for expired automation rules, documents, knowledge facts
- Creates notifications at 30/7/0-day thresholds
- Deactivates expired items
- Hourly knowledge export to Google Drive
- Every 10 minutes: Slack scan for expert answers
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.automation import AutomationRule
from app.models.documents import KnowledgeDocument
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.wisdom import WisdomFact
from app.services.notification_service import notification_service
from app.services.subdomain_service import subdomain_service

logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled background jobs."""

    def __init__(self):
        self.scheduler: AsyncIOScheduler | None = None

    def start(self):
        """Start the scheduler with all configured jobs."""
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(
            self.check_gud_expiry,
            CronTrigger(hour=2, minute=0),
            id="check_gud_expiry",
            name="Daily GUD expiry check",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self.check_sla_breaches,
            CronTrigger(minute=0),  # Every hour at :00
            id="check_sla_breaches",
            name="Hourly SLA breach check",
            replace_existing=True,
        )

        # MoltenLoris sync jobs (only if MCP is configured)
        if settings.MCP_SERVER_URL:
            # Scan Slack every 10 minutes
            self.scheduler.add_job(
                self.scan_slack_for_answers,
                IntervalTrigger(minutes=10),
                id="scan_slack_for_answers",
                name="Slack scan for expert answers",
                replace_existing=True,
            )
            # Export knowledge hourly
            self.scheduler.add_job(
                self.export_knowledge_to_gdrive,
                IntervalTrigger(hours=1),
                id="export_knowledge_to_gdrive",
                name="Export knowledge to Google Drive",
                replace_existing=True,
            )
            logger.info("MoltenLoris sync jobs configured (Slack scan: 10min, GDrive export: 1hr)")

        self.scheduler.start()
        logger.info("Scheduler started — daily GUD checks at 02:00, hourly SLA checks")

    def stop(self):
        """Shut down the scheduler gracefully."""
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    # ------------------------------------------------------------------
    # Hourly SLA check
    # ------------------------------------------------------------------

    async def check_sla_breaches(self):
        """Hourly job: check for questions exceeding their sub-domain's SLA."""
        logger.info("Running hourly SLA breach check …")
        async with AsyncSessionLocal() as db:
            stats = await subdomain_service.check_sla_breaches(db)
        logger.info(f"SLA check complete — {stats}")

    # ------------------------------------------------------------------
    # Main daily job
    # ------------------------------------------------------------------

    async def check_gud_expiry(self):
        """Daily job: check automation rules, documents, and facts for GUD expiry."""
        logger.info("Running daily GUD expiry check …")
        async with AsyncSessionLocal() as db:
            rule_stats = await self._check_automation_rules(db)
            doc_stats = await self._check_documents(db)
            fact_stats = await self._check_facts(db)
        logger.info(
            f"GUD check complete — rules: {rule_stats}, docs: {doc_stats}, facts: {fact_stats}"
        )

    # ------------------------------------------------------------------
    # Automation rules
    # ------------------------------------------------------------------

    async def _check_automation_rules(self, db: AsyncSession) -> Dict[str, int]:
        today = date.today()
        result = await db.execute(
            select(AutomationRule).where(
                AutomationRule.good_until_date.isnot(None),
                AutomationRule.is_enabled == True,
            )
        )
        rules = list(result.scalars().all())

        stats = {"expired": 0, "warned_7d": 0, "warned_30d": 0}
        for rule in rules:
            days_left = (rule.good_until_date - today).days

            if days_left <= 0:
                rule.is_enabled = False
                stats["expired"] += 1
                await notification_service.notify_rule_expired(
                    db=db,
                    expert_id=rule.created_by_id,
                    organization_id=rule.organization_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                )
            elif days_left == 7:
                stats["warned_7d"] += 1
                await notification_service.notify_rule_expiring(
                    db=db,
                    expert_id=rule.created_by_id,
                    organization_id=rule.organization_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    days_until_expiry=days_left,
                )
            elif days_left == 30:
                stats["warned_30d"] += 1
                await notification_service.notify_rule_expiring(
                    db=db,
                    expert_id=rule.created_by_id,
                    organization_id=rule.organization_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    days_until_expiry=days_left,
                )

        await db.commit()
        return stats

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    async def _get_org_expert_ids(
        self, db: AsyncSession, organization_id, cache: Dict
    ) -> List:
        """Get expert/admin user IDs for an organization (with cache)."""
        if organization_id not in cache:
            result = await db.execute(
                select(User.id).where(
                    User.organization_id == organization_id,
                    User.role.in_([UserRole.DOMAIN_EXPERT, UserRole.ADMIN]),
                    User.is_active == True,
                )
            )
            cache[organization_id] = [row[0] for row in result.all()]
        return cache[organization_id]

    async def _check_documents(self, db: AsyncSession) -> Dict[str, int]:
        today = date.today()
        result = await db.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.is_perpetual == False,
                KnowledgeDocument.good_until_date.isnot(None),
                KnowledgeDocument.is_active == True,
            )
        )
        docs = list(result.scalars().all())

        stats = {"expired": 0, "warned_7d": 0, "warned_30d": 0}
        expert_cache: Dict = {}

        for doc in docs:
            days_left = (doc.good_until_date - today).days
            expert_ids = await self._get_org_expert_ids(db, doc.organization_id, expert_cache)

            if days_left <= 0:
                if doc.auto_delete_on_expiry:
                    doc.is_active = False
                doc.needs_manual_review = True
                stats["expired"] += 1
                for eid in expert_ids:
                    await notification_service.notify_document_expired(
                        db=db,
                        expert_id=eid,
                        organization_id=doc.organization_id,
                        document_id=doc.id,
                        document_title=doc.title or "Untitled document",
                    )
            elif days_left in (7, 30):
                key = "warned_7d" if days_left == 7 else "warned_30d"
                stats[key] += 1
                for eid in expert_ids:
                    await notification_service.notify_document_expiring(
                        db=db,
                        expert_id=eid,
                        organization_id=doc.organization_id,
                        document_id=doc.id,
                        document_title=doc.title or "Untitled document",
                        days_until_expiry=days_left,
                    )

        await db.commit()
        return stats

    # ------------------------------------------------------------------
    # Knowledge facts
    # ------------------------------------------------------------------

    async def _check_facts(self, db: AsyncSession) -> Dict[str, int]:
        today = date.today()
        result = await db.execute(
            select(WisdomFact).where(
                WisdomFact.is_perpetual == False,
                WisdomFact.good_until_date.isnot(None),
                WisdomFact.is_active == True,
            )
        )
        facts = list(result.scalars().all())

        stats = {"expired": 0, "warned_7d": 0, "warned_30d": 0}
        expert_cache: Dict = {}

        for fact in facts:
            days_left = (fact.good_until_date - today).days
            expert_ids = await self._get_org_expert_ids(db, fact.organization_id, expert_cache)

            if days_left <= 0:
                fact.is_active = False
                stats["expired"] += 1
            elif days_left in (7, 30):
                key = "warned_7d" if days_left == 7 else "warned_30d"
                stats[key] += 1
                for eid in expert_ids:
                    await notification_service.notify_fact_expiring(
                        db=db,
                        expert_id=eid,
                        organization_id=fact.organization_id,
                        fact_id=fact.id,
                        fact_summary=fact.summary or fact.content[:100],
                        days_until_expiry=days_left,
                    )

        await db.commit()
        return stats


    # ------------------------------------------------------------------
    # MoltenLoris Sync Jobs
    # ------------------------------------------------------------------

    async def scan_slack_for_answers(self):
        """
        Scan Slack channels for expert answers to MoltenLoris escalations.
        Runs every 10 minutes, looks back 15 minutes to ensure no gaps.
        """
        if not settings.slack_channels_list:
            return

        logger.info("Running Slack scan for expert answers …")

        async with AsyncSessionLocal() as db:
            # Get all organizations
            result = await db.execute(select(Organization))
            orgs = list(result.scalars().all())

            total_captures = 0
            for org in orgs:
                try:
                    # Import here to avoid circular imports
                    from app.services.slack_monitor_service import SlackMonitorService

                    service = SlackMonitorService(db, org.id)
                    # Look back 15 minutes (slightly more than scan interval to ensure overlap)
                    since = datetime.now(timezone.utc) - timedelta(minutes=15)

                    qa_pairs = await service.scan_for_expert_answers(since=since)
                    if qa_pairs:
                        captures = await service.create_captures(qa_pairs)
                        total_captures += len(captures)

                except Exception as e:
                    logger.error(f"Slack scan error for org {org.id}: {e}")

        logger.info(f"Slack scan complete — created {total_captures} captures")

    async def export_knowledge_to_gdrive(self):
        """
        Export all approved knowledge to Google Drive.
        Runs every hour.
        """
        if not settings.MCP_SERVER_URL:
            return

        logger.info("Running knowledge export to Google Drive …")

        async with AsyncSessionLocal() as db:
            # Get all organizations
            result = await db.execute(select(Organization))
            orgs = list(result.scalars().all())

            total_exported = 0
            for org in orgs:
                try:
                    # Import here to avoid circular imports
                    from app.services.knowledge_export_service import KnowledgeExportService

                    service = KnowledgeExportService(db, org.id)
                    results = await service.export_all_knowledge()

                    exported = [r for r in results if r.get("status") == "exported"]
                    total_exported += len(exported)

                except Exception as e:
                    logger.error(f"Knowledge export error for org {org.id}: {e}")

        logger.info(f"Knowledge export complete — exported {total_exported} files")


# Global singleton
scheduler_service = SchedulerService()

"""
Analytics Service — computes metrics on-the-fly from existing tables.

Provides overview KPIs, question trends, automation performance,
knowledge coverage, and expert performance metrics.  All queries are
scoped by organization_id for multi-tenancy.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, case, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.questions import Question, QuestionStatus, QuestionPriority
from app.models.answers import Answer, AnswerSource
from app.models.automation import AutomationRule, AutomationLog, AutomationLogAction
from app.models.wisdom import WisdomFact, WisdomTier
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

# Statuses that count as "auto-answered"
_AUTO_STATUSES = {QuestionStatus.AUTO_ANSWERED}
# Statuses that count as "expert-answered"
_EXPERT_STATUSES = {QuestionStatus.ANSWERED, QuestionStatus.RESOLVED}


class AnalyticsService:
    """Compute analytics metrics from existing data."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _period_to_dates(period: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Return (start, prev_start) for the given period string.

        prev_start is the start of the equivalent previous period,
        used for trend comparison.
        """
        now = datetime.now(timezone.utc)
        mapping = {"7d": 7, "30d": 30, "90d": 90}
        days = mapping.get(period)
        if days is None:
            return None, None
        start = now - timedelta(days=days)
        prev_start = start - timedelta(days=days)
        return start, prev_start

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    async def get_overview(
        self,
        db: AsyncSession,
        organization_id: UUID,
        period: str = "30d",
    ) -> Dict[str, Any]:
        start, prev_start = self._period_to_dates(period)

        # Base filter
        org_filter = Question.organization_id == organization_id

        # Total questions (all time)
        total_q = (await db.execute(
            select(func.count()).select_from(Question).where(org_filter)
        )).scalar() or 0

        # Total resolved
        total_resolved = (await db.execute(
            select(func.count()).select_from(Question).where(
                org_filter, Question.status == QuestionStatus.RESOLVED
            )
        )).scalar() or 0

        # Auto-answered count (all time)
        auto_count = (await db.execute(
            select(func.count()).select_from(Question).where(
                org_filter, Question.automation_rule_id.isnot(None)
            )
        )).scalar() or 0

        automation_rate = (auto_count / total_q * 100) if total_q > 0 else 0.0

        # Averages
        avg_response = (await db.execute(
            select(func.avg(Question.response_time_seconds)).where(
                org_filter, Question.response_time_seconds.isnot(None)
            )
        )).scalar()

        avg_resolution = (await db.execute(
            select(func.avg(Question.resolution_time_seconds)).where(
                org_filter, Question.resolution_time_seconds.isnot(None)
            )
        )).scalar()

        avg_satisfaction = (await db.execute(
            select(func.avg(Question.satisfaction_rating)).where(
                org_filter, Question.satisfaction_rating.isnot(None)
            )
        )).scalar()

        # Period counts for trend
        period_count = total_q
        prev_count = 0
        if start is not None:
            period_count = (await db.execute(
                select(func.count()).select_from(Question).where(
                    org_filter, Question.created_at >= start
                )
            )).scalar() or 0
            if prev_start is not None:
                prev_count = (await db.execute(
                    select(func.count()).select_from(Question).where(
                        org_filter,
                        Question.created_at >= prev_start,
                        Question.created_at < start,
                    )
                )).scalar() or 0

        return {
            "total_questions": total_q,
            "total_resolved": total_resolved,
            "automation_rate": round(automation_rate, 1),
            "avg_response_time_seconds": round(avg_response, 1) if avg_response else None,
            "avg_resolution_time_seconds": round(avg_resolution, 1) if avg_resolution else None,
            "avg_satisfaction": round(float(avg_satisfaction), 2) if avg_satisfaction else None,
            "period_question_count": period_count,
            "prev_period_question_count": prev_count,
            "period": period,
        }

    # ------------------------------------------------------------------
    # Question trends
    # ------------------------------------------------------------------

    async def get_question_trends(
        self,
        db: AsyncSession,
        organization_id: UUID,
        period: str = "30d",
    ) -> Dict[str, Any]:
        start, _ = self._period_to_dates(period)
        org_filter = Question.organization_id == organization_id

        # Daily volumes
        date_col = cast(Question.created_at, Date).label("day")
        q = (
            select(
                date_col,
                func.count().label("total"),
                func.count(case((Question.automation_rule_id.isnot(None), 1))).label("auto_answered"),
            )
            .where(org_filter)
            .group_by(date_col)
            .order_by(date_col)
        )
        if start is not None:
            q = q.where(Question.created_at >= start)

        rows = (await db.execute(q)).all()
        daily_volumes = []
        for row in rows:
            daily_volumes.append({
                "date": row.day.isoformat(),
                "total": row.total,
                "auto_answered": row.auto_answered,
                "expert_answered": row.total - row.auto_answered,
            })

        # Status distribution
        status_rows = (await db.execute(
            select(Question.status, func.count().label("cnt"))
            .where(org_filter)
            .group_by(Question.status)
        )).all()
        status_dist = {row.status.value: row.cnt for row in status_rows}

        # Priority distribution
        prio_rows = (await db.execute(
            select(Question.priority, func.count().label("cnt"))
            .where(org_filter)
            .group_by(Question.priority)
        )).all()
        priority_dist = {row.priority.value: row.cnt for row in prio_rows}

        return {
            "daily_volumes": daily_volumes,
            "status_distribution": status_dist,
            "priority_distribution": priority_dist,
        }

    # ------------------------------------------------------------------
    # Automation performance
    # ------------------------------------------------------------------

    async def get_automation_performance(
        self,
        db: AsyncSession,
        organization_id: UUID,
        period: str = "30d",
    ) -> Dict[str, Any]:
        start, _ = self._period_to_dates(period)
        org_filter = AutomationRule.organization_id == organization_id

        # Overall totals from rules
        totals = (await db.execute(
            select(
                func.sum(AutomationRule.times_triggered).label("triggers"),
                func.sum(AutomationRule.times_accepted).label("accepted"),
                func.sum(AutomationRule.times_rejected).label("rejected"),
            ).where(org_filter)
        )).one()

        total_triggers = totals.triggers or 0
        total_accepted = totals.accepted or 0
        total_rejected = totals.rejected or 0
        total_decisions = total_accepted + total_rejected
        overall_rate = (total_accepted / total_decisions * 100) if total_decisions > 0 else None

        # Per-rule performance (top 20 by triggers)
        rule_rows = (await db.execute(
            select(
                AutomationRule.id,
                AutomationRule.name,
                AutomationRule.times_triggered,
                AutomationRule.times_accepted,
                AutomationRule.times_rejected,
                AutomationRule.is_enabled,
            )
            .where(org_filter)
            .order_by(AutomationRule.times_triggered.desc())
            .limit(20)
        )).all()

        rules = []
        for r in rule_rows:
            decisions = r.times_accepted + r.times_rejected
            rules.append({
                "rule_id": str(r.id),
                "name": r.name,
                "times_triggered": r.times_triggered,
                "times_accepted": r.times_accepted,
                "times_rejected": r.times_rejected,
                "acceptance_rate": round(r.times_accepted / decisions * 100, 1) if decisions > 0 else None,
                "is_enabled": r.is_enabled,
            })

        # Daily automation trend from AutomationLog
        log_date_col = cast(AutomationLog.created_at, Date).label("day")
        log_q = (
            select(
                log_date_col,
                func.count(case((AutomationLog.action == AutomationLogAction.ACCEPTED, 1))).label("accepted"),
                func.count(case((AutomationLog.action == AutomationLogAction.REJECTED, 1))).label("rejected"),
                func.count(case((AutomationLog.action == AutomationLogAction.DELIVERED, 1))).label("delivered"),
            )
            .join(AutomationRule, AutomationLog.rule_id == AutomationRule.id)
            .where(AutomationRule.organization_id == organization_id)
            .group_by(log_date_col)
            .order_by(log_date_col)
        )
        if start is not None:
            log_q = log_q.where(AutomationLog.created_at >= start)

        log_rows = (await db.execute(log_q)).all()
        daily_trend = [
            {
                "date": row.day.isoformat(),
                "delivered": row.delivered,
                "accepted": row.accepted,
                "rejected": row.rejected,
            }
            for row in log_rows
        ]

        return {
            "total_triggers": total_triggers,
            "total_accepted": total_accepted,
            "total_rejected": total_rejected,
            "overall_acceptance_rate": round(overall_rate, 1) if overall_rate is not None else None,
            "rules": rules,
            "daily_trend": daily_trend,
        }

    # ------------------------------------------------------------------
    # Knowledge coverage
    # ------------------------------------------------------------------

    async def get_knowledge_coverage(
        self,
        db: AsyncSession,
        organization_id: UUID,
    ) -> Dict[str, Any]:
        org_filter = WisdomFact.organization_id == organization_id
        active_filter = WisdomFact.is_active == True  # noqa: E712

        # Total active facts
        total = (await db.execute(
            select(func.count()).select_from(WisdomFact).where(org_filter, active_filter)
        )).scalar() or 0

        # By tier
        tier_rows = (await db.execute(
            select(WisdomFact.tier, func.count().label("cnt"))
            .where(org_filter, active_filter)
            .group_by(WisdomFact.tier)
        )).all()
        by_tier = {row.tier.value: row.cnt for row in tier_rows}

        # Expiring soon (next 30 days)
        today = date.today()
        soon = today + timedelta(days=30)
        expiring_soon = (await db.execute(
            select(func.count()).select_from(WisdomFact).where(
                org_filter,
                active_filter,
                WisdomFact.is_perpetual == False,  # noqa: E712
                WisdomFact.good_until_date.isnot(None),
                WisdomFact.good_until_date <= soon,
                WisdomFact.good_until_date >= today,
            )
        )).scalar() or 0

        # Recently added (7 days)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recently_added = (await db.execute(
            select(func.count()).select_from(WisdomFact).where(
                org_filter, active_filter, WisdomFact.created_at >= week_ago
            )
        )).scalar() or 0

        # Avg confidence
        avg_conf = (await db.execute(
            select(func.avg(WisdomFact.confidence_score)).where(
                org_filter, active_filter, WisdomFact.confidence_score.isnot(None)
            )
        )).scalar()

        return {
            "total_facts": total,
            "by_tier": by_tier,
            "expiring_soon": expiring_soon,
            "recently_added": recently_added,
            "avg_confidence": round(float(avg_conf), 2) if avg_conf else None,
        }

    # ------------------------------------------------------------------
    # Expert performance
    # ------------------------------------------------------------------

    async def get_expert_performance(
        self,
        db: AsyncSession,
        organization_id: UUID,
        period: str = "30d",
    ) -> Dict[str, Any]:
        start, _ = self._period_to_dates(period)

        # Join Answer → Question to scope by org, then group by expert
        q = (
            select(
                User.name.label("expert_name"),
                func.count(Answer.id).label("questions_answered"),
                func.avg(Question.response_time_seconds).label("avg_response"),
                func.avg(Question.satisfaction_rating).label("avg_satisfaction"),
            )
            .join(Answer, Answer.created_by_id == User.id)
            .join(Question, Answer.question_id == Question.id)
            .where(
                Question.organization_id == organization_id,
                Answer.source != AnswerSource.AUTOMATION,
            )
            .group_by(User.id, User.name)
            .order_by(func.count(Answer.id).desc())
        )
        if start is not None:
            q = q.where(Answer.created_at >= start)

        rows = (await db.execute(q)).all()
        experts = []
        for row in rows:
            experts.append({
                "expert_name": row.expert_name,
                "questions_answered": row.questions_answered,
                "avg_response_time_seconds": round(float(row.avg_response), 1) if row.avg_response else None,
                "avg_satisfaction": round(float(row.avg_satisfaction), 2) if row.avg_satisfaction else None,
            })

        return {"experts": experts}


# Global singleton
analytics_service = AnalyticsService()

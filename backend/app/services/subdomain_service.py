"""
SubDomain Service — manages sub-domain routing for expert assignment.

Responsibilities:
- CRUD for sub-domains
- Expert-to-subdomain assignment
- AI-based question classification
- Broadcast routing (notify all experts in a sub-domain)
- SLA breach detection
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subdomain import SubDomain, ExpertSubDomainAssignment
from app.models.questions import Question, QuestionStatus, QuestionRouting
from app.models.user import User, UserRole
from app.models.notifications import NotificationType
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)


class SubDomainService:
    """Service for sub-domain management and question routing."""

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_subdomain(
        self,
        db: AsyncSession,
        organization_id: UUID,
        name: str,
        description: Optional[str] = None,
        sla_hours: int = 24,
    ) -> SubDomain:
        subdomain = SubDomain(
            organization_id=organization_id,
            name=name,
            description=description,
            sla_hours=sla_hours,
        )
        db.add(subdomain)
        await db.commit()
        await db.refresh(subdomain)
        return subdomain

    async def update_subdomain(
        self,
        db: AsyncSession,
        subdomain: SubDomain,
        name: Optional[str] = None,
        description: Optional[str] = None,
        sla_hours: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> SubDomain:
        if name is not None:
            subdomain.name = name
        if description is not None:
            subdomain.description = description
        if sla_hours is not None:
            subdomain.sla_hours = sla_hours
        if is_active is not None:
            subdomain.is_active = is_active
        await db.commit()
        await db.refresh(subdomain)
        return subdomain

    async def get_subdomain(
        self, db: AsyncSession, subdomain_id: UUID
    ) -> Optional[SubDomain]:
        result = await db.execute(
            select(SubDomain).where(SubDomain.id == subdomain_id)
        )
        return result.scalar_one_or_none()

    async def list_subdomains(
        self,
        db: AsyncSession,
        organization_id: UUID,
        active_only: bool = False,
    ) -> List[SubDomain]:
        query = select(SubDomain).where(
            SubDomain.organization_id == organization_id
        )
        if active_only:
            query = query.where(SubDomain.is_active == True)
        query = query.order_by(SubDomain.name)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def delete_subdomain(
        self, db: AsyncSession, subdomain: SubDomain
    ) -> None:
        subdomain.is_active = False
        await db.commit()

    # ------------------------------------------------------------------
    # Expert assignment
    # ------------------------------------------------------------------

    async def assign_experts(
        self,
        db: AsyncSession,
        subdomain_id: UUID,
        expert_ids: List[UUID],
    ) -> List[ExpertSubDomainAssignment]:
        """Replace expert assignments for a sub-domain."""
        # Remove existing
        await db.execute(
            delete(ExpertSubDomainAssignment).where(
                ExpertSubDomainAssignment.subdomain_id == subdomain_id
            )
        )

        assignments = []
        for eid in expert_ids:
            a = ExpertSubDomainAssignment(
                expert_id=eid,
                subdomain_id=subdomain_id,
            )
            db.add(a)
            assignments.append(a)

        await db.commit()
        return assignments

    async def add_expert(
        self,
        db: AsyncSession,
        subdomain_id: UUID,
        expert_id: UUID,
        is_primary: bool = False,
    ) -> ExpertSubDomainAssignment:
        assignment = ExpertSubDomainAssignment(
            expert_id=expert_id,
            subdomain_id=subdomain_id,
            is_primary=is_primary,
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)
        return assignment

    async def remove_expert(
        self, db: AsyncSession, subdomain_id: UUID, expert_id: UUID
    ) -> bool:
        result = await db.execute(
            select(ExpertSubDomainAssignment).where(
                ExpertSubDomainAssignment.subdomain_id == subdomain_id,
                ExpertSubDomainAssignment.expert_id == expert_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            return False
        await db.delete(assignment)
        await db.commit()
        return True

    async def get_experts_for_subdomain(
        self, db: AsyncSession, subdomain_id: UUID
    ) -> List[User]:
        result = await db.execute(
            select(User)
            .join(
                ExpertSubDomainAssignment,
                ExpertSubDomainAssignment.expert_id == User.id,
            )
            .where(
                ExpertSubDomainAssignment.subdomain_id == subdomain_id,
                User.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def get_expert_subdomain_ids(
        self, db: AsyncSession, expert_id: UUID
    ) -> List[UUID]:
        """Get subdomain IDs assigned to an expert."""
        result = await db.execute(
            select(ExpertSubDomainAssignment.subdomain_id).where(
                ExpertSubDomainAssignment.expert_id == expert_id
            )
        )
        return [row[0] for row in result.all()]

    async def get_expert_count(
        self, db: AsyncSession, subdomain_id: UUID
    ) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(ExpertSubDomainAssignment)
            .where(ExpertSubDomainAssignment.subdomain_id == subdomain_id)
        )
        return result.scalar() or 0

    # ------------------------------------------------------------------
    # AI classification
    # ------------------------------------------------------------------

    async def classify_question(
        self,
        db: AsyncSession,
        question_text: str,
        organization_id: UUID,
    ) -> Optional[UUID]:
        """Use AI to classify a question into a sub-domain. Returns subdomain_id or None."""
        subdomains = await self.list_subdomains(db, organization_id, active_only=True)
        if not subdomains:
            return None

        subdomain_list = "\n".join(
            f"- {s.name}: {s.description or 'No description'}" for s in subdomains
        )

        prompt = f"""Given this question from a legal department user, classify it into one of the available sub-domains.

QUESTION:
{question_text}

AVAILABLE SUB-DOMAINS:
{subdomain_list}

Respond with ONLY the exact sub-domain name that best matches. If none clearly match, respond with "NONE".
"""

        try:
            from app.services.ai_provider_service import ai_provider_service

            response = await ai_provider_service.generate(
                prompt=prompt,
                system_prompt="You are a legal domain classifier. Respond with only the sub-domain name.",
                temperature=0.1,
                max_tokens=50,
            )
            response = response.strip().strip('"').strip("'")

            # Match response to a sub-domain
            for s in subdomains:
                if s.name.lower() == response.lower():
                    logger.info(f"AI classified question as sub-domain: {s.name}")
                    return s.id

            logger.info(f"AI classification did not match any sub-domain: {response}")
            return None

        except Exception as e:
            logger.warning(f"AI classification failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Question routing
    # ------------------------------------------------------------------

    async def route_question_to_subdomain(
        self,
        db: AsyncSession,
        question: Question,
        subdomain_id: UUID,
    ) -> List[QuestionRouting]:
        """Broadcast a question to all experts assigned to the sub-domain."""
        experts = await self.get_experts_for_subdomain(db, subdomain_id)
        if not experts:
            logger.info(f"No experts assigned to subdomain {subdomain_id}")
            return []

        routings = []
        for expert in experts:
            routing = QuestionRouting(
                question_id=question.id,
                expert_id=expert.id,
            )
            db.add(routing)
            routings.append(routing)

            # Notify each expert
            try:
                await notification_service.create_notification(
                    db=db,
                    user_id=expert.id,
                    organization_id=question.organization_id,
                    notification_type=NotificationType.QUESTION_ROUTED,
                    title="New question in your sub-domain",
                    message=f'"{question.original_text[:100]}..."' if len(question.original_text) > 100
                    else f'"{question.original_text}"',
                    link_url=f"/expert/questions/{question.id}",
                    extra_data={"question_id": str(question.id)},
                )
            except Exception:
                pass  # Non-blocking

        await db.commit()
        logger.info(f"Routed question {question.id} to {len(experts)} experts in subdomain {subdomain_id}")
        return routings

    # ------------------------------------------------------------------
    # SLA breach detection
    # ------------------------------------------------------------------

    async def check_sla_breaches(self, db: AsyncSession) -> Dict[str, int]:
        """Find questions exceeding their sub-domain's SLA. Returns stats."""
        now = datetime.now(timezone.utc)

        # Get all active sub-domains with SLA
        result = await db.execute(
            select(SubDomain).where(SubDomain.is_active == True)
        )
        subdomains = list(result.scalars().all())

        stats = {"breached": 0, "notified": 0}

        for sd in subdomains:
            # Find unassigned questions in this sub-domain past SLA
            result = await db.execute(
                select(Question).where(
                    Question.subdomain_id == sd.id,
                    Question.assigned_to_id.is_(None),
                    Question.status.in_([
                        QuestionStatus.EXPERT_QUEUE,
                        QuestionStatus.HUMAN_REQUESTED,
                    ]),
                )
            )
            questions = list(result.scalars().all())

            for q in questions:
                hours_elapsed = (now - q.created_at).total_seconds() / 3600
                if hours_elapsed >= sd.sla_hours:
                    stats["breached"] += 1

                    # Notify all admins in the org
                    admin_result = await db.execute(
                        select(User.id).where(
                            User.organization_id == q.organization_id,
                            User.role == UserRole.ADMIN,
                            User.is_active == True,
                        )
                    )
                    admin_ids = [row[0] for row in admin_result.all()]

                    for admin_id in admin_ids:
                        try:
                            await notification_service.create_notification(
                                db=db,
                                user_id=admin_id,
                                organization_id=q.organization_id,
                                notification_type=NotificationType.SLA_BREACH,
                                title="SLA breach — question overdue",
                                message=f'Question in "{sd.name}" has been unassigned for {int(hours_elapsed)}h (SLA: {sd.sla_hours}h)',
                                link_url=f"/expert/questions/{q.id}",
                                extra_data={
                                    "question_id": str(q.id),
                                    "subdomain_name": sd.name,
                                    "hours_elapsed": round(hours_elapsed, 1),
                                    "sla_hours": sd.sla_hours,
                                },
                            )
                            stats["notified"] += 1
                        except Exception:
                            pass

        await db.commit()
        return stats


# Global singleton
subdomain_service = SubDomainService()

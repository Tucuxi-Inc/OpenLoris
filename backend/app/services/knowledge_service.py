"""
Knowledge Service — manages WisdomFacts, semantic search, gap analysis,
and knowledge compounding from answered questions.

Ported from CounselScope's wisdom_service.py and knowledge_evaluation_service.py,
adapted to Loris async patterns (AsyncSession passed in, UUIDs, Mapped models).
"""

import logging
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.answers import Answer
from app.models.documents import (
    DocumentChunk,
    ExtractedFactCandidate,
    KnowledgeDocument,
)
from app.models.questions import Question
from app.models.wisdom import WisdomEmbedding, WisdomFact, WisdomTier
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------

@dataclass
class GapAnalysisResult:
    """Structured result of running gap analysis on a question."""
    query: str
    matching_facts: List[Dict[str, Any]]
    coverage_percentage: float
    has_full_answer: bool
    recommendation: str  # "internal", "hybrid", "external"
    proposed_answer: Optional[str] = None
    answered_aspects: List[str] = field(default_factory=list)
    unanswered_aspects: List[str] = field(default_factory=list)
    confidence_score: float = 0.0


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class KnowledgeService:
    """
    Manages the Wisdom knowledge base — CRUD, semantic search,
    gap analysis (semantic search + LLM), and knowledge compounding.
    """

    # -- Cosine similarity helper (shared with automation_service) ----------

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # -- Semantic search ---------------------------------------------------

    async def search_relevant_facts(
        self,
        question_text: str,
        organization_id: UUID,
        db: AsyncSession,
        limit: int = 10,
        min_similarity: float = 0.35,
    ) -> List[Dict[str, Any]]:
        """
        Find WisdomFacts semantically similar to *question_text*.
        Returns list of dicts with fact data + similarity score.
        """
        # 1. Generate query embedding
        query_embedding = await embedding_service.generate(question_text)

        # 2. Fetch active facts with embeddings for this org
        stmt = (
            select(WisdomFact, WisdomEmbedding.embedding_data)
            .outerjoin(WisdomEmbedding, WisdomFact.id == WisdomEmbedding.wisdom_fact_id)
            .where(
                WisdomFact.organization_id == organization_id,
                WisdomFact.is_active == True,
                WisdomFact.tier != WisdomTier.ARCHIVED,
            )
        )
        result = await db.execute(stmt)
        rows = result.all()

        # 3. Compute similarity
        scored: List[Dict[str, Any]] = []
        for fact, emb_data in rows:
            sim = 0.0
            if emb_data:
                sim = self._cosine_similarity(query_embedding, emb_data)
            if sim >= min_similarity:
                scored.append({
                    "id": str(fact.id),
                    "content": fact.content,
                    "summary": fact.summary,
                    "domain": fact.domain,
                    "category": fact.category,
                    "tier": fact.tier.value if fact.tier else "pending",
                    "confidence_score": fact.confidence_score,
                    "importance": fact.importance,
                    "similarity": round(sim, 4),
                })

        # 4. Sort & limit
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:limit]

    # -- Gap analysis (semantic search + LLM) ------------------------------

    async def run_gap_analysis(
        self,
        question_text: str,
        organization_id: UUID,
        db: AsyncSession,
    ) -> Optional[Dict[str, Any]]:
        """
        Run gap analysis: find relevant facts → ask LLM to evaluate coverage
        and propose an answer.  Returns structured dict or None on failure.
        Non-blocking — exceptions are caught and logged.
        """
        try:
            # Semantic search
            facts = await self.search_relevant_facts(
                question_text, organization_id, db, limit=10
            )

            # Call AI provider
            from app.services.ai_provider_service import ai_provider

            analysis = await ai_provider.analyze_gaps(
                question=question_text,
                knowledge_facts=facts,
            )

            # Attach the matched facts for the UI
            analysis["matching_facts"] = facts
            return analysis

        except Exception as e:
            logger.error(f"Gap analysis failed: {e}")
            return None

    # -- CRUD: Create fact -------------------------------------------------

    async def create_fact(
        self,
        db: AsyncSession,
        organization_id: UUID,
        content: str,
        expert_user_id: UUID,
        *,
        summary: Optional[str] = None,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        tier: WisdomTier = WisdomTier.PENDING,
        confidence_score: Optional[float] = None,
        importance: int = 5,
        jurisdiction: Optional[str] = None,
        tags: Optional[list] = None,
        good_until_date: Optional[date] = None,
        is_perpetual: bool = False,
        source_document_id: Optional[UUID] = None,
    ) -> WisdomFact:
        """Create a WisdomFact and generate its embedding."""
        fact = WisdomFact(
            organization_id=organization_id,
            content=content,
            summary=summary or (content[:497] + "..." if len(content) > 500 else content),
            domain=domain,
            category=category,
            tier=tier,
            confidence_score=confidence_score,
            importance=importance,
            jurisdiction=jurisdiction,
            tags=tags,
            good_until_date=good_until_date,
            is_perpetual=is_perpetual,
            source_document_id=source_document_id,
            validated_by_id=expert_user_id,
            validated_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(fact)
        await db.flush()

        # Generate & store embedding
        try:
            emb_data = await embedding_service.generate(content)
            embedding = WisdomEmbedding(
                wisdom_fact_id=fact.id,
                embedding_data=emb_data,
                model_name=embedding_service.model_name,
            )
            db.add(embedding)
        except Exception as e:
            logger.warning(f"Could not generate embedding for fact {fact.id}: {e}")

        await db.commit()
        await db.refresh(fact)
        return fact

    # -- Create fact from an answered question -----------------------------

    async def create_fact_from_answer(
        self,
        db: AsyncSession,
        question_id: UUID,
        expert_user_id: UUID,
        *,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        tier: WisdomTier = WisdomTier.TIER_0B,
        importance: int = 7,
        tags: Optional[list] = None,
    ) -> Optional[WisdomFact]:
        """
        Extract knowledge from an answered question and persist as a WisdomFact.
        Returns None if question or answer not found.
        """
        q_result = await db.execute(
            select(Question).where(Question.id == question_id)
        )
        question = q_result.scalar_one_or_none()
        if not question:
            return None

        a_result = await db.execute(
            select(Answer).where(Answer.question_id == question_id)
        )
        answer = a_result.scalar_one_or_none()
        if not answer:
            return None

        content = (
            f"Q: {question.original_text}\n\n"
            f"A: {answer.content}"
        )

        return await self.create_fact(
            db=db,
            organization_id=question.organization_id,
            content=content,
            expert_user_id=expert_user_id,
            domain=domain or question.category,
            category=category,
            tier=tier,
            importance=importance,
            tags=tags,
            source_document_id=None,
        )

    # -- Update fact -------------------------------------------------------

    async def update_fact(
        self,
        db: AsyncSession,
        fact_id: UUID,
        updates: Dict[str, Any],
    ) -> Optional[WisdomFact]:
        """
        Update a WisdomFact.  If content changes, regenerate embedding.
        """
        result = await db.execute(
            select(WisdomFact).where(WisdomFact.id == fact_id)
        )
        fact = result.scalar_one_or_none()
        if not fact:
            return None

        content_changed = False
        for key, val in updates.items():
            if key == "content" and val != fact.content:
                content_changed = True
            if hasattr(fact, key):
                setattr(fact, key, val)

        if content_changed:
            try:
                emb_data = await embedding_service.generate(fact.content)
                emb_result = await db.execute(
                    select(WisdomEmbedding).where(
                        WisdomEmbedding.wisdom_fact_id == fact_id
                    )
                )
                existing_emb = emb_result.scalar_one_or_none()
                if existing_emb:
                    existing_emb.embedding_data = emb_data
                    existing_emb.model_name = embedding_service.model_name
                else:
                    db.add(WisdomEmbedding(
                        wisdom_fact_id=fact_id,
                        embedding_data=emb_data,
                        model_name=embedding_service.model_name,
                    ))
            except Exception as e:
                logger.warning(f"Could not regenerate embedding for fact {fact_id}: {e}")

        await db.commit()
        await db.refresh(fact)
        return fact

    # -- Archive (soft delete) ---------------------------------------------

    async def archive_fact(
        self,
        db: AsyncSession,
        fact_id: UUID,
    ) -> bool:
        result = await db.execute(
            select(WisdomFact).where(WisdomFact.id == fact_id)
        )
        fact = result.scalar_one_or_none()
        if not fact:
            return False

        fact.tier = WisdomTier.ARCHIVED
        fact.is_active = False
        await db.commit()
        return True

    # -- Get single fact ---------------------------------------------------

    async def get_fact(
        self,
        db: AsyncSession,
        fact_id: UUID,
    ) -> Optional[WisdomFact]:
        result = await db.execute(
            select(WisdomFact).where(WisdomFact.id == fact_id)
        )
        return result.scalar_one_or_none()

    # -- List facts with filters + pagination ------------------------------

    async def list_facts(
        self,
        db: AsyncSession,
        organization_id: UUID,
        *,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        tier: Optional[str] = None,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        stmt = select(WisdomFact).where(
            WisdomFact.organization_id == organization_id
        )

        if active_only:
            stmt = stmt.where(WisdomFact.is_active == True)

        if domain:
            stmt = stmt.where(WisdomFact.domain == domain)
        if category:
            stmt = stmt.where(WisdomFact.category == category)
        if tier:
            stmt = stmt.where(WisdomFact.tier == WisdomTier(tier))

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Page
        offset = (page - 1) * page_size
        stmt = stmt.order_by(desc(WisdomFact.created_at)).offset(offset).limit(page_size)
        rows = (await db.execute(stmt)).scalars().all()

        return {
            "facts": [self._fact_to_dict(f) for f in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }

    # -- Expiring facts ----------------------------------------------------

    async def get_expiring_facts(
        self,
        db: AsyncSession,
        organization_id: UUID,
        days_ahead: int = 30,
    ) -> List[Dict[str, Any]]:
        threshold = date.today() + timedelta(days=days_ahead)
        stmt = (
            select(WisdomFact)
            .where(
                WisdomFact.organization_id == organization_id,
                WisdomFact.is_active == True,
                WisdomFact.is_perpetual == False,
                WisdomFact.good_until_date.isnot(None),
                WisdomFact.good_until_date <= threshold,
            )
            .order_by(WisdomFact.good_until_date)
            .limit(50)
        )
        rows = (await db.execute(stmt)).scalars().all()
        return [self._fact_to_dict(f) for f in rows]

    # -- Track usage -------------------------------------------------------

    async def track_usage(
        self,
        db: AsyncSession,
        fact_id: UUID,
    ) -> None:
        await db.execute(
            update(WisdomFact)
            .where(WisdomFact.id == fact_id)
            .values(
                usage_count=WisdomFact.usage_count + 1,
                last_used_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    # -- Statistics --------------------------------------------------------

    async def get_stats(
        self,
        db: AsyncSession,
        organization_id: UUID,
    ) -> Dict[str, Any]:
        base = select(func.count(WisdomFact.id)).where(
            WisdomFact.organization_id == organization_id,
            WisdomFact.is_active == True,
        )
        total = (await db.execute(base)).scalar() or 0

        tier_counts = {}
        for t in WisdomTier:
            cnt = (await db.execute(
                base.where(WisdomFact.tier == t)
            )).scalar() or 0
            tier_counts[t.value] = cnt

        domains_result = await db.execute(
            select(WisdomFact.domain)
            .where(
                WisdomFact.organization_id == organization_id,
                WisdomFact.is_active == True,
            )
            .distinct()
        )
        domains = [d for d in domains_result.scalars().all() if d]

        threshold = date.today() + timedelta(days=30)
        expiring = (await db.execute(
            select(func.count(WisdomFact.id)).where(
                WisdomFact.organization_id == organization_id,
                WisdomFact.is_active == True,
                WisdomFact.is_perpetual == False,
                WisdomFact.good_until_date.isnot(None),
                WisdomFact.good_until_date <= threshold,
            )
        )).scalar() or 0

        avg_conf = (await db.execute(
            select(func.avg(WisdomFact.confidence_score)).where(
                WisdomFact.organization_id == organization_id,
                WisdomFact.is_active == True,
            )
        )).scalar() or 0.0

        return {
            "total_facts": total,
            "tier_counts": tier_counts,
            "domains_covered": domains,
            "facts_expiring_soon": expiring,
            "average_confidence": round(float(avg_conf), 2),
        }

    # -- Semantic search endpoint ------------------------------------------

    async def search(
        self,
        db: AsyncSession,
        organization_id: UUID,
        query: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Public semantic search exposed via API."""
        return await self.search_relevant_facts(
            question_text=query,
            organization_id=organization_id,
            db=db,
            limit=limit,
            min_similarity=0.25,
        )

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _fact_to_dict(fact: WisdomFact) -> Dict[str, Any]:
        return {
            "id": str(fact.id),
            "content": fact.content,
            "summary": fact.summary,
            "domain": fact.domain,
            "category": fact.category,
            "tier": fact.tier.value if fact.tier else "pending",
            "confidence_score": fact.confidence_score,
            "importance": fact.importance,
            "jurisdiction": fact.jurisdiction,
            "tags": fact.tags or [],
            "good_until_date": fact.good_until_date.isoformat() if fact.good_until_date else None,
            "is_perpetual": fact.is_perpetual,
            "is_active": fact.is_active,
            "usage_count": fact.usage_count,
            "created_at": fact.created_at.isoformat() if fact.created_at else None,
            "validated_at": fact.validated_at.isoformat() if fact.validated_at else None,
        }


# Global singleton
knowledge_service = KnowledgeService()

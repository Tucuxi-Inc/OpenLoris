"""
Turbo Loris Service — user-controlled fast-answer mode that delivers AI-generated
responses when knowledge confidence exceeds a user-selected threshold.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.questions import Question, QuestionStatus
from app.models.answers import Answer, AnswerSource
from app.models.turbo import TurboAttribution
from app.models.wisdom import WisdomFact, WisdomTier
from app.models.user import User
from app.services.knowledge_service import knowledge_service
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


# Tier score mapping for confidence calculation
TIER_SCORES: Dict[str, float] = {
    "tier_0a": 1.0,   # Authoritative
    "tier_0b": 0.9,   # Expert-validated
    "tier_0c": 0.7,   # AI-generated
    "pending": 0.4,   # Not yet validated
    "archived": 0.0,  # Not usable
}


@dataclass
class TurboResult:
    """Result of a Turbo answer attempt."""
    success: bool
    confidence: float
    threshold: float
    answer_content: Optional[str] = None
    sources: List[Dict[str, Any]] = field(default_factory=list)
    message: Optional[str] = None


class TurboService:
    """
    Handles Turbo Loris mode — user-controlled fast-answer mode that delivers
    AI-generated responses when knowledge confidence exceeds a user-selected threshold.
    """

    def calculate_confidence(self, matched_facts: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence score using weighted formula:
        - Similarity: 40% (best semantic match)
        - Tier: 30% (quality of best source)
        - Coverage: 30% (how many sources support the answer)
        """
        if not matched_facts:
            return 0.0

        # Best semantic similarity
        best_similarity = max(f.get("similarity", 0) for f in matched_facts)

        # Best tier score
        best_tier_score = max(
            TIER_SCORES.get(f.get("tier", "pending"), 0.5)
            for f in matched_facts
        )

        # Coverage: how many facts are reasonably relevant (similarity > 0.6)
        relevant_count = len([f for f in matched_facts if f.get("similarity", 0) > 0.6])
        coverage = min(relevant_count / 3, 1.0)  # Cap at 3+ relevant facts = 100%

        # Weighted combination
        confidence = (best_similarity * 0.4) + (best_tier_score * 0.3) + (coverage * 0.3)

        return round(confidence, 4)

    async def attempt_turbo_answer(
        self,
        question: Question,
        threshold: float,
        db: AsyncSession,
    ) -> TurboResult:
        """
        Attempt to generate a Turbo answer for the given question.
        Returns a TurboResult indicating success/failure and answer details.
        """
        try:
            # Search knowledge base for relevant facts
            facts = await knowledge_service.search_relevant_facts(
                question_text=question.original_text,
                organization_id=question.organization_id,
                db=db,
                limit=10,
                min_similarity=0.35,
            )

            if not facts:
                return TurboResult(
                    success=False,
                    confidence=0.0,
                    threshold=threshold,
                    message="No relevant knowledge found",
                )

            # Calculate confidence
            confidence = self.calculate_confidence(facts)

            if confidence < threshold:
                return TurboResult(
                    success=False,
                    confidence=confidence,
                    threshold=threshold,
                    sources=facts,
                    message=f"Confidence {confidence:.0%} below threshold {threshold:.0%}",
                )

            # Generate answer using AI
            from app.services.ai_provider_service import ai_provider_service

            answer_content = await ai_provider_service.generate_turbo_answer(
                question=question.original_text,
                knowledge_facts=facts,
            )

            if not answer_content:
                return TurboResult(
                    success=False,
                    confidence=confidence,
                    threshold=threshold,
                    sources=facts,
                    message="Failed to generate answer",
                )

            return TurboResult(
                success=True,
                confidence=confidence,
                threshold=threshold,
                answer_content=answer_content,
                sources=facts,
            )

        except Exception as e:
            logger.error(f"Turbo answer attempt failed: {e}")
            return TurboResult(
                success=False,
                confidence=0.0,
                threshold=threshold,
                message=f"Error: {str(e)}",
            )

    async def deliver_turbo_answer(
        self,
        db: AsyncSession,
        question: Question,
        turbo_result: TurboResult,
    ) -> Answer:
        """
        Deliver a Turbo answer: create Answer record, update Question status,
        and create TurboAttribution records for each source.
        """
        # Create the answer
        answer = Answer(
            question_id=question.id,
            created_by_id=question.asked_by_id,  # User gets credit for initiating
            content=turbo_result.answer_content,
            source=AnswerSource.AUTOMATION,  # Turbo uses automation source type
            delivered_at=datetime.now(timezone.utc),
        )
        db.add(answer)

        # Update question
        question.status = QuestionStatus.TURBO_ANSWERED
        question.turbo_confidence = turbo_result.confidence
        question.first_response_at = datetime.now(timezone.utc)

        # Store sources in gap_analysis for reference
        question.gap_analysis = {
            "turbo_answer": True,
            "turbo_confidence": turbo_result.confidence,
            "turbo_threshold": turbo_result.threshold,
            "proposed_answer": turbo_result.answer_content,
            "matching_facts": turbo_result.sources,
        }

        # Create attributions
        await self.create_attributions(
            db=db,
            question_id=question.id,
            sources=turbo_result.sources,
        )

        await db.commit()
        await db.refresh(answer)
        return answer

    async def create_attributions(
        self,
        db: AsyncSession,
        question_id: UUID,
        sources: List[Dict[str, Any]],
    ) -> List[TurboAttribution]:
        """
        Create TurboAttribution records for each knowledge source.
        """
        attributions = []

        for source in sources:
            source_id = source.get("id")
            if not source_id:
                continue

            try:
                source_uuid = UUID(source_id)
            except (ValueError, TypeError):
                continue

            # Look up the fact to get the author
            fact_result = await db.execute(
                select(WisdomFact).where(WisdomFact.id == source_uuid)
            )
            fact = fact_result.scalar_one_or_none()

            attributed_user_id = None
            contribution_type = "authored"
            if fact:
                attributed_user_id = fact.validated_by_id
                if fact.source_document_id:
                    contribution_type = "extracted"

            attribution = TurboAttribution(
                question_id=question_id,
                source_type="fact",
                source_id=source_uuid,
                attributed_user_id=attributed_user_id,
                display_name=source.get("summary") or source.get("content", "")[:100],
                contribution_type=contribution_type,
                confidence_score=source.get("confidence_score") or 0.0,
                semantic_similarity=source.get("similarity") or 0.0,
            )
            db.add(attribution)
            attributions.append(attribution)

        return attributions

    async def get_attributions(
        self,
        db: AsyncSession,
        question_id: UUID,
    ) -> List[Dict[str, Any]]:
        """
        Get all attributions for a question with contributor info.
        """
        result = await db.execute(
            select(TurboAttribution, User.name)
            .outerjoin(User, TurboAttribution.attributed_user_id == User.id)
            .where(TurboAttribution.question_id == question_id)
            .order_by(TurboAttribution.semantic_similarity.desc())
        )
        rows = result.all()

        attributions = []
        for attr, user_name in rows:
            attributions.append({
                "id": str(attr.id),
                "source_type": attr.source_type,
                "source_id": str(attr.source_id),
                "display_name": attr.display_name,
                "contributor_name": user_name or "AI Generated",
                "contribution_type": attr.contribution_type,
                "confidence_score": attr.confidence_score,
                "semantic_similarity": attr.semantic_similarity,
            })

        return attributions

    async def handle_turbo_acceptance(
        self,
        db: AsyncSession,
        question: Question,
    ) -> None:
        """
        Handle user accepting a Turbo answer — mark as resolved.
        """
        question.status = QuestionStatus.RESOLVED
        question.resolved_at = datetime.now(timezone.utc)
        await db.commit()

    async def handle_turbo_rejection(
        self,
        db: AsyncSession,
        question: Question,
        rejection_reason: str,
    ) -> None:
        """
        Handle user rejecting a Turbo answer — route to expert queue.
        """
        question.status = QuestionStatus.HUMAN_REQUESTED
        question.rejection_reason = rejection_reason

        # Keep the turbo data for expert context
        if question.gap_analysis:
            question.gap_analysis["turbo_rejected"] = True
            question.gap_analysis["rejection_reason"] = rejection_reason

        await db.commit()


# Global singleton
turbo_service = TurboService()

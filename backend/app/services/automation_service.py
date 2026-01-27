"""
Automation Service - matches incoming questions to automation rules
using pgvector cosine similarity for semantic search.

Core flow:
1. Question arrives → generate embedding
2. Search automation_rule_embeddings for cosine similarity
3. If match >= threshold (default 0.85): auto-answer
4. If match >= suggest_threshold (0.70): suggest to expert
5. Otherwise: queue for expert review
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation import AutomationRule, AutomationRuleEmbedding, AutomationLog, AutomationLogAction
from app.models.answers import Answer, AnswerSource
from app.models.questions import Question, QuestionStatus
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

# Thresholds
AUTO_ANSWER_THRESHOLD = 0.85
SUGGEST_THRESHOLD = 0.70


@dataclass
class AutomationMatch:
    """Result of matching a question against automation rules."""
    rule_id: UUID
    rule_name: str
    similarity: float
    canonical_answer: str
    canonical_question: str
    threshold: float


@dataclass
class AutomationCheckResult:
    """Result of checking a question for automation."""
    matched: bool
    match: Optional[AutomationMatch] = None
    action: str = "queue_for_expert"  # auto_answer, suggest_to_expert, queue_for_expert


class AutomationService:
    """Service for matching questions to automation rules and managing rules."""

    async def check_for_automation(
        self,
        db: AsyncSession,
        question_text: str,
        organization_id: UUID,
        category: Optional[str] = None,
    ) -> AutomationCheckResult:
        """
        Check if an incoming question matches any automation rules.

        Uses cosine similarity via pgvector on stored embeddings.
        Returns the best match if above threshold.
        """
        # Generate embedding for the question
        question_embedding = await embedding_service.generate(question_text)

        # Find matching rules using cosine similarity
        matches = await self._find_matching_rules(
            db=db,
            embedding=question_embedding,
            organization_id=organization_id,
            category=category,
            question_text=question_text,
        )

        if not matches:
            return AutomationCheckResult(matched=False, action="queue_for_expert")

        best_match = matches[0]

        if best_match.similarity >= best_match.threshold:
            return AutomationCheckResult(
                matched=True,
                match=best_match,
                action="auto_answer"
            )
        elif best_match.similarity >= SUGGEST_THRESHOLD:
            return AutomationCheckResult(
                matched=True,
                match=best_match,
                action="suggest_to_expert"
            )

        return AutomationCheckResult(matched=False, action="queue_for_expert")

    async def _find_matching_rules(
        self,
        db: AsyncSession,
        embedding: List[float],
        organization_id: UUID,
        category: Optional[str],
        question_text: str,
        limit: int = 5,
    ) -> List[AutomationMatch]:
        """
        Find automation rules matching the question using cosine similarity.

        Computes similarity between the question embedding and all rule
        embeddings in the organization, filtering by enabled status,
        GUD date, and optional category.
        """
        # Use JSONB-based similarity since we store embeddings as JSONB arrays
        # For production, switch to native pgvector column for better performance
        query = (
            select(
                AutomationRule.id,
                AutomationRule.name,
                AutomationRule.canonical_question,
                AutomationRule.canonical_answer,
                AutomationRule.similarity_threshold,
                AutomationRule.exclude_keywords,
                AutomationRuleEmbedding.embedding_data,
            )
            .join(AutomationRuleEmbedding, AutomationRule.id == AutomationRuleEmbedding.rule_id)
            .where(
                AutomationRule.organization_id == organization_id,
                AutomationRule.is_enabled == True,
            )
        )

        # Filter out expired rules
        query = query.where(
            (AutomationRule.good_until_date == None) |
            (AutomationRule.good_until_date > date.today())
        )

        # Optional category filter
        if category:
            query = query.where(
                (AutomationRule.category_filter == None) |
                (AutomationRule.category_filter == category)
            )

        result = await db.execute(query)
        rows = result.all()

        matches = []
        for row in rows:
            rule_id, name, canonical_q, canonical_a, threshold, exclude_kw, emb_data = row

            # Check exclude keywords
            if exclude_kw:
                text_lower = question_text.lower()
                if any(kw.lower() in text_lower for kw in exclude_kw):
                    continue

            # Compute cosine similarity
            similarity = self._cosine_similarity(embedding, emb_data)

            if similarity >= SUGGEST_THRESHOLD:
                matches.append(AutomationMatch(
                    rule_id=rule_id,
                    rule_name=name,
                    similarity=similarity,
                    canonical_answer=canonical_a,
                    canonical_question=canonical_q,
                    threshold=threshold,
                ))

        # Sort by similarity descending
        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:limit]

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    async def deliver_auto_answer(
        self,
        db: AsyncSession,
        question: Question,
        match: AutomationMatch,
    ) -> Answer:
        """
        Deliver an automated answer to a question using the matched rule.
        Creates the answer, updates question status, and logs the event.
        """
        now = datetime.now(timezone.utc)

        # Create answer
        answer = Answer(
            question_id=question.id,
            created_by_id=question.asked_by_id,  # System-generated, attributed to asker
            content=match.canonical_answer,
            source=AnswerSource.AUTOMATION,
            delivered_at=now,
        )
        db.add(answer)

        # Update question
        question.status = QuestionStatus.AUTO_ANSWERED
        question.automation_rule_id = match.rule_id
        question.first_response_at = now
        if question.created_at:
            question.response_time_seconds = int(
                (now - question.created_at).total_seconds()
            )

        # Log the automation event
        log = AutomationLog(
            rule_id=match.rule_id,
            question_id=question.id,
            action=AutomationLogAction.DELIVERED,
            similarity_score=match.similarity,
        )
        db.add(log)

        # Increment trigger count
        await db.execute(
            update(AutomationRule)
            .where(AutomationRule.id == match.rule_id)
            .values(times_triggered=AutomationRule.times_triggered + 1)
        )

        await db.commit()
        await db.refresh(answer)

        logger.info(
            f"Auto-answered question {question.id} with rule {match.rule_name} "
            f"(similarity={match.similarity:.3f})"
        )

        return answer

    async def handle_user_feedback(
        self,
        db: AsyncSession,
        question: Question,
        accepted: bool,
        rejection_reason: Optional[str] = None,
    ) -> None:
        """
        Process user feedback on an auto-answer.
        If accepted: mark resolved. If rejected: escalate to expert queue.
        """
        now = datetime.now(timezone.utc)

        if accepted:
            question.status = QuestionStatus.RESOLVED
            question.auto_answer_accepted = True
            question.resolved_at = now
            if question.created_at:
                question.resolution_time_seconds = int(
                    (now - question.created_at).total_seconds()
                )

            # Log acceptance
            log = AutomationLog(
                rule_id=question.automation_rule_id,
                question_id=question.id,
                action=AutomationLogAction.ACCEPTED,
            )
            db.add(log)

            # Increment accept count
            await db.execute(
                update(AutomationRule)
                .where(AutomationRule.id == question.automation_rule_id)
                .values(times_accepted=AutomationRule.times_accepted + 1)
            )
        else:
            question.status = QuestionStatus.HUMAN_REQUESTED
            question.auto_answer_accepted = False
            question.rejection_reason = rejection_reason

            # Log rejection
            log = AutomationLog(
                rule_id=question.automation_rule_id,
                question_id=question.id,
                action=AutomationLogAction.REJECTED,
                user_feedback=rejection_reason,
            )
            db.add(log)

            # Increment reject count
            await db.execute(
                update(AutomationRule)
                .where(AutomationRule.id == question.automation_rule_id)
                .values(times_rejected=AutomationRule.times_rejected + 1)
            )

        await db.commit()

        action = "accepted" if accepted else "rejected"
        logger.info(f"User {action} auto-answer for question {question.id}")

    async def create_rule_from_answer(
        self,
        db: AsyncSession,
        question: Question,
        answer: Answer,
        name: str,
        description: Optional[str] = None,
        similarity_threshold: float = 0.85,
        category_filter: Optional[str] = None,
        exclude_keywords: Optional[List[str]] = None,
        good_until_date: Optional[date] = None,
    ) -> AutomationRule:
        """
        Create a new automation rule from an expert's Q&A pair.
        Generates embedding for the canonical question.
        """
        rule = AutomationRule(
            organization_id=question.organization_id,
            created_by_id=answer.created_by_id,
            name=name,
            description=description,
            source_question_id=question.id,
            canonical_question=question.original_text,
            canonical_answer=answer.content,
            similarity_threshold=similarity_threshold,
            category_filter=category_filter or question.category,
            exclude_keywords=exclude_keywords or [],
            good_until_date=good_until_date,
            is_enabled=True,
        )
        db.add(rule)
        await db.flush()  # Get the rule ID

        # Generate embedding for the canonical question
        embedding_data = await embedding_service.generate(question.original_text)

        rule_embedding = AutomationRuleEmbedding(
            rule_id=rule.id,
            embedding_data=embedding_data,
            model_name=embedding_service.model_name,
        )
        db.add(rule_embedding)

        await db.commit()
        await db.refresh(rule)

        logger.info(f"Created automation rule '{name}' from question {question.id}")

        return rule


# Global instance
automation_service = AutomationService()

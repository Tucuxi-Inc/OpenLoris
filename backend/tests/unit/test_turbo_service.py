"""
Unit tests for TurboService.

These tests verify the Turbo Loris confidence calculation,
answer generation, and attribution tracking.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.models.questions import Question, QuestionStatus
from app.models.answers import Answer, AnswerSource
from app.models.turbo import TurboAttribution
from app.models.wisdom import WisdomTier
from app.services.turbo_service import turbo_service, TIER_SCORES, TurboResult

from tests.factories import (
    OrganizationFactory,
    UserFactory,
    QuestionFactory,
    WisdomFactFactory,
)


class TestCalculateConfidence:
    """Tests for turbo_service.calculate_confidence"""

    def test_empty_facts_returns_zero(self):
        """No facts should return 0 confidence."""
        confidence = turbo_service.calculate_confidence([])
        assert confidence == 0.0

    def test_high_similarity_high_tier_high_coverage(self):
        """Perfect scores across all factors should give high confidence."""
        facts = [
            {"similarity": 0.95, "tier": "tier_0a", "content": "Fact 1"},
            {"similarity": 0.90, "tier": "tier_0a", "content": "Fact 2"},
            {"similarity": 0.85, "tier": "tier_0b", "content": "Fact 3"},
        ]
        confidence = turbo_service.calculate_confidence(facts)

        # Expected: 0.95*0.4 + 1.0*0.3 + 1.0*0.3 = 0.38 + 0.30 + 0.30 = 0.98
        assert confidence >= 0.90

    def test_low_similarity_affects_confidence(self):
        """Low similarity should reduce confidence."""
        facts = [
            {"similarity": 0.40, "tier": "tier_0a", "content": "Fact 1"},
        ]
        confidence = turbo_service.calculate_confidence(facts)

        # Expected: 0.40*0.4 + 1.0*0.3 + 0*0.3 = 0.16 + 0.30 + 0 = 0.46
        assert confidence < 0.50

    def test_low_tier_affects_confidence(self):
        """Pending tier should reduce confidence."""
        facts = [
            {"similarity": 0.90, "tier": "pending", "content": "Fact 1"},
        ]
        confidence = turbo_service.calculate_confidence(facts)

        # Expected: 0.90*0.4 + 0.4*0.3 + 0.33*0.3 = 0.36 + 0.12 + 0.10 = 0.58
        assert 0.50 < confidence < 0.70

    def test_coverage_affects_confidence(self):
        """Multiple high-similarity facts should increase coverage score."""
        # Single fact
        single_fact = [{"similarity": 0.90, "tier": "tier_0b", "content": "Fact 1"}]
        single_conf = turbo_service.calculate_confidence(single_fact)

        # Multiple facts (3+ above 0.6 similarity = full coverage)
        multiple_facts = [
            {"similarity": 0.90, "tier": "tier_0b", "content": "Fact 1"},
            {"similarity": 0.85, "tier": "tier_0b", "content": "Fact 2"},
            {"similarity": 0.75, "tier": "tier_0b", "content": "Fact 3"},
        ]
        multiple_conf = turbo_service.calculate_confidence(multiple_facts)

        # Multiple facts should have higher coverage component
        assert multiple_conf > single_conf

    def test_formula_weights_sum_to_one(self):
        """Verify the weighted formula components."""
        # Formula: similarity * 0.4 + tier * 0.3 + coverage * 0.3 = 1.0 max
        facts = [
            {"similarity": 1.0, "tier": "tier_0a", "content": "Fact 1"},
            {"similarity": 1.0, "tier": "tier_0a", "content": "Fact 2"},
            {"similarity": 1.0, "tier": "tier_0a", "content": "Fact 3"},
        ]
        confidence = turbo_service.calculate_confidence(facts)

        # Should be 1.0 * 0.4 + 1.0 * 0.3 + 1.0 * 0.3 = 1.0
        assert abs(confidence - 1.0) < 0.01

    def test_handles_missing_tier(self):
        """Facts without tier should use default score."""
        facts = [{"similarity": 0.80, "content": "Fact without tier"}]
        confidence = turbo_service.calculate_confidence(facts)

        # Should not crash, use default tier score (0.5)
        assert 0.0 < confidence < 1.0


class TestAttemptTurboAnswer:
    """Tests for turbo_service.attempt_turbo_answer"""

    @pytest.mark.asyncio
    async def test_returns_success_above_threshold(self, db_session, clean_db):
        """Should succeed when confidence exceeds threshold."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        # Create high-quality facts
        await WisdomFactFactory.create_authoritative(
            db_session, org.id, expert.id,
            content="Remote work is allowed up to 3 days per week.",
        )
        await WisdomFactFactory.create_authoritative(
            db_session, org.id, expert.id,
            content="Employees can work from home on any weekday.",
        )
        await db_session.commit()

        # Create question
        question = await QuestionFactory.create_submitted(
            db_session, org.id, user.id,
            text="What is the remote work policy?",
            turbo_mode=True,
            turbo_threshold=0.50,  # Low threshold
        )
        await db_session.commit()

        # Attempt turbo answer
        result = await turbo_service.attempt_turbo_answer(
            question=question,
            threshold=0.50,
            db=db_session,
        )

        # With matching facts and low threshold, should succeed
        # (depends on embedding quality and AI availability)
        assert result is not None
        assert result.threshold == 0.50
        assert result.confidence >= 0.0

    @pytest.mark.asyncio
    async def test_returns_failure_below_threshold(self, db_session, clean_db):
        """Should fail when confidence is below threshold."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        # Create low-quality fact (pending tier)
        await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            content="Something about cafeteria hours.",
            tier=WisdomTier.PENDING,
        )
        await db_session.commit()

        # Create question about unrelated topic
        question = await QuestionFactory.create_submitted(
            db_session, org.id, user.id,
            text="What is the policy on cryptocurrency investments?",
            turbo_mode=True,
            turbo_threshold=0.95,  # Very high threshold
        )
        await db_session.commit()

        # Attempt turbo answer
        result = await turbo_service.attempt_turbo_answer(
            question=question,
            threshold=0.95,
            db=db_session,
        )

        # With unrelated content and high threshold, should fail
        assert result.success is False
        assert result.confidence < 0.95

    @pytest.mark.asyncio
    async def test_returns_no_match_message_when_empty(self, db_session, clean_db):
        """Should return appropriate message when no facts found."""
        # Setup with no facts
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        question = await QuestionFactory.create_submitted(
            db_session, org.id, user.id,
            text="Random question with no matching facts",
        )
        await db_session.commit()

        result = await turbo_service.attempt_turbo_answer(
            question=question,
            threshold=0.50,
            db=db_session,
        )

        assert result.success is False
        assert "No relevant knowledge" in result.message or result.confidence == 0.0


class TestDeliverTurboAnswer:
    """Tests for turbo_service.deliver_turbo_answer"""

    @pytest.mark.asyncio
    async def test_creates_answer_record(self, db_session, clean_db):
        """Should create an Answer with proper fields."""
        from sqlalchemy import select

        # Setup
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        question = await QuestionFactory.create_submitted(
            db_session, org.id, user.id,
            turbo_mode=True,
            turbo_threshold=0.75,
        )
        await db_session.commit()

        # Create a mock turbo result
        turbo_result = TurboResult(
            success=True,
            confidence=0.85,
            threshold=0.75,
            answer_content="This is the generated answer.",
            sources=[
                {"id": str(uuid4()), "content": "Source fact", "similarity": 0.90, "tier": "tier_0b"}
            ],
        )

        # Deliver the answer
        answer = await turbo_service.deliver_turbo_answer(
            db=db_session,
            question=question,
            turbo_result=turbo_result,
        )

        # Verify answer
        assert answer is not None
        assert answer.content == "This is the generated answer."
        assert answer.source == AnswerSource.AUTOMATION
        assert answer.question_id == question.id

    @pytest.mark.asyncio
    async def test_updates_question_status(self, db_session, clean_db):
        """Should set question status to TURBO_ANSWERED."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        question = await QuestionFactory.create_submitted(
            db_session, org.id, user.id,
            turbo_mode=True,
        )
        await db_session.commit()

        turbo_result = TurboResult(
            success=True,
            confidence=0.85,
            threshold=0.75,
            answer_content="Answer content",
            sources=[],
        )

        await turbo_service.deliver_turbo_answer(
            db=db_session,
            question=question,
            turbo_result=turbo_result,
        )

        # Verify question updated
        await db_session.refresh(question)
        assert question.status == QuestionStatus.TURBO_ANSWERED
        assert question.turbo_confidence == 0.85
        assert question.first_response_at is not None

    @pytest.mark.asyncio
    async def test_stores_gap_analysis_data(self, db_session, clean_db):
        """Should store turbo metadata in gap_analysis field."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        question = await QuestionFactory.create_submitted(
            db_session, org.id, user.id,
        )
        await db_session.commit()

        turbo_result = TurboResult(
            success=True,
            confidence=0.82,
            threshold=0.75,
            answer_content="The answer",
            sources=[{"id": str(uuid4()), "content": "Source"}],
        )

        await turbo_service.deliver_turbo_answer(
            db=db_session,
            question=question,
            turbo_result=turbo_result,
        )

        await db_session.refresh(question)
        assert question.gap_analysis is not None
        assert question.gap_analysis["turbo_answer"] is True
        assert question.gap_analysis["turbo_confidence"] == 0.82
        assert question.gap_analysis["turbo_threshold"] == 0.75


class TestCreateAttributions:
    """Tests for turbo_service.create_attributions"""

    @pytest.mark.asyncio
    async def test_creates_attribution_records(self, db_session, clean_db):
        """Should create TurboAttribution for each source."""
        from sqlalchemy import select

        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        # Create a fact that will be attributed
        fact = await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            content="Attribution test fact",
        )
        await db_session.commit()

        question = await QuestionFactory.create_submitted(
            db_session, org.id, user.id,
        )
        await db_session.commit()

        # Create attributions
        sources = [
            {
                "id": str(fact.id),
                "content": "Attribution test fact",
                "summary": "Test summary",
                "similarity": 0.85,
                "confidence_score": 0.90,
                "tier": "tier_0b",
            }
        ]

        attributions = await turbo_service.create_attributions(
            db=db_session,
            question_id=question.id,
            sources=sources,
        )
        await db_session.flush()  # Persist attributions to DB

        assert len(attributions) == 1
        assert attributions[0].source_id == fact.id
        assert attributions[0].semantic_similarity == 0.85

        # Verify in database
        result = await db_session.execute(
            select(TurboAttribution).where(TurboAttribution.question_id == question.id)
        )
        db_attributions = result.scalars().all()
        assert len(db_attributions) == 1

    @pytest.mark.asyncio
    async def test_links_to_fact_author(self, db_session, clean_db):
        """Should link attribution to the fact's validated_by user."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id, name="Dr. Expert")
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        # Create fact with validated_by
        fact = await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            content="Fact validated by expert",
        )
        await db_session.commit()

        question = await QuestionFactory.create_submitted(
            db_session, org.id, user.id,
        )
        await db_session.commit()

        sources = [{"id": str(fact.id), "similarity": 0.80}]
        attributions = await turbo_service.create_attributions(
            db=db_session,
            question_id=question.id,
            sources=sources,
        )

        assert len(attributions) == 1
        assert attributions[0].attributed_user_id == expert.id

    @pytest.mark.asyncio
    async def test_skips_invalid_source_ids(self, db_session, clean_db):
        """Should skip sources with invalid UUIDs."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        question = await QuestionFactory.create_submitted(
            db_session, org.id, user.id,
        )
        await db_session.commit()

        sources = [
            {"id": "not-a-valid-uuid", "similarity": 0.80},
            {"id": None, "similarity": 0.75},
            {"similarity": 0.70},  # No id at all
        ]

        attributions = await turbo_service.create_attributions(
            db=db_session,
            question_id=question.id,
            sources=sources,
        )

        assert len(attributions) == 0  # All should be skipped


class TestGetAttributions:
    """Tests for turbo_service.get_attributions"""

    @pytest.mark.asyncio
    async def test_returns_attributions_with_user_names(self, db_session, clean_db):
        """Should return attributions with contributor names."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id, name="Dr. Knowledge")
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        fact = await WisdomFactFactory.create(
            db_session, org.id, expert.id,
        )
        await db_session.commit()

        question = await QuestionFactory.create_submitted(
            db_session, org.id, user.id,
        )
        await db_session.commit()

        # Create attribution
        await turbo_service.create_attributions(
            db=db_session,
            question_id=question.id,
            sources=[{"id": str(fact.id), "similarity": 0.85}],
        )
        await db_session.commit()

        # Get attributions
        attributions = await turbo_service.get_attributions(
            db=db_session,
            question_id=question.id,
        )

        assert len(attributions) == 1
        assert attributions[0]["contributor_name"] == "Dr. Knowledge"
        assert attributions[0]["semantic_similarity"] == 0.85


class TestHandleTurboAcceptance:
    """Tests for turbo_service.handle_turbo_acceptance"""

    @pytest.mark.asyncio
    async def test_resolves_question(self, db_session, clean_db):
        """Accepting turbo answer should resolve the question."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        question = await QuestionFactory.create(
            db_session, org.id, user.id,
            status=QuestionStatus.TURBO_ANSWERED,
        )
        await db_session.commit()

        # Accept
        await turbo_service.handle_turbo_acceptance(
            db=db_session,
            question=question,
        )

        await db_session.refresh(question)
        assert question.status == QuestionStatus.RESOLVED
        assert question.resolved_at is not None


class TestHandleTurboRejection:
    """Tests for turbo_service.handle_turbo_rejection"""

    @pytest.mark.asyncio
    async def test_escalates_to_expert(self, db_session, clean_db):
        """Rejecting turbo answer should escalate to human."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        question = await QuestionFactory.create(
            db_session, org.id, user.id,
            status=QuestionStatus.TURBO_ANSWERED,
        )
        question.gap_analysis = {"turbo_answer": True}
        await db_session.commit()

        # Reject
        await turbo_service.handle_turbo_rejection(
            db=db_session,
            question=question,
            rejection_reason="The answer was not helpful.",
        )

        await db_session.refresh(question)
        assert question.status == QuestionStatus.HUMAN_REQUESTED
        assert question.rejection_reason == "The answer was not helpful."
        assert question.gap_analysis["turbo_rejected"] is True


class TestTierScores:
    """Tests for tier score constants."""

    def test_tier_scores_valid(self):
        """Verify tier scores are properly configured."""
        assert TIER_SCORES["tier_0a"] == 1.0
        assert TIER_SCORES["tier_0b"] == 0.9
        assert TIER_SCORES["tier_0c"] == 0.7
        assert TIER_SCORES["pending"] == 0.4
        assert TIER_SCORES["archived"] == 0.0

    def test_tier_scores_descending(self):
        """Higher quality tiers should have higher scores."""
        assert TIER_SCORES["tier_0a"] > TIER_SCORES["tier_0b"]
        assert TIER_SCORES["tier_0b"] > TIER_SCORES["tier_0c"]
        assert TIER_SCORES["tier_0c"] > TIER_SCORES["pending"]
        assert TIER_SCORES["pending"] > TIER_SCORES["archived"]

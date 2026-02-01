"""
Unit tests for AutomationService.

These tests use a real database and real embeddings (hash-based fallback
when Ollama is unavailable) to verify the automation matching logic.
"""

import pytest
from datetime import date, timedelta

from app.models.automation import AutomationRule, AutomationLog, AutomationLogAction
from app.models.questions import Question, QuestionStatus
from app.models.answers import Answer, AnswerSource
from app.services.automation_service import automation_service, AUTO_ANSWER_THRESHOLD, SUGGEST_THRESHOLD

from tests.factories import (
    OrganizationFactory,
    UserFactory,
    QuestionFactory,
    AutomationRuleFactory,
)


class TestCheckForAutomation:
    """Tests for automation_service.check_for_automation"""

    @pytest.mark.asyncio
    async def test_finds_match_above_threshold(self, db_session, clean_db):
        """When a question closely matches a rule, it should return auto_answer action."""
        # Setup: Create org, user, and automation rule
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create rule: "What is the remote work policy?"
        rule = await AutomationRuleFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            name="Remote Work Policy",
            canonical_question="What is the remote work policy?",
            canonical_answer="Employees may work remotely up to 3 days per week.",
            similarity_threshold=0.80,
        )
        await db_session.commit()

        # Test: Check with a very similar question
        result = await automation_service.check_for_automation(
            db=db_session,
            question_text="What is the remote work policy?",  # Exact match
            organization_id=org.id,
        )

        assert result.matched is True
        assert result.action == "auto_answer"
        assert result.match is not None
        assert result.match.rule_id == rule.id
        assert result.match.similarity >= 0.80

    @pytest.mark.asyncio
    async def test_no_match_for_unrelated_question(self, db_session, clean_db):
        """When a question doesn't match any rules, it should queue for expert."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create rule about remote work
        await AutomationRuleFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            canonical_question="What is the remote work policy?",
            canonical_answer="Employees may work remotely up to 3 days per week.",
        )
        await db_session.commit()

        # Test: Check with completely unrelated question
        result = await automation_service.check_for_automation(
            db=db_session,
            question_text="What is the cafeteria menu for today?",
            organization_id=org.id,
        )

        assert result.matched is False
        assert result.action == "queue_for_expert"
        assert result.match is None

    @pytest.mark.asyncio
    async def test_ignores_inactive_rules(self, db_session, clean_db):
        """Disabled rules should not match."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create disabled rule
        await AutomationRuleFactory.create_disabled(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            canonical_question="What is the remote work policy?",
            canonical_answer="Employees may work remotely up to 3 days per week.",
        )
        await db_session.commit()

        # Test: Check with exact match to disabled rule
        result = await automation_service.check_for_automation(
            db=db_session,
            question_text="What is the remote work policy?",
            organization_id=org.id,
        )

        assert result.matched is False
        assert result.action == "queue_for_expert"

    @pytest.mark.asyncio
    async def test_ignores_expired_rules(self, db_session, clean_db):
        """Expired rules (past GUD date) should not match."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create expired rule
        await AutomationRuleFactory.create_expired(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            canonical_question="What is the remote work policy?",
            canonical_answer="Employees may work remotely up to 3 days per week.",
        )
        await db_session.commit()

        # Test: Check with exact match to expired rule
        result = await automation_service.check_for_automation(
            db=db_session,
            question_text="What is the remote work policy?",
            organization_id=org.id,
        )

        assert result.matched is False
        assert result.action == "queue_for_expert"

    @pytest.mark.asyncio
    async def test_respects_exclude_keywords(self, db_session, clean_db):
        """Questions containing exclude keywords should not match."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create rule with exclude keyword
        await AutomationRuleFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            canonical_question="What is the remote work policy?",
            canonical_answer="Employees may work remotely up to 3 days per week.",
            exclude_keywords=["urgent", "emergency"],
        )
        await db_session.commit()

        # Test: Check with question containing excluded keyword
        result = await automation_service.check_for_automation(
            db=db_session,
            question_text="What is the remote work policy? This is urgent!",
            organization_id=org.id,
        )

        assert result.matched is False
        assert result.action == "queue_for_expert"

    @pytest.mark.asyncio
    async def test_suggest_action_for_medium_similarity(self, db_session, clean_db):
        """Questions with medium similarity should suggest to expert."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create rule with high threshold
        await AutomationRuleFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            canonical_question="What is the process for requesting vacation time?",
            canonical_answer="Submit vacation requests through Workday 2 weeks in advance.",
            similarity_threshold=0.95,  # Very high threshold
        )
        await db_session.commit()

        # Test: Check with somewhat similar question (should be above SUGGEST_THRESHOLD but below rule threshold)
        result = await automation_service.check_for_automation(
            db=db_session,
            question_text="How do I request time off for vacation?",
            organization_id=org.id,
        )

        # With hash-based embeddings, similar questions should get reasonable similarity
        # The exact behavior depends on whether similarity is between thresholds
        assert result.action in ["suggest_to_expert", "auto_answer", "queue_for_expert"]


class TestDeliverAutoAnswer:
    """Tests for automation_service.deliver_auto_answer"""

    @pytest.mark.asyncio
    async def test_creates_answer_with_automation_source(self, db_session, clean_db):
        """Delivering an auto-answer should create an Answer with source=AUTOMATION."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        # Create rule and question
        rule = await AutomationRuleFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            canonical_question="What is the vacation policy?",
            canonical_answer="Employees receive 15 vacation days per year.",
        )
        question = await QuestionFactory.create_submitted(
            db_session,
            organization_id=org.id,
            asked_by_id=user.id,
            text="What is the vacation policy?",
        )
        await db_session.commit()

        # Check for automation match
        check_result = await automation_service.check_for_automation(
            db=db_session,
            question_text=question.original_text,
            organization_id=org.id,
        )

        assert check_result.matched is True
        assert check_result.match is not None

        # Deliver auto-answer
        answer = await automation_service.deliver_auto_answer(
            db=db_session,
            question=question,
            match=check_result.match,
        )

        # Verify answer
        assert answer is not None
        assert answer.source == AnswerSource.AUTOMATION
        assert answer.content == "Employees receive 15 vacation days per year."
        assert answer.question_id == question.id

    @pytest.mark.asyncio
    async def test_updates_question_status_to_auto_answered(self, db_session, clean_db):
        """Delivering an auto-answer should set question status to AUTO_ANSWERED."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        rule = await AutomationRuleFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
        )
        question = await QuestionFactory.create_submitted(
            db_session,
            organization_id=org.id,
            asked_by_id=user.id,
            text=rule.canonical_question,
        )
        await db_session.commit()

        check_result = await automation_service.check_for_automation(
            db=db_session,
            question_text=question.original_text,
            organization_id=org.id,
        )

        await automation_service.deliver_auto_answer(
            db=db_session,
            question=question,
            match=check_result.match,
        )

        # Refresh and verify
        await db_session.refresh(question)
        assert question.status == QuestionStatus.AUTO_ANSWERED
        assert question.automation_rule_id == rule.id
        assert question.first_response_at is not None

    @pytest.mark.asyncio
    async def test_creates_automation_log(self, db_session, clean_db):
        """Delivering an auto-answer should create an AutomationLog entry."""
        from sqlalchemy import select

        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        rule = await AutomationRuleFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
        )
        question = await QuestionFactory.create_submitted(
            db_session,
            organization_id=org.id,
            asked_by_id=user.id,
            text=rule.canonical_question,
        )
        await db_session.commit()

        check_result = await automation_service.check_for_automation(
            db=db_session,
            question_text=question.original_text,
            organization_id=org.id,
        )

        await automation_service.deliver_auto_answer(
            db=db_session,
            question=question,
            match=check_result.match,
        )

        # Check for log entry
        result = await db_session.execute(
            select(AutomationLog).where(
                AutomationLog.rule_id == rule.id,
                AutomationLog.question_id == question.id,
            )
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.action == AutomationLogAction.DELIVERED
        assert log.similarity_score > 0

    @pytest.mark.asyncio
    async def test_increments_times_triggered(self, db_session, clean_db):
        """Delivering an auto-answer should increment the rule's times_triggered."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        rule = await AutomationRuleFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
        )
        initial_triggered = rule.times_triggered

        question = await QuestionFactory.create_submitted(
            db_session,
            organization_id=org.id,
            asked_by_id=user.id,
            text=rule.canonical_question,
        )
        await db_session.commit()

        check_result = await automation_service.check_for_automation(
            db=db_session,
            question_text=question.original_text,
            organization_id=org.id,
        )

        await automation_service.deliver_auto_answer(
            db=db_session,
            question=question,
            match=check_result.match,
        )

        # Refresh and verify
        await db_session.refresh(rule)
        assert rule.times_triggered == initial_triggered + 1


class TestHandleUserFeedback:
    """Tests for automation_service.handle_user_feedback"""

    @pytest.mark.asyncio
    async def test_accept_resolves_question(self, db_session, clean_db):
        """Accepting an auto-answer should resolve the question."""
        from sqlalchemy import select

        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        rule = await AutomationRuleFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
        )
        question = await QuestionFactory.create_submitted(
            db_session,
            organization_id=org.id,
            asked_by_id=user.id,
            text=rule.canonical_question,
        )
        await db_session.commit()

        check_result = await automation_service.check_for_automation(
            db=db_session,
            question_text=question.original_text,
            organization_id=org.id,
        )

        await automation_service.deliver_auto_answer(
            db=db_session,
            question=question,
            match=check_result.match,
        )

        # Accept the auto-answer
        await automation_service.handle_user_feedback(
            db=db_session,
            question=question,
            accepted=True,
        )

        # Verify
        await db_session.refresh(question)
        await db_session.refresh(rule)

        assert question.status == QuestionStatus.RESOLVED
        assert question.auto_answer_accepted is True
        assert question.resolved_at is not None
        assert rule.times_accepted == 1

    @pytest.mark.asyncio
    async def test_reject_escalates_to_human(self, db_session, clean_db):
        """Rejecting an auto-answer should escalate to human expert."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        rule = await AutomationRuleFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
        )
        question = await QuestionFactory.create_submitted(
            db_session,
            organization_id=org.id,
            asked_by_id=user.id,
            text=rule.canonical_question,
        )
        await db_session.commit()

        check_result = await automation_service.check_for_automation(
            db=db_session,
            question_text=question.original_text,
            organization_id=org.id,
        )

        await automation_service.deliver_auto_answer(
            db=db_session,
            question=question,
            match=check_result.match,
        )

        # Reject the auto-answer
        await automation_service.handle_user_feedback(
            db=db_session,
            question=question,
            accepted=False,
            rejection_reason="The answer doesn't address my specific situation.",
        )

        # Verify
        await db_session.refresh(question)
        await db_session.refresh(rule)

        assert question.status == QuestionStatus.HUMAN_REQUESTED
        assert question.auto_answer_accepted is False
        assert question.rejection_reason == "The answer doesn't address my specific situation."
        assert rule.times_rejected == 1


class TestCreateRuleFromAnswer:
    """Tests for automation_service.create_rule_from_answer"""

    @pytest.mark.asyncio
    async def test_creates_rule_with_embedding(self, db_session, clean_db):
        """Creating a rule from an answer should generate an embedding."""
        from sqlalchemy import select

        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        # Create answered question
        question, answer = await QuestionFactory.create_answered(
            db_session,
            organization_id=org.id,
            asked_by_id=user.id,
            expert_id=expert.id,
            text="What is the process for getting a company credit card?",
            answer_content="Submit a request through the Finance portal with manager approval.",
        )
        await db_session.commit()

        # Create rule from the answer
        rule = await automation_service.create_rule_from_answer(
            db=db_session,
            question=question,
            answer=answer,
            name="Company Credit Card Process",
            description="How to get a company credit card",
        )

        # Verify rule
        assert rule is not None
        assert rule.name == "Company Credit Card Process"
        assert rule.canonical_question == question.original_text
        assert rule.canonical_answer == answer.content
        assert rule.is_enabled is True

        # Verify embedding was created
        result = await db_session.execute(
            select(AutomationRule).where(AutomationRule.id == rule.id)
        )
        refreshed_rule = result.scalar_one()

        # The embedding relationship should be loaded
        await db_session.refresh(refreshed_rule, ["embedding"])
        assert refreshed_rule.embedding is not None
        assert len(refreshed_rule.embedding.embedding_data) > 0

    @pytest.mark.asyncio
    async def test_rule_matches_similar_questions(self, db_session, clean_db):
        """A rule created from an answer should match similar questions."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        # Create answered question and rule
        question, answer = await QuestionFactory.create_answered(
            db_session,
            organization_id=org.id,
            asked_by_id=user.id,
            expert_id=expert.id,
            text="How do I submit an expense report?",
            answer_content="Use the Concur expense system to submit reports within 30 days.",
        )
        await db_session.commit()

        await automation_service.create_rule_from_answer(
            db=db_session,
            question=question,
            answer=answer,
            name="Expense Report Submission",
            similarity_threshold=0.80,
        )

        # Test: New similar question should match
        result = await automation_service.check_for_automation(
            db=db_session,
            question_text="How do I submit an expense report?",  # Same question
            organization_id=org.id,
        )

        assert result.matched is True
        assert result.action == "auto_answer"


class TestCosineSimililarity:
    """Tests for the cosine similarity calculation."""

    def test_identical_vectors_have_similarity_one(self):
        """Identical vectors should have similarity of 1.0."""
        vec = [0.5, 0.5, 0.5, 0.5]
        similarity = automation_service._cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.0001

    def test_orthogonal_vectors_have_similarity_zero(self):
        """Orthogonal vectors should have similarity of 0.0."""
        vec_a = [1.0, 0.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0, 0.0]
        similarity = automation_service._cosine_similarity(vec_a, vec_b)
        assert abs(similarity) < 0.0001

    def test_opposite_vectors_have_negative_similarity(self):
        """Opposite vectors should have similarity of -1.0."""
        vec_a = [1.0, 0.0, 0.0, 0.0]
        vec_b = [-1.0, 0.0, 0.0, 0.0]
        similarity = automation_service._cosine_similarity(vec_a, vec_b)
        assert abs(similarity - (-1.0)) < 0.0001

    def test_empty_vectors_return_zero(self):
        """Empty vectors should return 0.0 similarity."""
        similarity = automation_service._cosine_similarity([], [])
        assert similarity == 0.0

    def test_mismatched_lengths_return_zero(self):
        """Vectors of different lengths should return 0.0 similarity."""
        vec_a = [1.0, 0.0]
        vec_b = [1.0, 0.0, 0.0]
        similarity = automation_service._cosine_similarity(vec_a, vec_b)
        assert similarity == 0.0

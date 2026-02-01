"""
Unit tests for KnowledgeService.

These tests use a real database and real embeddings to verify
the knowledge base search, CRUD, and gap analysis functionality.
"""

import pytest
from datetime import date, timedelta
from uuid import uuid4

from app.models.wisdom import WisdomFact, WisdomEmbedding, WisdomTier
from app.services.knowledge_service import knowledge_service

from tests.factories import (
    OrganizationFactory,
    UserFactory,
    QuestionFactory,
    WisdomFactFactory,
)


class TestSearchRelevantFacts:
    """Tests for knowledge_service.search_relevant_facts"""

    @pytest.mark.asyncio
    async def test_finds_relevant_facts(self, db_session, clean_db):
        """Should find facts semantically similar to the query."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create facts about remote work
        await WisdomFactFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            content="Remote work is allowed up to 3 days per week with manager approval.",
            category="HR",
        )
        await WisdomFactFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            content="Employees can work from home on Mondays and Fridays.",
            category="HR",
        )
        await db_session.commit()

        # Search for remote work related content
        results = await knowledge_service.search_relevant_facts(
            question_text="What is the remote work policy?",
            organization_id=org.id,
            db=db_session,
            limit=10,
            min_similarity=0.3,
        )

        assert len(results) >= 1
        # Results should be sorted by similarity
        if len(results) > 1:
            assert results[0]["similarity"] >= results[1]["similarity"]

    @pytest.mark.asyncio
    async def test_respects_min_similarity_threshold(self, db_session, clean_db):
        """Facts below minimum similarity should not be returned."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create unrelated fact
        await WisdomFactFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            content="The company cafeteria serves lunch from 11am to 2pm.",
            category="Facilities",
        )
        await db_session.commit()

        # Search for something unrelated with high threshold
        results = await knowledge_service.search_relevant_facts(
            question_text="What is the policy on cryptocurrency investments?",
            organization_id=org.id,
            db=db_session,
            limit=10,
            min_similarity=0.8,  # High threshold
        )

        # Should return empty or very low match
        assert len(results) == 0 or all(r["similarity"] >= 0.8 for r in results)

    @pytest.mark.asyncio
    async def test_excludes_archived_facts(self, db_session, clean_db):
        """Archived facts should not be returned in search results."""
        from sqlalchemy import select

        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create and archive a fact
        fact = await WisdomFactFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            content="Remote work policy allows 3 days from home.",
        )
        await db_session.commit()

        # Archive it
        await knowledge_service.archive_fact(db_session, fact.id)

        # Search should not find the archived fact
        results = await knowledge_service.search_relevant_facts(
            question_text="What is the remote work policy?",
            organization_id=org.id,
            db=db_session,
            limit=10,
            min_similarity=0.0,  # Very low to catch any match
        )

        # Archived fact should not appear
        assert all(r["id"] != str(fact.id) for r in results)

    @pytest.mark.asyncio
    async def test_excludes_inactive_facts(self, db_session, clean_db):
        """Inactive facts should not be returned in search results."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create inactive fact
        fact = WisdomFact(
            organization_id=org.id,
            validated_by_id=expert.id,
            content="Remote work is allowed 5 days per week.",
            tier=WisdomTier.TIER_0B,
            is_active=False,  # Inactive
        )
        db_session.add(fact)
        await db_session.commit()

        # Search
        results = await knowledge_service.search_relevant_facts(
            question_text="What is the remote work policy?",
            organization_id=org.id,
            db=db_session,
            limit=10,
            min_similarity=0.0,
        )

        # Inactive fact should not appear
        assert all(r["id"] != str(fact.id) for r in results)

    @pytest.mark.asyncio
    async def test_returns_fact_metadata(self, db_session, clean_db):
        """Search results should include full fact metadata."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        await WisdomFactFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            content="Vacation requests must be submitted 2 weeks in advance.",
            category="HR",
            tier=WisdomTier.TIER_0A,
        )
        await db_session.commit()

        results = await knowledge_service.search_relevant_facts(
            question_text="How do I request vacation?",
            organization_id=org.id,
            db=db_session,
        )

        assert len(results) >= 1
        result = results[0]

        # Check metadata fields
        assert "id" in result
        assert "content" in result
        assert "tier" in result
        assert "category" in result
        assert "similarity" in result
        assert "confidence_score" in result


class TestCreateFact:
    """Tests for knowledge_service.create_fact"""

    @pytest.mark.asyncio
    async def test_creates_fact_with_embedding(self, db_session, clean_db):
        """Creating a fact should also generate an embedding."""
        from sqlalchemy import select

        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create fact
        fact = await knowledge_service.create_fact(
            db=db_session,
            organization_id=org.id,
            content="All contracts over $100k require legal review.",
            expert_user_id=expert.id,
            category="Legal",
            tier=WisdomTier.TIER_0B,
        )

        assert fact is not None
        assert fact.content == "All contracts over $100k require legal review."
        assert fact.tier == WisdomTier.TIER_0B
        assert fact.is_active is True

        # Check embedding was created
        result = await db_session.execute(
            select(WisdomEmbedding).where(WisdomEmbedding.wisdom_fact_id == fact.id)
        )
        embedding = result.scalar_one_or_none()

        assert embedding is not None
        assert len(embedding.embedding_data) > 0

    @pytest.mark.asyncio
    async def test_fact_searchable_after_creation(self, db_session, clean_db):
        """A newly created fact should be findable via semantic search."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create fact
        fact = await knowledge_service.create_fact(
            db=db_session,
            organization_id=org.id,
            content="The expense reimbursement limit is $500 per month.",
            expert_user_id=expert.id,
            category="Finance",
        )

        # Search should find it
        results = await knowledge_service.search_relevant_facts(
            question_text="What is the expense reimbursement limit?",
            organization_id=org.id,
            db=db_session,
        )

        assert any(r["id"] == str(fact.id) for r in results)


class TestCreateFactFromAnswer:
    """Tests for knowledge_service.create_fact_from_answer"""

    @pytest.mark.asyncio
    async def test_creates_fact_from_qa_pair(self, db_session, clean_db):
        """Should create a fact from an answered question."""
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
            text="What is the policy on parental leave?",
            answer_content="New parents receive 12 weeks of paid leave.",
        )
        await db_session.commit()

        # Create fact from the answer
        fact = await knowledge_service.create_fact_from_answer(
            db=db_session,
            question_id=question.id,
            expert_user_id=expert.id,
            tier=WisdomTier.TIER_0B,
        )

        assert fact is not None
        assert "parental leave" in fact.content.lower()
        assert "12 weeks" in fact.content

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_question(self, db_session, clean_db):
        """Should return None if question doesn't exist."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Try to create from non-existent question
        fact = await knowledge_service.create_fact_from_answer(
            db=db_session,
            question_id=uuid4(),  # Random UUID
            expert_user_id=expert.id,
        )

        assert fact is None


class TestUpdateFact:
    """Tests for knowledge_service.update_fact"""

    @pytest.mark.asyncio
    async def test_updates_fact_content(self, db_session, clean_db):
        """Updating content should regenerate embedding."""
        from sqlalchemy import select

        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create fact
        fact = await WisdomFactFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            content="Old content about vacation policy.",
        )
        await db_session.commit()

        # Get original embedding
        result = await db_session.execute(
            select(WisdomEmbedding).where(WisdomEmbedding.wisdom_fact_id == fact.id)
        )
        original_embedding = result.scalar_one()
        original_data = original_embedding.embedding_data.copy()

        # Update content
        updated = await knowledge_service.update_fact(
            db=db_session,
            fact_id=fact.id,
            updates={"content": "New content about remote work policy."},
        )

        assert updated is not None
        assert updated.content == "New content about remote work policy."

        # Check embedding was regenerated
        result = await db_session.execute(
            select(WisdomEmbedding).where(WisdomEmbedding.wisdom_fact_id == fact.id)
        )
        new_embedding = result.scalar_one()

        # Embeddings should be different (content changed)
        assert new_embedding.embedding_data != original_data

    @pytest.mark.asyncio
    async def test_updates_fact_tier(self, db_session, clean_db):
        """Updating tier should not regenerate embedding."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        fact = await WisdomFactFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            tier=WisdomTier.TIER_0C,
        )
        await db_session.commit()

        # Update tier only
        updated = await knowledge_service.update_fact(
            db=db_session,
            fact_id=fact.id,
            updates={"tier": WisdomTier.TIER_0A},
        )

        assert updated is not None
        assert updated.tier == WisdomTier.TIER_0A

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_fact(self, db_session, clean_db):
        """Should return None if fact doesn't exist."""
        result = await knowledge_service.update_fact(
            db=db_session,
            fact_id=uuid4(),
            updates={"content": "New content"},
        )
        assert result is None


class TestArchiveFact:
    """Tests for knowledge_service.archive_fact"""

    @pytest.mark.asyncio
    async def test_archives_fact(self, db_session, clean_db):
        """Archiving should set tier to ARCHIVED and is_active to False."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        fact = await WisdomFactFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
        )
        await db_session.commit()

        # Archive
        result = await knowledge_service.archive_fact(db_session, fact.id)
        assert result is True

        # Verify
        await db_session.refresh(fact)
        assert fact.tier == WisdomTier.ARCHIVED
        assert fact.is_active is False

    @pytest.mark.asyncio
    async def test_archived_fact_not_searchable(self, db_session, clean_db):
        """Archived facts should not appear in search results."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        fact = await WisdomFactFactory.create(
            db_session,
            organization_id=org.id,
            created_by_id=expert.id,
            content="Remote work policy details here.",
        )
        await db_session.commit()

        # Verify it's searchable before archiving
        results_before = await knowledge_service.search_relevant_facts(
            question_text="remote work",
            organization_id=org.id,
            db=db_session,
            min_similarity=0.0,
        )
        assert any(r["id"] == str(fact.id) for r in results_before)

        # Archive
        await knowledge_service.archive_fact(db_session, fact.id)

        # Verify not searchable after archiving
        results_after = await knowledge_service.search_relevant_facts(
            question_text="remote work",
            organization_id=org.id,
            db=db_session,
            min_similarity=0.0,
        )
        assert all(r["id"] != str(fact.id) for r in results_after)

    @pytest.mark.asyncio
    async def test_returns_false_for_missing_fact(self, db_session, clean_db):
        """Should return False if fact doesn't exist."""
        result = await knowledge_service.archive_fact(db_session, uuid4())
        assert result is False


class TestListFacts:
    """Tests for knowledge_service.list_facts"""

    @pytest.mark.asyncio
    async def test_lists_facts_with_pagination(self, db_session, clean_db):
        """Should return paginated list of facts."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create multiple facts
        for i in range(5):
            await WisdomFactFactory.create(
                db_session,
                organization_id=org.id,
                created_by_id=expert.id,
                content=f"Test fact number {i}",
            )
        await db_session.commit()

        # Get first page
        result = await knowledge_service.list_facts(
            db=db_session,
            organization_id=org.id,
            page=1,
            page_size=2,
        )

        assert result["total"] == 5
        assert len(result["facts"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2
        assert result["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_filters_by_tier(self, db_session, clean_db):
        """Should filter facts by tier."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create facts of different tiers
        await WisdomFactFactory.create_authoritative(
            db_session, org.id, expert.id, content="Authoritative fact"
        )
        await WisdomFactFactory.create_expert_validated(
            db_session, org.id, expert.id, content="Expert fact"
        )
        await WisdomFactFactory.create_ai_generated(
            db_session, org.id, expert.id, content="AI fact"
        )
        await db_session.commit()

        # Filter by tier_0a
        result = await knowledge_service.list_facts(
            db=db_session,
            organization_id=org.id,
            tier="tier_0a",
        )

        assert result["total"] == 1
        assert result["facts"][0]["tier"] == "tier_0a"

    @pytest.mark.asyncio
    async def test_filters_by_category(self, db_session, clean_db):
        """Should filter facts by category."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            content="HR related fact", category="HR"
        )
        await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            content="Legal related fact", category="Legal"
        )
        await db_session.commit()

        # Filter by HR
        result = await knowledge_service.list_facts(
            db=db_session,
            organization_id=org.id,
            category="HR",
        )

        assert result["total"] == 1
        assert result["facts"][0]["category"] == "HR"


class TestGetStats:
    """Tests for knowledge_service.get_stats"""

    @pytest.mark.asyncio
    async def test_returns_tier_counts(self, db_session, clean_db):
        """Should return correct counts by tier."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create facts of different tiers
        await WisdomFactFactory.create_authoritative(db_session, org.id, expert.id)
        await WisdomFactFactory.create_authoritative(db_session, org.id, expert.id)
        await WisdomFactFactory.create_expert_validated(db_session, org.id, expert.id)
        await db_session.commit()

        stats = await knowledge_service.get_stats(db_session, org.id)

        assert stats["total_facts"] == 3
        assert stats["tier_counts"]["tier_0a"] == 2
        assert stats["tier_counts"]["tier_0b"] == 1

    @pytest.mark.asyncio
    async def test_returns_expiring_count(self, db_session, clean_db):
        """Should count facts expiring within 30 days."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create facts with different expiry dates
        await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            good_until_date=date.today() + timedelta(days=10),  # Expiring
        )
        await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            good_until_date=date.today() + timedelta(days=60),  # Not expiring soon
        )
        await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            good_until_date=None,  # No expiry
        )
        await db_session.commit()

        stats = await knowledge_service.get_stats(db_session, org.id)

        assert stats["facts_expiring_soon"] == 1


class TestGetExpiringFacts:
    """Tests for knowledge_service.get_expiring_facts"""

    @pytest.mark.asyncio
    async def test_returns_facts_expiring_within_window(self, db_session, clean_db):
        """Should return facts expiring within the specified days."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create expiring fact
        expiring = await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            content="Expiring fact",
            good_until_date=date.today() + timedelta(days=5),
        )
        # Create non-expiring fact
        await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            content="Not expiring",
            good_until_date=date.today() + timedelta(days=60),
        )
        await db_session.commit()

        # Get facts expiring in 30 days
        results = await knowledge_service.get_expiring_facts(
            db=db_session,
            organization_id=org.id,
            days_ahead=30,
        )

        assert len(results) == 1
        assert results[0]["id"] == str(expiring.id)

    @pytest.mark.asyncio
    async def test_excludes_perpetual_facts(self, db_session, clean_db):
        """Perpetual facts should not appear in expiring list."""
        # Setup
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(db_session, org.id)
        await db_session.commit()

        # Create perpetual fact with a GUD (edge case)
        perpetual = WisdomFact(
            organization_id=org.id,
            validated_by_id=expert.id,
            content="Perpetual fact",
            tier=WisdomTier.TIER_0B,
            is_perpetual=True,
            good_until_date=date.today() + timedelta(days=5),
            is_active=True,
        )
        db_session.add(perpetual)
        await db_session.commit()

        results = await knowledge_service.get_expiring_facts(
            db=db_session,
            organization_id=org.id,
            days_ahead=30,
        )

        assert len(results) == 0


class TestCosineSimililarity:
    """Tests for the cosine similarity calculation."""

    def test_identical_vectors(self):
        """Identical vectors should have similarity of 1.0."""
        vec = [0.5, 0.5, 0.5, 0.5]
        similarity = knowledge_service._cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.0001

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity of 0.0."""
        vec_a = [1.0, 0.0]
        vec_b = [0.0, 1.0]
        similarity = knowledge_service._cosine_similarity(vec_a, vec_b)
        assert abs(similarity) < 0.0001

    def test_empty_vectors(self):
        """Empty vectors should return 0.0."""
        similarity = knowledge_service._cosine_similarity([], [])
        assert similarity == 0.0

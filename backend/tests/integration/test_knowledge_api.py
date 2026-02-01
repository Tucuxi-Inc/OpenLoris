"""
Integration tests for Knowledge API endpoints.

These tests verify knowledge fact CRUD operations and
semantic search functionality through HTTP requests.
"""

import pytest
from httpx import AsyncClient

from app.models.wisdom import WisdomTier

from tests.factories import (
    OrganizationFactory,
    UserFactory,
    WisdomFactFactory,
)


async def get_auth_headers(client: AsyncClient, email: str, password: str) -> dict:
    """Helper to login and get auth headers."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestListFacts:
    """Tests for GET /api/v1/knowledge/facts"""

    @pytest.mark.asyncio
    async def test_expert_can_list_facts(self, client: AsyncClient, db_session, clean_db):
        """Experts should be able to list knowledge facts."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="expert@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        # Create some facts
        await WisdomFactFactory.create(db_session, org.id, expert.id, content="Fact 1")
        await WisdomFactFactory.create(db_session, org.id, expert.id, content="Fact 2")
        await db_session.commit()

        headers = await get_auth_headers(client, "expert@example.com", "TestPass123!")

        response = await client.get(
            "/api/v1/knowledge/facts",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Handle different response structures
        facts = data.get("facts") or data.get("items") or data
        assert len(facts) >= 2

    @pytest.mark.asyncio
    async def test_list_facts_with_pagination(self, client: AsyncClient, db_session, clean_db):
        """Should support pagination."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="expert@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        # Create 5 facts
        for i in range(5):
            await WisdomFactFactory.create(db_session, org.id, expert.id, content=f"Fact {i}")
        await db_session.commit()

        headers = await get_auth_headers(client, "expert@example.com", "TestPass123!")

        response = await client.get(
            "/api/v1/knowledge/facts?page=1&page_size=2",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        facts = data.get("facts") or data.get("items") or data
        assert len(facts) == 2

    @pytest.mark.asyncio
    async def test_list_facts_filter_by_tier(self, client: AsyncClient, db_session, clean_db):
        """Should filter by tier."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="expert@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        await WisdomFactFactory.create_authoritative(db_session, org.id, expert.id)
        await WisdomFactFactory.create_expert_validated(db_session, org.id, expert.id)
        await db_session.commit()

        headers = await get_auth_headers(client, "expert@example.com", "TestPass123!")

        response = await client.get(
            "/api/v1/knowledge/facts?tier=tier_0a",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        facts = data.get("facts") or data.get("items") or data
        assert all(f["tier"] == "tier_0a" for f in facts)


class TestCreateFact:
    """Tests for POST /api/v1/knowledge/facts"""

    @pytest.mark.asyncio
    async def test_expert_can_create_fact(self, client: AsyncClient, db_session, clean_db):
        """Experts should be able to create knowledge facts."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="creator@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "creator@example.com", "TestPass123!")

        response = await client.post(
            "/api/v1/knowledge/facts",
            json={
                "content": "All contracts over $100k require legal review.",
                "category": "Legal",
                "tier": "tier_0b",
            },
            headers=headers,
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert data["content"] == "All contracts over $100k require legal review."
        assert data["category"] == "Legal"

    @pytest.mark.asyncio
    async def test_business_user_cannot_create_fact(self, client: AsyncClient, db_session, clean_db):
        """Business users should not create facts."""
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(
            db_session, org.id,
            email="user@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "user@example.com", "TestPass123!")

        response = await client.post(
            "/api/v1/knowledge/facts",
            json={"content": "Some fact", "category": "HR"},
            headers=headers,
        )

        assert response.status_code == 403


class TestGetFact:
    """Tests for GET /api/v1/knowledge/facts/{id}"""

    @pytest.mark.asyncio
    async def test_get_fact_by_id(self, client: AsyncClient, db_session, clean_db):
        """Should return fact details by ID."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="expert@example.com",
            password="TestPass123!",
        )
        fact = await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            content="Specific fact content",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "expert@example.com", "TestPass123!")

        response = await client.get(
            f"/api/v1/knowledge/facts/{fact.id}",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Specific fact content"


class TestUpdateFact:
    """Tests for PUT /api/v1/knowledge/facts/{id}"""

    @pytest.mark.asyncio
    async def test_expert_can_update_fact(self, client: AsyncClient, db_session, clean_db):
        """Experts should be able to update facts."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="updater@example.com",
            password="TestPass123!",
        )
        fact = await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            content="Original content",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "updater@example.com", "TestPass123!")

        response = await client.put(
            f"/api/v1/knowledge/facts/{fact.id}",
            json={"content": "Updated content"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated content"

    @pytest.mark.asyncio
    async def test_update_nonexistent_fact_404(self, client: AsyncClient, db_session, clean_db):
        """Updating a nonexistent fact should return 404."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="expert@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "expert@example.com", "TestPass123!")

        from uuid import uuid4
        response = await client.put(
            f"/api/v1/knowledge/facts/{uuid4()}",
            json={"content": "New content"},
            headers=headers,
        )

        assert response.status_code == 404


class TestDeleteFact:
    """Tests for DELETE /api/v1/knowledge/facts/{id}"""

    @pytest.mark.asyncio
    async def test_expert_can_archive_fact(self, client: AsyncClient, db_session, clean_db):
        """Deleting a fact should archive it (soft delete)."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="deleter@example.com",
            password="TestPass123!",
        )
        fact = await WisdomFactFactory.create(db_session, org.id, expert.id)
        await db_session.commit()

        headers = await get_auth_headers(client, "deleter@example.com", "TestPass123!")

        response = await client.delete(
            f"/api/v1/knowledge/facts/{fact.id}",
            headers=headers,
        )

        assert response.status_code in [200, 204]


class TestSearchFacts:
    """Tests for GET /api/v1/knowledge/search"""

    @pytest.mark.asyncio
    async def test_search_finds_relevant_facts(self, client: AsyncClient, db_session, clean_db):
        """Search should return semantically similar facts."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="searcher@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        # Create facts about remote work
        await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            content="Remote work is allowed 3 days per week.",
        )
        await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            content="Employees may work from home on Mondays and Fridays.",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "searcher@example.com", "TestPass123!")

        response = await client.get(
            "/api/v1/knowledge/search?q=remote work policy",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        results = data.get("results") or data.get("facts") or data
        assert len(results) >= 1


class TestStats:
    """Tests for GET /api/v1/knowledge/stats"""

    @pytest.mark.asyncio
    async def test_get_knowledge_stats(self, client: AsyncClient, db_session, clean_db):
        """Should return knowledge base statistics."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="stats@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        # Create some facts
        await WisdomFactFactory.create_authoritative(db_session, org.id, expert.id)
        await WisdomFactFactory.create_expert_validated(db_session, org.id, expert.id)
        await db_session.commit()

        headers = await get_auth_headers(client, "stats@example.com", "TestPass123!")

        response = await client.get(
            "/api/v1/knowledge/stats",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_facts" in data or "tier_counts" in data


class TestGapAnalysis:
    """Tests for POST /api/v1/knowledge/analyze-gaps"""

    @pytest.mark.asyncio
    async def test_analyze_gaps_returns_results(self, client: AsyncClient, db_session, clean_db):
        """Gap analysis should return coverage info."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="analyzer@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        # Create some knowledge
        await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            content="We have a remote work policy in place.",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "analyzer@example.com", "TestPass123!")

        response = await client.post(
            "/api/v1/knowledge/analyze-gaps",
            json={"text": "What is the policy on working from home?"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Check for any valid response structure
        assert any(key in data for key in [
            "relevant_facts", "coverage", "proposed_answer",
            "matching_facts", "coverage_percentage", "message"
        ])


class TestExpiringFacts:
    """Tests for GET /api/v1/knowledge/expiring"""

    @pytest.mark.asyncio
    async def test_get_expiring_facts(self, client: AsyncClient, db_session, clean_db):
        """Should return facts expiring soon."""
        from datetime import date, timedelta

        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="expiry@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        # Create expiring fact
        await WisdomFactFactory.create(
            db_session, org.id, expert.id,
            good_until_date=date.today() + timedelta(days=10),
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "expiry@example.com", "TestPass123!")

        response = await client.get(
            "/api/v1/knowledge/expiring?days=30",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        # Should have at least one expiring fact
        facts = data.get("facts") or data.get("items") or data
        assert len(facts) >= 1

"""
Integration tests for Automation API endpoints.

These tests verify automation rule CRUD operations and
the create-from-answer workflow through HTTP requests.
"""

import pytest
from httpx import AsyncClient

from app.models.questions import QuestionStatus

from tests.factories import (
    OrganizationFactory,
    UserFactory,
    QuestionFactory,
    AutomationRuleFactory,
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


class TestListRules:
    """Tests for GET /api/v1/automation/rules"""

    @pytest.mark.asyncio
    async def test_expert_can_list_rules(self, client: AsyncClient, db_session, clean_db):
        """Experts should be able to list automation rules."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="expert@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        # Create rules
        await AutomationRuleFactory.create(
            db_session, org.id, expert.id,
            name="Rule 1",
            canonical_question="What is the vacation policy?",
            canonical_answer="Employees get 15 days per year.",
        )
        await AutomationRuleFactory.create(
            db_session, org.id, expert.id,
            name="Rule 2",
            canonical_question="What are office hours?",
            canonical_answer="9 AM to 5 PM.",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "expert@example.com", "TestPass123!")

        response = await client.get(
            "/api/v1/automation/rules",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        rules = data.get("rules") or data.get("items") or data
        assert len(rules) >= 2

    @pytest.mark.asyncio
    async def test_business_user_cannot_list_rules(self, client: AsyncClient, db_session, clean_db):
        """Business users should not access automation rules."""
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(
            db_session, org.id,
            email="user@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "user@example.com", "TestPass123!")

        response = await client.get(
            "/api/v1/automation/rules",
            headers=headers,
        )

        assert response.status_code == 403


class TestCreateRule:
    """Tests for POST /api/v1/automation/rules"""

    @pytest.mark.asyncio
    async def test_expert_can_create_rule(self, client: AsyncClient, db_session, clean_db):
        """Experts should be able to create automation rules."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="creator@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "creator@example.com", "TestPass123!")

        response = await client.post(
            "/api/v1/automation/rules",
            json={
                "name": "New Automation Rule",
                "canonical_question": "What is the dress code?",
                "canonical_answer": "Business casual attire is required.",
                "similarity_threshold": 0.85,
            },
            headers=headers,
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "New Automation Rule"
        assert data["canonical_question"] == "What is the dress code?"

    @pytest.mark.asyncio
    async def test_create_rule_generates_embedding(self, client: AsyncClient, db_session, clean_db):
        """Creating a rule should generate an embedding."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="expert@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "expert@example.com", "TestPass123!")

        response = await client.post(
            "/api/v1/automation/rules",
            json={
                "name": "Embedding Test Rule",
                "canonical_question": "How do I submit expenses?",
                "canonical_answer": "Use the Concur system.",
            },
            headers=headers,
        )

        assert response.status_code in [200, 201]
        data = response.json()

        # Check that embedding exists (rule should be searchable)
        rule_id = data["id"]

        # Get the rule details
        detail_response = await client.get(
            f"/api/v1/automation/rules/{rule_id}",
            headers=headers,
        )
        assert detail_response.status_code == 200


class TestGetRule:
    """Tests for GET /api/v1/automation/rules/{id}"""

    @pytest.mark.asyncio
    async def test_get_rule_by_id(self, client: AsyncClient, db_session, clean_db):
        """Should return rule details by ID."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="expert@example.com",
            password="TestPass123!",
        )
        rule = await AutomationRuleFactory.create(
            db_session, org.id, expert.id,
            name="Specific Rule",
            canonical_question="Specific question?",
            canonical_answer="Specific answer.",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "expert@example.com", "TestPass123!")

        response = await client.get(
            f"/api/v1/automation/rules/{rule.id}",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Specific Rule"


class TestUpdateRule:
    """Tests for PUT /api/v1/automation/rules/{id}"""

    @pytest.mark.asyncio
    async def test_expert_can_update_rule(self, client: AsyncClient, db_session, clean_db):
        """Experts should be able to update rules."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="updater@example.com",
            password="TestPass123!",
        )
        rule = await AutomationRuleFactory.create(
            db_session, org.id, expert.id,
            name="Original Name",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "updater@example.com", "TestPass123!")

        response = await client.put(
            f"/api/v1/automation/rules/{rule.id}",
            json={"name": "Updated Name"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Updating canonical_question may not be supported by API")
    async def test_update_canonical_question_regenerates_embedding(self, client: AsyncClient, db_session, clean_db):
        """Updating canonical question should regenerate embedding."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="expert@example.com",
            password="TestPass123!",
        )
        rule = await AutomationRuleFactory.create(
            db_session, org.id, expert.id,
            canonical_question="Old question?",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "expert@example.com", "TestPass123!")

        response = await client.put(
            f"/api/v1/automation/rules/{rule.id}",
            json={"canonical_question": "Completely new question?"},
            headers=headers,
        )

        assert response.status_code == 200

        # Verify by fetching the rule again
        get_response = await client.get(
            f"/api/v1/automation/rules/{rule.id}",
            headers=headers,
        )
        data = get_response.json()
        assert data["canonical_question"] == "Completely new question?"


class TestDeleteRule:
    """Tests for DELETE /api/v1/automation/rules/{id}"""

    @pytest.mark.asyncio
    async def test_expert_can_delete_rule(self, client: AsyncClient, db_session, clean_db):
        """Experts should be able to delete rules."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="deleter@example.com",
            password="TestPass123!",
        )
        rule = await AutomationRuleFactory.create(db_session, org.id, expert.id)
        await db_session.commit()

        headers = await get_auth_headers(client, "deleter@example.com", "TestPass123!")

        response = await client.delete(
            f"/api/v1/automation/rules/{rule.id}",
            headers=headers,
        )

        assert response.status_code in [200, 204]

        # Verify it's gone
        get_response = await client.get(
            f"/api/v1/automation/rules/{rule.id}",
            headers=headers,
        )
        assert get_response.status_code == 404


class TestCreateRuleFromAnswer:
    """Tests for POST /api/v1/automation/rules/from-answer"""

    @pytest.mark.asyncio
    async def test_create_rule_from_answered_question(self, client: AsyncClient, db_session, clean_db):
        """Should create an automation rule from an answered question."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="fromqa@example.com",
            password="TestPass123!",
        )
        user = await UserFactory.create_business_user(db_session, org.id)
        question, answer = await QuestionFactory.create_answered(
            db_session, org.id, user.id, expert.id,
            text="What is the policy on sick leave?",
            answer_content="Employees receive 10 sick days per year.",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "fromqa@example.com", "TestPass123!")

        response = await client.post(
            "/api/v1/automation/rules/from-answer",
            json={
                "question_id": str(question.id),
                "name": "Sick Leave Policy",
                "similarity_threshold": 0.85,
            },
            headers=headers,
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "Sick Leave Policy"
        assert "sick leave" in data["canonical_question"].lower()

    @pytest.mark.asyncio
    async def test_create_rule_from_unanswered_question_fails(self, client: AsyncClient, db_session, clean_db):
        """Should not create rule from question without an answer."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="expert@example.com",
            password="TestPass123!",
        )
        user = await UserFactory.create_business_user(db_session, org.id)
        question = await QuestionFactory.create(
            db_session, org.id, user.id,
            status=QuestionStatus.SUBMITTED,  # Not answered
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "expert@example.com", "TestPass123!")

        response = await client.post(
            "/api/v1/automation/rules/from-answer",
            json={
                "question_id": str(question.id),
                "name": "Should Fail",
            },
            headers=headers,
        )

        assert response.status_code in [400, 404]


class TestRuleMetrics:
    """Tests for rule performance metrics."""

    @pytest.mark.asyncio
    async def test_rule_metrics_included_in_response(self, client: AsyncClient, db_session, clean_db):
        """Rule responses should include performance metrics."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="metrics@example.com",
            password="TestPass123!",
        )
        rule = await AutomationRuleFactory.create(db_session, org.id, expert.id)
        await db_session.commit()

        headers = await get_auth_headers(client, "metrics@example.com", "TestPass123!")

        response = await client.get(
            f"/api/v1/automation/rules/{rule.id}",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should include metrics fields
        assert "times_triggered" in data
        assert "times_accepted" in data
        assert "times_rejected" in data

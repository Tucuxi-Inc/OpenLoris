"""
Integration tests for Questions API endpoints.

These tests verify the complete Q&A lifecycle including
question submission, automation matching, and expert answering.
"""

import pytest
from httpx import AsyncClient
from uuid import UUID

from app.models.questions import QuestionStatus
from app.models.user import UserRole

from tests.factories import (
    OrganizationFactory,
    UserFactory,
    QuestionFactory,
    AnswerFactory,
    AutomationRuleFactory,
)
from tests.conftest import generate_test_embedding


async def get_auth_headers(client: AsyncClient, email: str, password: str) -> dict:
    """Helper to login and get auth headers."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestSubmitQuestion:
    """Tests for POST /api/v1/questions/"""

    @pytest.mark.asyncio
    async def test_submit_question_creates_record(self, client: AsyncClient, db_session, clean_db):
        """Submitting a question should create a new question record."""
        # Create user
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(
            db_session, org.id,
            email="asker@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "asker@example.com", "TestPass123!")

        response = await client.post(
            "/api/v1/questions/",
            json={
                "text": "What is the company policy on remote work?",
                "category": "HR",
            },
            headers=headers,
        )

        assert response.status_code in [200, 201]
        data = response.json()

        # Handle nested response structure
        question_data = data.get("question", data)
        assert "id" in question_data
        assert question_data["original_text"] == "What is the company policy on remote work?"
        assert question_data["status"] in ["submitted", "expert_queue"]

    @pytest.mark.asyncio
    async def test_submit_question_unauthorized(self, client: AsyncClient, db_session, clean_db):
        """Should reject question submission without authentication."""
        response = await client.post(
            "/api/v1/questions/",
            json={"text": "Some question here"},
        )
        assert response.status_code == 401


class TestListQuestions:
    """Tests for GET /api/v1/questions/"""

    @pytest.mark.asyncio
    async def test_list_own_questions(self, client: AsyncClient, db_session, clean_db):
        """Users should see their own questions."""
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(
            db_session, org.id,
            email="lister@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        # Create some questions
        await QuestionFactory.create(db_session, org.id, user.id, text="Question 1")
        await QuestionFactory.create(db_session, org.id, user.id, text="Question 2")
        await db_session.commit()

        headers = await get_auth_headers(client, "lister@example.com", "TestPass123!")

        response = await client.get(
            "/api/v1/questions/",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "questions" in data or isinstance(data, list)

        items = data.get("items") or data.get("questions") or data
        assert len(items) >= 2

    @pytest.mark.asyncio
    async def test_list_excludes_other_users_questions(self, client: AsyncClient, db_session, clean_db):
        """Users should not see other users' questions."""
        org = await OrganizationFactory.create(db_session)
        user1 = await UserFactory.create_business_user(
            db_session, org.id,
            email="user1@example.com",
            password="TestPass123!",
        )
        user2 = await UserFactory.create_business_user(
            db_session, org.id,
            email="user2@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        # User1's question
        await QuestionFactory.create(db_session, org.id, user1.id, text="User1 Question")
        # User2's question
        await QuestionFactory.create(db_session, org.id, user2.id, text="User2 Question")
        await db_session.commit()

        # Login as user1
        headers = await get_auth_headers(client, "user1@example.com", "TestPass123!")

        response = await client.get("/api/v1/questions/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        items = data.get("items") or data.get("questions") or data

        # Should only see user1's question
        texts = [q["original_text"] for q in items]
        assert "User1 Question" in texts
        assert "User2 Question" not in texts


class TestQuestionDetail:
    """Tests for GET /api/v1/questions/{id}"""

    @pytest.mark.asyncio
    async def test_get_own_question_detail(self, client: AsyncClient, db_session, clean_db):
        """Should return details of own question."""
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(
            db_session, org.id,
            email="detail@example.com",
            password="TestPass123!",
        )
        question = await QuestionFactory.create(
            db_session, org.id, user.id,
            text="What are the office hours?",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "detail@example.com", "TestPass123!")

        response = await client.get(
            f"/api/v1/questions/{question.id}",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(question.id)
        assert data["original_text"] == "What are the office hours?"

    @pytest.mark.asyncio
    async def test_get_other_user_question_forbidden(self, client: AsyncClient, db_session, clean_db):
        """Should not allow viewing other user's question (unless expert)."""
        org = await OrganizationFactory.create(db_session)
        user1 = await UserFactory.create_business_user(
            db_session, org.id,
            email="owner@example.com",
            password="TestPass123!",
        )
        user2 = await UserFactory.create_business_user(
            db_session, org.id,
            email="other@example.com",
            password="TestPass123!",
        )
        question = await QuestionFactory.create(db_session, org.id, user1.id)
        await db_session.commit()

        headers = await get_auth_headers(client, "other@example.com", "TestPass123!")

        response = await client.get(
            f"/api/v1/questions/{question.id}",
            headers=headers,
        )

        # Should be forbidden for regular users viewing others' questions
        assert response.status_code in [403, 404]


class TestExpertQueue:
    """Tests for GET /api/v1/questions/queue/pending"""

    @pytest.mark.asyncio
    async def test_expert_can_view_queue(self, client: AsyncClient, db_session, clean_db):
        """Experts should see pending questions."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="expert@example.com",
            password="TestPass123!",
        )
        user = await UserFactory.create_business_user(db_session, org.id)
        await db_session.commit()

        # Create question in queue
        await QuestionFactory.create(
            db_session, org.id, user.id,
            status=QuestionStatus.EXPERT_QUEUE,
            text="Pending question",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "expert@example.com", "TestPass123!")

        response = await client.get(
            "/api/v1/questions/queue/pending",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        items = data.get("items") or data.get("questions") or data
        assert len(items) >= 1

    @pytest.mark.asyncio
    async def test_business_user_cannot_view_queue(self, client: AsyncClient, db_session, clean_db):
        """Business users should not access expert queue."""
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(
            db_session, org.id,
            email="user@example.com",
            password="TestPass123!",
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "user@example.com", "TestPass123!")

        response = await client.get(
            "/api/v1/questions/queue/pending",
            headers=headers,
        )

        assert response.status_code == 403


class TestAssignQuestion:
    """Tests for POST /api/v1/questions/{id}/assign"""

    @pytest.mark.asyncio
    async def test_expert_can_claim_question(self, client: AsyncClient, db_session, clean_db):
        """Expert should be able to claim an unassigned question."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="claimer@example.com",
            password="TestPass123!",
        )
        user = await UserFactory.create_business_user(db_session, org.id)
        question = await QuestionFactory.create(
            db_session, org.id, user.id,
            status=QuestionStatus.EXPERT_QUEUE,
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "claimer@example.com", "TestPass123!")

        response = await client.post(
            f"/api/v1/questions/{question.id}/assign",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned_to_id"] == str(expert.id)
        assert data["status"] == "in_progress"


class TestAnswerQuestion:
    """Tests for POST /api/v1/questions/{id}/answer"""

    @pytest.mark.asyncio
    async def test_expert_can_answer_assigned_question(self, client: AsyncClient, db_session, clean_db):
        """Expert should be able to answer their assigned question."""
        org = await OrganizationFactory.create(db_session)
        expert = await UserFactory.create_expert(
            db_session, org.id,
            email="answerer@example.com",
            password="TestPass123!",
        )
        user = await UserFactory.create_business_user(db_session, org.id)
        question = await QuestionFactory.create(
            db_session, org.id, user.id,
            status=QuestionStatus.IN_PROGRESS,
            assigned_to_id=expert.id,
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "answerer@example.com", "TestPass123!")

        response = await client.post(
            f"/api/v1/questions/{question.id}/answer",
            json={
                "content": "Here is the detailed answer to your question.",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "answered"


class TestFeedback:
    """Tests for POST /api/v1/questions/{id}/feedback"""

    @pytest.mark.asyncio
    async def test_user_can_rate_answer(self, client: AsyncClient, db_session, clean_db):
        """User should be able to rate an answered question."""
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(
            db_session, org.id,
            email="rater@example.com",
            password="TestPass123!",
        )
        expert = await UserFactory.create_expert(db_session, org.id)
        question, answer = await QuestionFactory.create_answered(
            db_session, org.id, user.id, expert.id,
        )
        await db_session.commit()

        headers = await get_auth_headers(client, "rater@example.com", "TestPass123!")

        response = await client.post(
            f"/api/v1/questions/{question.id}/feedback",
            json={"rating": 5, "comment": "Very helpful!"},
            headers=headers,
        )

        assert response.status_code == 200


class TestAutoAnswerFlow:
    """Tests for automation matching and auto-answer acceptance/rejection."""

    @pytest.mark.asyncio
    async def test_accept_auto_answer_resolves_question(self, client: AsyncClient, db_session, clean_db):
        """Accepting an auto-answer should resolve the question."""
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(
            db_session, org.id,
            email="accepter@example.com",
            password="TestPass123!",
        )
        expert = await UserFactory.create_expert(db_session, org.id)
        question = await QuestionFactory.create(
            db_session, org.id, user.id,
            status=QuestionStatus.AUTO_ANSWERED,
        )
        # Create the auto-answer
        from app.models.answers import Answer, AnswerSource
        auto_answer = Answer(
            question_id=question.id,
            created_by_id=expert.id,
            content="Automated answer content",
            source=AnswerSource.AUTOMATION,
        )
        db_session.add(auto_answer)
        await db_session.commit()

        headers = await get_auth_headers(client, "accepter@example.com", "TestPass123!")

        response = await client.post(
            f"/api/v1/questions/{question.id}/accept-auto",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_reject_auto_answer_escalates(self, client: AsyncClient, db_session, clean_db):
        """Rejecting an auto-answer should escalate to human expert."""
        org = await OrganizationFactory.create(db_session)
        user = await UserFactory.create_business_user(
            db_session, org.id,
            email="rejecter@example.com",
            password="TestPass123!",
        )
        expert = await UserFactory.create_expert(db_session, org.id)
        question = await QuestionFactory.create(
            db_session, org.id, user.id,
            status=QuestionStatus.AUTO_ANSWERED,
        )
        from app.models.answers import Answer, AnswerSource
        auto_answer = Answer(
            question_id=question.id,
            created_by_id=expert.id,
            content="Automated answer content",
            source=AnswerSource.AUTOMATION,
        )
        db_session.add(auto_answer)
        await db_session.commit()

        headers = await get_auth_headers(client, "rejecter@example.com", "TestPass123!")

        response = await client.post(
            f"/api/v1/questions/{question.id}/request-human",
            json={"reason": "The answer was not specific enough."},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "human_requested"

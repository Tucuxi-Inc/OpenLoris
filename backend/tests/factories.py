"""
Test data factories for Loris backend tests.

These factories create real database records with actual embeddings.
They are designed to work with the real database and services.
"""

import random
import string
from datetime import date, datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.questions import Question, QuestionStatus, QuestionPriority
from app.models.answers import Answer, AnswerSource
from app.models.automation import AutomationRule, AutomationRuleEmbedding, AutomationLog, AutomationLogAction
from app.models.wisdom import WisdomFact, WisdomEmbedding, WisdomTier
from app.models.documents import KnowledgeDocument, DocumentType, ParsingStatus
from app.services.embedding_service import embedding_service

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def random_string(length: int = 8) -> str:
    """Generate a random string for unique identifiers."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def random_email() -> str:
    """Generate a random email address."""
    return f"user_{random_string()}@test.com"


class OrganizationFactory:
    """Factory for creating Organization records."""

    @staticmethod
    async def create(
        session: AsyncSession,
        name: str = None,
        slug: str = None,
        domain: str = None,
        settings: dict = None,
    ) -> Organization:
        """Create an organization with optional customization."""
        suffix = random_string(6)
        org = Organization(
            name=name or f"Test Org {suffix}",
            slug=slug or f"test-org-{suffix}",
            domain=domain,
            settings=settings or {
                "departments": ["Legal", "HR", "Finance"],
                "require_department": False,
                "turbo_loris": {
                    "enabled": True,
                    "min_threshold": 0.50,
                    "default_threshold": 0.75,
                    "threshold_options": [0.50, 0.75, 0.90],
                },
            },
        )
        session.add(org)
        await session.flush()
        return org


class UserFactory:
    """Factory for creating User records."""

    @staticmethod
    async def create(
        session: AsyncSession,
        organization_id: UUID,
        email: str = None,
        name: str = None,
        role: UserRole = UserRole.BUSINESS_USER,
        password: str = "testpassword123",
        is_active: bool = True,
        department: str = None,
    ) -> User:
        """Create a user with optional customization."""
        user = User(
            organization_id=organization_id,
            email=email or random_email(),
            name=name or f"Test User {random_string(4)}",
            hashed_password=pwd_context.hash(password),
            role=role,
            is_active=is_active,
            department=department,
        )
        session.add(user)
        await session.flush()
        return user

    @staticmethod
    async def create_business_user(session: AsyncSession, organization_id: UUID, **kwargs) -> User:
        """Create a business user."""
        return await UserFactory.create(session, organization_id, role=UserRole.BUSINESS_USER, **kwargs)

    @staticmethod
    async def create_expert(session: AsyncSession, organization_id: UUID, **kwargs) -> User:
        """Create a domain expert."""
        return await UserFactory.create(session, organization_id, role=UserRole.DOMAIN_EXPERT, **kwargs)

    @staticmethod
    async def create_admin(session: AsyncSession, organization_id: UUID, **kwargs) -> User:
        """Create an admin user."""
        return await UserFactory.create(session, organization_id, role=UserRole.ADMIN, **kwargs)


class QuestionFactory:
    """Factory for creating Question records."""

    # Sample questions for testing semantic similarity
    SAMPLE_QUESTIONS = [
        "What is the company policy on remote work?",
        "How many vacation days do employees get?",
        "What is the process for expense reimbursement?",
        "Can I work from home on Fridays?",
        "What are the health insurance options?",
        "How do I request time off?",
        "What is the dress code policy?",
        "When are performance reviews conducted?",
        "How do I submit a travel request?",
        "What is the policy on overtime?",
    ]

    @staticmethod
    async def create(
        session: AsyncSession,
        organization_id: UUID,
        asked_by_id: UUID,
        text: str = None,
        status: QuestionStatus = QuestionStatus.SUBMITTED,
        priority: QuestionPriority = QuestionPriority.NORMAL,
        category: str = None,
        department: str = None,
        assigned_to_id: UUID = None,
        turbo_mode: bool = False,
        turbo_threshold: float = None,
    ) -> Question:
        """Create a question with optional customization."""
        question = Question(
            organization_id=organization_id,
            asked_by_id=asked_by_id,
            original_text=text or random.choice(QuestionFactory.SAMPLE_QUESTIONS),
            status=status,
            priority=priority,
            category=category,
            department=department,
            assigned_to_id=assigned_to_id,
            turbo_mode=turbo_mode,
            turbo_threshold=turbo_threshold,
        )
        session.add(question)
        await session.flush()
        return question

    @staticmethod
    async def create_submitted(session: AsyncSession, organization_id: UUID, asked_by_id: UUID, **kwargs) -> Question:
        """Create a submitted question."""
        return await QuestionFactory.create(
            session, organization_id, asked_by_id, status=QuestionStatus.SUBMITTED, **kwargs
        )

    @staticmethod
    async def create_in_queue(session: AsyncSession, organization_id: UUID, asked_by_id: UUID, **kwargs) -> Question:
        """Create a question in the expert queue."""
        return await QuestionFactory.create(
            session, organization_id, asked_by_id, status=QuestionStatus.EXPERT_QUEUE, **kwargs
        )

    @staticmethod
    async def create_answered(
        session: AsyncSession,
        organization_id: UUID,
        asked_by_id: UUID,
        expert_id: UUID,
        answer_content: str = "This is the expert's answer.",
        **kwargs
    ) -> tuple[Question, Answer]:
        """Create an answered question with its answer."""
        question = await QuestionFactory.create(
            session, organization_id, asked_by_id,
            status=QuestionStatus.ANSWERED,
            assigned_to_id=expert_id,
            **kwargs
        )

        answer = Answer(
            question_id=question.id,
            created_by_id=expert_id,
            content=answer_content,
            source=AnswerSource.EXPERT,
            delivered_at=datetime.now(timezone.utc),
        )
        session.add(answer)
        await session.flush()

        return question, answer


class AnswerFactory:
    """Factory for creating Answer records."""

    @staticmethod
    async def create(
        session: AsyncSession,
        question_id: UUID,
        created_by_id: UUID,
        content: str = "This is a test answer with detailed information.",
        source: AnswerSource = AnswerSource.EXPERT,
    ) -> Answer:
        """Create an answer with optional customization."""
        answer = Answer(
            question_id=question_id,
            created_by_id=created_by_id,
            content=content,
            source=source,
            delivered_at=datetime.now(timezone.utc),
        )
        session.add(answer)
        await session.flush()
        return answer


class AutomationRuleFactory:
    """Factory for creating AutomationRule records with embeddings."""

    # Sample Q&A pairs for automation rules
    SAMPLE_RULES = [
        {
            "name": "Remote Work Policy",
            "question": "What is the remote work policy?",
            "answer": "Employees may work remotely up to 3 days per week with manager approval.",
        },
        {
            "name": "Vacation Days",
            "question": "How many vacation days do I get?",
            "answer": "Full-time employees receive 15 vacation days per year, increasing to 20 after 5 years.",
        },
        {
            "name": "Expense Reimbursement",
            "question": "How do I get reimbursed for expenses?",
            "answer": "Submit expense reports through the Concur system within 30 days with receipts.",
        },
        {
            "name": "Health Insurance",
            "question": "What health insurance plans are available?",
            "answer": "We offer PPO and HMO plans through Blue Cross. Open enrollment is in November.",
        },
        {
            "name": "Time Off Request",
            "question": "How do I request time off?",
            "answer": "Submit time off requests through Workday at least 2 weeks in advance.",
        },
    ]

    @staticmethod
    async def create(
        session: AsyncSession,
        organization_id: UUID,
        created_by_id: UUID,
        name: str = None,
        canonical_question: str = None,
        canonical_answer: str = None,
        similarity_threshold: float = 0.85,
        is_enabled: bool = True,
        category_filter: str = None,
        exclude_keywords: List[str] = None,
        good_until_date: date = None,
    ) -> AutomationRule:
        """Create an automation rule with real embedding."""
        # Use sample data if not provided
        if not canonical_question or not canonical_answer:
            sample = random.choice(AutomationRuleFactory.SAMPLE_RULES)
            name = name or sample["name"]
            canonical_question = canonical_question or sample["question"]
            canonical_answer = canonical_answer or sample["answer"]

        rule = AutomationRule(
            organization_id=organization_id,
            created_by_id=created_by_id,
            name=name or f"Rule {random_string(6)}",
            canonical_question=canonical_question,
            canonical_answer=canonical_answer,
            similarity_threshold=similarity_threshold,
            is_enabled=is_enabled,
            category_filter=category_filter,
            exclude_keywords=exclude_keywords or [],
            good_until_date=good_until_date,
        )
        session.add(rule)
        await session.flush()

        # Generate real embedding for the canonical question
        embedding_data = await embedding_service.generate(canonical_question)

        rule_embedding = AutomationRuleEmbedding(
            rule_id=rule.id,
            embedding_data=embedding_data,
            model_name=embedding_service.model_name,
        )
        session.add(rule_embedding)
        await session.flush()

        return rule

    @staticmethod
    async def create_expired(
        session: AsyncSession,
        organization_id: UUID,
        created_by_id: UUID,
        **kwargs
    ) -> AutomationRule:
        """Create an expired automation rule."""
        return await AutomationRuleFactory.create(
            session, organization_id, created_by_id,
            good_until_date=date.today() - timedelta(days=1),
            **kwargs
        )

    @staticmethod
    async def create_disabled(
        session: AsyncSession,
        organization_id: UUID,
        created_by_id: UUID,
        **kwargs
    ) -> AutomationRule:
        """Create a disabled automation rule."""
        return await AutomationRuleFactory.create(
            session, organization_id, created_by_id,
            is_enabled=False,
            **kwargs
        )


class WisdomFactFactory:
    """Factory for creating WisdomFact records with embeddings."""

    # Sample facts for testing
    SAMPLE_FACTS = [
        {"content": "Remote work is allowed up to 3 days per week with manager approval.", "category": "HR"},
        {"content": "All expense reports must include itemized receipts.", "category": "Finance"},
        {"content": "NDAs must be reviewed by legal before signing.", "category": "Legal"},
        {"content": "Performance reviews are conducted annually in Q4.", "category": "HR"},
        {"content": "Travel bookings should be made through the corporate travel portal.", "category": "Finance"},
        {"content": "Contract amendments require legal department approval.", "category": "Legal"},
        {"content": "New hires receive 15 vacation days in their first year.", "category": "HR"},
        {"content": "Vendor contracts over $50k require CFO signature.", "category": "Finance"},
    ]

    @staticmethod
    async def create(
        session: AsyncSession,
        organization_id: UUID,
        created_by_id: UUID,
        content: str = None,
        tier: WisdomTier = WisdomTier.TIER_0B,
        category: str = None,
        domain: str = None,
        good_until_date: date = None,
        confidence_score: float = 0.9,
    ) -> WisdomFact:
        """Create a wisdom fact with real embedding."""
        if not content:
            sample = random.choice(WisdomFactFactory.SAMPLE_FACTS)
            content = sample["content"]
            category = category or sample["category"]

        fact = WisdomFact(
            organization_id=organization_id,
            validated_by_id=created_by_id,  # WisdomFact uses validated_by_id
            content=content,
            tier=tier,
            category=category,
            domain=domain,
            good_until_date=good_until_date,
            confidence_score=confidence_score,
            is_active=True,
        )
        session.add(fact)
        await session.flush()

        # Generate real embedding
        embedding_data = await embedding_service.generate(content)

        fact_embedding = WisdomEmbedding(
            wisdom_fact_id=fact.id,
            embedding_data=embedding_data,
            model_name=embedding_service.model_name,
        )
        session.add(fact_embedding)
        await session.flush()

        return fact

    @staticmethod
    async def create_authoritative(session: AsyncSession, organization_id: UUID, created_by_id: UUID, **kwargs) -> WisdomFact:
        """Create a tier 0A (authoritative) fact."""
        return await WisdomFactFactory.create(
            session, organization_id, created_by_id,
            tier=WisdomTier.TIER_0A,
            confidence_score=1.0,
            **kwargs
        )

    @staticmethod
    async def create_expert_validated(session: AsyncSession, organization_id: UUID, created_by_id: UUID, **kwargs) -> WisdomFact:
        """Create a tier 0B (expert validated) fact."""
        return await WisdomFactFactory.create(
            session, organization_id, created_by_id,
            tier=WisdomTier.TIER_0B,
            confidence_score=0.9,
            **kwargs
        )

    @staticmethod
    async def create_ai_generated(session: AsyncSession, organization_id: UUID, created_by_id: UUID, **kwargs) -> WisdomFact:
        """Create a tier 0C (AI generated) fact."""
        return await WisdomFactFactory.create(
            session, organization_id, created_by_id,
            tier=WisdomTier.TIER_0C,
            confidence_score=0.7,
            **kwargs
        )


class DocumentFactory:
    """Factory for creating KnowledgeDocument records."""

    @staticmethod
    async def create(
        session: AsyncSession,
        organization_id: UUID,
        uploaded_by_id: UUID,
        title: str = None,
        file_name: str = None,
        document_type: DocumentType = DocumentType.POLICY_DOCUMENT,
        parsing_status: ParsingStatus = ParsingStatus.COMPLETED,
        department: str = None,
    ) -> KnowledgeDocument:
        """Create a knowledge document."""
        suffix = random_string(6)
        doc = KnowledgeDocument(
            organization_id=organization_id,
            uploaded_by_id=uploaded_by_id,
            title=title or f"Test Document {suffix}",
            file_name=file_name or f"test_doc_{suffix}.pdf",
            file_path=f"/uploads/{suffix}/test_doc.pdf",
            file_size=1024,
            document_type=document_type,
            parsing_status=parsing_status,
            department=department,
        )
        session.add(doc)
        await session.flush()
        return doc


class AutomationLogFactory:
    """Factory for creating AutomationLog records."""

    @staticmethod
    async def create(
        session: AsyncSession,
        rule_id: UUID,
        question_id: UUID,
        action: AutomationLogAction = AutomationLogAction.DELIVERED,
        similarity_score: float = 0.90,
        user_feedback: str = None,
    ) -> AutomationLog:
        """Create an automation log entry."""
        log = AutomationLog(
            rule_id=rule_id,
            question_id=question_id,
            action=action,
            similarity_score=similarity_score,
            user_feedback=user_feedback,
        )
        session.add(log)
        await session.flush()
        return log

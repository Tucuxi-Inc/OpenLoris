"""
Pytest configuration and fixtures for Loris backend tests.

Uses a real test database (loris_test) - NOT mocks.
The embedding service uses hash fallback when Ollama is unavailable,
which provides real semantic similarity for testing.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator
from uuid import UUID

# Add backend directory to Python path for module imports
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

# Set test environment before importing app modules
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://loris:password@localhost:5435/loris_test"

from app.core.config import settings
from app.core.database import get_db
from app.main import app as fastapi_app
from app.models.base import Base

# Import all models to ensure they're registered
from app import models as _models  # noqa: F401

# Test database URL - uses separate loris_test database
# Use postgres hostname (Docker network) when running inside container
# Use localhost:5435 when running outside Docker
import socket
def _get_db_host():
    """Determine correct database host based on environment."""
    try:
        socket.create_connection(("postgres", 5432), timeout=1).close()
        return "postgres:5432"  # Inside Docker network
    except (socket.error, socket.timeout):
        return "localhost:5435"  # Outside Docker, using exposed port

_db_host = _get_db_host()
TEST_DATABASE_URL = f"postgresql+asyncpg://loris:password@{_db_host}/loris_test"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for each test.

    Creates a new engine per test to avoid connection pooling issues.
    Rolls back after each test.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,
    )

    # Ensure tables exist (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,  # Disable autoflush to control when writes happen
    )

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def clean_db(db_session: AsyncSession) -> AsyncGenerator[None, None]:
    """
    Clean all data from database tables before test.

    Use this fixture when tests need a completely clean database state.
    """
    # Disable foreign key checks temporarily
    await db_session.execute(text("SET session_replication_role = 'replica'"))

    # Truncate all tables
    tables = [
        "turbo_attributions",
        "automation_logs",
        "automation_rule_embeddings",
        "automation_rules",
        "wisdom_embeddings",
        "wisdom_facts",
        "chunk_embeddings",
        "document_chunks",
        "extracted_fact_candidates",
        "knowledge_documents",
        "departments",
        "notifications",
        "question_messages",
        "reassignment_requests",
        "question_routings",
        "answers",
        "questions",
        "expert_subdomain_assignments",
        "subdomains",
        "slack_captures",
        "daily_metrics",
        "users",
        "organizations",
    ]
    for table in tables:
        try:
            await db_session.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
        except Exception:
            pass  # Table might not exist yet

    # Re-enable foreign key checks
    await db_session.execute(text("SET session_replication_role = 'origin'"))
    await db_session.commit()

    yield


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP client for API integration tests.

    Overrides the database dependency to use the test session.
    """
    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()


# =============================================================================
# Synchronous embedding generation for tests
# =============================================================================

def generate_test_embedding(text: str, dimension: int = 768) -> list[float]:
    """
    Generate a deterministic embedding using token hashing.

    This is a synchronous version of the embedding service's hash fallback,
    suitable for use in test fixtures without async complications.
    """
    import hashlib
    import math
    import re
    from collections import Counter

    # Tokenize: lowercase, split on non-alphanumeric, filter short tokens
    tokens = re.findall(r'[a-z]+', text.lower())
    tokens = [t for t in tokens if len(t) > 2]

    if not tokens:
        return [0.0] * dimension

    # Count token frequencies
    token_counts = Counter(tokens)

    # Build vector by hashing tokens to dimensions
    vector = [0.0] * dimension

    for token, count in token_counts.items():
        # Hash token to get primary dimension index
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        idx = h % dimension
        vector[idx] += count

        # Also add bigram-like features using a second hash
        h2 = int(hashlib.sha1(token.encode()).hexdigest(), 16)
        idx2 = h2 % dimension
        vector[idx2] += count * 0.5

    # L2-normalize to unit length
    norm = math.sqrt(sum(v * v for v in vector))
    if norm > 0:
        vector = [v / norm for v in vector]

    return vector


# =============================================================================
# Helper functions for creating test data
# =============================================================================

def hash_password(password: str) -> str:
    """Hash a password for test user creation."""
    return pwd_context.hash(password)


async def create_test_organization(
    session: AsyncSession,
    name: str = "Test Organization",
    slug: str = "test-org",
    settings: dict = None,
) -> "Organization":
    """Create a test organization."""
    from app.models.organization import Organization

    org = Organization(
        name=name,
        slug=slug,
        settings=settings or {"departments": [], "require_department": False},
    )
    session.add(org)
    await session.flush()
    return org


async def create_test_user(
    session: AsyncSession,
    organization_id: UUID,
    email: str = "test@example.com",
    name: str = "Test User",
    role: str = "business_user",
    password: str = "testpassword123",
) -> "User":
    """Create a test user."""
    from app.models.user import User, UserRole

    role_enum = UserRole(role)
    user = User(
        organization_id=organization_id,
        email=email,
        name=name,
        hashed_password=hash_password(password),
        role=role_enum,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def create_test_question(
    session: AsyncSession,
    organization_id: UUID,
    asked_by_id: UUID,
    text: str = "What is the company policy on remote work?",
    status: str = "submitted",
    category: str = None,
) -> "Question":
    """Create a test question."""
    from app.models.questions import Question, QuestionStatus

    question = Question(
        organization_id=organization_id,
        asked_by_id=asked_by_id,
        original_text=text,
        status=QuestionStatus(status),
        category=category,
    )
    session.add(question)
    await session.flush()
    return question


async def create_test_answer(
    session: AsyncSession,
    question_id: UUID,
    created_by_id: UUID,
    content: str = "Our remote work policy allows up to 3 days per week.",
    source: str = "expert",
) -> "Answer":
    """Create a test answer."""
    from app.models.answers import Answer, AnswerSource

    answer = Answer(
        question_id=question_id,
        created_by_id=created_by_id,
        content=content,
        source=AnswerSource(source),
    )
    session.add(answer)
    await session.flush()
    return answer


async def create_test_automation_rule(
    session: AsyncSession,
    organization_id: UUID,
    created_by_id: UUID,
    name: str = "Remote Work Policy",
    canonical_question: str = "What is the remote work policy?",
    canonical_answer: str = "Remote work is allowed up to 3 days per week.",
    similarity_threshold: float = 0.85,
    is_enabled: bool = True,
) -> "AutomationRule":
    """Create a test automation rule with embedding (using synchronous hash embedding)."""
    from app.models.automation import AutomationRule, AutomationRuleEmbedding

    rule = AutomationRule(
        organization_id=organization_id,
        created_by_id=created_by_id,
        name=name,
        canonical_question=canonical_question,
        canonical_answer=canonical_answer,
        similarity_threshold=similarity_threshold,
        is_enabled=is_enabled,
    )
    session.add(rule)
    await session.flush()

    # Generate embedding synchronously to avoid async complications
    embedding_data = generate_test_embedding(canonical_question)

    rule_embedding = AutomationRuleEmbedding(
        rule_id=rule.id,
        embedding_data=embedding_data,
        model_name="test-hash-embedding",
    )
    session.add(rule_embedding)
    await session.flush()

    return rule


async def create_test_wisdom_fact(
    session: AsyncSession,
    organization_id: UUID,
    created_by_id: UUID,
    content: str = "Remote work policy allows 3 days per week from home.",
    tier: str = "tier_0b",
    category: str = "HR",
) -> "WisdomFact":
    """Create a test wisdom fact with embedding (using synchronous hash embedding)."""
    from app.models.wisdom import WisdomFact, WisdomEmbedding, WisdomTier

    fact = WisdomFact(
        organization_id=organization_id,
        validated_by_id=created_by_id,  # WisdomFact uses validated_by_id
        content=content,
        tier=WisdomTier(tier),
        category=category,
        is_active=True,
    )
    session.add(fact)
    await session.flush()

    # Generate embedding synchronously
    embedding_data = generate_test_embedding(content)

    fact_embedding = WisdomEmbedding(
        wisdom_fact_id=fact.id,
        embedding_data=embedding_data,
        model_name="test-hash-embedding",
    )
    session.add(fact_embedding)
    await session.flush()

    return fact


# =============================================================================
# Fixtures for common test scenarios
# =============================================================================

@pytest_asyncio.fixture
async def test_org(db_session: AsyncSession, clean_db) -> "Organization":
    """Provide a clean test organization."""
    org = await create_test_organization(db_session)
    await db_session.commit()
    return org


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_org) -> "User":
    """Provide a test business user."""
    user = await create_test_user(
        db_session,
        organization_id=test_org.id,
        email="user@test.com",
        name="Test User",
        role="business_user",
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_expert(db_session: AsyncSession, test_org) -> "User":
    """Provide a test domain expert."""
    expert = await create_test_user(
        db_session,
        organization_id=test_org.id,
        email="expert@test.com",
        name="Test Expert",
        role="domain_expert",
    )
    await db_session.commit()
    return expert


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession, test_org) -> "User":
    """Provide a test admin user."""
    admin = await create_test_user(
        db_session,
        organization_id=test_org.id,
        email="admin@test.com",
        name="Test Admin",
        role="admin",
    )
    await db_session.commit()
    return admin


@pytest_asyncio.fixture
async def test_question(db_session: AsyncSession, test_org, test_user) -> "Question":
    """Provide a test question."""
    question = await create_test_question(
        db_session,
        organization_id=test_org.id,
        asked_by_id=test_user.id,
    )
    await db_session.commit()
    return question


@pytest_asyncio.fixture
async def test_automation_rule(db_session: AsyncSession, test_org, test_expert) -> "AutomationRule":
    """Provide a test automation rule with embedding."""
    rule = await create_test_automation_rule(
        db_session,
        organization_id=test_org.id,
        created_by_id=test_expert.id,
    )
    await db_session.commit()
    return rule


@pytest_asyncio.fixture
async def test_wisdom_fact(db_session: AsyncSession, test_org, test_expert) -> "WisdomFact":
    """Provide a test wisdom fact with embedding."""
    fact = await create_test_wisdom_fact(
        db_session,
        organization_id=test_org.id,
        created_by_id=test_expert.id,
    )
    await db_session.commit()
    return fact

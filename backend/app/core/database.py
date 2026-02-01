from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


# Create async engine
engine = create_async_engine(
    settings.database_url_async,
    echo=settings.DATABASE_ECHO,
    future=True,
    poolclass=NullPool if settings.ENVIRONMENT == "test" else None
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize all database tables and create default admin."""
    from app.models.base import Base
    # Import all models to ensure they're registered with SQLAlchemy
    import app.models  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables initialized successfully")

        # Create default admin user if none exists
        await create_default_admin()

        return True
    except Exception as e:
        print(f"Failed to initialize database tables: {e}")
        return False


async def create_default_admin():
    """Create default admin and seed demo data if database is empty."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select, func
    from passlib.context import CryptContext
    from app.models.user import User, UserRole
    from app.models.organization import Organization
    from app.models.subdomain import SubDomain, ExpertSubDomainAssignment
    from app.models.wisdom import WisdomFact, WisdomTier
    from app.models.questions import Question, QuestionStatus, QuestionPriority
    from app.models.answers import Answer, AnswerSource
    from app.models.automation import AutomationRule

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async with AsyncSessionLocal() as session:
        try:
            # Check if any admin user exists
            result = await session.execute(
                select(func.count(User.id)).where(User.role == UserRole.ADMIN)
            )
            admin_count = result.scalar()

            if admin_count > 0:
                print("Admin user already exists, skipping seed")
                return

            # Create default organization with settings
            org = Organization(
                name="Loris Demo Organization",
                slug="demo",
                settings={
                    "departments": ["Engineering", "Sales", "Marketing", "Finance", "HR", "Legal"],
                    "require_department": False,
                    "turbo_loris": {
                        "enabled": True,
                        "default_threshold": 0.75,
                        "threshold_options": [0.50, 0.75, 0.90]
                    }
                }
            )
            session.add(org)
            await session.flush()
            print("Created demo organization")

            # Create default admin user
            admin_user = User(
                email="admin@loris.local",
                hashed_password=pwd_context.hash("Password123"),
                name="Administrator",
                role=UserRole.ADMIN,
                organization_id=org.id,
                is_active=True
            )
            session.add(admin_user)
            await session.flush()
            print("Created default admin: admin@loris.local / Password123")

            # Create demo expert
            expert = User(
                email="expert@loris.local",
                hashed_password=pwd_context.hash("Password123"),
                name="Demo Expert",
                role=UserRole.DOMAIN_EXPERT,
                organization_id=org.id,
                is_active=True
            )
            session.add(expert)
            await session.flush()
            print("Created demo expert: expert@loris.local / Password123")

            # Create demo business user
            user = User(
                email="user@loris.local",
                hashed_password=pwd_context.hash("Password123"),
                name="Demo User",
                role=UserRole.BUSINESS_USER,
                organization_id=org.id,
                is_active=True
            )
            session.add(user)
            await session.flush()
            print("Created demo user: user@loris.local / Password123")

            # Create sub-domains
            subdomains_data = [
                ("General Questions", "General inquiries and common questions"),
                ("Policies & Procedures", "Company policies, procedures, and guidelines"),
                ("Technical Support", "Technical questions and IT support"),
            ]
            subdomains = []
            for name, desc in subdomains_data:
                sd = SubDomain(
                    organization_id=org.id,
                    name=name,
                    description=desc,
                    is_active=True,
                    sla_hours=24,
                )
                session.add(sd)
                subdomains.append(sd)
            await session.flush()
            print(f"Created {len(subdomains)} sub-domains")

            # Assign expert to all sub-domains
            for sd in subdomains:
                assignment = ExpertSubDomainAssignment(
                    expert_id=expert.id,
                    subdomain_id=sd.id,
                )
                session.add(assignment)
            await session.flush()

            # Create some knowledge facts
            facts_data = [
                ("Company office hours are Monday through Friday, 9 AM to 5 PM.", "General", WisdomTier.TIER_0A),
                ("Vacation requests must be submitted at least 2 weeks in advance.", "HR Policy", WisdomTier.TIER_0A),
                ("Password resets can be done via the IT self-service portal.", "IT Support", WisdomTier.TIER_0B),
                ("All expenses over $100 require manager approval.", "Finance", WisdomTier.TIER_0B),
                ("Remote work is allowed with manager approval.", "HR Policy", WisdomTier.TIER_0B),
            ]
            for content, category, tier in facts_data:
                fact = WisdomFact(
                    organization_id=org.id,
                    content=content,
                    category=category,
                    tier=tier,
                    confidence_score=0.9,
                    good_until_date=(datetime.now(timezone.utc) + timedelta(days=365)).date(),
                )
                session.add(fact)
            await session.flush()
            print(f"Created {len(facts_data)} knowledge facts")

            # Create an automation rule
            rule = AutomationRule(
                organization_id=org.id,
                name="Office Hours",
                canonical_question="What are the office hours?",
                canonical_answer="Our office hours are Monday through Friday, 9 AM to 5 PM. For emergencies outside these hours, please contact the on-call support line.",
                similarity_threshold=0.85,
                created_by_id=expert.id,
                good_until_date=(datetime.now(timezone.utc) + timedelta(days=180)).date(),
            )
            session.add(rule)
            await session.flush()
            print("Created 1 automation rule")

            # Create some sample questions
            questions_data = [
                ("How do I request time off?", QuestionStatus.RESOLVED, QuestionPriority.NORMAL),
                ("What is the process for expense reimbursement?", QuestionStatus.ANSWERED, QuestionPriority.NORMAL),
                ("Can I work from home on Fridays?", QuestionStatus.EXPERT_QUEUE, QuestionPriority.LOW),
                ("How do I reset my password?", QuestionStatus.EXPERT_QUEUE, QuestionPriority.HIGH),
            ]
            for text, status, priority in questions_data:
                q = Question(
                    organization_id=org.id,
                    asked_by_id=user.id,
                    original_text=text,
                    status=status,
                    priority=priority,
                    subdomain_id=subdomains[1].id if "time off" in text.lower() or "home" in text.lower() else subdomains[2].id,
                    created_at=datetime.now(timezone.utc) - timedelta(days=2),
                )
                session.add(q)
                await session.flush()

                # Add answers for answered/resolved questions
                if status in [QuestionStatus.ANSWERED, QuestionStatus.RESOLVED]:
                    answer = Answer(
                        question_id=q.id,
                        created_by_id=expert.id,
                        content="Thank you for your question. Based on our company policies, here is the guidance...\n\nPlease let me know if you need any additional information.",
                        source=AnswerSource.EXPERT,
                    )
                    session.add(answer)
                    if status == QuestionStatus.RESOLVED:
                        q.resolved_at = datetime.now(timezone.utc)
                        q.satisfaction_rating = 5

            await session.commit()
            print(f"Created {len(questions_data)} sample questions")
            print("\n" + "="*50)
            print("Demo data seeded successfully!")
            print("="*50)
            print("\nLogin accounts (all use password: Password123):")
            print("  Admin:  admin@loris.local")
            print("  Expert: expert@loris.local")
            print("  User:   user@loris.local")
            print("="*50 + "\n")

        except Exception as e:
            await session.rollback()
            print(f"Failed to create default admin and seed data: {e}")
            import traceback
            traceback.print_exc()


async def test_connection():
    """Test database connection."""
    try:
        async with engine.connect() as connection:
            from sqlalchemy import text
            await connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

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
    """Create default admin user if no admin exists."""
    from sqlalchemy import select, func
    from passlib.context import CryptContext
    from app.models.user import User, UserRole
    from app.models.organization import Organization

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async with AsyncSessionLocal() as session:
        try:
            # Check if any admin user exists
            result = await session.execute(
                select(func.count(User.id)).where(User.role == UserRole.ADMIN)
            )
            admin_count = result.scalar()

            if admin_count > 0:
                print("Admin user already exists, skipping default admin creation")
                return

            # Check if default org exists, create if not
            result = await session.execute(
                select(Organization).where(Organization.slug == "default")
            )
            org = result.scalar_one_or_none()

            if not org:
                org = Organization(
                    name="Default Organization",
                    slug="default",
                    settings={
                        "departments": [],
                        "require_department": False,
                        "gdrive_sync_enabled": False,
                        "moltenloris_enabled": False
                    }
                )
                session.add(org)
                await session.flush()
                print("Created default organization")

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
            await session.commit()
            print("Created default admin user: admin@loris.local / Password123")

        except Exception as e:
            await session.rollback()
            print(f"Failed to create default admin: {e}")


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

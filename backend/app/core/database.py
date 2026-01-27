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
    """Initialize all database tables."""
    from app.models.base import Base
    # Import all models to ensure they're registered with SQLAlchemy
    import app.models  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables initialized successfully")
        return True
    except Exception as e:
        print(f"Failed to initialize database tables: {e}")
        return False


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

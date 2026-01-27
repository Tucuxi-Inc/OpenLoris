from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.config import settings
from app.core.database import engine, test_connection, init_db

# Import all models to ensure SQLAlchemy relationships are properly configured
import app.models  # noqa: F401

from app.api.v1 import health, auth, questions, automation
from app.api.v1 import settings as settings_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting Loris API...")

    try:
        print("Testing database connection...")

        if await test_connection():
            print("Database connection successful")
            await init_db()
        else:
            print("Database connection failed, skipping table initialization")

    except Exception as e:
        print(f"Database initialization failed: {e}")

    print("Loris API started successfully")

    yield

    # Shutdown
    print("Shutting down Loris API...")
    try:
        await engine.dispose()
    except Exception as e:
        print(f"Engine disposal failed: {e}")
    print("Loris API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="Loris API",
        description="Intelligent Q&A Platform - Connecting Business Users with Domain Experts",
        version="0.1.0",
        docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(questions.router, prefix="/api/v1/questions", tags=["questions"])
    app.include_router(automation.router, prefix="/api/v1/automation", tags=["automation"])
    app.include_router(settings_api.router, prefix="/api/v1/settings", tags=["settings"])

    return app


# Create the FastAPI application instance
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )

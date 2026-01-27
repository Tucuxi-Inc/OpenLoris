from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.services.ai_provider_service import ai_provider_service

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "service": "loris-api"}


@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check including database and AI provider"""
    health = {
        "status": "healthy",
        "service": "loris-api",
        "checks": {}
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        health["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Check AI provider info
    try:
        ai_info = ai_provider_service.get_provider_info()
        health["checks"]["ai_provider"] = {
            "status": "configured",
            "provider": ai_info["provider"],
            "model": ai_info["model"],
            "data_locality": ai_info["data_locality"]
        }
    except Exception as e:
        health["checks"]["ai_provider"] = {"status": "error", "error": str(e)}

    return health

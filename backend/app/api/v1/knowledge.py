"""
Knowledge API — CRUD for WisdomFacts, semantic search, gap analysis, stats.
Expert-only routes (domain_expert or admin).
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.wisdom import WisdomTier
from app.api.v1.auth import get_current_active_expert
from app.services.knowledge_service import knowledge_service

router = APIRouter()


# ---------- Schemas ----------

class FactCreate(BaseModel):
    content: str
    summary: Optional[str] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    tier: Optional[str] = "pending"
    confidence_score: Optional[float] = None
    importance: int = 5
    jurisdiction: Optional[str] = None
    tags: Optional[List[str]] = None
    good_until_date: Optional[str] = None
    is_perpetual: bool = False


class FactFromAnswerCreate(BaseModel):
    question_id: UUID
    domain: Optional[str] = None
    category: Optional[str] = None
    tier: Optional[str] = "tier_0b"
    importance: int = 7
    tags: Optional[List[str]] = None


class FactUpdate(BaseModel):
    content: Optional[str] = None
    summary: Optional[str] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    tier: Optional[str] = None
    confidence_score: Optional[float] = None
    importance: Optional[int] = None
    jurisdiction: Optional[str] = None
    tags: Optional[List[str]] = None
    good_until_date: Optional[str] = None
    is_perpetual: Optional[bool] = None


class GapAnalysisRequest(BaseModel):
    text: str


# ---------- Routes ----------

@router.get("/facts")
async def list_facts(
    domain: Optional[str] = None,
    category: Optional[str] = None,
    tier: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """List wisdom facts with filters and pagination."""
    return await knowledge_service.list_facts(
        db=db,
        organization_id=current_user.organization_id,
        domain=domain,
        category=category,
        tier=tier,
        page=page,
        page_size=page_size,
    )


@router.get("/facts/{fact_id}")
async def get_fact(
    fact_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Get a single wisdom fact."""
    fact = await knowledge_service.get_fact(db, fact_id)
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    return knowledge_service._fact_to_dict(fact)


@router.post("/facts", status_code=status.HTTP_201_CREATED)
async def create_fact(
    data: FactCreate,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Create a new wisdom fact."""
    gud = None
    if data.good_until_date:
        try:
            gud = date.fromisoformat(data.good_until_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid good_until_date format")

    fact = await knowledge_service.create_fact(
        db=db,
        organization_id=current_user.organization_id,
        content=data.content,
        expert_user_id=current_user.id,
        summary=data.summary,
        domain=data.domain,
        category=data.category,
        tier=WisdomTier(data.tier) if data.tier else WisdomTier.PENDING,
        confidence_score=data.confidence_score,
        importance=data.importance,
        jurisdiction=data.jurisdiction,
        tags=data.tags,
        good_until_date=gud,
        is_perpetual=data.is_perpetual,
    )
    return knowledge_service._fact_to_dict(fact)


@router.post("/facts/from-answer", status_code=status.HTTP_201_CREATED)
async def create_fact_from_answer(
    data: FactFromAnswerCreate,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Create a wisdom fact from an answered question."""
    fact = await knowledge_service.create_fact_from_answer(
        db=db,
        question_id=data.question_id,
        expert_user_id=current_user.id,
        domain=data.domain,
        category=data.category,
        tier=WisdomTier(data.tier) if data.tier else WisdomTier.TIER_0B,
        importance=data.importance,
        tags=data.tags,
    )
    if not fact:
        raise HTTPException(status_code=404, detail="Question or answer not found")
    return knowledge_service._fact_to_dict(fact)


@router.put("/facts/{fact_id}")
async def update_fact(
    fact_id: UUID,
    data: FactUpdate,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Update a wisdom fact. Regenerates embedding if content changes."""
    updates = data.model_dump(exclude_none=True)

    # Convert good_until_date string to date
    if "good_until_date" in updates:
        try:
            updates["good_until_date"] = date.fromisoformat(updates["good_until_date"])
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid good_until_date format")

    # Convert tier string to enum
    if "tier" in updates:
        try:
            updates["tier"] = WisdomTier(updates["tier"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tier value")

    fact = await knowledge_service.update_fact(db, fact_id, updates)
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    return knowledge_service._fact_to_dict(fact)


@router.delete("/facts/{fact_id}")
async def archive_fact(
    fact_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Soft-archive a wisdom fact."""
    if not await knowledge_service.archive_fact(db, fact_id):
        raise HTTPException(status_code=404, detail="Fact not found")
    return {"message": "Fact archived"}


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Semantic search over the knowledge base."""
    results = await knowledge_service.search(
        db=db,
        organization_id=current_user.organization_id,
        query=q,
        limit=limit,
    )
    return {"results": results, "total": len(results)}


@router.post("/analyze-gaps")
async def analyze_gaps(
    data: GapAnalysisRequest,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Run gap analysis on arbitrary text."""
    result = await knowledge_service.run_gap_analysis(
        question_text=data.text,
        organization_id=current_user.organization_id,
        db=db,
    )
    if result is None:
        return {"message": "Gap analysis unavailable", "matching_facts": [], "coverage_percentage": 0}
    return result


@router.get("/stats")
async def get_knowledge_stats(
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Knowledge base statistics."""
    return await knowledge_service.get_stats(db, current_user.organization_id)


@router.get("/expiring")
async def get_expiring_facts(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Facts expiring within N days."""
    facts = await knowledge_service.get_expiring_facts(
        db=db,
        organization_id=current_user.organization_id,
        days_ahead=days,
    )
    return {"facts": facts, "total": len(facts)}

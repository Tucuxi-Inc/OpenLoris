"""Analytics REST API — KPI overview, question trends, automation performance, knowledge coverage."""

from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_active_expert
from app.services.analytics_service import analytics_service

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────

class OverviewResponse(BaseModel):
    total_questions: int
    total_resolved: int
    automation_rate: float
    avg_response_time_seconds: Optional[float]
    avg_resolution_time_seconds: Optional[float]
    avg_satisfaction: Optional[float]
    period_question_count: int
    prev_period_question_count: int
    period: str


class DailyVolume(BaseModel):
    date: str
    total: int
    auto_answered: int
    expert_answered: int


class QuestionTrendsResponse(BaseModel):
    daily_volumes: List[DailyVolume]
    status_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]


class RulePerformance(BaseModel):
    rule_id: str
    name: str
    times_triggered: int
    times_accepted: int
    times_rejected: int
    acceptance_rate: Optional[float]
    is_enabled: bool


class DailyAutomationTrend(BaseModel):
    date: str
    delivered: int
    accepted: int
    rejected: int


class AutomationPerformanceResponse(BaseModel):
    total_triggers: int
    total_accepted: int
    total_rejected: int
    overall_acceptance_rate: Optional[float]
    rules: List[RulePerformance]
    daily_trend: List[DailyAutomationTrend]


class KnowledgeCoverageResponse(BaseModel):
    total_facts: int
    by_tier: Dict[str, int]
    expiring_soon: int
    recently_added: int
    avg_confidence: Optional[float]


class ExpertStats(BaseModel):
    expert_name: str
    questions_answered: int
    avg_response_time_seconds: Optional[float]
    avg_satisfaction: Optional[float]


class ExpertPerformanceResponse(BaseModel):
    experts: List[ExpertStats]


# ── Endpoints ────────────────────────────────────────────────────────

VALID_PERIODS = {"7d", "30d", "90d", "all"}


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, or all"),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """High-level KPI overview for the analytics dashboard."""
    if period not in VALID_PERIODS:
        period = "30d"
    data = await analytics_service.get_overview(
        db=db, organization_id=current_user.organization_id, period=period
    )
    return OverviewResponse(**data)


@router.get("/questions", response_model=QuestionTrendsResponse)
async def get_question_trends(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, or all"),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Question volume trends and distributions."""
    if period not in VALID_PERIODS:
        period = "30d"
    data = await analytics_service.get_question_trends(
        db=db, organization_id=current_user.organization_id, period=period
    )
    return QuestionTrendsResponse(**data)


@router.get("/automation", response_model=AutomationPerformanceResponse)
async def get_automation_performance(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, or all"),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Automation rule performance and trends."""
    if period not in VALID_PERIODS:
        period = "30d"
    data = await analytics_service.get_automation_performance(
        db=db, organization_id=current_user.organization_id, period=period
    )
    return AutomationPerformanceResponse(**data)


@router.get("/knowledge", response_model=KnowledgeCoverageResponse)
async def get_knowledge_coverage(
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Knowledge base coverage metrics."""
    data = await analytics_service.get_knowledge_coverage(
        db=db, organization_id=current_user.organization_id
    )
    return KnowledgeCoverageResponse(**data)


@router.get("/experts", response_model=ExpertPerformanceResponse)
async def get_expert_performance(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, or all"),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Expert performance leaderboard."""
    if period not in VALID_PERIODS:
        period = "30d"
    data = await analytics_service.get_expert_performance(
        db=db, organization_id=current_user.organization_id, period=period
    )
    return ExpertPerformanceResponse(**data)

"""
Automation API endpoints - CRUD for automation rules + create-from-answer flow.

Expert-only endpoints for managing automation rules that power auto-answering.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.automation import AutomationRule, AutomationRuleEmbedding, AutomationLog
from app.models.answers import Answer
from app.models.questions import Question
from app.models.user import User
from app.api.v1.auth import get_current_active_expert
from app.services.automation_service import automation_service
from app.services.embedding_service import embedding_service

router = APIRouter()


# Schemas
class AutomationRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    canonical_question: str
    canonical_answer: str
    similarity_threshold: float = 0.85
    category_filter: Optional[str] = None
    exclude_keywords: Optional[List[str]] = None
    good_until_date: Optional[date] = None


class AutomationRuleFromAnswer(BaseModel):
    question_id: UUID
    name: str
    description: Optional[str] = None
    similarity_threshold: float = 0.85
    category_filter: Optional[str] = None
    exclude_keywords: Optional[List[str]] = None
    good_until_date: Optional[date] = None


class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    canonical_answer: Optional[str] = None
    similarity_threshold: Optional[float] = None
    category_filter: Optional[str] = None
    exclude_keywords: Optional[List[str]] = None
    good_until_date: Optional[date] = None
    is_enabled: Optional[bool] = None


class AutomationRuleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    canonical_question: str
    canonical_answer: str
    similarity_threshold: float
    category_filter: Optional[str]
    exclude_keywords: List[str]
    good_until_date: Optional[date]
    is_enabled: bool
    times_triggered: int
    times_accepted: int
    times_rejected: int
    organization_id: UUID
    created_by_id: UUID
    source_question_id: Optional[UUID]

    class Config:
        from_attributes = True


class AutomationRuleListResponse(BaseModel):
    items: List[AutomationRuleResponse]
    total: int
    page: int
    page_size: int


# Endpoints

@router.get("/rules", response_model=AutomationRuleListResponse)
async def list_automation_rules(
    is_enabled: Optional[bool] = None,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """List automation rules for the expert's organization."""
    query = select(AutomationRule).where(
        AutomationRule.organization_id == current_user.organization_id
    )

    if is_enabled is not None:
        query = query.where(AutomationRule.is_enabled == is_enabled)
    if category:
        query = query.where(AutomationRule.category_filter == category)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = query.order_by(AutomationRule.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    rules = result.scalars().all()

    return AutomationRuleListResponse(
        items=rules, total=total, page=page, page_size=page_size
    )


@router.get("/rules/{rule_id}", response_model=AutomationRuleResponse)
async def get_automation_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific automation rule."""
    result = await db.execute(
        select(AutomationRule).where(
            AutomationRule.id == rule_id,
            AutomationRule.organization_id == current_user.organization_id,
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")

    return rule


@router.post("/rules", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_automation_rule(
    rule_data: AutomationRuleCreate,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Create a new automation rule with a canonical Q&A pair."""
    rule = AutomationRule(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        name=rule_data.name,
        description=rule_data.description,
        canonical_question=rule_data.canonical_question,
        canonical_answer=rule_data.canonical_answer,
        similarity_threshold=rule_data.similarity_threshold,
        category_filter=rule_data.category_filter,
        exclude_keywords=rule_data.exclude_keywords or [],
        good_until_date=rule_data.good_until_date,
        is_enabled=True,
    )
    db.add(rule)
    await db.flush()

    # Generate embedding for the canonical question
    embedding_data = await embedding_service.generate(rule_data.canonical_question)

    rule_embedding = AutomationRuleEmbedding(
        rule_id=rule.id,
        embedding_data=embedding_data,
        model_name=embedding_service.model_name,
    )
    db.add(rule_embedding)

    await db.commit()
    await db.refresh(rule)

    return rule


@router.post("/rules/from-answer", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule_from_answer(
    rule_data: AutomationRuleFromAnswer,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Create an automation rule from an existing answered question."""
    # Load question
    q_result = await db.execute(
        select(Question).where(
            Question.id == rule_data.question_id,
            Question.organization_id == current_user.organization_id,
        )
    )
    question = q_result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Load answer
    a_result = await db.execute(
        select(Answer).where(Answer.question_id == rule_data.question_id)
    )
    answer = a_result.scalar_one_or_none()
    if not answer:
        raise HTTPException(status_code=400, detail="Question has no answer")

    rule = await automation_service.create_rule_from_answer(
        db=db,
        question=question,
        answer=answer,
        name=rule_data.name,
        description=rule_data.description,
        similarity_threshold=rule_data.similarity_threshold,
        category_filter=rule_data.category_filter,
        exclude_keywords=rule_data.exclude_keywords,
        good_until_date=rule_data.good_until_date,
    )

    return rule


@router.put("/rules/{rule_id}", response_model=AutomationRuleResponse)
async def update_automation_rule(
    rule_id: UUID,
    rule_data: AutomationRuleUpdate,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Update an automation rule."""
    result = await db.execute(
        select(AutomationRule).where(
            AutomationRule.id == rule_id,
            AutomationRule.organization_id == current_user.organization_id,
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")

    if rule_data.name is not None:
        rule.name = rule_data.name
    if rule_data.description is not None:
        rule.description = rule_data.description
    if rule_data.canonical_answer is not None:
        rule.canonical_answer = rule_data.canonical_answer
    if rule_data.similarity_threshold is not None:
        rule.similarity_threshold = rule_data.similarity_threshold
    if rule_data.category_filter is not None:
        rule.category_filter = rule_data.category_filter
    if rule_data.exclude_keywords is not None:
        rule.exclude_keywords = rule_data.exclude_keywords
    if rule_data.good_until_date is not None:
        rule.good_until_date = rule_data.good_until_date
    if rule_data.is_enabled is not None:
        rule.is_enabled = rule_data.is_enabled

    await db.commit()
    await db.refresh(rule)

    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Delete an automation rule and its embedding."""
    result = await db.execute(
        select(AutomationRule).where(
            AutomationRule.id == rule_id,
            AutomationRule.organization_id == current_user.organization_id,
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")

    # Delete embedding first (cascade should handle this, but be explicit)
    emb_result = await db.execute(
        select(AutomationRuleEmbedding).where(AutomationRuleEmbedding.rule_id == rule_id)
    )
    embedding = emb_result.scalar_one_or_none()
    if embedding:
        await db.delete(embedding)

    await db.delete(rule)
    await db.commit()

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.questions import Question, QuestionStatus, QuestionPriority, QuestionMessage, MessageType
from app.models.answers import Answer, AnswerSource
from app.models.user import User
from app.api.v1.auth import get_current_user, get_current_active_expert
from app.services.automation_service import automation_service

router = APIRouter()


# Schemas
class QuestionCreate(BaseModel):
    text: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[QuestionPriority] = QuestionPriority.NORMAL


class QuestionResponse(BaseModel):
    id: UUID
    original_text: str
    category: Optional[str]
    tags: List[str]
    status: QuestionStatus
    priority: QuestionPriority
    asked_by_id: UUID
    assigned_to_id: Optional[UUID]
    automation_rule_id: Optional[UUID] = None
    created_at: datetime
    first_response_at: Optional[datetime]
    resolved_at: Optional[datetime]
    satisfaction_rating: Optional[int]

    class Config:
        from_attributes = True


class QuestionDetail(QuestionResponse):
    gap_analysis: Optional[dict]
    auto_answer_accepted: Optional[bool]
    rejection_reason: Optional[str]


class AnswerCreate(BaseModel):
    content: str
    source: AnswerSource = AnswerSource.EXPERT
    cited_knowledge: Optional[List[dict]] = None


class AnswerResponse(BaseModel):
    id: UUID
    question_id: UUID
    content: str
    source: AnswerSource
    created_by_id: UUID
    created_at: datetime
    delivered_at: Optional[datetime]

    class Config:
        from_attributes = True


class QuestionSubmitResponse(BaseModel):
    """Response for question submission - includes auto-answer if matched."""
    question: QuestionResponse
    auto_answered: bool = False
    auto_answer: Optional[AnswerResponse] = None
    automation_similarity: Optional[float] = None


class FeedbackCreate(BaseModel):
    rating: int  # 1-5
    comment: Optional[str] = None


class ClarificationRequest(BaseModel):
    message: str


class QuestionListResponse(BaseModel):
    items: List[QuestionResponse]
    total: int
    page: int
    page_size: int


# Business User Endpoints
@router.post("/", response_model=QuestionSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_question(
    question_data: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit a new question. Checks automation rules for instant answers."""
    import logging
    logger = logging.getLogger(__name__)

    question = Question(
        organization_id=current_user.organization_id,
        asked_by_id=current_user.id,
        original_text=question_data.text,
        category=question_data.category,
        tags=question_data.tags or [],
        priority=question_data.priority,
        status=QuestionStatus.SUBMITTED
    )

    db.add(question)
    await db.commit()
    await db.refresh(question)

    # Check automation rules for a matching answer
    try:
        check_result = await automation_service.check_for_automation(
            db=db,
            question_text=question_data.text,
            organization_id=current_user.organization_id,
            category=question_data.category,
        )

        if check_result.action == "auto_answer" and check_result.match:
            # Deliver auto-answer (TransWarp)
            answer = await automation_service.deliver_auto_answer(
                db=db,
                question=question,
                match=check_result.match,
            )
            await db.refresh(question)
            return QuestionSubmitResponse(
                question=question,
                auto_answered=True,
                auto_answer=answer,
                automation_similarity=check_result.match.similarity,
            )

        elif check_result.action == "suggest_to_expert" and check_result.match:
            # Medium confidence - store suggestion, queue for expert
            question.status = QuestionStatus.EXPERT_QUEUE
            question.gap_analysis = {
                "automation_suggestion": {
                    "rule_id": str(check_result.match.rule_id),
                    "rule_name": check_result.match.rule_name,
                    "similarity": check_result.match.similarity,
                    "suggested_answer": check_result.match.canonical_answer,
                }
            }
            await db.commit()
            await db.refresh(question)

        else:
            # No match - queue for expert
            question.status = QuestionStatus.EXPERT_QUEUE
            await db.commit()
            await db.refresh(question)

    except Exception as e:
        # Automation check failed - don't block question submission
        logger.warning(f"Automation check failed for question {question.id}: {e}")
        question.status = QuestionStatus.EXPERT_QUEUE
        await db.commit()
        await db.refresh(question)

    return QuestionSubmitResponse(question=question)


@router.get("/", response_model=QuestionListResponse)
async def list_my_questions(
    status: Optional[QuestionStatus] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List questions asked by the current user"""
    query = select(Question).where(Question.asked_by_id == current_user.id)

    if status:
        query = query.where(Question.status == status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Get paginated results
    query = query.order_by(Question.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    questions = result.scalars().all()

    return QuestionListResponse(
        items=questions,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{question_id}", response_model=QuestionDetail)
async def get_question(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get question details"""
    query = select(Question).where(Question.id == question_id)

    # Non-experts can only see their own questions
    if not current_user.is_expert:
        query = query.where(Question.asked_by_id == current_user.id)

    result = await db.execute(query)
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return question


@router.post("/{question_id}/feedback")
async def submit_feedback(
    question_id: UUID,
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit feedback on an answered question"""
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.asked_by_id == current_user.id
        )
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.status not in (QuestionStatus.ANSWERED, QuestionStatus.AUTO_ANSWERED, QuestionStatus.RESOLVED):
        raise HTTPException(status_code=400, detail="Question has not been answered yet")

    question.satisfaction_rating = feedback.rating

    if question.status == QuestionStatus.AUTO_ANSWERED:
        # Accepting auto-answer via feedback
        await automation_service.handle_user_feedback(
            db=db, question=question, accepted=True
        )
    elif question.status == QuestionStatus.ANSWERED:
        question.status = QuestionStatus.RESOLVED
        question.resolved_at = datetime.now(timezone.utc)
        await db.commit()
    else:
        await db.commit()

    return {"message": "Feedback submitted successfully"}


@router.post("/{question_id}/accept-auto")
async def accept_auto_answer(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Accept an auto-answer, marking the question as resolved."""
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.asked_by_id == current_user.id
        )
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.status != QuestionStatus.AUTO_ANSWERED:
        raise HTTPException(status_code=400, detail="Question is not auto-answered")

    await automation_service.handle_user_feedback(
        db=db, question=question, accepted=True
    )

    return {"message": "Auto-answer accepted"}


@router.post("/{question_id}/request-human")
async def request_human_review(
    question_id: UUID,
    clarification: ClarificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject auto-answer and request human review."""
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.asked_by_id == current_user.id
        )
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.status != QuestionStatus.AUTO_ANSWERED:
        raise HTTPException(status_code=400, detail="Question is not auto-answered")

    await automation_service.handle_user_feedback(
        db=db,
        question=question,
        accepted=False,
        rejection_reason=clarification.message,
    )

    return {"message": "Human review requested"}


# Expert Endpoints
@router.get("/queue/pending", response_model=QuestionListResponse)
async def get_expert_queue(
    category: Optional[str] = None,
    priority: Optional[QuestionPriority] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """Get questions in the expert queue"""
    query = select(Question).where(
        Question.organization_id == current_user.organization_id,
        Question.status.in_([
            QuestionStatus.EXPERT_QUEUE,
            QuestionStatus.HUMAN_REQUESTED,
            QuestionStatus.NEEDS_CLARIFICATION
        ])
    )

    if category:
        query = query.where(Question.category == category)
    if priority:
        query = query.where(Question.priority == priority)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Order by priority and creation time
    query = query.order_by(
        Question.priority.desc(),
        Question.created_at.asc()
    )
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    questions = result.scalars().all()

    return QuestionListResponse(
        items=questions,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/{question_id}/assign")
async def assign_question(
    question_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """Assign a question to the current expert"""
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.organization_id == current_user.organization_id
        )
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    question.assigned_to_id = current_user.id
    question.status = QuestionStatus.IN_PROGRESS

    await db.commit()

    return {"message": "Question assigned successfully"}


@router.post("/{question_id}/answer", response_model=AnswerResponse)
async def submit_answer(
    question_id: UUID,
    answer_data: AnswerCreate,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """Submit an answer to a question"""
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.organization_id == current_user.organization_id
        )
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check for existing answer with explicit query (avoids lazy loading in async)
    existing_answer = (await db.execute(
        select(Answer).where(Answer.question_id == question_id)
    )).scalar_one_or_none()

    if existing_answer:
        raise HTTPException(status_code=400, detail="Question already has an answer")

    # Create answer
    answer = Answer(
        question_id=question_id,
        created_by_id=current_user.id,
        content=answer_data.content,
        source=answer_data.source,
        cited_knowledge=answer_data.cited_knowledge or [],
        delivered_at=datetime.now(timezone.utc)
    )

    db.add(answer)

    # Update question status
    question.status = QuestionStatus.ANSWERED
    question.first_response_at = datetime.now(timezone.utc)
    if question.created_at:
        question.response_time_seconds = int(
            (datetime.now(timezone.utc) - question.created_at).total_seconds()
        )

    await db.commit()
    await db.refresh(answer)

    return answer


@router.post("/{question_id}/request-clarification")
async def request_clarification(
    question_id: UUID,
    request: ClarificationRequest,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """Request clarification from the question asker"""
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.organization_id == current_user.organization_id
        )
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Create clarification message
    message = QuestionMessage(
        question_id=question_id,
        user_id=current_user.id,
        message_type=MessageType.CLARIFICATION_REQUEST,
        content=request.message
    )

    db.add(message)
    question.status = QuestionStatus.NEEDS_CLARIFICATION

    await db.commit()

    return {"message": "Clarification requested"}

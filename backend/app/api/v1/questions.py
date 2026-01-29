from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.questions import (
    Question, QuestionStatus, QuestionPriority, QuestionMessage, MessageType,
    ReassignmentRequest, ReassignmentStatus,
)
from app.models.answers import Answer, AnswerSource
from app.models.user import User
from app.models.notifications import NotificationType
from app.api.v1.auth import get_current_user, get_current_active_expert, get_current_admin
from app.models.automation import AutomationRule
from app.services.automation_service import automation_service
from app.services.knowledge_service import knowledge_service
from app.services.notification_service import notification_service
from app.services.subdomain_service import subdomain_service
from app.services.turbo_service import turbo_service
from app.models.subdomain import ExpertSubDomainAssignment
from app.models.turbo import TurboAttribution

router = APIRouter()


# Schemas
class QuestionCreate(BaseModel):
    text: str
    category: Optional[str] = None
    department: Optional[str] = None
    subdomain_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    priority: Optional[QuestionPriority] = QuestionPriority.NORMAL
    # Turbo Loris mode
    turbo_mode: bool = False
    turbo_threshold: float = 0.75


class QuestionResponse(BaseModel):
    id: UUID
    original_text: str
    category: Optional[str]
    department: Optional[str] = None
    subdomain_id: Optional[UUID] = None
    ai_classified_subdomain: bool = False
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
    # Turbo fields
    turbo_mode: bool = False
    turbo_threshold: Optional[float] = None
    turbo_confidence: Optional[float] = None

    class Config:
        from_attributes = True


class TurboAttributionResponse(BaseModel):
    id: UUID
    source_type: str
    source_id: UUID
    display_name: str
    contributor_name: Optional[str] = None
    contribution_type: str
    confidence_score: float
    semantic_similarity: float

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
    # Turbo Loris response
    turbo_answered: bool = False
    turbo_confidence: Optional[float] = None
    turbo_attributions: List[TurboAttributionResponse] = []


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


# Reassignment schemas (defined here to be available before routes)
class ReassignmentRequestCreate(BaseModel):
    suggested_subdomain_id: UUID
    reason: str


class ReassignmentRequestResponse(BaseModel):
    id: UUID
    question_id: UUID
    requested_by_id: UUID
    requested_by_name: Optional[str] = None
    current_subdomain_id: Optional[UUID]
    current_subdomain_name: Optional[str] = None
    suggested_subdomain_id: UUID
    suggested_subdomain_name: Optional[str] = None
    reason: str
    status: ReassignmentStatus
    reviewed_by_id: Optional[UUID]
    admin_notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReassignmentReviewRequest(BaseModel):
    approved: bool
    admin_notes: Optional[str] = None


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

    # Resolve sub-domain: explicit, or AI classification
    resolved_subdomain_id = question_data.subdomain_id
    ai_classified = False
    if not resolved_subdomain_id:
        try:
            resolved_subdomain_id = await subdomain_service.classify_question(
                db, question_data.text, current_user.organization_id
            )
            if resolved_subdomain_id:
                ai_classified = True
        except Exception as cls_err:
            logger.debug(f"Sub-domain classification skipped: {cls_err}")

    question = Question(
        organization_id=current_user.organization_id,
        asked_by_id=current_user.id,
        original_text=question_data.text,
        category=question_data.category,
        department=question_data.department,
        subdomain_id=resolved_subdomain_id,
        ai_classified_subdomain=ai_classified,
        tags=question_data.tags or [],
        priority=question_data.priority,
        status=QuestionStatus.SUBMITTED,
        turbo_mode=question_data.turbo_mode,
        turbo_threshold=question_data.turbo_threshold if question_data.turbo_mode else None,
    )

    db.add(question)
    await db.commit()
    await db.refresh(question)

    # TURBO MODE: Try to generate instant answer from knowledge base
    if question_data.turbo_mode:
        try:
            turbo_result = await turbo_service.attempt_turbo_answer(
                question=question,
                threshold=question_data.turbo_threshold,
                db=db,
            )

            if turbo_result.success and turbo_result.answer_content:
                # Deliver Turbo answer
                answer = await turbo_service.deliver_turbo_answer(
                    db=db,
                    question=question,
                    turbo_result=turbo_result,
                )
                await db.refresh(question)

                # Get attributions for response
                attributions = await turbo_service.get_attributions(db, question.id)

                return QuestionSubmitResponse(
                    question=question,
                    turbo_answered=True,
                    turbo_confidence=turbo_result.confidence,
                    turbo_attributions=[
                        TurboAttributionResponse(
                            id=UUID(a["id"]),
                            source_type=a["source_type"],
                            source_id=UUID(a["source_id"]),
                            display_name=a["display_name"],
                            contributor_name=a.get("contributor_name"),
                            contribution_type=a["contribution_type"],
                            confidence_score=a["confidence_score"],
                            semantic_similarity=a["semantic_similarity"],
                        )
                        for a in attributions
                    ],
                    auto_answer=AnswerResponse(
                        id=answer.id,
                        question_id=answer.question_id,
                        content=answer.content,
                        source=answer.source,
                        created_by_id=answer.created_by_id,
                        created_at=answer.created_at,
                        delivered_at=answer.delivered_at,
                    ),
                )
            else:
                # Turbo failed - fall through to standard flow
                logger.info(f"Turbo mode failed for question {question.id}: {turbo_result.message}")

        except Exception as turbo_err:
            logger.warning(f"Turbo mode error for question {question.id}: {turbo_err}")
            # Fall through to standard automation check

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
            # Notify user of auto-answer
            try:
                await notification_service.notify_auto_answer(
                    db=db,
                    user_id=current_user.id,
                    organization_id=current_user.organization_id,
                    question_id=question.id,
                    question_text=question_data.text,
                )
            except Exception:
                pass  # Non-blocking
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
            # Run knowledge gap analysis (non-blocking)
            try:
                ka = await knowledge_service.run_gap_analysis(
                    question_data.text, current_user.organization_id, db
                )
                if ka:
                    question.gap_analysis["knowledge_analysis"] = ka
            except Exception as gap_err:
                logger.debug(f"Gap analysis skipped: {gap_err}")
            await db.commit()
            await db.refresh(question)

        else:
            # No match - queue for expert
            question.status = QuestionStatus.EXPERT_QUEUE
            # Run knowledge gap analysis (non-blocking)
            try:
                ka = await knowledge_service.run_gap_analysis(
                    question_data.text, current_user.organization_id, db
                )
                if ka:
                    question.gap_analysis = {"knowledge_analysis": ka}
            except Exception as gap_err:
                logger.debug(f"Gap analysis skipped: {gap_err}")
            await db.commit()
            await db.refresh(question)

    except Exception as e:
        # Automation check failed - don't block question submission
        logger.warning(f"Automation check failed for question {question.id}: {e}")
        question.status = QuestionStatus.EXPERT_QUEUE
        await db.commit()
        await db.refresh(question)

    # Route to sub-domain experts if applicable
    if question.status == QuestionStatus.EXPERT_QUEUE and question.subdomain_id:
        try:
            await subdomain_service.route_question_to_subdomain(
                db, question, question.subdomain_id
            )
        except Exception as route_err:
            logger.debug(f"Sub-domain routing skipped: {route_err}")

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


# ------------------------------------------------------------------
# Reassignment workflow - Admin endpoints (must be before /{question_id})
# ------------------------------------------------------------------

@router.get("/reassignment-requests", response_model=List[ReassignmentRequestResponse])
async def list_reassignment_requests(
    status_filter: Optional[ReassignmentStatus] = None,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: list reassignment requests."""
    from app.models.subdomain import SubDomain

    query = select(ReassignmentRequest).join(
        Question, ReassignmentRequest.question_id == Question.id
    ).where(
        Question.organization_id == current_user.organization_id,
    )
    if status_filter:
        query = query.where(ReassignmentRequest.status == status_filter)
    query = query.order_by(ReassignmentRequest.created_at.desc())

    result = await db.execute(query)
    requests = list(result.scalars().all())

    # Enrich with names
    items = []
    for r in requests:
        # Get requester name
        user_result = await db.execute(select(User.name).where(User.id == r.requested_by_id))
        requester_name = user_result.scalar_one_or_none()

        # Get subdomain names
        current_sd_name = None
        if r.current_subdomain_id:
            sd_result = await db.execute(select(SubDomain.name).where(SubDomain.id == r.current_subdomain_id))
            current_sd_name = sd_result.scalar_one_or_none()

        sd_result = await db.execute(select(SubDomain.name).where(SubDomain.id == r.suggested_subdomain_id))
        suggested_sd_name = sd_result.scalar_one_or_none()

        items.append(ReassignmentRequestResponse(
            id=r.id,
            question_id=r.question_id,
            requested_by_id=r.requested_by_id,
            requested_by_name=requester_name,
            current_subdomain_id=r.current_subdomain_id,
            current_subdomain_name=current_sd_name,
            suggested_subdomain_id=r.suggested_subdomain_id,
            suggested_subdomain_name=suggested_sd_name,
            reason=r.reason,
            status=r.status,
            reviewed_by_id=r.reviewed_by_id,
            admin_notes=r.admin_notes,
            created_at=r.created_at,
        ))

    return items


@router.put("/reassignment-requests/{request_id}/review")
async def review_reassignment_request(
    request_id: UUID,
    data: ReassignmentReviewRequest,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: approve or reject a reassignment request."""
    result = await db.execute(
        select(ReassignmentRequest).where(ReassignmentRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Reassignment request not found")

    if req.status != ReassignmentStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request already reviewed")

    req.reviewed_by_id = current_user.id
    req.reviewed_at = datetime.now(timezone.utc)
    req.admin_notes = data.admin_notes

    if data.approved:
        req.status = ReassignmentStatus.APPROVED

        # Update question's sub-domain
        q_result = await db.execute(select(Question).where(Question.id == req.question_id))
        question = q_result.scalar_one_or_none()
        if question:
            question.subdomain_id = req.suggested_subdomain_id
            question.ai_classified_subdomain = False

            # Unassign from current expert so it goes back to queue
            question.assigned_to_id = None
            if question.status == QuestionStatus.IN_PROGRESS:
                question.status = QuestionStatus.EXPERT_QUEUE

            # Route to new sub-domain experts
            try:
                await subdomain_service.route_question_to_subdomain(
                    db, question, req.suggested_subdomain_id
                )
            except Exception:
                pass

        # Notify requesting expert
        try:
            from app.models.subdomain import SubDomain
            sd_result = await db.execute(
                select(SubDomain.name).where(SubDomain.id == req.suggested_subdomain_id)
            )
            sd_name = sd_result.scalar_one_or_none() or "Unknown"
            await notification_service.create_notification(
                db=db,
                user_id=req.requested_by_id,
                organization_id=current_user.organization_id,
                notification_type=NotificationType.REASSIGNMENT_APPROVED,
                title="Reassignment approved",
                message=f'Question rerouted to "{sd_name}"',
                link_url=f"/expert/questions/{req.question_id}",
                extra_data={"question_id": str(req.question_id)},
            )
        except Exception:
            pass
    else:
        req.status = ReassignmentStatus.REJECTED

        # Notify requesting expert
        try:
            msg = "Your reassignment request was declined"
            if data.admin_notes:
                msg += f": {data.admin_notes[:100]}"
            await notification_service.create_notification(
                db=db,
                user_id=req.requested_by_id,
                organization_id=current_user.organization_id,
                notification_type=NotificationType.REASSIGNMENT_REJECTED,
                title="Reassignment declined",
                message=msg,
                link_url=f"/expert/questions/{req.question_id}",
                extra_data={"question_id": str(req.question_id)},
            )
        except Exception:
            pass

    await db.commit()

    action = "approved" if data.approved else "rejected"
    return {"message": f"Reassignment request {action}"}


# ------------------------------------------------------------------
# Question detail and actions
# ------------------------------------------------------------------

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

    if question.status not in (QuestionStatus.ANSWERED, QuestionStatus.AUTO_ANSWERED, QuestionStatus.TURBO_ANSWERED, QuestionStatus.RESOLVED):
        raise HTTPException(status_code=400, detail="Question has not been answered yet")

    question.satisfaction_rating = feedback.rating

    if question.status == QuestionStatus.AUTO_ANSWERED:
        # Accepting auto-answer via feedback
        await automation_service.handle_user_feedback(
            db=db, question=question, accepted=True
        )
    elif question.status == QuestionStatus.TURBO_ANSWERED:
        # Accepting turbo answer via feedback
        await turbo_service.handle_turbo_acceptance(db=db, question=question)
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
    """Accept an auto-answer or turbo-answer, marking the question as resolved."""
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.asked_by_id == current_user.id
        )
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.status == QuestionStatus.TURBO_ANSWERED:
        await turbo_service.handle_turbo_acceptance(db=db, question=question)
        return {"message": "Turbo answer accepted"}
    elif question.status == QuestionStatus.AUTO_ANSWERED:
        await automation_service.handle_user_feedback(
            db=db, question=question, accepted=True
        )
        return {"message": "Auto-answer accepted"}
    else:
        raise HTTPException(status_code=400, detail="Question is not auto-answered or turbo-answered")


@router.post("/{question_id}/request-human")
async def request_human_review(
    question_id: UUID,
    clarification: ClarificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject auto-answer or turbo-answer and request human review."""
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.asked_by_id == current_user.id
        )
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.status == QuestionStatus.TURBO_ANSWERED:
        # Handle Turbo rejection
        await turbo_service.handle_turbo_rejection(
            db=db,
            question=question,
            rejection_reason=clarification.message,
        )
        # Run gap analysis for the expert who will handle this
        try:
            ka = await knowledge_service.run_gap_analysis(
                question.original_text, current_user.organization_id, db
            )
            if ka:
                existing_ga = question.gap_analysis or {}
                existing_ga["knowledge_analysis"] = ka
                question.gap_analysis = existing_ga
                await db.commit()
        except Exception:
            pass  # Non-blocking
        return {"message": "Human review requested"}

    elif question.status != QuestionStatus.AUTO_ANSWERED:
        raise HTTPException(status_code=400, detail="Question is not auto-answered or turbo-answered")

    await automation_service.handle_user_feedback(
        db=db,
        question=question,
        accepted=False,
        rejection_reason=clarification.message,
    )

    # Notify rule creator that auto-answer was rejected
    try:
        if question.automation_rule_id:
            rule_result = await db.execute(
                select(AutomationRule).where(AutomationRule.id == question.automation_rule_id)
            )
            rule = rule_result.scalar_one_or_none()
            if rule:
                await notification_service.notify_auto_answer_rejected(
                    db=db,
                    expert_id=rule.created_by_id,
                    organization_id=question.organization_id,
                    question_id=question.id,
                    question_text=question.original_text,
                    rejection_reason=clarification.message,
                )
    except Exception:
        pass  # Non-blocking

    # Run gap analysis for the expert who will handle this
    try:
        ka = await knowledge_service.run_gap_analysis(
            question.original_text, current_user.organization_id, db
        )
        if ka:
            existing_ga = question.gap_analysis or {}
            existing_ga["knowledge_analysis"] = ka
            question.gap_analysis = existing_ga
            await db.commit()
    except Exception:
        pass  # Non-blocking

    return {"message": "Human review requested"}


# Expert Endpoints
@router.get("/queue/pending", response_model=QuestionListResponse)
async def get_expert_queue(
    category: Optional[str] = None,
    subdomain_id: Optional[UUID] = None,
    priority: Optional[QuestionPriority] = None,
    show_all: bool = False,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """Get questions in the expert queue.

    By default, filters to the expert's assigned sub-domains.
    Pass show_all=true to see all questions (admins) or unrouted ones.
    Pass subdomain_id to filter to a specific sub-domain.
    """
    query = select(Question).where(
        Question.organization_id == current_user.organization_id,
        Question.status.in_([
            QuestionStatus.EXPERT_QUEUE,
            QuestionStatus.HUMAN_REQUESTED,
            QuestionStatus.NEEDS_CLARIFICATION
        ])
    )

    if subdomain_id:
        query = query.where(Question.subdomain_id == subdomain_id)
    elif not show_all:
        # Filter to expert's assigned sub-domains + unrouted questions
        expert_sd_ids = await subdomain_service.get_expert_subdomain_ids(
            db, current_user.id
        )
        if expert_sd_ids:
            from sqlalchemy import or_
            query = query.where(
                or_(
                    Question.subdomain_id.in_(expert_sd_ids),
                    Question.subdomain_id.is_(None),
                )
            )
        # If expert has no sub-domain assignments, show all (backward compatible)

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

    # Notify question asker that their question was answered
    try:
        await notification_service.notify_question_answered(
            db=db,
            user_id=question.asked_by_id,
            organization_id=question.organization_id,
            question_id=question.id,
            question_text=question.original_text,
        )
    except Exception:
        pass  # Non-blocking

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

    # Notify question asker
    try:
        await notification_service.notify_clarification_requested(
            db=db,
            user_id=question.asked_by_id,
            organization_id=question.organization_id,
            question_id=question.id,
            clarification_text=request.message,
        )
    except Exception:
        pass  # Non-blocking

    return {"message": "Clarification requested"}


# ------------------------------------------------------------------
# Expert request-reassignment endpoint
# ------------------------------------------------------------------

@router.post("/{question_id}/request-reassignment", response_model=ReassignmentRequestResponse)
async def request_reassignment(
    question_id: UUID,
    data: ReassignmentRequestCreate,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Expert flags a question as not belonging to their sub-domain."""
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.organization_id == current_user.organization_id,
        )
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check for existing pending reassignment
    existing = await db.execute(
        select(ReassignmentRequest).where(
            ReassignmentRequest.question_id == question_id,
            ReassignmentRequest.status == ReassignmentStatus.PENDING,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A reassignment request is already pending")

    req = ReassignmentRequest(
        question_id=question_id,
        requested_by_id=current_user.id,
        current_subdomain_id=question.subdomain_id,
        suggested_subdomain_id=data.suggested_subdomain_id,
        reason=data.reason,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    # Notify admins
    try:
        from app.models.user import UserRole
        admin_result = await db.execute(
            select(User).where(
                User.organization_id == current_user.organization_id,
                User.role == UserRole.ADMIN,
                User.is_active == True,
            )
        )
        admins = list(admin_result.scalars().all())
        for admin in admins:
            await notification_service.create_notification(
                db=db,
                user_id=admin.id,
                organization_id=current_user.organization_id,
                notification_type=NotificationType.REASSIGNMENT_REQUESTED,
                title="Reassignment requested",
                message=f'{current_user.name} flagged a question as wrong sub-domain',
                link_url="/admin/reassignments",
                extra_data={"question_id": str(question_id), "reassignment_id": str(req.id)},
            )
    except Exception:
        pass

    return ReassignmentRequestResponse(
        id=req.id,
        question_id=req.question_id,
        requested_by_id=req.requested_by_id,
        requested_by_name=current_user.name,
        current_subdomain_id=req.current_subdomain_id,
        suggested_subdomain_id=req.suggested_subdomain_id,
        reason=req.reason,
        status=req.status,
        reviewed_by_id=req.reviewed_by_id,
        admin_notes=req.admin_notes,
        created_at=req.created_at,
    )

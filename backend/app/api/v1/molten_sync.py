"""
MoltenLoris Sync API endpoints.

Manual triggers and status for:
- Scanning Slack for expert answers to MoltenLoris escalations
- Exporting knowledge to Google Drive
- Reviewing captured Q&A pairs
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.v1.auth import get_current_user, get_current_active_expert, get_current_admin
from app.core.config import settings
from app.models.user import User
from app.models.slack_capture import SlackCapture, SlackCaptureStatus
from app.services.slack_monitor_service import SlackMonitorService
from app.services.knowledge_export_service import KnowledgeExportService

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────────


class SyncStatusResponse(BaseModel):
    """MoltenLoris sync configuration status."""
    mcp_configured: bool
    gdrive_folder: str
    slack_channels: List[str]
    status: str  # "ready", "partially_configured", "not_configured"


class SlackScanResponse(BaseModel):
    """Result of Slack scan operation."""
    status: str
    qa_pairs_found: int
    captures_created: int
    channels_scanned: List[str]


class KnowledgeExportResponse(BaseModel):
    """Result of knowledge export operation."""
    status: str
    exports: List[dict]
    total_exported: int
    total_errors: int


class SlackCaptureResponse(BaseModel):
    """Slack capture for review."""
    id: UUID
    channel: str
    thread_ts: str
    original_question: str
    expert_answer: str
    expert_name: str
    confidence_score: float
    status: str
    suggested_category: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CaptureReviewRequest(BaseModel):
    """Request to approve or reject a capture."""
    notes: Optional[str] = None
    category: Optional[str] = None  # For approve


class ExportStatusResponse(BaseModel):
    """Current export status and statistics."""
    total_facts: int
    categories: dict
    automation_rules: int
    gdrive_folder: str
    mcp_configured: bool


# ── Endpoints ───────────────────────────────────────────────────────────


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    current_user: User = Depends(get_current_active_expert)
):
    """
    Get MoltenLoris sync configuration status.

    Shows whether MCP is configured, which channels are monitored,
    and the target GDrive folder.
    """
    mcp_configured = bool(settings.MCP_SERVER_URL)
    gdrive_configured = bool(settings.GDRIVE_KNOWLEDGE_FOLDER_ID or settings.GDRIVE_KNOWLEDGE_FOLDER_PATH)
    slack_configured = bool(settings.slack_channels_list)

    if mcp_configured and gdrive_configured and slack_configured:
        status = "ready"
    elif mcp_configured or gdrive_configured or slack_configured:
        status = "partially_configured"
    else:
        status = "not_configured"

    return SyncStatusResponse(
        mcp_configured=mcp_configured,
        gdrive_folder=settings.GDRIVE_KNOWLEDGE_FOLDER_PATH,
        slack_channels=settings.slack_channels_list,
        status=status
    )


@router.post("/scan-slack", response_model=SlackScanResponse)
async def trigger_slack_scan(
    hours_back: int = Query(default=24, ge=1, le=168, description="Hours to look back"),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger Slack scan for expert answers.

    Scans configured Slack channels for MoltenLoris escalations
    that have been answered by experts, and creates SlackCapture
    records for review.
    """
    if not settings.slack_channels_list:
        raise HTTPException(
            status_code=400,
            detail="No Slack channels configured for monitoring"
        )

    service = SlackMonitorService(db, current_user.organization_id)

    since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    qa_pairs = await service.scan_for_expert_answers(since=since)

    captures = []
    if qa_pairs:
        captures = await service.create_captures(qa_pairs)

    return SlackScanResponse(
        status="success",
        qa_pairs_found=len(qa_pairs),
        captures_created=len(captures),
        channels_scanned=settings.slack_channels_list
    )


@router.post("/export-knowledge", response_model=KnowledgeExportResponse)
async def trigger_knowledge_export(
    category: Optional[str] = Query(default=None, description="Export specific category only"),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger knowledge export to Google Drive.

    Exports approved knowledge facts as markdown files to the
    configured GDrive folder for MoltenLoris to consume.
    """
    service = KnowledgeExportService(db, current_user.organization_id)

    if category:
        result = await service.export_category(category)
        exports = [result]
    else:
        exports = await service.export_all_knowledge()

    # Count results
    successful = [e for e in exports if e.get("status") == "exported"]
    errors = [e for e in exports if e.get("status") == "error"]

    return KnowledgeExportResponse(
        status="success" if not errors else "partial",
        exports=exports,
        total_exported=len(successful),
        total_errors=len(errors)
    )


@router.get("/export-status", response_model=ExportStatusResponse)
async def get_export_status(
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current export status and statistics.

    Shows how many facts are available for export by category,
    and the current MCP/GDrive configuration status.
    """
    service = KnowledgeExportService(db, current_user.organization_id)
    status = await service.get_export_status()
    return ExportStatusResponse(**status)


@router.post("/refresh-index")
async def refresh_knowledge_index(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh the knowledge index by scanning the GDrive folder.

    Scans the Loris-Knowledge folder and updates the _Loris-Knowledge-Index
    file with a complete list of all available files.
    """
    service = KnowledgeExportService(db, current_user.organization_id)
    result = await service.refresh_knowledge_index()

    if result:
        return {
            "status": "success",
            "message": "Knowledge index refreshed",
            "index_url": result.get("results", {}).get("url")
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to refresh knowledge index"
        )


@router.post("/export-wisdom")
async def export_accumulated_wisdom(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Export all expert-approved facts to the Accumulated_Wisdom file.

    Creates/updates the Accumulated_Wisdom file in GDrive with all
    validated knowledge organized by tier.
    """
    service = KnowledgeExportService(db, current_user.organization_id)
    result = await service.export_accumulated_wisdom()

    if result:
        return {
            "status": result.get("status", "success"),
            "fact_count": result.get("fact_count", 0),
            "url": result.get("url")
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to export accumulated wisdom"
        )


@router.post("/sync-document/{document_id}")
async def sync_document_to_gdrive(
    document_id: UUID,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync a specific document to Google Drive.

    Uploads the document content to GDrive so MoltenLoris can access it.
    Also updates the knowledge index.
    """
    from app.services.document_service import document_service
    from app.models.documents import KnowledgeDocument, DocumentChunk

    # Get the document
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.organization_id == current_user.organization_id
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get document content from chunks
    chunks_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = list(chunks_result.scalars().all())
    content = "\n\n".join(c.content for c in chunks)

    if not content:
        raise HTTPException(status_code=400, detail="Document has no parsed content")

    # Sync to GDrive
    service = KnowledgeExportService(db, current_user.organization_id)
    gud_str = doc.good_until_date.isoformat() if doc.good_until_date else None

    upload_result = await service.sync_document_to_gdrive(
        doc_id=doc.id,
        doc_title=doc.title or doc.original_filename,
        doc_content=content,
        good_until_date=gud_str,
        domain=doc.domain
    )

    if upload_result:
        # Update the index
        await service.refresh_knowledge_index()
        return {
            "status": "synced",
            "document_id": str(doc.id),
            "title": doc.title or doc.original_filename,
            "url": upload_result.get("results", {}).get("url")
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to sync document to GDrive"
        )


# ── Slack Captures Review ───────────────────────────────────────────────


@router.get("/captures", response_model=List[SlackCaptureResponse])
async def list_slack_captures(
    status: Optional[str] = Query(default="pending", description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """
    List Slack captures for review.

    Returns Q&A pairs captured from Slack where MoltenLoris
    escalated and an expert responded.
    """
    query = select(SlackCapture).where(
        SlackCapture.organization_id == current_user.organization_id
    )

    if status and status != "all":
        try:
            status_enum = SlackCaptureStatus(status)
            query = query.where(SlackCapture.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    query = query.order_by(SlackCapture.created_at.desc()).limit(limit)

    result = await db.execute(query)
    captures = result.scalars().all()

    return [
        SlackCaptureResponse(
            id=c.id,
            channel=c.channel,
            thread_ts=c.thread_ts,
            original_question=c.original_question,
            expert_answer=c.expert_answer,
            expert_name=c.expert_name,
            confidence_score=c.confidence_score,
            status=c.status.value,
            suggested_category=c.suggested_category,
            created_at=c.created_at
        )
        for c in captures
    ]


@router.get("/captures/{capture_id}", response_model=SlackCaptureResponse)
async def get_slack_capture(
    capture_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific Slack capture."""
    result = await db.execute(
        select(SlackCapture).where(
            SlackCapture.id == capture_id,
            SlackCapture.organization_id == current_user.organization_id
        )
    )
    capture = result.scalar_one_or_none()

    if not capture:
        raise HTTPException(status_code=404, detail="Capture not found")

    return SlackCaptureResponse(
        id=capture.id,
        channel=capture.channel,
        thread_ts=capture.thread_ts,
        original_question=capture.original_question,
        expert_answer=capture.expert_answer,
        expert_name=capture.expert_name,
        confidence_score=capture.confidence_score,
        status=capture.status.value,
        suggested_category=capture.suggested_category,
        created_at=capture.created_at
    )


@router.post("/captures/{capture_id}/approve")
async def approve_slack_capture(
    capture_id: UUID,
    request: CaptureReviewRequest,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a Slack capture.

    The Q&A pair can then be converted to a WisdomFact.
    """
    service = SlackMonitorService(db, current_user.organization_id)

    try:
        capture = await service.approve_capture(
            capture_id=capture_id,
            reviewer_id=current_user.id,
            notes=request.notes,
            category=request.category
        )
        return {
            "status": "approved",
            "capture_id": str(capture.id),
            "message": "Capture approved. You can now create a WisdomFact from this Q&A pair."
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/captures/{capture_id}/reject")
async def reject_slack_capture(
    capture_id: UUID,
    request: CaptureReviewRequest,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """
    Reject a Slack capture.

    Marks the capture as not suitable for the knowledge base.
    """
    if not request.notes:
        raise HTTPException(
            status_code=400,
            detail="Rejection reason is required"
        )

    service = SlackMonitorService(db, current_user.organization_id)

    try:
        capture = await service.reject_capture(
            capture_id=capture_id,
            reviewer_id=current_user.id,
            reason=request.notes
        )
        return {
            "status": "rejected",
            "capture_id": str(capture.id)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

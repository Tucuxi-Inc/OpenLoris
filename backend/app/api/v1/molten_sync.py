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
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.api.v1.auth import get_current_user, get_current_active_expert, get_current_admin
from app.core.config import settings
from app.models.user import User
from app.models.slack_capture import SlackCapture, SlackCaptureStatus
from app.models.molten_activity import MoltenLorisActivity
from app.services.slack_monitor_service import SlackMonitorService
from app.services.knowledge_export_service import KnowledgeExportService
from app.services.soul_generation_service import soul_generation_service

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


# ── MoltenLoris Settings Schemas ────────────────────────────────────────


class MoltenLorisSettingsResponse(BaseModel):
    """MoltenLoris configuration settings."""
    enabled: bool
    mcp_server_url_set: bool  # Don't expose the actual URL
    slack_channels: List[str]
    last_test_at: Optional[datetime] = None
    last_test_result: Optional[dict] = None


class MoltenLorisSettingsUpdate(BaseModel):
    """Request to update MoltenLoris settings."""
    enabled: Optional[bool] = None
    mcp_server_url: Optional[str] = None  # Admin can set/update
    slack_channels: Optional[List[str]] = None


class ConnectionTestResponse(BaseModel):
    """Result of MCP connection test."""
    connected: bool
    message: str
    tested_at: datetime


# ── Helper Functions ────────────────────────────────────────────────────


def get_molten_settings(org_settings: dict) -> dict:
    """Extract MoltenLoris settings from org settings JSONB."""
    return org_settings.get("molten_loris", {
        "enabled": False,
        "mcp_server_url": None,
        "slack_channels": [],
        "last_test_at": None,
        "last_test_result": None,
    })


def get_molten_mcp_url(org_settings: dict) -> Optional[str]:
    """Get MCP URL from org settings, falling back to env var."""
    molten = get_molten_settings(org_settings)
    return molten.get("mcp_server_url") or settings.MCP_SERVER_URL


def get_molten_channels(org_settings: dict) -> List[str]:
    """Get Slack channels from org settings, falling back to env var."""
    molten = get_molten_settings(org_settings)
    channels = molten.get("slack_channels", [])
    if channels:
        return channels
    return settings.slack_channels_list or []


# ── Endpoints ───────────────────────────────────────────────────────────


# ── MoltenLoris Settings ────────────────────────────────────────────────


@router.get("/settings", response_model=MoltenLorisSettingsResponse)
async def get_molten_loris_settings(
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """
    Get MoltenLoris configuration settings for the organization.
    """
    from app.models.organization import Organization

    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    molten = get_molten_settings(org.settings or {})

    return MoltenLorisSettingsResponse(
        enabled=molten.get("enabled", False),
        mcp_server_url_set=bool(molten.get("mcp_server_url")),
        slack_channels=molten.get("slack_channels", []),
        last_test_at=molten.get("last_test_at"),
        last_test_result=molten.get("last_test_result"),
    )


@router.put("/settings", response_model=MoltenLorisSettingsResponse)
async def update_molten_loris_settings(
    update: MoltenLorisSettingsUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update MoltenLoris configuration settings.

    Admin-only. Allows configuring MCP server URL and Slack channels.
    """
    from app.models.organization import Organization

    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get current settings
    org_settings = org.settings or {}
    molten = get_molten_settings(org_settings)

    # Apply updates
    if update.enabled is not None:
        molten["enabled"] = update.enabled
    if update.mcp_server_url is not None:
        molten["mcp_server_url"] = update.mcp_server_url
    if update.slack_channels is not None:
        # Normalize channel names (remove # prefix if present)
        molten["slack_channels"] = [
            ch.lstrip("#").strip() for ch in update.slack_channels if ch.strip()
        ]

    # Save back to org settings
    org_settings["molten_loris"] = molten
    org.settings = org_settings
    await db.commit()
    await db.refresh(org)

    return MoltenLorisSettingsResponse(
        enabled=molten.get("enabled", False),
        mcp_server_url_set=bool(molten.get("mcp_server_url")),
        slack_channels=molten.get("slack_channels", []),
        last_test_at=molten.get("last_test_at"),
        last_test_result=molten.get("last_test_result"),
    )


@router.post("/test-connection", response_model=ConnectionTestResponse)
async def test_mcp_connection(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Test the MCP server connection.

    Attempts to connect to the configured MCP server URL and
    verifies it responds correctly.
    """
    import httpx
    from app.models.organization import Organization

    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org_settings = org.settings or {}
    mcp_url = get_molten_mcp_url(org_settings)

    if not mcp_url:
        return ConnectionTestResponse(
            connected=False,
            message="No MCP server URL configured. Please save a URL first.",
            tested_at=datetime.now(timezone.utc)
        )

    # Test the connection
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Send a simple ping/test request to the MCP server
            # Most MCP servers accept a GET request or a simple POST
            response = await client.get(mcp_url)

            # Consider various success responses
            if response.status_code in [200, 201, 202, 204]:
                connected = True
                message = "Successfully connected to MCP server"
            elif response.status_code == 405:
                # Method not allowed - server exists but may only accept POST
                connected = True
                message = "MCP server is reachable (may require POST requests)"
            else:
                connected = False
                message = f"MCP server responded with status {response.status_code}"

    except httpx.TimeoutException:
        connected = False
        message = "Connection timed out. Check the URL and ensure the server is running."
    except httpx.ConnectError:
        connected = False
        message = "Could not connect to MCP server. Check the URL."
    except Exception as e:
        connected = False
        message = f"Connection error: {str(e)}"

    # Save test result
    molten = get_molten_settings(org_settings)
    molten["last_test_at"] = datetime.now(timezone.utc).isoformat()
    molten["last_test_result"] = {
        "connected": connected,
        "message": message,
    }
    org_settings["molten_loris"] = molten
    org.settings = org_settings
    await db.commit()

    return ConnectionTestResponse(
        connected=connected,
        message=message,
        tested_at=datetime.now(timezone.utc)
    )


# ── Sync Status ─────────────────────────────────────────────────────────


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """
    Get MoltenLoris sync configuration status.

    Shows whether MCP is configured, which channels are monitored,
    and the target GDrive folder. Reads from database settings with
    fallback to environment variables.
    """
    from app.models.organization import Organization

    # Load org settings
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    org_settings = org.settings if org else {}

    # Get settings from DB or fall back to env vars
    mcp_url = get_molten_mcp_url(org_settings)
    slack_channels = get_molten_channels(org_settings)

    mcp_configured = bool(mcp_url)
    gdrive_configured = bool(settings.GDRIVE_KNOWLEDGE_FOLDER_ID or settings.GDRIVE_KNOWLEDGE_FOLDER_PATH)
    slack_configured = bool(slack_channels)

    if mcp_configured and gdrive_configured and slack_configured:
        status = "ready"
    elif mcp_configured or gdrive_configured or slack_configured:
        status = "partially_configured"
    else:
        status = "not_configured"

    return SyncStatusResponse(
        mcp_configured=mcp_configured,
        gdrive_folder=settings.GDRIVE_KNOWLEDGE_FOLDER_PATH,
        slack_channels=slack_channels,
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
    from app.models.organization import Organization

    # Get channels from DB settings or fall back to env vars
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    org_settings = org.settings if org else {}
    slack_channels = get_molten_channels(org_settings)

    if not slack_channels:
        raise HTTPException(
            status_code=400,
            detail="No Slack channels configured for monitoring. Configure them in Settings."
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
        channels_scanned=slack_channels
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


# ── SOUL File Generation ─────────────────────────────────────────────────


class SoulFileResponse(BaseModel):
    """Generated SOUL file content."""
    soul_content: str
    generated_at: datetime
    organization_name: str
    stats: dict


@router.post("/soul", response_model=SoulFileResponse)
async def generate_soul_file(
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate SOUL configuration file for MoltenLoris.

    Creates a markdown file containing all validated knowledge,
    automation rules, and answering guidelines for the organization.
    """
    from app.models.organization import Organization

    # Get organization
    org_result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        soul_content = await soul_generation_service.generate_soul_file(
            organization_id=current_user.organization_id,
            db=db
        )

        # Get basic stats for response
        stats = await soul_generation_service._get_stats(db, current_user.organization_id)

        return SoulFileResponse(
            soul_content=soul_content,
            generated_at=datetime.now(timezone.utc),
            organization_name=org.name,
            stats=stats
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate SOUL file: {str(e)}"
        )


# ── MoltenLoris Activity Tracking ────────────────────────────────────────


class MoltenActivityResponse(BaseModel):
    """MoltenLoris activity record."""
    id: UUID
    channel_id: str
    channel_name: str
    thread_ts: Optional[str]
    user_slack_id: Optional[str]
    user_name: Optional[str]
    question_text: str
    answer_text: str
    confidence_score: float
    source_facts: list
    was_corrected: bool
    corrected_by: Optional[dict] = None
    corrected_at: Optional[datetime] = None
    correction_text: Optional[str] = None
    correction_reason: Optional[str] = None
    created_question_id: Optional[UUID] = None
    created_fact_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityListResponse(BaseModel):
    """Paginated list of MoltenLoris activities."""
    activities: List[MoltenActivityResponse]
    total: int
    limit: int
    offset: int


class ActivityCorrectionRequest(BaseModel):
    """Request to correct a MoltenLoris answer."""
    correction_text: str
    correction_reason: str
    create_fact: bool = False  # Optionally create a WisdomFact from the correction


class ActivityStatsResponse(BaseModel):
    """MoltenLoris activity statistics."""
    total_answers: int
    high_confidence_count: int
    low_confidence_count: int
    corrected_count: int
    correction_rate: float
    avg_confidence: float
    top_channels: List[dict]
    confidence_distribution: List[dict]
    daily_trend: List[dict]


@router.get("/activities", response_model=ActivityListResponse)
async def list_activities(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    channel_id: Optional[str] = Query(default=None, description="Filter by channel"),
    corrected_only: bool = Query(default=False, description="Only show corrected answers"),
    needs_review: bool = Query(default=False, description="Only show low-confidence uncorrected"),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """
    List MoltenLoris activity log.

    Shows all Q&A pairs from the MoltenLoris Slack bot, including
    expert corrections.
    """
    # Base query
    query = select(MoltenLorisActivity).where(
        MoltenLorisActivity.organization_id == current_user.organization_id
    )

    # Apply filters
    if channel_id:
        query = query.where(MoltenLorisActivity.channel_id == channel_id)
    if corrected_only:
        query = query.where(MoltenLorisActivity.was_corrected == True)
    if needs_review:
        query = query.where(
            and_(
                MoltenLorisActivity.confidence_score < 0.6,
                MoltenLorisActivity.was_corrected == False
            )
        )

    # Get total count
    count_query = select(func.count(MoltenLorisActivity.id)).where(
        MoltenLorisActivity.organization_id == current_user.organization_id
    )
    if channel_id:
        count_query = count_query.where(MoltenLorisActivity.channel_id == channel_id)
    if corrected_only:
        count_query = count_query.where(MoltenLorisActivity.was_corrected == True)
    if needs_review:
        count_query = count_query.where(
            and_(
                MoltenLorisActivity.confidence_score < 0.6,
                MoltenLorisActivity.was_corrected == False
            )
        )

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(MoltenLorisActivity.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    activities = result.scalars().all()

    # Build response with corrector info
    activity_responses = []
    for activity in activities:
        corrected_by = None
        if activity.corrected_by_id:
            # Get corrector info
            from app.models.user import User as UserModel
            corrector_result = await db.execute(
                select(UserModel).where(UserModel.id == activity.corrected_by_id)
            )
            corrector = corrector_result.scalar_one_or_none()
            if corrector:
                corrected_by = {
                    "id": str(corrector.id),
                    "name": corrector.name,
                    "email": corrector.email
                }

        activity_responses.append(MoltenActivityResponse(
            id=activity.id,
            channel_id=activity.channel_id,
            channel_name=activity.channel_name,
            thread_ts=activity.thread_ts,
            user_slack_id=activity.user_slack_id,
            user_name=activity.user_name,
            question_text=activity.question_text,
            answer_text=activity.answer_text,
            confidence_score=activity.confidence_score,
            source_facts=activity.source_facts or [],
            was_corrected=activity.was_corrected,
            corrected_by=corrected_by,
            corrected_at=activity.corrected_at,
            correction_text=activity.correction_text,
            correction_reason=activity.correction_reason,
            created_question_id=activity.created_question_id,
            created_fact_id=activity.created_fact_id,
            created_at=activity.created_at
        ))

    return ActivityListResponse(
        activities=activity_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/activities/stats", response_model=ActivityStatsResponse)
async def get_activity_stats(
    period: str = Query(default="30d", description="Time period: 7d, 30d, 90d, all"),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """
    Get MoltenLoris activity statistics.

    Returns metrics on answer volume, confidence, correction rates,
    and channel distribution.
    """
    # Parse period
    if period == "all":
        since = None
    else:
        days = int(period.rstrip("d"))
        since = datetime.now(timezone.utc) - timedelta(days=days)

    # Base filter
    org_filter = MoltenLorisActivity.organization_id == current_user.organization_id
    time_filter = MoltenLorisActivity.created_at >= since if since else True

    # Total answers
    total_result = await db.execute(
        select(func.count(MoltenLorisActivity.id)).where(org_filter, time_filter)
    )
    total_answers = total_result.scalar() or 0

    if total_answers == 0:
        return ActivityStatsResponse(
            total_answers=0,
            high_confidence_count=0,
            low_confidence_count=0,
            corrected_count=0,
            correction_rate=0.0,
            avg_confidence=0.0,
            top_channels=[],
            confidence_distribution=[],
            daily_trend=[]
        )

    # High confidence (>= 0.8)
    high_conf_result = await db.execute(
        select(func.count(MoltenLorisActivity.id)).where(
            org_filter,
            time_filter,
            MoltenLorisActivity.confidence_score >= 0.8
        )
    )
    high_confidence_count = high_conf_result.scalar() or 0

    # Low confidence (< 0.6)
    low_conf_result = await db.execute(
        select(func.count(MoltenLorisActivity.id)).where(
            org_filter,
            time_filter,
            MoltenLorisActivity.confidence_score < 0.6
        )
    )
    low_confidence_count = low_conf_result.scalar() or 0

    # Corrected count
    corrected_result = await db.execute(
        select(func.count(MoltenLorisActivity.id)).where(
            org_filter,
            time_filter,
            MoltenLorisActivity.was_corrected == True
        )
    )
    corrected_count = corrected_result.scalar() or 0

    # Average confidence
    avg_conf_result = await db.execute(
        select(func.avg(MoltenLorisActivity.confidence_score)).where(org_filter, time_filter)
    )
    avg_confidence = float(avg_conf_result.scalar() or 0)

    # Top channels
    channel_result = await db.execute(
        select(
            MoltenLorisActivity.channel_name,
            func.count(MoltenLorisActivity.id).label("count")
        )
        .where(org_filter, time_filter)
        .group_by(MoltenLorisActivity.channel_name)
        .order_by(func.count(MoltenLorisActivity.id).desc())
        .limit(10)
    )
    top_channels = [
        {"channel": row[0], "count": row[1]}
        for row in channel_result.all()
    ]

    # Confidence distribution (buckets: 0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0)
    confidence_distribution = []
    buckets = [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
    for low, high in buckets:
        bucket_result = await db.execute(
            select(func.count(MoltenLorisActivity.id)).where(
                org_filter,
                time_filter,
                MoltenLorisActivity.confidence_score >= low,
                MoltenLorisActivity.confidence_score < high
            )
        )
        count = bucket_result.scalar() or 0
        confidence_distribution.append({
            "range": f"{low:.1f}-{high:.1f}",
            "count": count
        })

    # Daily trend (last 30 days max)
    trend_days = min(30, int(period.rstrip("d")) if period != "all" else 30)
    trend_since = datetime.now(timezone.utc) - timedelta(days=trend_days)

    daily_trend = []
    for i in range(trend_days):
        day_start = trend_since + timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        day_result = await db.execute(
            select(func.count(MoltenLorisActivity.id)).where(
                org_filter,
                MoltenLorisActivity.created_at >= day_start,
                MoltenLorisActivity.created_at < day_end
            )
        )
        day_count = day_result.scalar() or 0
        daily_trend.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": day_count
        })

    return ActivityStatsResponse(
        total_answers=total_answers,
        high_confidence_count=high_confidence_count,
        low_confidence_count=low_confidence_count,
        corrected_count=corrected_count,
        correction_rate=round(corrected_count / total_answers, 4) if total_answers > 0 else 0,
        avg_confidence=round(avg_confidence, 4),
        top_channels=top_channels,
        confidence_distribution=confidence_distribution,
        daily_trend=daily_trend
    )


@router.get("/activities/{activity_id}", response_model=MoltenActivityResponse)
async def get_activity(
    activity_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific MoltenLoris activity."""
    result = await db.execute(
        select(MoltenLorisActivity).where(
            MoltenLorisActivity.id == activity_id,
            MoltenLorisActivity.organization_id == current_user.organization_id
        )
    )
    activity = result.scalar_one_or_none()

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    corrected_by = None
    if activity.corrected_by_id:
        from app.models.user import User as UserModel
        corrector_result = await db.execute(
            select(UserModel).where(UserModel.id == activity.corrected_by_id)
        )
        corrector = corrector_result.scalar_one_or_none()
        if corrector:
            corrected_by = {
                "id": str(corrector.id),
                "name": corrector.name,
                "email": corrector.email
            }

    return MoltenActivityResponse(
        id=activity.id,
        channel_id=activity.channel_id,
        channel_name=activity.channel_name,
        thread_ts=activity.thread_ts,
        user_slack_id=activity.user_slack_id,
        user_name=activity.user_name,
        question_text=activity.question_text,
        answer_text=activity.answer_text,
        confidence_score=activity.confidence_score,
        source_facts=activity.source_facts or [],
        was_corrected=activity.was_corrected,
        corrected_by=corrected_by,
        corrected_at=activity.corrected_at,
        correction_text=activity.correction_text,
        correction_reason=activity.correction_reason,
        created_question_id=activity.created_question_id,
        created_fact_id=activity.created_fact_id,
        created_at=activity.created_at
    )


@router.post("/activities/{activity_id}/correct")
async def correct_activity(
    activity_id: UUID,
    request: ActivityCorrectionRequest,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db)
):
    """
    Record expert correction to a MoltenLoris answer.

    Experts can correct automated answers to improve accuracy.
    Optionally creates a WisdomFact from the corrected answer.
    """
    result = await db.execute(
        select(MoltenLorisActivity).where(
            MoltenLorisActivity.id == activity_id,
            MoltenLorisActivity.organization_id == current_user.organization_id
        )
    )
    activity = result.scalar_one_or_none()

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if activity.was_corrected:
        raise HTTPException(
            status_code=400,
            detail="This activity has already been corrected"
        )

    # Apply correction
    activity.was_corrected = True
    activity.corrected_by_id = current_user.id
    activity.corrected_at = datetime.now(timezone.utc)
    activity.correction_text = request.correction_text
    activity.correction_reason = request.correction_reason

    created_fact_id = None

    # Optionally create a WisdomFact
    if request.create_fact:
        from app.models.wisdom import WisdomFact, WisdomTier
        from app.services.embedding_service import embedding_service

        # Create fact from the corrected answer
        fact = WisdomFact(
            organization_id=current_user.organization_id,
            content=request.correction_text,
            category="MoltenLoris Correction",
            domain="slack",
            tier=WisdomTier.TIER_0B,  # Expert-validated
            source_type="molten_correction",
            source_reference=f"Activity {activity_id}",
            validated_by_id=current_user.id,
            confidence_score=0.9,
            is_active=True
        )
        db.add(fact)
        await db.flush()

        # Generate embedding
        try:
            embedding_data = await embedding_service.generate_embedding(request.correction_text)
            from app.models.wisdom import WisdomEmbedding
            fact_embedding = WisdomEmbedding(
                wisdom_fact_id=fact.id,
                embedding_data=embedding_data,
                model_name="nomic-embed-text"
            )
            db.add(fact_embedding)
        except Exception:
            # Non-blocking - fact created but without embedding
            pass

        activity.created_fact_id = fact.id
        created_fact_id = fact.id

    await db.commit()

    return {
        "status": "corrected",
        "activity_id": str(activity.id),
        "corrected_at": activity.corrected_at.isoformat(),
        "created_fact_id": str(created_fact_id) if created_fact_id else None
    }

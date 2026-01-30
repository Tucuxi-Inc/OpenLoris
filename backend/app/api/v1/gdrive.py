"""
Google Drive API endpoints.

Provides endpoints for GDrive connection status, folder listing, and knowledge sync.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user, get_current_admin
from app.models.user import User
from app.models.organization import Organization
from app.services.gdrive_service import (
    GDriveService,
    GDriveError,
    get_gdrive_service,
    sync_knowledge_to_drive,
    import_from_drive,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────


class GDriveSettingsResponse(BaseModel):
    """GDrive configuration response."""
    enabled: bool = False
    zapier_mcp_url_set: bool = False
    folder_id: Optional[str] = None
    folder_name: Optional[str] = None
    sync_direction: str = "export"  # export | import | bidirectional
    last_sync_at: Optional[str] = None
    last_sync_result: Optional[Dict[str, Any]] = None


class GDriveSettingsUpdate(BaseModel):
    """GDrive configuration update request."""
    enabled: Optional[bool] = None
    zapier_mcp_url: Optional[str] = Field(None, description="Zapier MCP webhook URL")
    folder_id: Optional[str] = None
    folder_name: Optional[str] = None
    sync_direction: Optional[str] = Field(
        None,
        description="Sync direction: export, import, or bidirectional"
    )


class GDriveConnectionTest(BaseModel):
    """GDrive connection test result."""
    connected: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class GDriveFolderInfo(BaseModel):
    """GDrive folder information."""
    id: str
    name: str
    parent_id: Optional[str] = None


class GDriveFileInfo(BaseModel):
    """GDrive file information."""
    id: str
    name: str
    mime_type: Optional[str] = None
    size: Optional[int] = None
    modified_at: Optional[str] = None


class GDriveSyncResult(BaseModel):
    """Result of a sync operation."""
    success: bool
    direction: str
    exported: Optional[int] = None
    imported: Optional[int] = None
    skipped: Optional[int] = None
    total: Optional[int] = None
    errors: List[Dict[str, Any]] = []
    timestamp: str


# ── Helper Functions ─────────────────────────────────────────────────


def _get_gdrive_settings(org: Organization) -> Dict[str, Any]:
    """Get GDrive settings from organization."""
    settings = org.settings or {}
    return settings.get("gdrive", {})


def _build_settings_response(gdrive_settings: Dict[str, Any]) -> GDriveSettingsResponse:
    """Build GDrive settings response."""
    return GDriveSettingsResponse(
        enabled=gdrive_settings.get("enabled", False),
        zapier_mcp_url_set=bool(gdrive_settings.get("zapier_mcp_url")),
        folder_id=gdrive_settings.get("folder_id"),
        folder_name=gdrive_settings.get("folder_name"),
        sync_direction=gdrive_settings.get("sync_direction", "export"),
        last_sync_at=gdrive_settings.get("last_sync_at"),
        last_sync_result=gdrive_settings.get("last_sync_result"),
    )


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/settings", response_model=GDriveSettingsResponse)
async def get_gdrive_settings_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get GDrive configuration. Any authenticated user can read.
    The MCP URL is not returned for security.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    gdrive_settings = _get_gdrive_settings(org)
    return _build_settings_response(gdrive_settings)


@router.put("/settings", response_model=GDriveSettingsResponse)
async def update_gdrive_settings(
    data: GDriveSettingsUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update GDrive configuration. Admin-only.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    settings = dict(org.settings or {})
    gdrive_settings = dict(settings.get("gdrive", {}))

    # Update settings
    if data.enabled is not None:
        gdrive_settings["enabled"] = data.enabled

    if data.zapier_mcp_url is not None:
        gdrive_settings["zapier_mcp_url"] = data.zapier_mcp_url

    if data.folder_id is not None:
        gdrive_settings["folder_id"] = data.folder_id

    if data.folder_name is not None:
        gdrive_settings["folder_name"] = data.folder_name

    if data.sync_direction is not None:
        if data.sync_direction not in ["export", "import", "bidirectional"]:
            raise HTTPException(
                status_code=400,
                detail="sync_direction must be 'export', 'import', or 'bidirectional'"
            )
        gdrive_settings["sync_direction"] = data.sync_direction

    settings["gdrive"] = gdrive_settings
    org.settings = settings

    await db.commit()
    await db.refresh(org)

    logger.info(f"GDrive settings updated by user {current_user.email} for org {org.id}")

    return _build_settings_response(gdrive_settings)


@router.post("/test", response_model=GDriveConnectionTest)
async def test_gdrive_connection(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Test GDrive connection via Zapier MCP. Admin-only.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    gdrive = await get_gdrive_service(org)
    if not gdrive:
        return GDriveConnectionTest(
            connected=False,
            message="GDrive not configured. Please set the Zapier MCP URL and enable the integration.",
        )

    try:
        test_result = await gdrive.test_connection()
        return GDriveConnectionTest(
            connected=test_result["connected"],
            message=test_result["message"],
            details=test_result.get("details"),
        )
    except Exception as e:
        logger.error(f"GDrive connection test failed: {e}")
        return GDriveConnectionTest(
            connected=False,
            message=f"Connection test failed: {str(e)}",
        )
    finally:
        await gdrive.close()


@router.get("/folders", response_model=List[GDriveFolderInfo])
async def list_gdrive_folders(
    parent_id: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List available GDrive folders. Admin-only.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    gdrive = await get_gdrive_service(org)
    if not gdrive:
        raise HTTPException(
            status_code=400,
            detail="GDrive not configured. Please set the Zapier MCP URL first."
        )

    try:
        folders = await gdrive.list_folders(parent_id)
        return [
            GDriveFolderInfo(
                id=f.get("id", ""),
                name=f.get("name", ""),
                parent_id=f.get("parent_id"),
            )
            for f in folders
        ]
    except GDriveError as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await gdrive.close()


@router.get("/files", response_model=List[GDriveFileInfo])
async def list_gdrive_files(
    folder_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List files in the configured GDrive folder.
    Any authenticated user can view (needed for knowledge browsing).
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    gdrive = await get_gdrive_service(org)
    if not gdrive:
        raise HTTPException(
            status_code=400,
            detail="GDrive not configured"
        )

    # Use provided folder_id or configured folder
    gdrive_settings = _get_gdrive_settings(org)
    target_folder = folder_id or gdrive_settings.get("folder_id")

    if not target_folder:
        raise HTTPException(
            status_code=400,
            detail="No folder specified and no default folder configured"
        )

    try:
        files = await gdrive.list_files(target_folder)
        return [
            GDriveFileInfo(
                id=f.get("id", ""),
                name=f.get("name", ""),
                mime_type=f.get("mime_type"),
                size=f.get("size"),
                modified_at=f.get("modified_at"),
            )
            for f in files
        ]
    except GDriveError as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await gdrive.close()


@router.post("/sync", response_model=GDriveSyncResult)
async def trigger_sync(
    direction: Optional[str] = None,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger knowledge sync with GDrive. Admin-only.

    Args:
        direction: Override sync direction (export, import, bidirectional).
                   Uses configured direction if not specified.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    gdrive = await get_gdrive_service(org)
    if not gdrive:
        raise HTTPException(
            status_code=400,
            detail="GDrive not configured or not enabled"
        )

    gdrive_settings = _get_gdrive_settings(org)
    folder_id = gdrive_settings.get("folder_id")

    if not folder_id:
        raise HTTPException(
            status_code=400,
            detail="No folder configured for sync"
        )

    # Determine sync direction
    sync_dir = direction or gdrive_settings.get("sync_direction", "export")
    if sync_dir not in ["export", "import", "bidirectional"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid sync direction"
        )

    try:
        exported = None
        imported = None
        skipped = None
        total = None
        all_errors = []

        # Export to GDrive
        if sync_dir in ["export", "bidirectional"]:
            export_result = await sync_knowledge_to_drive(
                org_id=org.id,
                db=db,
                gdrive=gdrive,
                folder_id=folder_id,
            )
            exported = export_result.get("exported", 0)
            total = export_result.get("total", 0)
            all_errors.extend(export_result.get("errors", []))

        # Import from GDrive
        if sync_dir in ["import", "bidirectional"]:
            import_result = await import_from_drive(
                org_id=org.id,
                db=db,
                gdrive=gdrive,
                folder_id=folder_id,
                created_by=current_user.id,
            )
            imported = import_result.get("imported", 0)
            skipped = import_result.get("skipped", 0)
            if total is None:
                total = import_result.get("total_files", 0)
            all_errors.extend(import_result.get("errors", []))

        # Update last sync info
        timestamp = datetime.now(timezone.utc).isoformat()
        settings = dict(org.settings or {})
        gdrive_settings = dict(settings.get("gdrive", {}))
        gdrive_settings["last_sync_at"] = timestamp
        gdrive_settings["last_sync_result"] = {
            "direction": sync_dir,
            "exported": exported,
            "imported": imported,
            "skipped": skipped,
            "errors_count": len(all_errors),
        }
        settings["gdrive"] = gdrive_settings
        org.settings = settings
        await db.commit()

        logger.info(
            f"GDrive sync completed for org {org.id}: "
            f"direction={sync_dir}, exported={exported}, imported={imported}"
        )

        return GDriveSyncResult(
            success=len(all_errors) == 0,
            direction=sync_dir,
            exported=exported,
            imported=imported,
            skipped=skipped,
            total=total,
            errors=all_errors,
            timestamp=timestamp,
        )

    except GDriveError as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await gdrive.close()


@router.get("/status")
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current GDrive sync status.
    """
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    gdrive_settings = _get_gdrive_settings(org)

    return {
        "enabled": gdrive_settings.get("enabled", False),
        "configured": bool(gdrive_settings.get("zapier_mcp_url")),
        "folder_configured": bool(gdrive_settings.get("folder_id")),
        "folder_name": gdrive_settings.get("folder_name"),
        "sync_direction": gdrive_settings.get("sync_direction", "export"),
        "last_sync_at": gdrive_settings.get("last_sync_at"),
        "last_sync_result": gdrive_settings.get("last_sync_result"),
    }

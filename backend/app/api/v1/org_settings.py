"""
Organization settings API — manage departments list, require_department toggle, etc.
Settings are stored in the Organization.settings JSONB field.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user, get_current_admin
from app.models.user import User
from app.models.organization import Organization

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────

class TurboLorisSettings(BaseModel):
    enabled: bool = True
    min_threshold: float = 0.50
    default_threshold: float = 0.75
    threshold_options: List[float] = [0.50, 0.75, 0.90]


class OrgSettingsResponse(BaseModel):
    departments: List[str]
    require_department: bool
    turbo_loris: TurboLorisSettings

    class Config:
        from_attributes = True


class TurboLorisSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    min_threshold: Optional[float] = None
    default_threshold: Optional[float] = None
    threshold_options: Optional[List[float]] = None


class OrgSettingsUpdate(BaseModel):
    departments: Optional[List[str]] = None
    require_department: Optional[bool] = None
    turbo_loris: Optional[TurboLorisSettingsUpdate] = None


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/settings", response_model=OrgSettingsResponse)
async def get_org_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get organization settings. Any authenticated user can read."""
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    settings = org.settings or {}

    # Default Turbo Loris settings
    turbo_settings = settings.get("turbo_loris", {})
    turbo_loris = TurboLorisSettings(
        enabled=turbo_settings.get("enabled", True),
        min_threshold=turbo_settings.get("min_threshold", 0.50),
        default_threshold=turbo_settings.get("default_threshold", 0.75),
        threshold_options=turbo_settings.get("threshold_options", [0.50, 0.75, 0.90]),
    )

    return OrgSettingsResponse(
        departments=settings.get("departments", []),
        require_department=settings.get("require_department", False),
        turbo_loris=turbo_loris,
    )


@router.put("/settings", response_model=OrgSettingsResponse)
async def update_org_settings(
    data: OrgSettingsUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update organization settings. Admin-only."""
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    settings = dict(org.settings or {})

    if data.departments is not None:
        settings["departments"] = data.departments
    if data.require_department is not None:
        settings["require_department"] = data.require_department

    # Update Turbo Loris settings
    if data.turbo_loris is not None:
        turbo_settings = settings.get("turbo_loris", {})
        if data.turbo_loris.enabled is not None:
            turbo_settings["enabled"] = data.turbo_loris.enabled
        if data.turbo_loris.min_threshold is not None:
            turbo_settings["min_threshold"] = data.turbo_loris.min_threshold
        if data.turbo_loris.default_threshold is not None:
            turbo_settings["default_threshold"] = data.turbo_loris.default_threshold
        if data.turbo_loris.threshold_options is not None:
            turbo_settings["threshold_options"] = data.turbo_loris.threshold_options
        settings["turbo_loris"] = turbo_settings

    org.settings = settings
    await db.commit()
    await db.refresh(org)

    # Build Turbo Loris response
    turbo_settings = settings.get("turbo_loris", {})
    turbo_loris = TurboLorisSettings(
        enabled=turbo_settings.get("enabled", True),
        min_threshold=turbo_settings.get("min_threshold", 0.50),
        default_threshold=turbo_settings.get("default_threshold", 0.75),
        threshold_options=turbo_settings.get("threshold_options", [0.50, 0.75, 0.90]),
    )

    return OrgSettingsResponse(
        departments=settings.get("departments", []),
        require_department=settings.get("require_department", False),
        turbo_loris=turbo_loris,
    )

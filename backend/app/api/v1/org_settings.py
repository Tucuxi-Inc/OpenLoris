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

class OrgSettingsResponse(BaseModel):
    departments: List[str]
    require_department: bool

    class Config:
        from_attributes = True


class OrgSettingsUpdate(BaseModel):
    departments: Optional[List[str]] = None
    require_department: Optional[bool] = None


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
    return OrgSettingsResponse(
        departments=settings.get("departments", []),
        require_department=settings.get("require_department", False),
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

    org.settings = settings
    await db.commit()
    await db.refresh(org)

    return OrgSettingsResponse(
        departments=settings.get("departments", []),
        require_department=settings.get("require_department", False),
    )

"""
SubDomain API — admin manages sub-domains, assigns experts.

Endpoints:
- CRUD for sub-domains (admin-only for write, expert+ for read)
- Expert assignment to sub-domains (admin-only)
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.subdomain import SubDomain, ExpertSubDomainAssignment
from app.models.questions import Question
from app.models.user import User
from app.api.v1.auth import get_current_active_expert, get_current_admin
from app.services.subdomain_service import subdomain_service

router = APIRouter()


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class SubDomainCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sla_hours: int = 24


class SubDomainUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sla_hours: Optional[int] = None
    is_active: Optional[bool] = None


class ExpertBrief(BaseModel):
    id: UUID
    name: str
    email: str

    class Config:
        from_attributes = True


class SubDomainResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    sla_hours: int
    is_active: bool
    created_at: datetime
    expert_count: int = 0

    class Config:
        from_attributes = True


class SubDomainDetailResponse(SubDomainResponse):
    experts: List[ExpertBrief] = []


class ExpertAssignRequest(BaseModel):
    expert_ids: List[UUID]


class SubDomainListResponse(BaseModel):
    items: List[SubDomainResponse]
    total: int


# ------------------------------------------------------------------
# Read endpoints (expert+)
# ------------------------------------------------------------------

@router.get("/", response_model=SubDomainListResponse)
async def list_subdomains(
    active_only: bool = False,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """List all sub-domains for the organization."""
    subdomains = await subdomain_service.list_subdomains(
        db, current_user.organization_id, active_only=active_only
    )

    items = []
    for sd in subdomains:
        count = await subdomain_service.get_expert_count(db, sd.id)
        items.append(SubDomainResponse(
            id=sd.id,
            name=sd.name,
            description=sd.description,
            sla_hours=sd.sla_hours,
            is_active=sd.is_active,
            created_at=sd.created_at,
            expert_count=count,
        ))

    return SubDomainListResponse(items=items, total=len(items))


@router.get("/{subdomain_id}", response_model=SubDomainDetailResponse)
async def get_subdomain(
    subdomain_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Get sub-domain detail with assigned experts."""
    sd = await subdomain_service.get_subdomain(db, subdomain_id)
    if not sd or sd.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Sub-domain not found")

    experts = await subdomain_service.get_experts_for_subdomain(db, subdomain_id)
    count = len(experts)

    return SubDomainDetailResponse(
        id=sd.id,
        name=sd.name,
        description=sd.description,
        sla_hours=sd.sla_hours,
        is_active=sd.is_active,
        created_at=sd.created_at,
        expert_count=count,
        experts=[ExpertBrief(id=e.id, name=e.name, email=e.email) for e in experts],
    )


# ------------------------------------------------------------------
# Write endpoints (admin-only)
# ------------------------------------------------------------------

@router.post("/", response_model=SubDomainResponse, status_code=status.HTTP_201_CREATED)
async def create_subdomain(
    data: SubDomainCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new sub-domain."""
    # Check for duplicate name
    existing = await db.execute(
        select(SubDomain).where(
            SubDomain.organization_id == current_user.organization_id,
            SubDomain.name == data.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Sub-domain with this name already exists")

    sd = await subdomain_service.create_subdomain(
        db=db,
        organization_id=current_user.organization_id,
        name=data.name,
        description=data.description,
        sla_hours=data.sla_hours,
    )
    return SubDomainResponse(
        id=sd.id,
        name=sd.name,
        description=sd.description,
        sla_hours=sd.sla_hours,
        is_active=sd.is_active,
        created_at=sd.created_at,
        expert_count=0,
    )


@router.put("/{subdomain_id}", response_model=SubDomainResponse)
async def update_subdomain(
    subdomain_id: UUID,
    data: SubDomainUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a sub-domain."""
    sd = await subdomain_service.get_subdomain(db, subdomain_id)
    if not sd or sd.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Sub-domain not found")

    sd = await subdomain_service.update_subdomain(
        db=db,
        subdomain=sd,
        name=data.name,
        description=data.description,
        sla_hours=data.sla_hours,
        is_active=data.is_active,
    )
    count = await subdomain_service.get_expert_count(db, sd.id)
    return SubDomainResponse(
        id=sd.id,
        name=sd.name,
        description=sd.description,
        sla_hours=sd.sla_hours,
        is_active=sd.is_active,
        created_at=sd.created_at,
        expert_count=count,
    )


@router.delete("/{subdomain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_subdomain(
    subdomain_id: UUID,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a sub-domain (soft delete)."""
    sd = await subdomain_service.get_subdomain(db, subdomain_id)
    if not sd or sd.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Sub-domain not found")

    await subdomain_service.delete_subdomain(db, sd)


# ------------------------------------------------------------------
# Expert assignment (admin-only)
# ------------------------------------------------------------------

@router.post("/{subdomain_id}/experts", response_model=SubDomainDetailResponse)
async def assign_experts(
    subdomain_id: UUID,
    data: ExpertAssignRequest,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Assign experts to a sub-domain (replaces current assignments)."""
    sd = await subdomain_service.get_subdomain(db, subdomain_id)
    if not sd or sd.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Sub-domain not found")

    await subdomain_service.assign_experts(db, subdomain_id, data.expert_ids)

    experts = await subdomain_service.get_experts_for_subdomain(db, subdomain_id)
    return SubDomainDetailResponse(
        id=sd.id,
        name=sd.name,
        description=sd.description,
        sla_hours=sd.sla_hours,
        is_active=sd.is_active,
        created_at=sd.created_at,
        expert_count=len(experts),
        experts=[ExpertBrief(id=e.id, name=e.name, email=e.email) for e in experts],
    )


@router.delete("/{subdomain_id}/experts/{expert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_expert(
    subdomain_id: UUID,
    expert_id: UUID,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Remove an expert from a sub-domain."""
    sd = await subdomain_service.get_subdomain(db, subdomain_id)
    if not sd or sd.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Sub-domain not found")

    removed = await subdomain_service.remove_expert(db, subdomain_id, expert_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Expert not assigned to this sub-domain")


@router.get("/{subdomain_id}/experts", response_model=List[ExpertBrief])
async def list_subdomain_experts(
    subdomain_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """List experts assigned to a sub-domain."""
    sd = await subdomain_service.get_subdomain(db, subdomain_id)
    if not sd or sd.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Sub-domain not found")

    experts = await subdomain_service.get_experts_for_subdomain(db, subdomain_id)
    return [ExpertBrief(id=e.id, name=e.name, email=e.email) for e in experts]

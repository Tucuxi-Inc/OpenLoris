"""
Users API — list, create, edit, delete users. Manage roles and status.
Admin and expert routes.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.subdomain import SubDomain, ExpertSubDomainAssignment
from app.api.v1.auth import get_current_active_expert, get_current_admin, get_password_hash

router = APIRouter()


# ---------- Schemas ----------

class SubDomainBrief(BaseModel):
    id: UUID
    name: str


class UserListItem(BaseModel):
    id: UUID
    email: str
    name: str
    role: UserRole
    department: Optional[str] = None
    title: Optional[str] = None
    is_active: bool
    is_verified: bool
    subdomain_assignments: List[SubDomainBrief] = []

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: list[UserListItem]
    total: int
    page: int
    page_size: int


class SubDomainAssignmentUpdate(BaseModel):
    subdomain_ids: List[UUID]


class RoleUpdate(BaseModel):
    role: UserRole


class StatusUpdate(BaseModel):
    is_active: bool


class UserCreateRequest(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: UserRole = UserRole.BUSINESS_USER
    department: Optional[str] = None
    title: Optional[str] = None


class UserEditRequest(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    email: Optional[EmailStr] = None


# ---------- Routes ----------

@router.get("/", response_model=UserListResponse)
async def list_users(
    role: Optional[UserRole] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """List users in the current organization."""
    stmt = select(User).where(
        User.organization_id == current_user.organization_id
    )
    if role:
        stmt = stmt.where(User.role == role)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.order_by(User.name).offset(offset).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    # Fetch sub-domain assignments for all users in one query
    user_ids = [u.id for u in rows]
    sd_stmt = (
        select(ExpertSubDomainAssignment.expert_id, SubDomain.id, SubDomain.name)
        .join(SubDomain, SubDomain.id == ExpertSubDomainAssignment.subdomain_id)
        .where(ExpertSubDomainAssignment.expert_id.in_(user_ids))
    )
    sd_rows = (await db.execute(sd_stmt)).all()
    # Group by user
    user_sds: dict[UUID, list[SubDomainBrief]] = {}
    for expert_id, sd_id, sd_name in sd_rows:
        user_sds.setdefault(expert_id, []).append(SubDomainBrief(id=sd_id, name=sd_name))

    users_out = []
    for u in rows:
        item = UserListItem.model_validate(u)
        item.subdomain_assignments = user_sds.get(u.id, [])
        users_out.append(item)

    return UserListResponse(
        users=users_out,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserListItem)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Get user detail."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserListItem)
async def create_user(
    data: UserCreateRequest,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user in the admin's organization."""
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        name=data.name,
        hashed_password=get_password_hash(data.password),
        organization_id=current_user.organization_id,
        role=data.role,
        department=data.department,
        title=data.title,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserListItem)
async def edit_user(
    user_id: UUID,
    data: UserEditRequest,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Edit user details (admin only)."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.email is not None and data.email != user.email:
        existing = await db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = data.email

    if data.name is not None:
        user.name = data.name
    if data.department is not None:
        user.department = data.department
    if data.title is not None:
        user.title = data.title

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user (admin only). Cannot delete yourself."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}


@router.put("/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    data: RoleUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's role (admin only)."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    user.role = data.role
    await db.commit()
    return {"message": f"Role updated to {data.role.value}"}


@router.put("/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    data: StatusUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Activate or deactivate a user (admin only)."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own status")

    user.is_active = data.is_active
    await db.commit()
    action = "activated" if data.is_active else "deactivated"
    return {"message": f"User {action}"}


@router.put("/{user_id}/subdomains")
async def update_user_subdomains(
    user_id: UUID,
    data: SubDomainAssignmentUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Set sub-domain assignments for a user (admin only). Replaces all existing assignments."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete existing assignments
    await db.execute(
        sa_delete(ExpertSubDomainAssignment).where(
            ExpertSubDomainAssignment.expert_id == user_id
        )
    )

    # Create new assignments
    for sd_id in data.subdomain_ids:
        # Verify the sub-domain exists in the same org
        sd_result = await db.execute(
            select(SubDomain).where(
                SubDomain.id == sd_id,
                SubDomain.organization_id == current_user.organization_id,
            )
        )
        if not sd_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Sub-domain {sd_id} not found")
        db.add(ExpertSubDomainAssignment(expert_id=user_id, subdomain_id=sd_id))

    await db.commit()

    # Return updated assignments
    sd_stmt = (
        select(SubDomain.id, SubDomain.name)
        .join(ExpertSubDomainAssignment, SubDomain.id == ExpertSubDomainAssignment.subdomain_id)
        .where(ExpertSubDomainAssignment.expert_id == user_id)
    )
    sd_rows = (await db.execute(sd_stmt)).all()
    return [SubDomainBrief(id=r[0], name=r[1]) for r in sd_rows]

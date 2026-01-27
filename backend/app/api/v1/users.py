"""
Users API — list, create, edit, delete users. Manage roles and status.
Admin and expert routes.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User, UserRole
from app.api.v1.auth import get_current_active_expert, get_current_admin, get_password_hash

router = APIRouter()


# ---------- Schemas ----------

class UserListItem(BaseModel):
    id: UUID
    email: str
    name: str
    role: UserRole
    department: Optional[str] = None
    title: Optional[str] = None
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: list[UserListItem]
    total: int
    page: int
    page_size: int


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

    return UserListResponse(
        users=rows,
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

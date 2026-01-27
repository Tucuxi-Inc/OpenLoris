"""
Documents API — upload, CRUD, fact extraction, candidate approval/rejection,
GUD management, and department management.
Expert-only routes.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_active_expert
from app.services.document_service import document_service
from app.services.document_expiration_service import document_expiration_service

router = APIRouter()


# ---------- Schemas ----------

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    topics: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    department: Optional[str] = None
    responsible_person: Optional[str] = None
    responsible_email: Optional[str] = None
    good_until_date: Optional[str] = None
    is_perpetual: Optional[bool] = None
    auto_delete_on_expiry: Optional[bool] = None
    document_type: Optional[str] = None


class CandidateApproval(BaseModel):
    modified_text: Optional[str] = None
    domain: Optional[str] = None
    importance: Optional[int] = None


class CandidateRejection(BaseModel):
    reason: str


class GudExtension(BaseModel):
    new_good_until_date: Optional[str] = None
    is_perpetual: bool = False


class DepartmentCreate(BaseModel):
    name: str
    contact_email: Optional[str] = None


# ---------- Routes: Documents ----------

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("other"),
    domain: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    responsible_person: Optional[str] = Form(None),
    responsible_email: Optional[str] = Form(None),
    good_until_date: Optional[str] = Form(None),
    is_perpetual: bool = Form(True),
    auto_delete_on_expiry: bool = Form(False),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document with metadata and GUD fields."""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    doc, error = await document_service.ingest_document(
        db=db,
        file_bytes=file_bytes,
        original_filename=file.filename or "untitled",
        organization_id=current_user.organization_id,
        uploaded_by_id=current_user.id,
        document_type=document_type,
        domain=domain,
        title=title,
        description=description,
        department=department,
        responsible_person=responsible_person,
        responsible_email=responsible_email,
        good_until_date=good_until_date,
        is_perpetual=is_perpetual,
        auto_delete_on_expiry=auto_delete_on_expiry,
    )

    if not doc:
        raise HTTPException(status_code=500, detail=error or "Upload failed")

    result = document_service._doc_to_dict(doc)
    if error:
        result["parsing_error"] = error
    return result


@router.get("/")
async def list_documents(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """List documents with filters and pagination."""
    return await document_service.list_documents(
        db=db,
        organization_id=current_user.organization_id,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}")
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Get document detail + processing status."""
    doc = await document_service.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return document_service._doc_to_dict(doc)


@router.put("/{document_id}")
async def update_document(
    document_id: UUID,
    data: DocumentUpdate,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Update document metadata and GUD."""
    doc = await document_service.update_document(
        db, document_id, data.model_dump(exclude_none=True)
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return document_service._doc_to_dict(doc)


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its associated data."""
    if not await document_service.delete_document(db, document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted"}


# ---------- Routes: Fact extraction ----------

@router.post("/{document_id}/extract")
async def trigger_extraction(
    document_id: UUID,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Trigger fact extraction from a parsed document."""
    count, error = await document_service.extract_facts(db, document_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"extracted_count": count}


@router.get("/{document_id}/facts")
async def get_document_facts(
    document_id: UUID,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Get extracted fact candidates for a document."""
    candidates = await document_service.get_candidates(db, document_id, status=status)
    return {"candidates": candidates, "total": len(candidates)}


# ---------- Routes: Candidate approval / rejection ----------

@router.post("/facts/{candidate_id}/approve", status_code=status.HTTP_201_CREATED)
async def approve_candidate(
    candidate_id: UUID,
    data: CandidateApproval = CandidateApproval(),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Approve a fact candidate → create WisdomFact."""
    fact, error = await document_service.approve_candidate(
        db=db,
        candidate_id=candidate_id,
        expert_user_id=current_user.id,
        organization_id=current_user.organization_id,
        modified_text=data.modified_text,
        domain=data.domain,
        importance=data.importance,
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    from app.services.knowledge_service import knowledge_service
    return knowledge_service._fact_to_dict(fact)


@router.post("/facts/{candidate_id}/reject")
async def reject_candidate(
    candidate_id: UUID,
    data: CandidateRejection,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Reject a fact candidate with reason."""
    if not await document_service.reject_candidate(
        db=db,
        candidate_id=candidate_id,
        expert_user_id=current_user.id,
        reason=data.reason,
    ):
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {"message": "Candidate rejected"}


# ---------- Routes: GUD management ----------

@router.post("/{document_id}/extend")
async def extend_gud(
    document_id: UUID,
    data: GudExtension,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Extend a document's Good Until Date or mark perpetual."""
    new_gud = None
    if data.new_good_until_date:
        try:
            new_gud = date.fromisoformat(data.new_good_until_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    doc = await document_expiration_service.extend_validity(
        db=db,
        document_id=document_id,
        new_gud=new_gud,
        is_perpetual=data.is_perpetual,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return document_service._doc_to_dict(doc)


@router.get("/expiring/list")
async def get_expiring_documents(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Documents expiring within N days."""
    docs = await document_expiration_service.get_expiring_soon(
        db=db,
        organization_id=current_user.organization_id,
        days=days,
    )
    return {
        "documents": [document_service._doc_to_dict(d) for d in docs],
        "total": len(docs),
    }


# ---------- Routes: Departments ----------

@router.get("/departments/list")
async def list_departments(
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """List departments for this organization."""
    depts = await document_expiration_service.get_departments(
        db=db, organization_id=current_user.organization_id
    )
    return {
        "departments": [
            {
                "id": str(d.id),
                "name": d.name,
                "contact_email": d.contact_email,
                "is_active": d.is_active,
            }
            for d in depts
        ]
    }


@router.post("/departments", status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreate,
    current_user: User = Depends(get_current_active_expert),
    db: AsyncSession = Depends(get_db),
):
    """Create a new department."""
    dept = await document_expiration_service.create_department(
        db=db,
        organization_id=current_user.organization_id,
        name=data.name,
        contact_email=data.contact_email,
    )
    return {
        "id": str(dept.id),
        "name": dept.name,
        "contact_email": dept.contact_email,
    }

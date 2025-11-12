"""
Email draft management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from src.database import get_db
from src.models import EmailDraft, DraftStatus, EmailTemplate
from src.services.drafting import generate_email_draft, generate_email_drafts_bulk
from src.services.approval import approve_draft, reject_draft, get_pending_approvals
from src.services.sending import send_email, send_emails_bulk
from src.services.spam_checker import check_spam_score
from src.services.quota_manager import GmailQuotaManager
from src.services.cost_tracker import CostTracker

router = APIRouter(prefix="/api/drafts", tags=["drafts"])


# Pydantic models
class DraftCreate(BaseModel):
    contact_id: int
    template_id: Optional[int] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class DraftUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    status: Optional[DraftStatus] = None


class DraftResponse(BaseModel):
    id: int
    contact_id: int
    subject: str
    body: str
    status: str
    quality_score: Optional[float]
    created_at: str

    class Config:
        from_attributes = True


class ApprovalRequest(BaseModel):
    notes: Optional[str] = None


class RejectionRequest(BaseModel):
    reason: str


class SendRequest(BaseModel):
    mock_mode: bool = False


@router.post("/", response_model=DraftResponse)
def create_draft(draft: DraftCreate, db: Session = Depends(get_db)):
    """Create a new email draft."""
    from src.models import Contact

    contact = db.query(Contact).filter(Contact.id == draft.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Get template if specified
    template = None
    if draft.template_id:
        template = db.query(EmailTemplate).filter(EmailTemplate.id == draft.template_id).first()
    elif draft.subject and draft.body:
        template = EmailTemplate(subject=draft.subject, body=draft.body)

    if not template:
        raise HTTPException(status_code=400, detail="Either template_id or subject+body required")

    try:
        cost_tracker = CostTracker(db, user_id=1)
        new_draft = generate_email_draft(contact, template, db, cost_tracker=cost_tracker)

        return new_draft

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Draft generation failed: {str(e)}")


@router.get("/", response_model=List[DraftResponse])
def list_drafts(
    skip: int = 0,
    limit: int = 100,
    status: Optional[DraftStatus] = None,
    db: Session = Depends(get_db)
):
    """List all drafts."""
    query = db.query(EmailDraft)

    if status:
        query = query.filter(EmailDraft.status == status)

    drafts = query.offset(skip).limit(limit).all()
    return drafts


@router.get("/{draft_id}", response_model=DraftResponse)
def get_draft(draft_id: int, db: Session = Depends(get_db)):
    """Get a specific draft."""
    draft = db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    return draft


@router.put("/{draft_id}", response_model=DraftResponse)
def update_draft(draft_id: int, updates: DraftUpdate, db: Session = Depends(get_db)):
    """Update a draft."""
    draft = db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status == DraftStatus.SENT:
        raise HTTPException(status_code=400, detail="Cannot update sent draft")

    # Update fields
    if updates.subject:
        draft.subject = updates.subject
    if updates.body:
        draft.body = updates.body
    if updates.status:
        draft.status = updates.status

    db.commit()
    db.refresh(draft)

    return draft


@router.delete("/{draft_id}")
def delete_draft(draft_id: int, db: Session = Depends(get_db)):
    """Delete a draft."""
    draft = db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status == DraftStatus.SENT:
        raise HTTPException(status_code=400, detail="Cannot delete sent draft")

    db.delete(draft)
    db.commit()

    return {"message": "Draft deleted successfully"}


@router.post("/{draft_id}/approve")
def approve_draft_endpoint(
    draft_id: int,
    request: ApprovalRequest,
    db: Session = Depends(get_db)
):
    """Approve a draft for sending."""
    try:
        draft = approve_draft(draft_id, user_id=1, db=db, notes=request.notes)
        return {"message": "Draft approved", "draft": draft}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{draft_id}/reject")
def reject_draft_endpoint(
    draft_id: int,
    request: RejectionRequest,
    db: Session = Depends(get_db)
):
    """Reject a draft."""
    try:
        draft = reject_draft(draft_id, user_id=1, db=db, reason=request.reason)
        return {"message": "Draft rejected", "draft": draft}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pending/approvals", response_model=List[DraftResponse])
def get_pending_approvals_endpoint(db: Session = Depends(get_db)):
    """Get all drafts pending approval."""
    drafts = get_pending_approvals(db, user_id=1)
    return drafts


@router.post("/{draft_id}/send")
def send_draft(draft_id: int, request: SendRequest, db: Session = Depends(get_db)):
    """Send an approved draft."""
    try:
        quota_tracker = GmailQuotaManager(db, user_id=1)

        result = send_email(
            draft_id=draft_id,
            db=db,
            mock_mode=request.mock_mode,
            quota_tracker=quota_tracker
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/send/bulk")
def send_drafts_bulk_endpoint(
    draft_ids: List[int],
    mock_mode: bool = False,
    db: Session = Depends(get_db)
):
    """Send multiple drafts in bulk."""
    try:
        quota_tracker = GmailQuotaManager(db, user_id=1)

        results = send_emails_bulk(
            draft_ids=draft_ids,
            db=db,
            quota_tracker=quota_tracker
        )

        return {
            "message": f"Processed {len(results)} drafts",
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{draft_id}/spam-score")
def check_draft_spam_score(draft_id: int, db: Session = Depends(get_db)):
    """Check spam score for a draft."""
    draft = db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    result = check_spam_score(draft)
    return result

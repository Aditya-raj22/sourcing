"""
Campaign workflow API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from src.database import get_db
from src.models import Contact, EmailTemplate, EmailDraft
from src.services.clustering import cluster_contacts
from src.services.drafting import generate_email_drafts_bulk
from src.services.followup import check_and_generate_followups
from src.services.cost_tracker import CostTracker
from src.services.import_export import export_campaign_data

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


# Pydantic models
class ClusterRequest(BaseModel):
    contact_ids: List[int]
    n_clusters: Optional[int] = None
    auto_k: bool = True


class ClusterResponse(BaseModel):
    id: int
    label: str
    contact_count: int
    contacts: List[int]


class BulkDraftRequest(BaseModel):
    contact_ids: List[int]
    template_id: int


class FollowupRequest(BaseModel):
    days_since_send: int = 7
    max_followup_count: int = 2


@router.post("/cluster", response_model=List[ClusterResponse])
def cluster_contacts_endpoint(request: ClusterRequest, db: Session = Depends(get_db)):
    """Cluster contacts by similarity for targeted campaigns."""
    contacts = db.query(Contact).filter(Contact.id.in_(request.contact_ids)).all()

    if not contacts:
        raise HTTPException(status_code=404, detail="No contacts found")

    # Check if contacts have embeddings
    missing_embeddings = [c for c in contacts if not c.embedding]
    if missing_embeddings:
        raise HTTPException(
            status_code=400,
            detail=f"{len(missing_embeddings)} contacts missing embeddings. Enrich them first."
        )

    try:
        cost_tracker = CostTracker(db, user_id=1)

        clusters = cluster_contacts(
            contacts=contacts,
            n_clusters=request.n_clusters,
            auto_k=request.auto_k,
            db=db,
            cost_tracker=cost_tracker
        )

        # Format response
        response = []
        for i, cluster in enumerate(clusters):
            response.append({
                "id": i,
                "label": cluster.label,
                "contact_count": len(cluster.contacts),
                "contacts": [c.id for c in cluster.contacts]
            })

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(e)}")


@router.post("/drafts/bulk")
def generate_bulk_drafts(request: BulkDraftRequest, db: Session = Depends(get_db)):
    """Generate drafts for multiple contacts using a template."""
    contacts = db.query(Contact).filter(Contact.id.in_(request.contact_ids)).all()

    if not contacts:
        raise HTTPException(status_code=404, detail="No contacts found")

    template = db.query(EmailTemplate).filter(EmailTemplate.id == request.template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        cost_tracker = CostTracker(db, user_id=1)

        drafts = generate_email_drafts_bulk(
            contacts=contacts,
            template=template,
            db=db,
            cost_tracker=cost_tracker
        )

        return {
            "message": f"Generated {len(drafts)} drafts",
            "draft_ids": [d.id for d in drafts]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk draft generation failed: {str(e)}")


@router.post("/followups/generate")
def generate_followups(request: FollowupRequest, db: Session = Depends(get_db)):
    """Generate follow-up emails for non-responders."""
    try:
        cost_tracker = CostTracker(db, user_id=1)

        followups = check_and_generate_followups(
            db=db,
            days_since_send=request.days_since_send,
            max_followup_count=request.max_followup_count,
            cost_tracker=cost_tracker
        )

        return {
            "message": f"Generated {len(followups)} follow-up drafts",
            "draft_ids": [f.id for f in followups]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Follow-up generation failed: {str(e)}")


@router.get("/export")
def export_campaign(
    campaign_id: Optional[int] = None,
    include_drafts: bool = True,
    include_replies: bool = True,
    db: Session = Depends(get_db)
):
    """Export complete campaign data."""
    try:
        data = export_campaign_data(
            db=db,
            campaign_id=campaign_id,
            user_id=1,
            include_drafts=include_drafts,
            include_replies=include_replies
        )

        return data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/stats")
def get_campaign_stats(db: Session = Depends(get_db)):
    """Get campaign statistics."""
    from src.models import DraftStatus, ContactStatus

    total_contacts = db.query(Contact).filter(Contact.deleted == False).count()
    enriched_contacts = db.query(Contact).filter(
        Contact.status == ContactStatus.ENRICHED
    ).count()

    total_drafts = db.query(EmailDraft).count()
    sent_drafts = db.query(EmailDraft).filter(
        EmailDraft.status == DraftStatus.SENT
    ).count()
    pending_drafts = db.query(EmailDraft).filter(
        EmailDraft.status == DraftStatus.PENDING_APPROVAL
    ).count()

    from src.models import Reply
    total_replies = db.query(Reply).count()

    return {
        "contacts": {
            "total": total_contacts,
            "enriched": enriched_contacts
        },
        "drafts": {
            "total": total_drafts,
            "sent": sent_drafts,
            "pending": pending_drafts
        },
        "replies": {
            "total": total_replies
        }
    }

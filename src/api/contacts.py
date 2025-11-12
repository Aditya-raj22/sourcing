"""
Contact management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from src.database import get_db
from src.models import Contact, ContactStatus
from src.services.import_export import import_contacts, export_contacts, delete_contact_data
from src.services.enrichment import enrich_contact, enrich_contacts_batch
from src.services.cost_tracker import CostTracker

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


# Pydantic models
class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    title: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None


class ContactResponse(BaseModel):
    id: int
    name: str
    email: str
    company: Optional[str]
    title: Optional[str]
    status: str
    relevance_score: Optional[float]
    created_at: str

    class Config:
        from_attributes = True


class ImportResponse(BaseModel):
    success_count: int
    error_count: int
    duplicates: List[str]
    errors: List[str]


@router.post("/", response_model=ContactResponse)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    """Create a new contact."""
    # Check for duplicates
    existing = db.query(Contact).filter(Contact.email == contact.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Contact with this email already exists")

    new_contact = Contact(**contact.dict(), status=ContactStatus.IMPORTED)
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)

    return new_contact


@router.get("/", response_model=List[ContactResponse])
def list_contacts(
    skip: int = 0,
    limit: int = 100,
    status: Optional[ContactStatus] = None,
    db: Session = Depends(get_db)
):
    """List all contacts."""
    query = db.query(Contact).filter(Contact.deleted == False)

    if status:
        query = query.filter(Contact.status == status)

    contacts = query.offset(skip).limit(limit).all()
    return contacts


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """Get a specific contact."""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.deleted == False
    ).first()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    return contact


@router.delete("/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    """Delete a contact (GDPR compliance - soft delete)."""
    success = delete_contact_data(db, contact_id)

    if not success:
        raise HTTPException(status_code=404, detail="Contact not found")

    return {"message": "Contact deleted successfully"}


@router.post("/import", response_model=ImportResponse)
async def import_contacts_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import contacts from CSV file."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV format")

    content = await file.read()
    csv_content = content.decode('utf-8')

    result = import_contacts(csv_content, db)

    return {
        "success_count": result.success_count,
        "error_count": result.error_count,
        "duplicates": result.duplicates,
        "errors": result.errors
    }


@router.get("/export/csv")
def export_contacts_csv(
    status: Optional[ContactStatus] = None,
    db: Session = Depends(get_db)
):
    """Export contacts to CSV."""
    csv_data = export_contacts(db, status=status, format="csv")

    return {
        "content": csv_data,
        "filename": f"contacts_{status.value if status else 'all'}.csv"
    }


@router.post("/{contact_id}/enrich")
def enrich_contact_endpoint(contact_id: int, db: Session = Depends(get_db)):
    """Enrich a single contact with AI."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    try:
        cost_tracker = CostTracker(db, user_id=1)  # TODO: Get real user ID
        enriched = enrich_contact(contact, db, cost_tracker=cost_tracker)

        return {
            "message": "Contact enriched successfully",
            "contact": enriched
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")


@router.post("/enrich/batch")
def enrich_contacts_batch_endpoint(
    contact_ids: List[int],
    db: Session = Depends(get_db)
):
    """Enrich multiple contacts in batch."""
    contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()

    if not contacts:
        raise HTTPException(status_code=404, detail="No contacts found")

    try:
        cost_tracker = CostTracker(db, user_id=1)
        enriched = enrich_contacts_batch(contacts, db, cost_tracker=cost_tracker)

        return {
            "message": f"Enriched {len(enriched)} contacts",
            "count": len(enriched)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch enrichment failed: {str(e)}")

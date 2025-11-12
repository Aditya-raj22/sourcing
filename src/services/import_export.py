"""
Data import and export services.
"""

import csv
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from io import StringIO
from sqlalchemy.orm import Session
from src.models import Contact, ContactStatus, EmailDraft, Reply
from src.utils.helpers import validate_email, parse_csv_content
import logging

logger = logging.getLogger(__name__)


class ImportResult:
    """Result of import operation."""

    def __init__(self):
        self.contacts: List[Contact] = []
        self.success_count: int = 0
        self.error_count: int = 0
        self.errors: List[str] = []
        self.duplicates: List[str] = []


def import_contacts(
    csv_content: str,
    db: Session,
    user_id: Optional[int] = None,
    skip_duplicates: bool = True
) -> ImportResult:
    """
    Import contacts from CSV content.

    Args:
        csv_content: CSV string content
        db: Database session
        user_id: Optional user ID
        skip_duplicates: If True, skip duplicate emails

    Returns:
        ImportResult object
    """
    result = ImportResult()

    try:
        # Parse CSV
        reader = csv.DictReader(StringIO(csv_content))

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
            try:
                # Required fields
                name = row.get("name", "").strip()
                email = row.get("email", "").strip()

                if not name or not email:
                    result.errors.append(f"Row {row_num}: Missing name or email")
                    result.error_count += 1
                    continue

                # Validate email
                if not validate_email(email):
                    result.errors.append(f"Row {row_num}: Invalid email '{email}'")
                    result.error_count += 1
                    continue

                # Check for duplicates
                existing = db.query(Contact).filter(Contact.email == email).first()
                if existing:
                    if skip_duplicates:
                        result.duplicates.append(email)
                        continue
                    else:
                        result.errors.append(f"Row {row_num}: Duplicate email '{email}'")
                        result.error_count += 1
                        continue

                # Create contact
                contact = Contact(
                    name=name,
                    email=email,
                    company=row.get("company", "").strip() or None,
                    title=row.get("title", "").strip() or None,
                    industry=row.get("industry", "").strip() or None,
                    location=row.get("location", "").strip() or None,
                    phone=row.get("phone", "").strip() or None,
                    linkedin_url=row.get("linkedin_url", "").strip() or None,
                    website=row.get("website", "").strip() or None,
                    notes=row.get("notes", "").strip() or None,
                    status=ContactStatus.IMPORTED,
                    user_id=user_id,
                    created_at=datetime.utcnow()
                )

                db.add(contact)
                result.contacts.append(contact)
                result.success_count += 1

            except Exception as e:
                result.errors.append(f"Row {row_num}: {str(e)}")
                result.error_count += 1
                logger.error(f"Error importing row {row_num}: {e}")

        # Commit all contacts
        db.commit()

        logger.info(f"Imported {result.success_count} contacts, {result.error_count} errors, "
                   f"{len(result.duplicates)} duplicates")

    except Exception as e:
        db.rollback()
        result.errors.append(f"Import failed: {str(e)}")
        logger.error(f"Failed to import contacts: {e}")

    return result


def export_contacts(
    db: Session,
    user_id: Optional[int] = None,
    status: Optional[ContactStatus] = None,
    format: str = "csv"
) -> str:
    """
    Export contacts to CSV or JSON.

    Args:
        db: Database session
        user_id: Optional user ID filter
        status: Optional status filter
        format: Export format ("csv" or "json")

    Returns:
        Exported data as string
    """
    # Build query
    query = db.query(Contact).filter(Contact.deleted == False)

    if user_id:
        query = query.filter(Contact.user_id == user_id)

    if status:
        query = query.filter(Contact.status == status)

    contacts = query.all()

    if format == "csv":
        return _export_contacts_csv(contacts)
    elif format == "json":
        return _export_contacts_json(contacts)
    else:
        raise ValueError(f"Unsupported export format: {format}")


def _export_contacts_csv(contacts: List[Contact]) -> str:
    """Export contacts as CSV string."""
    output = StringIO()

    fieldnames = [
        "id", "name", "email", "company", "title", "industry", "location",
        "phone", "linkedin_url", "website", "status", "relevance_score",
        "created_at", "updated_at"
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for contact in contacts:
        writer.writerow({
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "company": contact.company or "",
            "title": contact.title or "",
            "industry": contact.industry or "",
            "location": contact.location or "",
            "phone": contact.phone or "",
            "linkedin_url": contact.linkedin_url or "",
            "website": contact.website or "",
            "status": contact.status.value if contact.status else "",
            "relevance_score": contact.relevance_score or "",
            "created_at": contact.created_at.isoformat() if contact.created_at else "",
            "updated_at": contact.updated_at.isoformat() if contact.updated_at else ""
        })

    return output.getvalue()


def _export_contacts_json(contacts: List[Contact]) -> str:
    """Export contacts as JSON string."""
    data = []

    for contact in contacts:
        data.append({
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "company": contact.company,
            "title": contact.title,
            "industry": contact.industry,
            "location": contact.location,
            "phone": contact.phone,
            "linkedin_url": contact.linkedin_url,
            "website": contact.website,
            "status": contact.status.value if contact.status else None,
            "relevance_score": contact.relevance_score,
            "created_at": contact.created_at.isoformat() if contact.created_at else None,
            "updated_at": contact.updated_at.isoformat() if contact.updated_at else None
        })

    return json.dumps(data, indent=2)


def export_campaign_data(
    db: Session,
    campaign_id: Optional[int] = None,
    user_id: Optional[int] = None,
    include_drafts: bool = True,
    include_replies: bool = True
) -> Dict[str, Any]:
    """
    Export complete campaign data including contacts, drafts, and replies.

    Args:
        db: Database session
        campaign_id: Optional campaign ID filter
        user_id: Optional user ID filter
        include_drafts: Include email drafts
        include_replies: Include replies

    Returns:
        Dictionary with campaign data
    """
    data = {
        "exported_at": datetime.utcnow().isoformat(),
        "contacts": [],
        "drafts": [],
        "replies": []
    }

    # Export contacts
    query = db.query(Contact).filter(Contact.deleted == False)
    if user_id:
        query = query.filter(Contact.user_id == user_id)

    contacts = query.all()
    data["contacts"] = [
        {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "company": c.company,
            "status": c.status.value if c.status else None
        }
        for c in contacts
    ]

    # Export drafts
    if include_drafts:
        contact_ids = [c.id for c in contacts]
        drafts = db.query(EmailDraft).filter(
            EmailDraft.contact_id.in_(contact_ids)
        ).all()

        data["drafts"] = [
            {
                "id": d.id,
                "contact_id": d.contact_id,
                "subject": d.subject,
                "status": d.status.value if d.status else None,
                "sent_at": d.sent_at.isoformat() if d.sent_at else None
            }
            for d in drafts
        ]

    # Export replies
    if include_replies:
        draft_ids = [d["id"] for d in data["drafts"]]
        replies = db.query(Reply).filter(
            Reply.draft_id.in_(draft_ids)
        ).all()

        data["replies"] = [
            {
                "id": r.id,
                "draft_id": r.draft_id,
                "from_email": r.from_email,
                "intent": r.intent.value if r.intent else None,
                "received_at": r.received_at.isoformat() if r.received_at else None
            }
            for r in replies
        ]

    return data


def delete_contact_data(db: Session, contact_id: int) -> bool:
    """
    Delete all data for a contact (GDPR compliance).

    Args:
        db: Database session
        contact_id: Contact ID to delete

    Returns:
        True if successful
    """
    try:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            return False

        # Soft delete contact
        contact.deleted = True
        contact.email = f"deleted_{contact_id}@deleted.com"
        contact.name = f"Deleted User {contact_id}"
        contact.phone = None
        contact.linkedin_url = None
        contact.notes = None

        # Also mark associated drafts and replies
        drafts = db.query(EmailDraft).filter(EmailDraft.contact_id == contact_id).all()
        for draft in drafts:
            draft.to_email = contact.email

        db.commit()
        logger.info(f"Deleted data for contact {contact_id}")

        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete contact data: {e}")
        return False

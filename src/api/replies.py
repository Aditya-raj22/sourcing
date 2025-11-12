"""
Reply management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
from src.database import get_db
from src.models import Reply, ReplyIntent
from src.services.reply_parser import ReplyParser, parse_reply_batch
from src.services.cost_tracker import CostTracker

router = APIRouter(prefix="/api/replies", tags=["replies"])


# Pydantic models
class ReplyCreate(BaseModel):
    draft_id: int
    from_email: EmailStr
    subject: str
    body: str
    received_at: Optional[datetime] = None
    in_reply_to: Optional[str] = None


class ReplyResponse(BaseModel):
    id: int
    draft_id: int
    from_email: str
    subject: str
    intent: Optional[str]
    received_at: str
    availability_text: Optional[str]

    class Config:
        from_attributes = True


class ReplyBatchCreate(BaseModel):
    replies: List[ReplyCreate]


@router.post("/", response_model=ReplyResponse)
def create_reply(reply: ReplyCreate, db: Session = Depends(get_db)):
    """Parse and save a new reply."""
    try:
        cost_tracker = CostTracker(db, user_id=1)
        parser = ReplyParser(db, cost_tracker=cost_tracker)

        parsed_reply = parser.parse_reply(
            draft_id=reply.draft_id,
            from_email=reply.from_email,
            subject=reply.subject,
            body=reply.body,
            received_at=reply.received_at,
            in_reply_to=reply.in_reply_to
        )

        return parsed_reply

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch", response_model=List[ReplyResponse])
def create_replies_batch(batch: ReplyBatchCreate, db: Session = Depends(get_db)):
    """Parse and save multiple replies in batch."""
    try:
        cost_tracker = CostTracker(db, user_id=1)

        reply_dicts = [r.dict() for r in batch.replies]
        parsed_replies = parse_reply_batch(reply_dicts, db, cost_tracker=cost_tracker)

        return parsed_replies

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch parsing failed: {str(e)}")


@router.get("/", response_model=List[ReplyResponse])
def list_replies(
    skip: int = 0,
    limit: int = 100,
    intent: Optional[ReplyIntent] = None,
    db: Session = Depends(get_db)
):
    """List all replies."""
    query = db.query(Reply)

    if intent:
        query = query.filter(Reply.intent == intent)

    replies = query.offset(skip).limit(limit).all()
    return replies


@router.get("/{reply_id}", response_model=ReplyResponse)
def get_reply(reply_id: int, db: Session = Depends(get_db)):
    """Get a specific reply."""
    reply = db.query(Reply).filter(Reply.id == reply_id).first()

    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")

    return reply


@router.post("/{reply_id}/reclassify")
def reclassify_reply(reply_id: int, db: Session = Depends(get_db)):
    """Re-classify a reply's intent."""
    try:
        cost_tracker = CostTracker(db, user_id=1)
        parser = ReplyParser(db, cost_tracker=cost_tracker)

        intent = parser.classify_reply_intent(reply_id)

        return {
            "message": "Reply reclassified",
            "reply_id": reply_id,
            "intent": intent.value
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/draft/{draft_id}", response_model=List[ReplyResponse])
def get_replies_for_draft(draft_id: int, db: Session = Depends(get_db)):
    """Get all replies for a specific draft."""
    replies = db.query(Reply).filter(Reply.draft_id == draft_id).all()

    return replies


@router.get("/stats/intents")
def get_reply_intent_stats(db: Session = Depends(get_db)):
    """Get statistics on reply intents."""
    from sqlalchemy import func

    stats = db.query(
        Reply.intent,
        func.count(Reply.id).label('count')
    ).group_by(Reply.intent).all()

    return {
        intent.value if intent else "UNCLASSIFIED": count
        for intent, count in stats
    }

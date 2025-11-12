"""
Reply parsing and classification service.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from src.models import Reply, EmailDraft, Contact, ReplyIntent
from src.config import config
from src.services.cost_tracker import CostTracker
from src.utils.helpers import strip_html, calculate_cost
import openai
import json
import logging

logger = logging.getLogger(__name__)

openai.api_key = config.OPENAI_API_KEY


class ReplyParser:
    """Parse and classify email replies."""

    def __init__(self, db: Session, cost_tracker: Optional[CostTracker] = None):
        self.db = db
        self.cost_tracker = cost_tracker

    def parse_reply(
        self,
        draft_id: int,
        from_email: str,
        subject: str,
        body: str,
        received_at: datetime = None,
        in_reply_to: str = None
    ) -> Reply:
        """
        Parse and save an email reply.

        Args:
            draft_id: ID of original draft
            from_email: Sender email
            subject: Reply subject
            body: Reply body (may contain HTML)
            received_at: When reply was received
            in_reply_to: Message-ID being replied to

        Returns:
            Reply object
        """
        # Get the draft
        draft = self.db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        # Strip HTML from body
        plain_body = strip_html(body)

        # Classify intent
        intent = self._classify_intent(plain_body)

        # Extract meeting availability if interested
        availability = None
        if intent == ReplyIntent.INTERESTED:
            availability = self._extract_availability(plain_body)

        # Create reply record
        reply = Reply(
            draft_id=draft_id,
            from_email=from_email,
            subject=subject,
            body=plain_body,
            intent=intent,
            received_at=received_at or datetime.utcnow(),
            in_reply_to=in_reply_to,
            availability_text=availability
        )

        self.db.add(reply)
        self.db.commit()
        self.db.refresh(reply)

        # Update contact status
        contact = self.db.query(Contact).filter(Contact.id == draft.contact_id).first()
        if contact and intent == ReplyIntent.INTERESTED:
            from src.models import ContactStatus
            contact.status = ContactStatus.REPLIED_INTERESTED
            self.db.commit()

        logger.info(f"Parsed reply from {from_email} with intent: {intent.value}")

        return reply

    def _classify_intent(self, body: str) -> ReplyIntent:
        """
        Classify reply intent using GPT-4.

        Args:
            body: Reply body text

        Returns:
            ReplyIntent enum
        """
        prompt = f"""Classify the intent of this email reply into one of these categories:
- INTERESTED: Positive response, wants to continue conversation
- DECLINE: Not interested, polite rejection
- OUT_OF_OFFICE: Automated out-of-office reply
- UNSUBSCRIBE: Wants to be removed from communications
- QUESTION: Asking for more information
- OTHER: Unclear or other intent

Reply text:
{body[:500]}

Respond with ONLY the category name (e.g., "INTERESTED").
"""

        try:
            response = openai.chat.completions.create(
                model=config.OPENAI_MODEL_GPT,
                messages=[
                    {"role": "system", "content": "You are an email intent classifier."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=20
            )

            intent_str = response.choices[0].message.content.strip().upper()

            # Track cost
            if self.cost_tracker:
                tokens_used = response.usage.total_tokens
                cost = calculate_cost("classification", config.OPENAI_MODEL_GPT, tokens_used)
                self.cost_tracker.track_operation(
                    operation_type="reply_classification",
                    model=config.OPENAI_MODEL_GPT,
                    tokens_used=tokens_used,
                    cost=cost
                )

            # Map to enum
            intent_map = {
                "INTERESTED": ReplyIntent.INTERESTED,
                "DECLINE": ReplyIntent.DECLINE,
                "OUT_OF_OFFICE": ReplyIntent.OUT_OF_OFFICE,
                "UNSUBSCRIBE": ReplyIntent.UNSUBSCRIBE,
                "QUESTION": ReplyIntent.QUESTION,
                "OTHER": ReplyIntent.OTHER
            }

            return intent_map.get(intent_str, ReplyIntent.OTHER)

        except Exception as e:
            logger.error(f"Failed to classify intent: {e}")
            return ReplyIntent.OTHER

    def _extract_availability(self, body: str) -> Optional[str]:
        """
        Extract meeting availability from reply text.

        Args:
            body: Reply body text

        Returns:
            Availability text or None
        """
        # Simple keyword matching for availability
        keywords = ["available", "free", "time", "tuesday", "wednesday", "thursday",
                   "friday", "monday", "morning", "afternoon", "evening", "schedule"]

        body_lower = body.lower()

        # Check if any availability keywords present
        if any(kw in body_lower for kw in keywords):
            # Extract sentences with availability info
            sentences = body.split('.')
            availability_sentences = [
                s.strip() for s in sentences
                if any(kw in s.lower() for kw in keywords)
            ]

            if availability_sentences:
                return ". ".join(availability_sentences[:2])  # Return first 2 relevant sentences

        return None

    def classify_reply_intent(self, reply_id: int) -> ReplyIntent:
        """
        Re-classify an existing reply's intent.

        Args:
            reply_id: Reply ID to classify

        Returns:
            ReplyIntent enum
        """
        reply = self.db.query(Reply).filter(Reply.id == reply_id).first()
        if not reply:
            raise ValueError(f"Reply {reply_id} not found")

        intent = self._classify_intent(reply.body)

        reply.intent = intent
        self.db.commit()

        return intent


def parse_reply_batch(
    replies: list,
    db: Session,
    cost_tracker: Optional[CostTracker] = None
) -> list:
    """
    Parse multiple replies in batch.

    Args:
        replies: List of reply dicts with keys: draft_id, from_email, subject, body
        db: Database session
        cost_tracker: Optional cost tracker

    Returns:
        List of Reply objects
    """
    parser = ReplyParser(db, cost_tracker=cost_tracker)

    parsed_replies = []
    for reply_data in replies:
        try:
            reply = parser.parse_reply(
                draft_id=reply_data["draft_id"],
                from_email=reply_data["from_email"],
                subject=reply_data.get("subject", ""),
                body=reply_data["body"],
                received_at=reply_data.get("received_at"),
                in_reply_to=reply_data.get("in_reply_to")
            )
            parsed_replies.append(reply)
        except Exception as e:
            logger.error(f"Failed to parse reply from {reply_data.get('from_email')}: {e}")

    return parsed_replies


def get_unprocessed_replies(db: Session, limit: int = 100) -> list:
    """
    Get replies that haven't been processed yet.

    Args:
        db: Database session
        limit: Maximum number of replies to return

    Returns:
        List of Reply objects
    """
    return db.query(Reply).filter(
        Reply.intent == None
    ).limit(limit).all()

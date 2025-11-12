"""
Follow-up email automation service.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from src.models import EmailDraft, DraftStatus, Contact, ContactStatus, Reply, EmailTemplate
from src.config import config
from src.services.drafting import generate_email_draft
from src.services.cost_tracker import CostTracker
import logging

logger = logging.getLogger(__name__)


class FollowupGenerator:
    """Generate follow-up emails for non-responders."""

    def __init__(self, db: Session, cost_tracker: Optional[CostTracker] = None):
        self.db = db
        self.cost_tracker = cost_tracker

    def check_and_generate_followups(
        self,
        days_since_send: int = 7,
        max_followup_count: int = 2,
        template: Optional[EmailTemplate] = None
    ) -> List[EmailDraft]:
        """
        Check for drafts that need follow-ups and generate them.

        Args:
            days_since_send: Days to wait before sending follow-up
            max_followup_count: Maximum number of follow-ups per contact
            template: Optional custom follow-up template

        Returns:
            List of generated follow-up drafts
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_since_send)

        # Find sent drafts that need follow-up
        sent_drafts = self.db.query(EmailDraft).filter(
            EmailDraft.status == DraftStatus.SENT,
            EmailDraft.sent_at <= cutoff_date,
            EmailDraft.followup_count < max_followup_count
        ).all()

        followup_drafts = []

        for draft in sent_drafts:
            # Check if contact has replied
            has_reply = self.db.query(Reply).filter(
                Reply.draft_id == draft.id
            ).first()

            if has_reply:
                logger.debug(f"Skipping follow-up for draft {draft.id} - contact replied")
                continue

            # Check if contact unsubscribed
            contact = self.db.query(Contact).filter(Contact.id == draft.contact_id).first()
            if not contact or contact.unsubscribed:
                logger.debug(f"Skipping follow-up for draft {draft.id} - contact unsubscribed")
                continue

            # Generate follow-up draft
            try:
                followup = self._generate_followup_draft(draft, contact, template)
                followup_drafts.append(followup)

                # Increment followup count on original draft
                draft.followup_count += 1
                self.db.commit()

                logger.info(f"Generated follow-up draft for contact {contact.email}")

            except Exception as e:
                logger.error(f"Failed to generate follow-up for draft {draft.id}: {e}")

        return followup_drafts

    def _generate_followup_draft(
        self,
        original_draft: EmailDraft,
        contact: Contact,
        template: Optional[EmailTemplate] = None
    ) -> EmailDraft:
        """
        Generate a follow-up draft based on the original email.

        Args:
            original_draft: Original sent draft
            contact: Contact to follow up with
            template: Optional custom template

        Returns:
            New EmailDraft for follow-up
        """
        if not template:
            # Use default follow-up template
            template = self._get_default_followup_template(original_draft)

        # Generate draft
        followup_draft = generate_email_draft(
            contact=contact,
            template=template,
            db=self.db,
            cost_tracker=self.cost_tracker,
            original_thread_id=original_draft.thread_id
        )

        # Mark as follow-up
        followup_draft.is_followup = True
        followup_draft.parent_draft_id = original_draft.id
        followup_draft.followup_sequence = original_draft.followup_count + 1

        self.db.commit()
        self.db.refresh(followup_draft)

        return followup_draft

    def _get_default_followup_template(self, original_draft: EmailDraft) -> EmailTemplate:
        """
        Create default follow-up template based on original email.

        Args:
            original_draft: Original sent draft

        Returns:
            EmailTemplate for follow-up
        """
        # Simple follow-up templates based on sequence
        if original_draft.followup_count == 0:
            # First follow-up
            subject = f"Re: {original_draft.subject}"
            body = f"""Hi {{{{name}}}},

I wanted to follow up on my previous email about {{{{topic}}}}.

{{{{original_value_prop}}}}

Would you have 15 minutes this week to discuss?

Best regards,
{{{{sender_name}}}}

---
Original message:
{original_draft.body[:200]}...
"""
        else:
            # Second+ follow-up
            subject = f"Re: {original_draft.subject}"
            body = f"""Hi {{{{name}}}},

I know you're busy, so I'll keep this brief.

I'd love to share how {{{{topic}}}} could benefit {{{{company}}}}.

If you're not interested, just let me know and I won't follow up again.

Best,
{{{{sender_name}}}}
"""

        return EmailTemplate(
            name=f"Auto Follow-up #{original_draft.followup_count + 1}",
            subject=subject,
            body=body
        )

    def schedule_followup(
        self,
        draft_id: int,
        days_delay: int = 7,
        template: Optional[EmailTemplate] = None
    ) -> EmailDraft:
        """
        Schedule a follow-up for a specific draft.

        Args:
            draft_id: Original draft ID
            days_delay: Days to wait before follow-up
            template: Optional custom template

        Returns:
            Generated follow-up draft
        """
        draft = self.db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        if draft.status != DraftStatus.SENT:
            raise ValueError(f"Draft {draft_id} not sent yet")

        contact = self.db.query(Contact).filter(Contact.id == draft.contact_id).first()
        if not contact:
            raise ValueError(f"Contact {draft.contact_id} not found")

        # Check if already has reply
        has_reply = self.db.query(Reply).filter(Reply.draft_id == draft_id).first()
        if has_reply:
            raise ValueError(f"Contact already replied to draft {draft_id}")

        # Generate follow-up
        followup = self._generate_followup_draft(draft, contact, template)

        # Schedule for future
        followup.scheduled_at = datetime.utcnow() + timedelta(days=days_delay)
        followup.status = DraftStatus.SCHEDULED

        self.db.commit()
        self.db.refresh(followup)

        return followup


def check_and_generate_followups(
    db: Session,
    days_since_send: int = 7,
    max_followup_count: int = 2,
    cost_tracker: Optional[CostTracker] = None
) -> List[EmailDraft]:
    """
    Convenience function to check and generate follow-ups.

    Args:
        db: Database session
        days_since_send: Days to wait before follow-up
        max_followup_count: Maximum follow-ups per contact
        cost_tracker: Optional cost tracker

    Returns:
        List of generated follow-up drafts
    """
    generator = FollowupGenerator(db, cost_tracker=cost_tracker)
    return generator.check_and_generate_followups(
        days_since_send=days_since_send,
        max_followup_count=max_followup_count
    )


def get_scheduled_followups(db: Session) -> List[EmailDraft]:
    """
    Get all scheduled follow-up drafts that are ready to send.

    Args:
        db: Database session

    Returns:
        List of EmailDraft objects ready to send
    """
    now = datetime.utcnow()

    return db.query(EmailDraft).filter(
        EmailDraft.status == DraftStatus.SCHEDULED,
        EmailDraft.is_followup == True,
        EmailDraft.scheduled_at <= now
    ).all()

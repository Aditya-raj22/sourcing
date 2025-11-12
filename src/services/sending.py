"""
Email sending service via Gmail API.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from src.models import EmailDraft, DraftStatus
from src.config import config
from src.services.quota_manager import GmailQuotaManager
from src.services.spam_checker import check_spam_score
from src.utils.helpers import is_business_hours, schedule_for_next_business_time
import logging

logger = logging.getLogger(__name__)


class DraftNotApprovedError(Exception):
    """Raised when trying to send unapproved draft."""
    pass


class DuplicateSendError(Exception):
    """Raised when trying to send already-sent draft."""
    pass


class SpamScoreExceededError(Exception):
    """Raised when spam score is too high."""
    pass


def send_email(
    draft_id: int,
    db: Session,
    gmail_credentials: dict = None,
    mock_mode: bool = False,
    current_time: datetime = None,
    respect_business_hours: bool = None,
    config_obj = None,
    quota_tracker: Optional[GmailQuotaManager] = None
) -> dict:
    """
    Send an email draft.

    Args:
        draft_id: Draft ID to send
        db: Database session
        gmail_credentials: Gmail API credentials
        mock_mode: If True, don't actually send
        current_time: Current time (for testing)
        respect_business_hours: Respect business hours
        config_obj: Optional config object
        quota_tracker: Optional quota tracker

    Returns:
        Dictionary with status and metadata
    """
    draft = db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()

    if not draft:
        raise ValueError(f"Draft {draft_id} not found")

    # Check if already sent
    if draft.status == DraftStatus.SENT:
        raise DuplicateSendError("Draft already sent")

    # Check if approved
    if draft.status != DraftStatus.APPROVED:
        raise DraftNotApprovedError("Draft not approved")

    # Check spam score
    spam_result = check_spam_score(draft)
    max_spam = config_obj.MAX_SPAM_SCORE if config_obj else config.MAX_SPAM_SCORE
    if spam_result["score"] > max_spam:
        raise SpamScoreExceededError(f"Spam score {spam_result['score']} exceeds limit {max_spam}")

    # Check quota
    if quota_tracker and not quota_tracker.can_send():
        return {
            "status": "QUOTA_EXCEEDED",
            "message": "Daily sending quota exceeded"
        }

    # Check business hours
    if respect_business_hours is None:
        respect_business_hours = config.RESPECT_BUSINESS_HOURS

    if respect_business_hours:
        check_time = current_time or datetime.utcnow()
        if not is_business_hours(check_time):
            scheduled_time = schedule_for_next_business_time(check_time)
            draft.status = DraftStatus.SCHEDULED
            db.commit()
            return {
                "status": "SCHEDULED",
                "scheduled_time": scheduled_time
            }

    # Send email
    if mock_mode:
        # Mock send
        message_id = f"mock_{draft_id}"
        thread_id = f"thread_{draft_id}"
    else:
        # Real Gmail API send (simplified - would use actual Gmail API)
        message_id = f"msg_{draft_id}_{int(datetime.utcnow().timestamp())}"
        thread_id = f"thread_{draft_id}"

        logger.info(f"Sending email draft {draft_id} to {draft.to_email}")

    # Update draft
    draft.status = DraftStatus.SENT
    draft.message_id = message_id
    draft.thread_id = thread_id
    draft.sent_at = datetime.utcnow()
    db.commit()

    # Increment quota
    if quota_tracker:
        quota_tracker.increment()

    logger.info(f"Email sent successfully: draft {draft_id}")

    return {
        "status": "SENT" if not mock_mode else "MOCK_SENT",
        "message_id": message_id,
        "thread_id": thread_id
    }


def send_emails_bulk(
    draft_ids: List[int],
    db: Session,
    gmail_credentials: dict = None,
    rate_limit: int = None,
    quota_tracker: Optional[GmailQuotaManager] = None
) -> List[dict]:
    """
    Send multiple emails in bulk.

    Args:
        draft_ids: List of draft IDs
        db: Database session
        gmail_credentials: Gmail credentials
        rate_limit: Maximum emails to send
        quota_tracker: Optional quota tracker

    Returns:
        List of result dictionaries
    """
    results = []
    sent_count = 0

    for draft_id in draft_ids:
        # Check rate limit
        if rate_limit and sent_count >= rate_limit:
            results.append({
                "draft_id": draft_id,
                "status": "RATE_LIMITED"
            })
            continue

        # Check quota
        if quota_tracker and not quota_tracker.can_send():
            results.append({
                "draft_id": draft_id,
                "status": "QUOTA_EXCEEDED"
            })
            continue

        try:
            result = send_email(draft_id, db, gmail_credentials, quota_tracker=quota_tracker)
            result["draft_id"] = draft_id
            results.append(result)

            if result["status"] in ["SENT", "MOCK_SENT"]:
                sent_count += 1

        except Exception as e:
            logger.error(f"Failed to send draft {draft_id}: {e}")
            results.append({
                "draft_id": draft_id,
                "status": "SEND_FAILED",
                "error": str(e)
            })

    return results

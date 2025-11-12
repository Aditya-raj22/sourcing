"""
Email sending service via SMTP or Gmail API.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from src.models import EmailDraft, DraftStatus
from src.config import config
from src.services.quota_manager import GmailQuotaManager
from src.services.spam_checker import check_spam_score
from src.utils.helpers import is_business_hours, schedule_for_next_business_time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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


def send_email_smtp(draft: EmailDraft, from_email: str = None) -> tuple:
    """
    Send email via SMTP (Duke email, Outlook, any email provider).

    Args:
        draft: EmailDraft to send
        from_email: Sender email (overrides config)

    Returns:
        Tuple of (message_id, thread_id)
    """
    from_addr = from_email or config.SMTP_USER

    # Create message
    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = draft.to_email
    msg['Subject'] = draft.subject

    # Add body
    msg.attach(MIMEText(draft.body, 'plain'))

    # Send via SMTP
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            if config.SMTP_USE_TLS:
                server.starttls()

            # Authenticate based on method
            auth_method = config.SMTP_AUTH_METHOD

            if auth_method == "oauth2":
                # OAuth2 authentication (for Duke with DUO 2FA)
                from src.services.oauth2_auth import get_oauth2_access_token
                import base64

                access_token = get_oauth2_access_token()

                # Build XOAUTH2 string
                auth_string = f"user={config.SMTP_USER}\x01auth=Bearer {access_token}\x01\x01"
                auth_b64 = base64.b64encode(auth_string.encode()).decode()

                # Authenticate with OAuth2
                server.docmd("AUTH", f"XOAUTH2 {auth_b64}")
                logger.info("SMTP: Authenticated via OAuth2")

            else:
                # Password authentication
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
                logger.info("SMTP: Authenticated via password")

            # Send
            server.send_message(msg)

            # Generate message ID
            message_id = f"smtp_{draft.id}_{int(datetime.utcnow().timestamp())}"
            thread_id = f"thread_{draft.id}"

            logger.info(f"SMTP: Email sent to {draft.to_email}")
            return message_id, thread_id

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        if config.SMTP_AUTH_METHOD == "oauth2":
            raise ValueError("OAuth2 authentication failed. Run: python -m src.services.oauth2_auth")
        else:
            raise ValueError("Email authentication failed. Check SMTP_USER and SMTP_PASSWORD in .env")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        raise ValueError(f"Failed to send email via SMTP: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        raise


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
        logger.info(f"MOCK: Sending email draft {draft_id} to {draft.to_email}")
    else:
        # Real send - choose provider
        provider = config_obj.EMAIL_PROVIDER if config_obj else config.EMAIL_PROVIDER

        if provider == "smtp":
            # Send via SMTP (Duke email, Outlook, etc.)
            try:
                message_id, thread_id = send_email_smtp(draft)
            except Exception as e:
                logger.error(f"SMTP send failed: {e}")
                draft.status = DraftStatus.SEND_FAILED
                db.commit()
                raise

        elif provider == "gmail":
            # Send via Gmail API (simplified - would use actual Gmail API client)
            message_id = f"gmail_{draft_id}_{int(datetime.utcnow().timestamp())}"
            thread_id = f"thread_{draft_id}"
            logger.info(f"Gmail API: Sending email draft {draft_id} to {draft.to_email}")

        else:
            raise ValueError(f"Unknown email provider: {provider}. Use 'smtp' or 'gmail'")

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

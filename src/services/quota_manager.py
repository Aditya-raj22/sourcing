"""
Gmail quota management service.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.models import QuotaUsage
from src.config import config
import logging

logger = logging.getLogger(__name__)


class GmailQuotaManager:
    """Manage Gmail daily sending quota."""

    def __init__(self, db: Session, user_id: int = 1, daily_limit: int = None):
        self.db = db
        self.user_id = user_id
        self.daily_limit = daily_limit or config.GMAIL_DAILY_SEND_LIMIT
        self._ensure_quota_record()

    def _ensure_quota_record(self):
        """Ensure quota record exists for today."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        quota = self.db.query(QuotaUsage).filter(
            QuotaUsage.user_id == self.user_id,
            QuotaUsage.date == today
        ).first()

        if not quota:
            quota = QuotaUsage(
                user_id=self.user_id,
                date=today,
                emails_sent=0,
                quota_limit=self.daily_limit
            )
            self.db.add(quota)
            self.db.commit()
            logger.info(f"Created quota record for {today.date()}")

    def increment(self, count: int = 1):
        """
        Increment sent email count.

        Args:
            count: Number of emails sent (default 1)
        """
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        quota = self.db.query(QuotaUsage).filter(
            QuotaUsage.user_id == self.user_id,
            QuotaUsage.date == today
        ).first()

        if quota:
            quota.emails_sent += count
            self.db.commit()
            logger.info(f"Incremented quota: {quota.emails_sent}/{self.daily_limit}")
        else:
            logger.error("Quota record not found")

    def get_used_quota(self) -> int:
        """Get number of emails sent today."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        quota = self.db.query(QuotaUsage).filter(
            QuotaUsage.user_id == self.user_id,
            QuotaUsage.date == today
        ).first()

        return quota.emails_sent if quota else 0

    def get_remaining_quota(self) -> int:
        """Get remaining quota for today."""
        return max(0, self.daily_limit - self.get_used_quota())

    def can_send(self, count: int = 1) -> bool:
        """
        Check if can send specified number of emails.

        Args:
            count: Number of emails to send

        Returns:
            True if within quota, False otherwise
        """
        remaining = self.get_remaining_quota()

        if remaining < count:
            logger.warning(f"Quota exceeded: {remaining} remaining, {count} requested")
            return False

        return True

    def check_and_reset(self, current_time: datetime = None):
        """
        Check if need to reset quota (new day).

        Args:
            current_time: Current time (for testing)
        """
        if current_time is None:
            current_time = datetime.utcnow()

        today = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get most recent quota record
        latest = self.db.query(QuotaUsage).filter(
            QuotaUsage.user_id == self.user_id
        ).order_by(QuotaUsage.date.desc()).first()

        if latest and latest.date < today:
            logger.info(f"New day detected, resetting quota")
            self._ensure_quota_record()

    def reset(self):
        """Manually reset quota (for testing)."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        quota = self.db.query(QuotaUsage).filter(
            QuotaUsage.user_id == self.user_id,
            QuotaUsage.date == today
        ).first()

        if quota:
            quota.emails_sent = 0
            self.db.commit()
            logger.info("Quota reset to 0")

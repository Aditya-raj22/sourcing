"""
Draft approval workflow service.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from src.models import EmailDraft, DraftStatus, AuditLog, Contact
import logging

logger = logging.getLogger(__name__)


class ApprovalWorkflow:
    """Manage draft approval workflow."""

    def __init__(self, db: Session):
        self.db = db

    def approve_draft(
        self,
        draft_id: int,
        user_id: int,
        notes: Optional[str] = None
    ) -> EmailDraft:
        """
        Approve a draft for sending.

        Args:
            draft_id: Draft ID to approve
            user_id: User ID approving the draft
            notes: Optional approval notes

        Returns:
            Approved EmailDraft
        """
        draft = self.db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        if draft.status == DraftStatus.APPROVED:
            logger.warning(f"Draft {draft_id} already approved")
            return draft

        if draft.status == DraftStatus.SENT:
            raise ValueError(f"Draft {draft_id} already sent")

        # Update status
        old_status = draft.status
        draft.status = DraftStatus.APPROVED
        draft.approved_by = user_id
        draft.approved_at = datetime.utcnow()

        # Log the approval
        audit_log = AuditLog(
            user_id=user_id,
            action="approve_draft",
            entity_type="EmailDraft",
            entity_id=draft_id,
            old_value=old_status.value,
            new_value=DraftStatus.APPROVED.value,
            notes=notes,
            timestamp=datetime.utcnow()
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(draft)

        logger.info(f"Draft {draft_id} approved by user {user_id}")

        return draft

    def reject_draft(
        self,
        draft_id: int,
        user_id: int,
        reason: Optional[str] = None
    ) -> EmailDraft:
        """
        Reject a draft.

        Args:
            draft_id: Draft ID to reject
            user_id: User ID rejecting the draft
            reason: Optional rejection reason

        Returns:
            Rejected EmailDraft
        """
        draft = self.db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        if draft.status == DraftStatus.SENT:
            raise ValueError(f"Draft {draft_id} already sent")

        # Update status
        old_status = draft.status
        draft.status = DraftStatus.REJECTED
        draft.rejected_by = user_id
        draft.rejected_at = datetime.utcnow()
        draft.rejection_reason = reason

        # Log the rejection
        audit_log = AuditLog(
            user_id=user_id,
            action="reject_draft",
            entity_type="EmailDraft",
            entity_id=draft_id,
            old_value=old_status.value,
            new_value=DraftStatus.REJECTED.value,
            notes=reason,
            timestamp=datetime.utcnow()
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(draft)

        logger.info(f"Draft {draft_id} rejected by user {user_id}: {reason}")

        return draft

    def bulk_approve_drafts(
        self,
        draft_ids: List[int],
        user_id: int
    ) -> dict:
        """
        Approve multiple drafts at once.

        Args:
            draft_ids: List of draft IDs
            user_id: User ID approving the drafts

        Returns:
            Dictionary with success and failure counts
        """
        result = {
            "approved": [],
            "failed": [],
            "already_approved": []
        }

        for draft_id in draft_ids:
            try:
                draft = self.approve_draft(draft_id, user_id)

                if draft.status == DraftStatus.APPROVED:
                    result["approved"].append(draft_id)
                else:
                    result["already_approved"].append(draft_id)

            except Exception as e:
                logger.error(f"Failed to approve draft {draft_id}: {e}")
                result["failed"].append({"draft_id": draft_id, "error": str(e)})

        logger.info(f"Bulk approved {len(result['approved'])} drafts by user {user_id}")

        return result

    def get_pending_approvals(
        self,
        user_id: Optional[int] = None,
        limit: int = 100
    ) -> List[EmailDraft]:
        """
        Get drafts pending approval.

        Args:
            user_id: Optional user ID filter
            limit: Maximum number of drafts

        Returns:
            List of EmailDraft objects
        """
        query = self.db.query(EmailDraft).filter(
            EmailDraft.status == DraftStatus.PENDING_APPROVAL
        )

        if user_id:
            query = query.join(Contact).filter(Contact.user_id == user_id)

        return query.order_by(EmailDraft.created_at.desc()).limit(limit).all()

    def auto_approve_drafts(
        self,
        quality_threshold: float = 8.0,
        user_id: Optional[int] = None
    ) -> List[EmailDraft]:
        """
        Auto-approve high-quality drafts above threshold.

        Args:
            quality_threshold: Minimum quality score (0-10)
            user_id: User ID for audit logging

        Returns:
            List of auto-approved drafts
        """
        # Get pending drafts with high quality
        query = self.db.query(EmailDraft).filter(
            EmailDraft.status == DraftStatus.PENDING_APPROVAL,
            EmailDraft.quality_score >= quality_threshold
        )

        drafts = query.all()
        approved = []

        for draft in drafts:
            try:
                self.approve_draft(
                    draft.id,
                    user_id=user_id or 0,  # System user
                    notes="Auto-approved (high quality score)"
                )
                approved.append(draft)

            except Exception as e:
                logger.error(f"Failed to auto-approve draft {draft.id}: {e}")

        logger.info(f"Auto-approved {len(approved)} high-quality drafts")

        return approved


def approve_draft(draft_id: int, user_id: int, db: Session, notes: Optional[str] = None) -> EmailDraft:
    """
    Convenience function to approve a draft.

    Args:
        draft_id: Draft ID
        user_id: User ID
        db: Database session
        notes: Optional notes

    Returns:
        Approved EmailDraft
    """
    workflow = ApprovalWorkflow(db)
    return workflow.approve_draft(draft_id, user_id, notes)


def reject_draft(draft_id: int, user_id: int, db: Session, reason: Optional[str] = None) -> EmailDraft:
    """
    Convenience function to reject a draft.

    Args:
        draft_id: Draft ID
        user_id: User ID
        db: Database session
        reason: Optional rejection reason

    Returns:
        Rejected EmailDraft
    """
    workflow = ApprovalWorkflow(db)
    return workflow.reject_draft(draft_id, user_id, reason)


def get_pending_approvals(db: Session, user_id: Optional[int] = None) -> List[EmailDraft]:
    """
    Get drafts pending approval.

    Args:
        db: Database session
        user_id: Optional user ID filter

    Returns:
        List of pending EmailDraft objects
    """
    workflow = ApprovalWorkflow(db)
    return workflow.get_pending_approvals(user_id=user_id)

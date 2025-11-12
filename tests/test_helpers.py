"""
Mock objects, helper classes, and utilities for testing the AI outreach engine.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, MagicMock
import random
import string


# ============================================================================
# Enums
# ============================================================================

class ContactStatus(Enum):
    IMPORTED = "imported"
    ENRICHED = "enriched"
    ENRICHMENT_FAILED = "enrichment_failed"
    RATE_LIMITED = "rate_limited"
    EMAIL_SENT = "email_sent"


class DraftStatus(Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    SEND_FAILED = "send_failed"
    SCHEDULED = "scheduled"


class SendStatus(Enum):
    SENT = "sent"
    MOCK_SENT = "mock_sent"
    SEND_FAILED = "send_failed"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    SCHEDULED = "scheduled"


class ReplyIntent(Enum):
    INTERESTED = "interested"
    MAYBE = "maybe"
    DECLINE = "decline"
    AUTO_REPLY = "auto_reply"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Contact:
    email: str
    id: Optional[int] = None
    name: Optional[str] = None
    industry: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    painpoint: Optional[str] = None
    relevance_score: Optional[float] = None
    status: ContactStatus = ContactStatus.IMPORTED
    user_id: Optional[int] = None
    timezone: str = "UTC"
    unsubscribed: bool = False
    unsubscribed_at: Optional[datetime] = None
    do_not_followup: bool = False
    deleted: bool = False
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class EmailDraft:
    contact_id: int
    id: Optional[int] = None
    to_email: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    status: DraftStatus = DraftStatus.PENDING_APPROVAL
    from_email: str = "sender@example.com"
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approval_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    edited: bool = False
    cancel_reason: Optional[str] = None
    attachments: List[str] = field(default_factory=list)
    unsubscribe_url: Optional[str] = None
    user_id: Optional[int] = None
    followup_sequence_number: int = 0
    original_draft_id: Optional[int] = None


@dataclass
class Reply:
    draft_id: int
    id: Optional[int] = None
    from_email: Optional[str] = None
    body: str = ""
    intent: Optional[ReplyIntent] = None
    confidence: float = 0.0
    attachments: List[str] = field(default_factory=list)
    has_inline_images: bool = False
    cc_recipients: List[str] = field(default_factory=list)
    received_at: datetime = field(default_factory=datetime.now)


@dataclass
class EmailTemplate:
    subject: str
    body: str
    id: Optional[int] = None
    name: Optional[str] = None


@dataclass
class Config:
    daily_budget_limit: float = 100.00
    gmail_daily_limit: int = 100
    max_spam_score: float = 5.0
    skip_weekends: bool = False
    respect_business_hours: bool = True


@dataclass
class ImportResult:
    contacts: List[Contact] = field(default_factory=list)
    errors: List[Any] = field(default_factory=list)
    duplicates: List[Any] = field(default_factory=list)
    import_time_seconds: float = 0.0


@dataclass
class EnrichmentResult:
    completed_count: int = 0
    failed_count: int = 0
    stopped_reason: Optional[str] = None
    status: str = "success"
    error_message: Optional[str] = None


@dataclass
class CostEstimate:
    min_cost: float
    max_cost: float
    estimated_cost: float
    breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class SpamScore:
    score: float
    warnings: List[str] = field(default_factory=list)
    recommendation: str = "OK"


@dataclass
class SpamAnalysis:
    suggestions: List[str] = field(default_factory=list)
    improved_subject: Optional[str] = None


# ============================================================================
# Mock Database
# ============================================================================

class MockDatabase:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.contacts: Dict[int, Contact] = {}
        self.drafts: Dict[int, EmailDraft] = {}
        self.replies: Dict[int, Reply] = {}
        self.audit_log: List[Dict] = []
        self._next_contact_id = 1
        self._next_draft_id = 1
        self._next_reply_id = 1

    def migrate(self):
        """Run migrations (no-op for mock)."""
        pass

    def close(self):
        """Close database connection."""
        pass

    def save_contact(self, contact: Contact) -> int:
        if contact.id is None:
            contact.id = self._next_contact_id
            self._next_contact_id += 1
        self.contacts[contact.id] = contact
        return contact.id

    def get_contact(self, contact_id: int, include_deleted: bool = False) -> Optional[Contact]:
        contact = self.contacts.get(contact_id)
        if contact and (include_deleted or not contact.deleted):
            return contact
        return None

    def update_contact_status(self, contact_id: int, status: ContactStatus, user_id: Optional[int] = None):
        if contact_id in self.contacts:
            old_status = self.contacts[contact_id].status
            self.contacts[contact_id].status = status
            self.audit_log.append({
                "contact_id": contact_id,
                "old_status": old_status,
                "new_status": status,
                "user_id": user_id,
                "timestamp": datetime.now()
            })

    def save_draft(self, draft: EmailDraft) -> int:
        if draft.id is None:
            draft.id = self._next_draft_id
            self._next_draft_id += 1
        self.drafts[draft.id] = draft
        return draft.id

    def get_draft(self, draft_id: int) -> Optional[EmailDraft]:
        return self.drafts.get(draft_id)

    def get_drafts_by_status(self, status: DraftStatus) -> List[EmailDraft]:
        return [d for d in self.drafts.values() if d.status == status]

    def get_drafts_by_user(self, user_id: int) -> List[EmailDraft]:
        return [d for d in self.drafts.values() if d.user_id == user_id]

    def get_drafts_for_contact(self, contact_id: int) -> List[EmailDraft]:
        return [d for d in self.drafts.values() if d.contact_id == contact_id]

    def update_draft(self, draft_id: int, **kwargs):
        if draft_id in self.drafts:
            for key, value in kwargs.items():
                setattr(self.drafts[draft_id], key, value)

    def save_reply(self, reply: Reply) -> int:
        if reply.id is None:
            reply.id = self._next_reply_id
            self._next_reply_id += 1
        self.replies[reply.id] = reply
        return reply.id

    def get_reply_for_draft(self, draft_id: int) -> Optional[Reply]:
        for reply in self.replies.values():
            if reply.draft_id == draft_id:
                return reply
        return None

    def get_replies_for_draft(self, draft_id: int) -> List[Reply]:
        return [r for r in self.replies.values() if r.draft_id == draft_id]

    def delete_contact(self, contact_id: int):
        if contact_id in self.contacts:
            self.contacts[contact_id].deleted = True

    def count_contacts(self) -> int:
        return len([c for c in self.contacts.values() if not c.deleted])

    def count_contacts_by_status(self, status: ContactStatus) -> int:
        return len([c for c in self.contacts.values() if c.status == status and not c.deleted])

    def get_contacts_by_user(self, user_id: int) -> List[Contact]:
        return [c for c in self.contacts.values() if c.user_id == user_id and not c.deleted]

    def get_audit_log(self, contact_id: int) -> List[Dict]:
        return [log for log in self.audit_log if log["contact_id"] == contact_id]

    def transaction(self):
        """Return a mock transaction context manager."""
        from contextlib import contextmanager
        @contextmanager
        def _transaction():
            try:
                yield
            except Exception:
                # In a real implementation, would rollback
                raise
        return _transaction()


# ============================================================================
# Mock API Clients
# ============================================================================

class MockOpenAIClient:
    def __init__(self):
        self.call_count = 0
        self.fail_after_n_calls = None
        self.fail_indices = []
        self.mock_response = None
        self.timeout = False
        self.complete_failure = False

    def enrich_contact(self, contact: Contact) -> Contact:
        self.call_count += 1

        if self.complete_failure:
            raise Exception("OpenAI API complete failure")

        if self.timeout:
            raise TimeoutError("OpenAI API timeout")

        if self.fail_after_n_calls and self.call_count > self.fail_after_n_calls:
            raise Exception("Rate limit exceeded")

        if self.call_count - 1 in self.fail_indices:
            raise Exception("Enrichment failed for this contact")

        if self.mock_response:
            for key, value in self.mock_response.items():
                setattr(contact, key, value)
            contact.status = ContactStatus.ENRICHED
            return contact

        # Default enrichment
        contact.title = "VP of Engineering"
        contact.company = f"{contact.name}'s Company"
        contact.painpoint = "Looking for better solutions"
        contact.relevance_score = 7.5
        contact.status = ContactStatus.ENRICHED
        return contact

    def generate_embedding(self, text: str):
        """Generate a mock embedding vector."""
        return [random.random() for _ in range(1536)]

    def generate_draft(self, contact: Contact, template: EmailTemplate) -> EmailDraft:
        """Generate a mock email draft."""
        subject = template.subject.replace("{{name}}", contact.name or "there")
        body = template.body
        body = body.replace("{{name}}", contact.name or "there")
        body = body.replace("{{company}}", contact.company or "your organization")
        body = body.replace("{{industry}}", contact.industry or "your industry")
        body = body.replace("{{painpoint}}", contact.painpoint or "industry challenges")

        return EmailDraft(
            contact_id=contact.id,
            to_email=contact.email,
            subject=subject,
            body=body,
            status=DraftStatus.PENDING_APPROVAL
        )

    def classify_reply(self, reply: Reply) -> ReplyIntent:
        """Classify reply intent."""
        body_lower = reply.body.lower()

        if any(word in body_lower for word in ["interested", "yes", "love to", "schedule", "call"]):
            reply.intent = ReplyIntent.INTERESTED
            reply.confidence = 0.9
        elif any(word in body_lower for word in ["not interested", "no thanks", "decline"]):
            reply.intent = ReplyIntent.DECLINE
            reply.confidence = 0.9
        elif any(word in body_lower for word in ["out of office", "away", "auto"]):
            reply.intent = ReplyIntent.AUTO_REPLY
            reply.confidence = 0.95
        else:
            reply.intent = ReplyIntent.MAYBE
            reply.confidence = 0.6

        return reply.intent


class MockGmailAPI:
    def __init__(self):
        self.sent_messages = []
        self.replies = []
        self.fail_on_send = False
        self.last_response = {}

    def send_message(self, draft: EmailDraft) -> Dict[str, str]:
        if self.fail_on_send:
            raise Exception("Gmail API send failed")

        message_id = f"msg_{len(self.sent_messages) + 1}"
        thread_id = draft.thread_id or f"thread_{len(self.sent_messages) + 1}"

        self.sent_messages.append({
            "message_id": message_id,
            "thread_id": thread_id,
            "draft": draft
        })

        return {"message_id": message_id, "thread_id": thread_id}

    def add_reply(self, thread_id: str, from_email: str = "recipient@example.com",
                  body: str = "", cc: List[str] = None):
        self.replies.append({
            "thread_id": thread_id,
            "from_email": from_email,
            "body": body,
            "cc": cc or []
        })

    def get_last_sent_message(self):
        if self.sent_messages:
            return self.sent_messages[-1]["draft"]
        return None

    def set_response(self, message_id: str, thread_id: str):
        self.last_response = {"message_id": message_id, "thread_id": thread_id}


# ============================================================================
# Mock Services
# ============================================================================

class CostTracker:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.enrichment_cost = 0.0
        self.embedding_cost = 0.0
        self.draft_generation_cost = 0.0
        self.calls = []

    def track_enrichment(self, num_contacts: int, model: str = "gpt-4-turbo"):
        cost = num_contacts * 0.01  # Mock cost
        self.enrichment_cost += cost
        self.calls.append({"type": "enrichment", "cost": cost, "model": model})

    def track_embedding(self, num_embeddings: int, model: str = "text-embedding-3-small"):
        cost = num_embeddings * 0.0001  # Mock cost
        self.embedding_cost += cost
        self.calls.append({"type": "embedding", "cost": cost, "model": model})

    def track_draft(self, num_drafts: int, model: str = "gpt-4-turbo"):
        cost = num_drafts * 0.005  # Mock cost
        self.draft_generation_cost += cost
        self.calls.append({"type": "draft", "cost": cost, "model": model})

    def get_total_cost(self) -> float:
        return self.enrichment_cost + self.embedding_cost + self.draft_generation_cost

    def get_breakdown(self) -> Dict[str, float]:
        breakdown = {}
        for call in self.calls:
            model = call["model"]
            if model not in breakdown:
                breakdown[model] = 0.0
            breakdown[model] += call["cost"]
        return breakdown

    def check_budget(self) -> bool:
        return self.get_total_cost() < self.config.daily_budget_limit


class GmailQuotaTracker:
    def __init__(self, daily_limit: int = 100, config: Optional[Config] = None):
        self.daily_limit = daily_limit
        self.used_quota = 0
        self.last_reset = datetime.now()

    def increment(self):
        self.used_quota += 1

    def get_used_quota(self) -> int:
        return self.used_quota

    def get_remaining_quota(self) -> int:
        return max(0, self.daily_limit - self.used_quota)

    def check_and_reset(self, current_time: datetime):
        if current_time.date() > self.last_reset.date():
            self.used_quota = 0
            self.last_reset = current_time

    def can_send(self) -> bool:
        return self.used_quota < self.daily_limit


class AlertService:
    def __init__(self, failure_threshold: float = 0.10):
        self.failure_threshold = failure_threshold
        self.sent_alerts = []

    def check_failure_rate(self, total: int, failed: int):
        if total == 0:
            return

        failure_rate = failed / total
        if failure_rate > self.failure_threshold:
            self.send_alert(f"High failure rate: {int(failure_rate * 100)}%")

    def send_alert(self, message: str):
        self.sent_alerts.append({
            "message": message,
            "timestamp": datetime.now()
        })

    def get_sent_alerts(self) -> List[Dict]:
        return self.sent_alerts


class NotificationService:
    def __init__(self, user_email: str):
        self.user_email = user_email
        self.sent_notifications = []

    def send_notification(self, message: str, priority: str = "NORMAL"):
        self.sent_notifications.append({
            "message": message,
            "priority": priority,
            "timestamp": datetime.now()
        })

    def get_sent_notifications(self) -> List[Dict]:
        return self.sent_notifications


class DraftQualityTracker:
    def __init__(self):
        self.scores = []

    def score_draft(self, draft: EmailDraft) -> float:
        # Mock scoring logic
        score = 7.0
        if draft.body and len(draft.body) > 50:
            score += 1.0
        if draft.subject and len(draft.subject) > 10:
            score += 0.5
        return min(10.0, score)

    def record_score(self, score: float):
        self.scores.append(score)

    def get_metrics(self):
        if not self.scores:
            return Mock(average_score=0, trend="STABLE", alert_triggered=False)

        average = sum(self.scores) / len(self.scores)
        trend = "STABLE"

        if len(self.scores) >= 10:
            recent = sum(self.scores[-5:]) / 5
            older = sum(self.scores[-10:-5]) / 5
            if recent < older - 1.0:
                trend = "DECLINING"

        return Mock(
            average_score=average,
            trend=trend,
            alert_triggered=(trend == "DECLINING")
        )


# ============================================================================
# Helper Functions
# ============================================================================

def generate_csv_with_n_contacts(n: int) -> str:
    """Generate a CSV with n contacts."""
    lines = ["name,email,industry"]
    for i in range(n):
        lines.append(f"User{i},user{i}@example.com,Industry{i % 5}")
    return "\n".join(lines)


def generate_random_token(length: int = 32) -> str:
    """Generate a random token."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def parse_csv(csv_content: str) -> List[Dict]:
    """Parse CSV content into list of dicts."""
    lines = csv_content.strip().split("\n")
    if len(lines) < 2:
        return []

    headers = lines[0].split(",")
    result = []

    for line in lines[1:]:
        values = line.split(",")
        row = {headers[i]: values[i] if i < len(values) else "" for i in range(len(headers))}
        result.append(row)

    return result


def contains_aggressive_language(text: str) -> bool:
    """Check if text contains aggressive language."""
    aggressive_words = ["must", "urgent!!", "act now", "limited time"]
    return any(word.lower() in text.lower() for word in aggressive_words)


def contains_overly_casual_language(text: str) -> bool:
    """Check if text is overly casual."""
    casual_words = ["hey", "sup", "yo", "lol"]
    return any(word in text.lower() for word in casual_words)


def has_professional_greeting(text: str) -> bool:
    """Check if text has a professional greeting."""
    greetings = ["hi ", "hello ", "dear ", "good morning", "good afternoon"]
    return any(greeting in text.lower() for greeting in greetings)


# ============================================================================
# Exception Classes
# ============================================================================

class InvalidStateTransition(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class DuplicateSendError(Exception):
    """Raised when attempting to send the same draft twice."""
    pass


class DraftNotApprovedError(Exception):
    """Raised when attempting to send an unapproved draft."""
    pass


class ContactUnsubscribedError(Exception):
    """Raised when attempting to email an unsubscribed contact."""
    pass


class SpamScoreExceededError(Exception):
    """Raised when email spam score exceeds threshold."""
    pass

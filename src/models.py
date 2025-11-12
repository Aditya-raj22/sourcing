"""
SQLAlchemy database models for the outreach engine.
"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum, create_engine, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session

Base = declarative_base()


# Enums
class ContactStatus(PyEnum):
    IMPORTED = "imported"
    ENRICHED = "enriched"
    ENRICHMENT_FAILED = "enrichment_failed"
    RATE_LIMITED = "rate_limited"
    EMAIL_SENT = "email_sent"


class DraftStatus(PyEnum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    SEND_FAILED = "send_failed"
    SCHEDULED = "scheduled"


class ReplyIntent(PyEnum):
    INTERESTED = "interested"
    MAYBE = "maybe"
    DECLINE = "decline"
    AUTO_REPLY = "auto_reply"


# Models
class Contact(Base):
    """Contact model representing a person to reach out to."""
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, default=1)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    industry = Column(String)

    # Enriched fields
    title = Column(String)
    company = Column(String)
    painpoint = Column(Text)
    relevance_score = Column(Float)

    # Status and metadata
    status = Column(Enum(ContactStatus), default=ContactStatus.IMPORTED, index=True)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Preferences and flags
    timezone = Column(String, default="UTC")
    unsubscribed = Column(Boolean, default=False, index=True)
    unsubscribed_at = Column(DateTime)
    do_not_followup = Column(Boolean, default=False)
    deleted = Column(Boolean, default=False, index=True)

    # Embeddings for clustering
    embedding = Column(JSON)  # Stored as JSON array

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    drafts = relationship("EmailDraft", back_populates="contact")
    audit_logs = relationship("AuditLog", back_populates="contact")

    # Indexes
    __table_args__ = (
        Index('idx_contact_email_status', 'email', 'status'),
        Index('idx_contact_user_deleted', 'user_id', 'deleted'),
    )


class EmailTemplate(Base):
    """Email template model."""
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, default=1)
    name = Column(String)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailDraft(Base):
    """Email draft model."""
    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    user_id = Column(Integer, index=True, default=1)

    # Email content
    to_email = Column(String, nullable=False)
    from_email = Column(String, default="sender@example.com")
    subject = Column(String)
    body = Column(Text)
    attachments = Column(JSON)  # List of attachment paths

    # Status and workflow
    status = Column(Enum(DraftStatus), default=DraftStatus.PENDING_APPROVAL, index=True)
    approved_at = Column(DateTime)
    approved_by = Column(Integer)
    approval_notes = Column(Text)
    rejection_reason = Column(Text)
    cancel_reason = Column(Text)
    edited = Column(Boolean, default=False)

    # Gmail tracking
    message_id = Column(String, index=True)
    thread_id = Column(String, index=True)
    sent_at = Column(DateTime, index=True)

    # Unsubscribe compliance
    unsubscribe_url = Column(String)
    unsubscribe_token = Column(String, index=True)

    # Follow-up tracking
    original_draft_id = Column(Integer, ForeignKey("email_drafts.id"))
    followup_sequence_number = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contact = relationship("Contact", back_populates="drafts")
    replies = relationship("Reply", back_populates="draft")
    original_draft = relationship("EmailDraft", remote_side=[id], foreign_keys=[original_draft_id])

    # Indexes
    __table_args__ = (
        Index('idx_draft_status_user', 'status', 'user_id'),
        Index('idx_draft_sent_followup', 'sent_at', 'followup_sequence_number'),
    )


class Reply(Base):
    """Email reply model."""
    __tablename__ = "replies"

    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer, ForeignKey("email_drafts.id"), nullable=False, index=True)

    # Reply content
    from_email = Column(String, nullable=False)
    body = Column(Text)
    body_html = Column(Text)
    body_plain = Column(Text)  # Parsed plain text

    # Classification
    intent = Column(Enum(ReplyIntent), index=True)
    confidence = Column(Float)

    # Metadata
    cc_recipients = Column(JSON)  # List of CC'd emails
    attachments = Column(JSON)  # List of attachment names
    has_inline_images = Column(Boolean, default=False)

    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime)

    # Relationships
    draft = relationship("EmailDraft", back_populates="replies")


class AuditLog(Base):
    """Audit log for tracking state changes."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), index=True)
    user_id = Column(Integer)

    # State change tracking
    old_status = Column(String)
    new_status = Column(String)
    action = Column(String)
    details = Column(JSON)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    contact = relationship("Contact", back_populates="audit_logs")


class CostLog(Base):
    """Log of API costs for budget tracking."""
    __tablename__ = "cost_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, default=1)

    # Cost details
    operation_type = Column(String)  # enrichment, embedding, draft
    model = Column(String)
    tokens_used = Column(Integer)
    cost = Column(Float, nullable=False)

    # Metadata
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    draft_id = Column(Integer, ForeignKey("email_drafts.id"))

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('idx_cost_user_date', 'user_id', 'created_at'),
    )


class QuotaUsage(Base):
    """Track daily Gmail sending quota."""
    __tablename__ = "quota_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, default=1)
    date = Column(DateTime, nullable=False, index=True)
    emails_sent = Column(Integer, default=0)
    quota_limit = Column(Integer, nullable=False)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_quota_user_date', 'user_id', 'date'),
    )


class UnsubscribeToken(Base):
    """Track unsubscribe tokens for compliance."""
    __tablename__ = "unsubscribe_tokens"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    used = Column(Boolean, default=False)
    used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

"""
Contact enrichment service using OpenAI GPT-4.
"""

import json
import time
from typing import List, Optional
from openai import OpenAI
from sqlalchemy.orm import Session
from src.models import Contact, ContactStatus, AuditLog
from src.config import config
from src.services.cost_tracker import CostTracker
import logging

logger = logging.getLogger(__name__)

# Lazy-load OpenAI client
_client = None

def get_openai_client():
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def enrich_contact(
    contact: Contact,
    db: Session,
    api_key: str = None,
    retry_count: int = 0,
    cost_tracker: Optional[CostTracker] = None
) -> Contact:
    """
    Enrich a single contact with GPT-4.

    Args:
        contact: Contact to enrich
        db: Database session
        api_key: Optional API key (uses config if not provided)
        retry_count: Current retry attempt
        cost_tracker: Optional cost tracker

    Returns:
        Enriched contact

    Raises:
        Exception: If enrichment fails after retries
    """
    try:
        # Build prompt
        prompt = f"""Given the following contact information, provide enrichment data in JSON format.

Contact:
- Name: {contact.name or 'Unknown'}
- Email: {contact.email}
- Industry: {contact.industry or 'Unknown'}

Please provide:
1. title: Their professional title/role
2. company: Their company name (infer from email domain if possible)
3. painpoint: A brief description of potential pain points for their role/industry
4. relevance_score: A score from 0-10 indicating how relevant this contact is for B2B outreach

Return ONLY a valid JSON object with these exact fields. Be specific and avoid generic responses."""

        # Call GPT-4
        response = get_openai_client().chat.completions.create(
            model=config.OPENAI_MODEL_GPT,
            messages=[
                {"role": "system", "content": "You are a B2B contact research assistant. Provide specific, actionable insights."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        # Parse response
        content = response.choices[0].message.content
        data = json.loads(content)

        # Update contact
        contact.title = data.get("title", "")
        contact.company = data.get("company", "")
        contact.painpoint = data.get("painpoint", "")
        contact.relevance_score = float(data.get("relevance_score", 5.0))

        # Clamp relevance score to 0-10
        contact.relevance_score = max(0.0, min(10.0, contact.relevance_score))

        contact.status = ContactStatus.ENRICHED

        # Track cost
        if cost_tracker:
            tokens = response.usage.total_tokens if hasattr(response, 'usage') else 500
            cost_tracker.track_operation("enrichment", config.OPENAI_MODEL_GPT, tokens, contact.id)

        # Save to database
        db.add(contact)

        # Log audit trail
        audit = AuditLog(
            contact_id=contact.id,
            old_status=ContactStatus.IMPORTED.value,
            new_status=ContactStatus.ENRICHED.value,
            action="enrichment",
            details={"model": config.OPENAI_MODEL_GPT}
        )
        db.add(audit)

        db.commit()

        logger.info(f"Enriched contact {contact.id}: {contact.name}")

        return contact

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response for contact {contact.id}: {e}")
        contact.status = ContactStatus.ENRICHMENT_FAILED
        contact.error_message = "Invalid response format"
        db.commit()
        return contact

    except Exception as e:
        logger.error(f"Error enriching contact {contact.id}: {e}")

        if retry_count < 3:
            logger.info(f"Retrying enrichment for contact {contact.id} (attempt {retry_count + 1})")
            time.sleep(2 ** retry_count)  # Exponential backoff
            return enrich_contact(contact, db, api_key, retry_count + 1, cost_tracker)

        contact.status = ContactStatus.ENRICHMENT_FAILED
        contact.error_message = f"API error after {retry_count} retries: {str(e)}"
        contact.retry_count = retry_count
        db.commit()

        return contact


def enrich_contacts_batch(
    contacts: List[Contact],
    db: Session,
    api_key: str = None,
    batch_size: int = 10,
    progress_callback=None,
    cost_tracker: Optional[CostTracker] = None
) -> List[Contact]:
    """
    Enrich multiple contacts in batches.

    Args:
        contacts: List of contacts to enrich
        db: Database session
        api_key: Optional API key
        batch_size: Number of contacts per batch
        progress_callback: Optional callback function(current, total)
        cost_tracker: Optional cost tracker

    Returns:
        List of enriched contacts
    """
    enriched = []

    for i, contact in enumerate(contacts):
        # Check budget if cost tracker provided
        if cost_tracker and not cost_tracker.check_budget():
            logger.warning(f"Budget limit reached after {i} contacts")
            break

        try:
            result = enrich_contact(contact, db, api_key, cost_tracker=cost_tracker)
            enriched.append(result)

            if progress_callback:
                progress_callback(i + 1, len(contacts))

        except Exception as e:
            logger.error(f"Failed to enrich contact {contact.id}: {e}")
            contact.status = ContactStatus.ENRICHMENT_FAILED
            enriched.append(contact)

        # Small delay to avoid rate limiting
        if (i + 1) % batch_size == 0:
            time.sleep(1)

    return enriched

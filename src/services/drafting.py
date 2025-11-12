"""
Email draft generation service using GPT-4.
"""

from typing import List, Optional
from openai import OpenAI
from sqlalchemy.orm import Session
from src.models import Contact, EmailTemplate, EmailDraft, DraftStatus
from src.config import config
from src.utils.helpers import replace_template_variables, generate_unsubscribe_token
from src.services.cost_tracker import CostTracker
import logging

logger = logging.getLogger(__name__)

client = OpenAI(api_key=config.OPENAI_API_KEY)


def generate_email_draft(
    contact: Contact,
    template: Optional[EmailTemplate],
    db: Session,
    api_key: str = None,
    max_words: int = 150,
    cost_tracker: Optional[CostTracker] = None,
    **kwargs
) -> EmailDraft:
    """
    Generate personalized email draft for a contact.

    Args:
        contact: Contact to email
        template: Email template (if None, GPT generates one)
        db: Database session
        api_key: Optional API key
        max_words: Maximum words in email body
        cost_tracker: Optional cost tracker
        **kwargs: Additional parameters

    Returns:
        EmailDraft object
    """
    # Check if contact is unsubscribed
    if contact.unsubscribed:
        from src.utils.helpers import ContactUnsubscribedError
        raise ContactUnsubscribedError(f"Contact {contact.id} has unsubscribed")

    # Prepare variables for template
    variables = {
        "name": contact.name or "there",
        "email": contact.email,
        "company": contact.company or "your organization",
        "industry": contact.industry or "your industry",
        "title": contact.title or "",
        "painpoint": contact.painpoint or "industry challenges"
    }

    if template:
        # Use provided template
        subject = replace_template_variables(template.subject, variables)
        body = replace_template_variables(template.body, variables)
    else:
        # Generate with GPT-4
        prompt = f"""Write a professional, personalized cold email for B2B outreach.

Contact Details:
- Name: {contact.name or 'Unknown'}
- Company: {contact.company or 'Unknown'}
- Title: {contact.title or 'Unknown'}
- Industry: {contact.industry or 'Unknown'}
- Pain Point: {contact.painpoint or 'Unknown'}

Requirements:
- Keep it under {max_words} words
- Professional but friendly tone
- Personalized based on their role/industry
- Clear value proposition
- Include subject line

Return in format:
SUBJECT: [subject line]
BODY: [email body]"""

        response = client.chat.completions.create(
            model=config.OPENAI_MODEL_GPT,
            messages=[
                {"role": "system", "content": "You are an expert email copywriter for B2B sales."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400
        )

        content = response.choices[0].message.content

        # Parse response
        if "SUBJECT:" in content and "BODY:" in content:
            parts = content.split("BODY:")
            subject = parts[0].replace("SUBJECT:", "").strip()
            body = parts[1].strip()
        else:
            subject = f"Quick question about {contact.company or 'your work'}"
            body = content

        # Track cost
        if cost_tracker:
            tokens = response.usage.total_tokens if hasattr(response, 'usage') else 300
            cost_tracker.track_operation("draft", config.OPENAI_MODEL_GPT, tokens)

    # Generate unsubscribe token
    unsubscribe_token = generate_unsubscribe_token(contact.id)

    # Add unsubscribe link to body
    unsubscribe_url = f"https://yourapp.com/unsubscribe/{unsubscribe_token}"
    body += f"\n\n---\nTo unsubscribe, click: {unsubscribe_url}"

    # Create draft
    draft = EmailDraft(
        contact_id=contact.id,
        to_email=contact.email,
        subject=subject,
        body=body,
        status=DraftStatus.PENDING_APPROVAL,
        unsubscribe_token=unsubscribe_token,
        unsubscribe_url=unsubscribe_url
    )

    db.add(draft)
    db.commit()

    logger.info(f"Generated draft for contact {contact.id}")

    return draft


def generate_email_drafts_bulk(
    contacts: List[Contact],
    template: EmailTemplate,
    db: Session,
    api_key: str = None,
    user_id: int = 1,
    cost_tracker: Optional[CostTracker] = None
) -> List[EmailDraft]:
    """
    Generate drafts for multiple contacts.

    Args:
        contacts: List of contacts
        template: Email template
        db: Database session
        api_key: Optional API key
        user_id: User ID
        cost_tracker: Optional cost tracker

    Returns:
        List of EmailDraft objects
    """
    drafts = []

    for contact in contacts:
        try:
            draft = generate_email_draft(contact, template, db, api_key, cost_tracker=cost_tracker)
            draft.user_id = user_id
            drafts.append(draft)
        except Exception as e:
            logger.error(f"Failed to generate draft for contact {contact.id}: {e}")

    db.commit()

    return drafts

"""
Helper utilities for the outreach engine.
"""

import re
import csv
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from io import StringIO
import logging

logger = logging.getLogger(__name__)


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def parse_csv_content(csv_content: str) -> List[Dict[str, str]]:
    """
    Parse CSV content into list of dictionaries.

    Args:
        csv_content: CSV string content

    Returns:
        List of dictionaries with column headers as keys
    """
    reader = csv.DictReader(StringIO(csv_content))
    return [row for row in reader]


def generate_unsubscribe_token(contact_id: int, salt: str = None) -> str:
    """
    Generate secure unsubscribe token.

    Args:
        contact_id: Contact ID
        salt: Optional salt for token generation

    Returns:
        Secure token string
    """
    if salt is None:
        salt = secrets.token_hex(16)

    data = f"{contact_id}:{salt}:{datetime.utcnow().isoformat()}"
    token = hashlib.sha256(data.encode()).hexdigest()

    return f"unsub_{contact_id}_{token}"


def extract_unsubscribe_token(text: str) -> Optional[str]:
    """Extract unsubscribe token from text."""
    pattern = r'unsub_\d+_[a-f0-9]{64}'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def parse_contact_id_from_token(token: str) -> Optional[int]:
    """Extract contact ID from unsubscribe token."""
    match = re.match(r'unsub_(\d+)_', token)
    return int(match.group(1)) if match else None


def strip_html(html: str) -> str:
    """
    Strip HTML tags from text.

    Args:
        html: HTML content

    Returns:
        Plain text with HTML tags removed
    """
    # Remove script and style elements
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)

    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def replace_template_variables(template: str, variables: Dict[str, Any]) -> str:
    """
    Replace template variables like {{name}} with actual values.

    Args:
        template: Template string with {{variable}} placeholders
        variables: Dictionary of variable values

    Returns:
        String with variables replaced
    """
    result = template

    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"

        # Handle None/empty values with fallbacks
        if value is None or value == "":
            if key == "company":
                value = "your organization"
            elif key == "industry":
                value = "your industry"
            elif key == "title":
                value = ""
            else:
                value = ""

        result = result.replace(placeholder, str(value))

    return result


def is_business_hours(dt: datetime, timezone: str = "UTC") -> bool:
    """
    Check if datetime is during business hours (9 AM - 5 PM weekdays).

    Args:
        dt: Datetime to check
        timezone: Timezone string (currently not implemented, assumes UTC)

    Returns:
        True if during business hours
    """
    # Check if weekend
    if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    # Check if between 9 AM and 5 PM
    return 9 <= dt.hour < 17


def schedule_for_next_business_time(current_time: datetime) -> datetime:
    """
    Schedule for next available business time.

    Args:
        current_time: Current datetime

    Returns:
        Next business datetime (9 AM weekday)
    """
    # Start with next day at 9 AM
    next_time = (current_time + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    # Skip weekends
    while next_time.weekday() >= 5:
        next_time += timedelta(days=1)

    return next_time


def calculate_cost(operation: str, model: str, tokens: int = None) -> float:
    """
    Calculate cost for API operation.

    Args:
        operation: Operation type (enrichment, embedding, draft)
        model: Model name
        tokens: Number of tokens used (if known)

    Returns:
        Estimated cost in USD
    """
    # Simplified cost calculation
    # Real implementation would use actual token counts and pricing
    costs = {
        "gpt-4-turbo-preview": 0.01,  # per 1k tokens
        "gpt-4": 0.03,
        "text-embedding-3-large": 0.00013,
        "text-embedding-3-small": 0.00002,
    }

    base_cost = costs.get(model, 0.01)

    if tokens:
        return (tokens / 1000) * base_cost

    # Default estimates for operations
    if operation == "enrichment":
        return base_cost * 5  # ~500 tokens
    elif operation == "embedding":
        return costs.get(model, 0.0001)
    elif operation == "draft":
        return base_cost * 3  # ~300 tokens

    return 0.0


def export_to_csv(data: List[Dict[str, Any]], filename: str = None) -> str:
    """
    Export list of dictionaries to CSV format.

    Args:
        data: List of dictionaries
        filename: Optional filename to save to

    Returns:
        CSV string content
    """
    if not data:
        return ""

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

    csv_content = output.getvalue()

    if filename:
        with open(filename, 'w') as f:
            f.write(csv_content)
        logger.info(f"Exported {len(data)} records to {filename}")

    return csv_content


def contains_spam_triggers(text: str) -> bool:
    """Check if text contains common spam triggers."""
    spam_words = [
        "free", "buy now", "urgent", "limited time", "act now",
        "click here", "guarantee", "winner", "prize", "cash"
    ]

    text_lower = text.lower()
    return any(word in text_lower for word in spam_words)


def calculate_spam_score(subject: str, body: str) -> float:
    """
    Calculate spam score for email.

    Args:
        subject: Email subject
        body: Email body

    Returns:
        Spam score (0-10, higher is spammier)
    """
    score = 0.0

    # Check for excessive caps
    if body:
        caps_ratio = sum(1 for c in body if c.isupper()) / max(len(body), 1)
        if caps_ratio > 0.3:
            score += 3.0

    # Check for excessive punctuation
    if "!!!" in body or "???" in body:
        score += 2.0

    # Check for spam words
    if contains_spam_triggers(body):
        score += 1.0

    # Check subject line
    if subject:
        if subject.isupper():
            score += 2.0
        if contains_spam_triggers(subject):
            score += 1.5

    return min(score, 10.0)


def truncate_text(text: str, max_length: int = 150) -> str:
    """Truncate text to maximum word count."""
    words = text.split()
    if len(words) <= max_length:
        return text

    return ' '.join(words[:max_length]) + '...'

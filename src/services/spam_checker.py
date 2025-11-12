"""
Spam score checking service.
"""

from typing import List, Tuple
from src.models import EmailDraft
from src.utils.helpers import calculate_spam_score
import logging

logger = logging.getLogger(__name__)


def check_spam_score(draft: EmailDraft) -> dict:
    """
    Check spam score for a draft.

    Args:
        draft: Email draft to check

    Returns:
        Dictionary with score, warnings, and recommendation
    """
    score = calculate_spam_score(draft.subject or "", draft.body or "")

    warnings = []
    if score >= 3:
        warnings.append("High spam score detected")

    # Check specific issues
    body = draft.body or ""
    subject = draft.subject or ""

    caps_ratio = sum(1 for c in body if c.isupper()) / max(len(body), 1)
    if caps_ratio > 0.3:
        warnings.append("Excessive caps")

    if "!!!" in body or "???" in body:
        warnings.append("Excessive punctuation")

    recommendation = "OK" if score < 5.0 else "REVISE_DRAFT"

    result = {
        "score": score,
        "warnings": warnings,
        "recommendation": recommendation
    }

    logger.info(f"Spam score for draft {draft.id}: {score:.2f}")

    return result


def analyze_spam_factors(draft: EmailDraft) -> dict:
    """
    Analyze spam factors and provide suggestions.

    Args:
        draft: Email draft to analyze

    Returns:
        Dictionary with suggestions and improved text
    """
    suggestions = []
    improved_subject = draft.subject

    body = draft.body or ""
    subject = draft.subject or ""

    # Check for excessive punctuation
    if "!!!" in body:
        suggestions.append("Reduce excessive punctuation")

    # Check for excessive caps
    caps_ratio = sum(1 for c in body if c.isupper()) / max(len(body), 1)
    if caps_ratio > 0.3:
        suggestions.append("Reduce caps - use sentence case")

    # Check subject line
    if "URGENT" in subject.upper():
        suggestions.append("Remove 'URGENT' from subject")
        improved_subject = subject.replace("URGENT!!!", "").replace("URGENT", "").strip()

    if "FREE" in subject.upper():
        suggestions.append("Avoid words like 'FREE' in subject")

    return {
        "suggestions": suggestions,
        "improved_subject": improved_subject if improved_subject != subject else None
    }

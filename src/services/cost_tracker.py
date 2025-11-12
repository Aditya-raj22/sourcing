"""
Cost tracking and budget enforcement service.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models import CostLog
from src.config import config
from src.utils.helpers import calculate_cost
import logging

logger = logging.getLogger(__name__)


class CostTracker:
    """Track API costs and enforce budget limits."""

    def __init__(self, db: Session, user_id: int = 1, daily_limit: float = None):
        self.db = db
        self.user_id = user_id
        self.daily_limit = daily_limit or config.DAILY_BUDGET_LIMIT
        self.enrichment_cost = 0.0
        self.embedding_cost = 0.0
        self.draft_generation_cost = 0.0

    def track_operation(
        self,
        operation_type: str,
        model: str,
        tokens_used: int = None,
        contact_id: int = None,
        draft_id: int = None
    ) -> float:
        """
        Track a single API operation cost.

        Args:
            operation_type: Type of operation (enrichment, embedding, draft)
            model: Model name used
            tokens_used: Number of tokens used
            contact_id: Optional contact ID
            draft_id: Optional draft ID

        Returns:
            Cost of the operation
        """
        cost = calculate_cost(operation_type, model, tokens_used)

        # Log to database
        cost_log = CostLog(
            user_id=self.user_id,
            operation_type=operation_type,
            model=model,
            tokens_used=tokens_used or 0,
            cost=cost,
            contact_id=contact_id,
            draft_id=draft_id
        )
        self.db.add(cost_log)
        self.db.commit()

        # Update local counters
        if operation_type == "enrichment":
            self.enrichment_cost += cost
        elif operation_type == "embedding":
            self.embedding_cost += cost
        elif operation_type == "draft":
            self.draft_generation_cost += cost

        logger.info(f"Tracked {operation_type} cost: ${cost:.4f} (model: {model})")

        return cost

    def track_enrichment(self, count: int, model: str = None):
        """Track enrichment operations."""
        model = model or config.OPENAI_MODEL_GPT
        for _ in range(count):
            self.track_operation("enrichment", model)

    def track_embedding(self, count: int, model: str = None):
        """Track embedding operations."""
        model = model or config.OPENAI_MODEL_EMBEDDING
        for _ in range(count):
            self.track_operation("embedding", model)

    def track_draft(self, count: int, model: str = None):
        """Track draft generation operations."""
        model = model or config.OPENAI_MODEL_GPT
        for _ in range(count):
            self.track_operation("draft", model)

    def get_total_cost(self) -> float:
        """Get total accumulated cost."""
        return self.enrichment_cost + self.embedding_cost + self.draft_generation_cost

    def get_daily_cost(self, date: datetime = None) -> float:
        """
        Get total cost for a specific day.

        Args:
            date: Date to check (defaults to today)

        Returns:
            Total cost for the day
        """
        if date is None:
            date = datetime.utcnow()

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        total = self.db.query(func.sum(CostLog.cost)).filter(
            CostLog.user_id == self.user_id,
            CostLog.created_at >= start_of_day,
            CostLog.created_at < end_of_day
        ).scalar()

        return float(total or 0.0)

    def check_budget(self) -> bool:
        """
        Check if under budget limit.

        Returns:
            True if under budget, False if over
        """
        daily_cost = self.get_daily_cost()
        remaining = self.daily_limit - daily_cost

        if remaining <= 0:
            logger.warning(f"Budget limit reached: ${daily_cost:.2f} / ${self.daily_limit:.2f}")
            return False

        return True

    def get_remaining_budget(self) -> float:
        """Get remaining budget for today."""
        return max(0, self.daily_limit - self.get_daily_cost())

    def get_breakdown(self) -> Dict[str, float]:
        """
        Get cost breakdown by model.

        Returns:
            Dictionary of model names to costs
        """
        start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        results = self.db.query(
            CostLog.model,
            func.sum(CostLog.cost).label('total_cost')
        ).filter(
            CostLog.user_id == self.user_id,
            CostLog.created_at >= start_of_day
        ).group_by(CostLog.model).all()

        return {model: float(cost) for model, cost in results}


def estimate_enrichment_cost(num_contacts: int, model: str = None) -> Dict[str, float]:
    """
    Estimate cost for enriching contacts.

    Args:
        num_contacts: Number of contacts to enrich
        model: Model to use

    Returns:
        Dictionary with cost estimates
    """
    model = model or config.OPENAI_MODEL_GPT
    embedding_model = config.OPENAI_MODEL_EMBEDDING

    enrichment_cost = calculate_cost("enrichment", model) * num_contacts
    embedding_cost = calculate_cost("embedding", embedding_model) * num_contacts

    total = enrichment_cost + embedding_cost

    return {
        "min_cost": total * 0.8,
        "max_cost": total * 1.2,
        "estimated_cost": total,
        "breakdown": {
            "enrichment": enrichment_cost,
            "embedding": embedding_cost
        }
    }

"""
Configuration module for the AI-driven outreach engine.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL_GPT: str = os.getenv("OPENAI_MODEL_GPT", "gpt-4-turbo-preview")
    OPENAI_MODEL_EMBEDDING: str = os.getenv("OPENAI_MODEL_EMBEDDING", "text-embedding-3-large")

    # Gmail Configuration
    GMAIL_CLIENT_ID: str = os.getenv("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET: str = os.getenv("GMAIL_CLIENT_SECRET", "")
    GMAIL_REFRESH_TOKEN: str = os.getenv("GMAIL_REFRESH_TOKEN", "")
    GMAIL_SENDER_EMAIL: str = os.getenv("GMAIL_SENDER_EMAIL", "")

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./outreach.db")

    # Budget and Quota Limits
    DAILY_BUDGET_LIMIT: float = float(os.getenv("DAILY_BUDGET_LIMIT", "100.0"))
    GMAIL_DAILY_SEND_LIMIT: int = int(os.getenv("GMAIL_DAILY_SEND_LIMIT", "500"))
    MAX_SPAM_SCORE: float = float(os.getenv("MAX_SPAM_SCORE", "5.0"))

    # Scheduling Configuration
    FOLLOWUP_DAYS: int = int(os.getenv("FOLLOWUP_DAYS", "7"))
    MAX_FOLLOWUPS: int = int(os.getenv("MAX_FOLLOWUPS", "3"))
    SKIP_WEEKENDS: bool = os.getenv("SKIP_WEEKENDS", "true").lower() == "true"
    RESPECT_BUSINESS_HOURS: bool = os.getenv("RESPECT_BUSINESS_HOURS", "true").lower() == "true"

    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"

    # Derived paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    CACHE_DIR: Path = BASE_DIR / "cache"
    LOGS_DIR: Path = BASE_DIR / "logs"

    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        required_fields = ["OPENAI_API_KEY"]

        missing = [field for field in required_fields if not getattr(cls, field)]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        # Create necessary directories
        cls.CACHE_DIR.mkdir(exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)

        return True


# Singleton instance
config = Config()

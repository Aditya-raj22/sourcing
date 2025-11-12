"""
Pytest configuration and shared fixtures for the AI outreach engine tests.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def db():
    """In-memory SQLite database for tests."""
    from test_helpers import MockDatabase
    database = MockDatabase(":memory:")
    database.migrate()
    yield database
    database.close()


# ============================================================================
# API Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_openai():
    """Mock OpenAI API client."""
    from test_helpers import MockOpenAIClient
    return MockOpenAIClient()


@pytest.fixture
def mock_gmail():
    """Mock Gmail API client."""
    from test_helpers import MockGmailAPI
    return MockGmailAPI()


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def config():
    """Default test configuration."""
    from test_helpers import Config
    return Config(
        daily_budget_limit=100.00,
        gmail_daily_limit=100,
        max_spam_score=5.0,
        skip_weekends=False,
        respect_business_hours=True
    )


@pytest.fixture
def openai_key():
    """Mock OpenAI API key."""
    return "test-openai-key-12345"


@pytest.fixture
def gmail_creds():
    """Mock Gmail credentials."""
    return {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "client_id": "mock_client_id",
        "client_secret": "mock_client_secret"
    }


# ============================================================================
# Data Fixtures
# ============================================================================

@pytest.fixture
def sample_contacts():
    """Sample contacts for testing."""
    from test_helpers import Contact, ContactStatus
    return [
        Contact(
            id=1,
            name="Alice Smith",
            email="alice@example.com",
            industry="Healthcare",
            status=ContactStatus.IMPORTED
        ),
        Contact(
            id=2,
            name="Bob Jones",
            email="bob@example.com",
            industry="Finance",
            status=ContactStatus.IMPORTED
        ),
        Contact(
            id=3,
            name="Charlie Brown",
            email="charlie@example.com",
            industry="Technology",
            status=ContactStatus.IMPORTED
        )
    ]


@pytest.fixture
def sample_csv():
    """Sample CSV content for import tests."""
    return """name,email,industry
Alice Smith,alice@example.com,Healthcare
Bob Jones,bob@example.com,Finance
Charlie Brown,charlie@example.com,Technology"""


@pytest.fixture
def email_template():
    """Sample email template."""
    from test_helpers import EmailTemplate
    return EmailTemplate(
        id=1,
        subject="Hi {{name}}",
        body="Hi {{name}},\n\nI noticed you work at {{company}} in the {{industry}} industry.\n\n{{painpoint}}\n\nBest regards"
    )


@pytest.fixture
def enriched_contact():
    """A fully enriched contact."""
    from test_helpers import Contact, ContactStatus
    return Contact(
        id=1,
        name="Alice Smith",
        email="alice@example.com",
        industry="Healthcare",
        title="VP of Engineering",
        company="HealthTech Inc",
        painpoint="Struggling with patient data integration",
        relevance_score=8.5,
        status=ContactStatus.ENRICHED
    )


# ============================================================================
# Time Fixtures
# ============================================================================

@pytest.fixture
def freeze_time():
    """Freeze time for testing time-dependent logic."""
    from freezegun import freeze_time as _freeze_time
    return _freeze_time


@pytest.fixture
def current_time():
    """Current time for testing."""
    return datetime(2025, 11, 12, 10, 0, 0)


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def cost_tracker():
    """Mock cost tracker."""
    from test_helpers import CostTracker
    return CostTracker()


@pytest.fixture
def quota_tracker():
    """Mock Gmail quota tracker."""
    from test_helpers import GmailQuotaTracker
    return GmailQuotaTracker(daily_limit=100)


@pytest.fixture
def alert_service():
    """Mock alert service."""
    from test_helpers import AlertService
    return AlertService()


@pytest.fixture
def notification_service():
    """Mock notification service."""
    from test_helpers import NotificationService
    return NotificationService(user_email="test@example.com")


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "tier1: marks tests as Tier 1 production readiness tests"
    )
    config.addinivalue_line(
        "markers", "tier2: marks tests as Tier 2 production readiness tests"
    )

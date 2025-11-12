# AI-Driven Outreach Engine - Test Suite

Comprehensive test suite for the AI-powered relationship outreach engine. **106 test cases** covering all aspects from data ingestion to production-ready features.

## 📋 Test Coverage Summary

### Total Tests: 106 across 13 categories

| Category | Tests | File | Status |
|----------|-------|------|--------|
| **Data Ingestion & Validation** | 6 | `test_data_ingestion.py` | ✅ |
| **AI-Powered Enrichment** | 8 | `test_enrichment.py` | ✅ |
| **Semantic Clustering** | 7 | `test_outreach_workflow.py` | ✅ |
| **Email Draft Generation** | 7 | `test_outreach_workflow.py` | ✅ |
| **Human Approval Workflow** | 6 | `test_outreach_workflow.py` | ✅ |
| **Email Sending** | 8 | `test_outreach_workflow.py` | ✅ |
| **Reply Monitoring & Classification** | 8 | `test_replies_followups.py` | ✅ |
| **Follow-up Automation** | 7 | `test_replies_followups.py` | ✅ |
| **Meeting Scheduling** | 5 | `test_meetings_persistence_e2e.py` | ✅ |
| **Persistence & State Management** | 8 | `test_meetings_persistence_e2e.py` | ✅ |
| **End-to-End Integration** | 5 | `test_meetings_persistence_e2e.py` | ✅ |
| **Production Tier 1 (Must-Have)** | 16 | `test_production_tier1.py` | ✅ |
| **Production Tier 2 (Should-Have)** | 15 | `test_production_tier2.py` | ✅ |

## 🚀 Quick Start

### Installation

```bash
# Install test dependencies
pip install -r requirements-test.txt
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific category
pytest tests/test_data_ingestion.py -v

# Run by marker
pytest tests/ -m tier1  # Production Tier 1 tests only
pytest tests/ -m "not slow"  # Skip slow tests
pytest tests/ -m integration  # Integration tests only
```

## 📂 Test Structure

```
tests/
├── conftest.py                      # Pytest configuration and fixtures
├── test_helpers.py                  # Mock objects and utilities
├── test_data_ingestion.py           # CSV import and validation (6 tests)
├── test_enrichment.py               # AI enrichment (8 tests)
├── test_outreach_workflow.py        # Clustering, drafts, approval, sending (28 tests)
├── test_replies_followups.py        # Reply classification and follow-ups (15 tests)
├── test_meetings_persistence_e2e.py # Meetings, DB, E2E (18 tests)
├── test_production_tier1.py         # Production critical features (16 tests)
├── test_production_tier2.py         # Production nice-to-have features (15 tests)
└── README.md                        # This file
```

## 🎯 Test Categories Explained

### 1. Data Ingestion & Validation (6 tests)
Tests CSV import with validation, error handling, deduplication, and special characters.

**Key Tests:**
- ✅ Valid CSV import with all required fields
- ✅ Handling missing/invalid email addresses
- ✅ Duplicate detection within CSV and database
- ✅ Large file handling (10,000+ rows)
- ✅ Special characters (Unicode, quotes, commas)

### 2. AI-Powered Enrichment (8 tests)
Tests GPT-4 integration for contact enrichment with error handling and quality validation.

**Key Tests:**
- ✅ Successful enrichment with title, company, painpoint, relevance score
- ✅ Handling minimal contact information
- ✅ API timeout and retry logic (3 retries)
- ✅ Rate limiting with exponential backoff
- ✅ Invalid response format handling
- ✅ Relevance score validation (0-10 bounds)
- ✅ Batch processing with progress tracking
- ✅ Output quality validation

### 3. Semantic Clustering (7 tests)
Tests embedding generation and contact clustering by similarity.

**Key Tests:**
- ✅ 1536-dimension embedding generation
- ✅ Similar contacts clustered together
- ✅ Edge cases (single contact, all identical)
- ✅ Auto-detection of optimal cluster count
- ✅ Cluster labeling from common themes

### 4. Email Draft Generation (7 tests)
Tests personalized email draft creation with template variables.

**Key Tests:**
- ✅ Template-based personalization
- ✅ Handling missing contact data with fallbacks
- ✅ Draft length validation
- ✅ Subject line personalization
- ✅ Bulk draft generation
- ✅ Tone consistency (professional, friendly)
- ✅ Plain text formatting

### 5. Human Approval Workflow (6 tests)
Tests the approval process before emails are sent.

**Key Tests:**
- ✅ Single draft approval/rejection
- ✅ Bulk approval operations
- ✅ Draft editing before approval
- ✅ State transition validation
- ✅ Approval notes tracking

### 6. Email Sending (8 tests)
Tests Gmail API integration and sending logic.

**Key Tests:**
- ✅ Successful sending via Gmail API
- ✅ API failure handling with retries
- ✅ Duplicate send prevention
- ✅ Only send approved drafts
- ✅ Mock send mode for testing
- ✅ Rate limiting (100-500 emails/day)
- ✅ Message/thread ID tracking
- ✅ Attachment support

### 7. Reply Monitoring & Classification (8 tests)
Tests email reply detection and AI-powered intent classification.

**Key Tests:**
- ✅ Reply detection from Gmail API
- ✅ Intent classification (Interested, Maybe, Decline, Auto-reply)
- ✅ Multi-message thread handling
- ✅ Filtering self-replies
- ✅ Attachment-only replies
- ✅ HTML email parsing
- ✅ Inline image handling
- ✅ CC recipient tracking

### 8. Follow-up Automation (7 tests)
Tests automated follow-up generation after 7 days.

**Key Tests:**
- ✅ Generate follow-up after 7 days of no reply
- ✅ Don't follow up if already replied
- ✅ Don't follow up if contact declined
- ✅ Multi-stage follow-up sequences (up to 3)
- ✅ Max follow-up limit enforcement
- ✅ Follow-up personalization
- ✅ Respect "do not follow up" flag

### 9. Meeting Scheduling (5 tests)
Tests meeting time suggestions and calendar integration.

**Key Tests:**
- ✅ Suggest 3-5 meeting times for interested replies
- ✅ Parse availability from reply text
- ✅ Generate .ics calendar invites
- ✅ No suggestions for declined replies
- ✅ Timezone conversion handling

### 10. Persistence & State Management (8 tests)
Tests database operations and state tracking.

**Key Tests:**
- ✅ Save and retrieve contacts
- ✅ Contact status lifecycle tracking
- ✅ Transaction rollback on errors
- ✅ Concurrent edit handling
- ✅ Soft delete (mark as deleted, don't remove)
- ✅ Query by status
- ✅ Audit log for state changes
- ✅ Database migrations

### 11. End-to-End Integration (5 tests)
Tests complete workflows from start to finish.

**Key Tests:**
- ✅ Full pipeline: Import → Enrich → Cluster → Draft → Approve → Send
- ✅ Reply handling and follow-up prevention
- ✅ Multi-user campaign isolation
- ✅ Error recovery and retry logic
- ✅ Performance with 1000+ contacts

### 12. Production Tier 1 - Must-Have (16 tests)
Critical production features required before launch.

**Key Tests:**
- ✅ **Cost Control:** API cost tracking, budget limits, cost estimation
- ✅ **Legal Compliance:** CAN-SPAM unsubscribe links, unsubscribe processing, GDPR data deletion
- ✅ **Gmail Quotas:** Daily send limits (100-500), quota reset at midnight
- ✅ **Deduplication:** Global contact dedup, contact merging
- ✅ **Error Recovery:** Cancel pending sends, undo bulk approval
- ✅ **Data Export:** Export contacts and campaign history to CSV

### 13. Production Tier 2 - Should-Have (15 tests)
Important but non-critical production features.

**Key Tests:**
- ✅ **Spam Prevention:** Spam score checking, sending prevention, improvement suggestions
- ✅ **Smart Scheduling:** Business hours, weekend skip, industry-optimized send times
- ✅ **Monitoring:** High failure rate alerts, daily summaries, real-time notifications
- ✅ **Email Parsing:** HTML parsing, inline image handling, CC tracking
- ✅ **Quality Assurance:** Hallucination detection, quality tracking, external validation

## 🏷️ Test Markers

Tests are marked for easy filtering:

```python
@pytest.mark.slow          # Long-running tests
@pytest.mark.integration   # Integration tests
@pytest.mark.e2e           # End-to-end tests
@pytest.mark.tier1         # Production Tier 1 (critical)
@pytest.mark.tier2         # Production Tier 2 (important)
```

## 🔧 Available Fixtures

### Database Fixtures
- `db` - In-memory SQLite database
- `sample_contacts` - List of 3 test contacts
- `enriched_contact` - Fully enriched contact

### API Mock Fixtures
- `mock_openai` - Mock OpenAI client
- `mock_gmail` - Mock Gmail API client
- `openai_key` - Test OpenAI API key
- `gmail_creds` - Test Gmail credentials

### Configuration Fixtures
- `config` - Default test configuration
- `email_template` - Sample email template
- `cost_tracker` - Cost tracking service
- `quota_tracker` - Gmail quota tracker
- `alert_service` - Alert notification service

### Time Fixtures
- `freeze_time` - Freeze time for testing
- `current_time` - Fixed current time

## 📊 Running Specific Test Suites

```bash
# Run only fast tests (skip slow integration tests)
pytest tests/ -m "not slow" -v

# Run only production-critical tests
pytest tests/ -m tier1 -v

# Run integration tests in staging
pytest tests/ -m integration --e2e -v

# Run with verbose output and show print statements
pytest tests/ -v -s

# Run and generate HTML coverage report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html  # View coverage report

# Run specific test by name
pytest tests/test_data_ingestion.py::test_import_valid_csv -v

# Run tests in parallel (requires pytest-xdist)
pytest tests/ -n auto
```

## 🐛 Debugging Failed Tests

```bash
# Run with detailed output
pytest tests/ -vv

# Stop at first failure
pytest tests/ -x

# Drop into debugger on failure
pytest tests/ --pdb

# Show local variables on failure
pytest tests/ -l

# Re-run only failed tests
pytest tests/ --lf
```

## 📈 CI/CD Integration

### Example GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements-test.txt
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## ✅ What's Tested vs. What's Not

### ✅ Tested
- Core functionality (CSV import, AI enrichment, email workflows)
- Edge cases (missing data, API failures, duplicates)
- Error handling (retries, timeouts, validation)
- Production readiness (costs, compliance, quotas)
- Performance (large datasets)
- State management (database, audit logs)

### ❌ Not Tested (Requires Infrastructure)
- OAuth2 flow for Gmail API (requires browser)
- Real OpenAI/Gmail API calls (mocked)
- UI/UX (Streamlit/React components)
- Email deliverability (SPF/DKIM/DMARC)
- Extreme scale (1M+ contacts)
- Network conditions (latency, packet loss)

## 🎓 Writing New Tests

### Example Test Structure

```python
import pytest
from test_helpers import Contact, ContactStatus

def test_my_new_feature(db, openai_key):
    """
    Clear description of what this test validates.
    """
    # Arrange - Set up test data
    contact = Contact(name="Test User", email="test@example.com")
    db.save_contact(contact)

    # Act - Execute the functionality
    result = my_function(contact, api_key=openai_key)

    # Assert - Verify expected behavior
    assert result.status == "success"
    assert result.data is not None
```

### Best Practices

1. **Use descriptive test names**: `test_import_csv_with_missing_email` not `test_csv_1`
2. **One assertion concept per test**: Test one thing at a time
3. **Use fixtures**: Leverage `conftest.py` fixtures for common setup
4. **Mock external APIs**: Use `MockOpenAIClient` and `MockGmailAPI`
5. **Mark slow tests**: Use `@pytest.mark.slow` for tests > 1 second
6. **Add docstrings**: Explain what the test validates
7. **Keep tests independent**: Tests should not depend on each other

## 📝 Test Metrics

- **Total Tests:** 106
- **Test Files:** 7
- **Test Categories:** 13
- **Estimated Runtime:** ~30 seconds (fast tests only)
- **Estimated Runtime:** ~5 minutes (all tests including slow)
- **Code Coverage Target:** >80%

## 🔍 Troubleshooting

### Common Issues

**Issue:** Tests failing with import errors
```bash
# Solution: Install test dependencies
pip install -r requirements-test.txt
```

**Issue:** Tests can't find fixtures
```bash
# Solution: Ensure you're running from the project root
cd /path/to/sourcing
pytest tests/ -v
```

**Issue:** Mock objects not working
```bash
# Solution: Check test_helpers.py is being imported correctly
python -c "from tests.test_helpers import Contact; print('OK')"
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Test Plan](../TEST_PLAN.md) - Full test specification
- [Mock Objects](./test_helpers.py) - Available mock classes and utilities

## 🤝 Contributing

When adding new tests:

1. Add test to appropriate file (or create new file)
2. Use existing fixtures from `conftest.py`
3. Add new fixtures to `conftest.py` if needed
4. Mark tests appropriately (`@pytest.mark.slow`, etc.)
5. Update this README if adding new categories
6. Ensure tests pass: `pytest tests/ -v`
7. Check coverage: `pytest tests/ --cov=src`

---

**Last Updated:** 2025-11-12
**Test Suite Version:** 1.0.0
**Coverage:** 106/131 tests from original test plan

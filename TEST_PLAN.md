# AI-Driven Outreach Engine - Comprehensive Test Plan

## 1. Overview of Test Categories

This test plan covers the following major categories:

### 1.1 Data Ingestion & Validation
- CSV parsing and schema validation
- Missing/malformed field handling
- Duplicate contact detection
- Large file handling

### 1.2 AI-Powered Contact Enrichment
- GPT-4 Turbo API integration
- Field extraction (title, company, painpoint, relevance_score)
- Rate limiting and retry logic
- API error handling (timeout, rate limit, invalid response)
- Prompt quality and output validation

### 1.3 Semantic Embedding & Clustering
- Embedding generation via OpenAI
- Clustering algorithm correctness
- Edge cases (1 contact, all identical, all unique)
- Dimensionality and similarity metrics

### 1.4 Email Draft Generation
- Template-based personalization
- GPT-4 draft quality
- Character limits and formatting
- Missing enrichment data handling

### 1.5 Human-in-the-Loop Approval
- Approval workflow state management
- Bulk approve/reject
- Edit-before-send functionality

### 1.6 Email Sending
- Gmail API integration
- Mock send for testing
- Duplicate send prevention
- Send failure handling and retry
- Throttling/rate limiting

### 1.7 Reply Monitoring & Classification
- Email fetching via Gmail API
- Intent classification (Interested, Maybe, Decline, Auto-reply)
- Thread tracking and reply association
- Ambiguous reply handling
- Multi-reply threads

### 1.8 Follow-up Automation
- 7-day timer logic
- Follow-up suggestion generation
- Already-replied prevention
- Multi-stage follow-up sequences

### 1.9 Meeting Scheduling
- Availability slot parsing
- Meeting time suggestion
- Calendar integration readiness

### 1.10 Persistence & State Management
- SQLite/Firebase CRUD operations
- State transitions (Draft → Approved → Sent → Replied)
- Concurrent access handling
- Data integrity and rollback

### 1.11 End-to-End Integration
- Full pipeline tests
- Multi-user scenarios
- Performance and load testing

### 1.12 Production Readiness - Tier 1 (Must-Have)
- Cost tracking and budget enforcement
- Unsubscribe mechanism and CAN-SPAM compliance
- Gmail quota management
- Global contact deduplication
- Cancel/undo operations
- Data export and GDPR compliance

### 1.13 Production Readiness - Tier 2 (Should-Have)
- Spam score checking and prevention
- Business hours scheduling
- Failure monitoring and alerts
- HTML email parsing
- Prompt quality validation and hallucination detection

---

## 2. Detailed Test Cases

### 2.1 Data Ingestion & Validation

#### Test 2.1.1: Valid CSV Import
```python
def test_import_valid_csv():
    """
    Test successful import of well-formed CSV with all required fields.
    """
    input_csv = """
    name,email,industry
    Alice Smith,alice@example.com,Healthcare
    Bob Jones,bob@example.com,Finance
    """

    contacts = import_contacts(input_csv)

    assert len(contacts) == 2
    assert contacts[0].name == "Alice Smith"
    assert contacts[0].email == "alice@example.com"
    assert contacts[0].industry == "Healthcare"
    assert contacts[0].status == ContactStatus.IMPORTED
```

#### Test 2.1.2: CSV with Missing Required Fields
```python
def test_import_csv_missing_email():
    """
    Should reject rows with missing email, log error, continue with valid rows.
    """
    input_csv = """
    name,email,industry
    Alice Smith,,Healthcare
    Bob Jones,bob@example.com,Finance
    """

    result = import_contacts(input_csv)

    assert len(result.contacts) == 1
    assert result.contacts[0].name == "Bob Jones"
    assert len(result.errors) == 1
    assert "missing email" in result.errors[0].message.lower()
```

#### Test 2.1.3: CSV with Invalid Email Format
```python
def test_import_csv_invalid_email():
    """
    Should validate email format and reject invalid entries.
    """
    input_csv = """
    name,email,industry
    Alice Smith,not-an-email,Healthcare
    Bob Jones,bob@example.com,Finance
    """

    result = import_contacts(input_csv)

    assert len(result.contacts) == 1
    assert len(result.errors) == 1
    assert "invalid email" in result.errors[0].message.lower()
```

#### Test 2.1.4: CSV with Duplicate Emails
```python
def test_import_csv_duplicate_emails():
    """
    Should detect duplicates within CSV and existing database.
    Only import first occurrence, flag others.
    """
    # Pre-populate database
    db.add_contact(Contact(name="Existing", email="alice@example.com"))

    input_csv = """
    name,email,industry
    Alice Smith,alice@example.com,Healthcare
    Alice Duplicate,alice@example.com,Healthcare
    """

    result = import_contacts(input_csv)

    assert len(result.contacts) == 0  # Both skipped
    assert len(result.duplicates) == 2
    assert "already exists" in result.duplicates[0].reason.lower()
```

#### Test 2.1.5: Large CSV Import (10,000+ rows)
```python
def test_import_large_csv():
    """
    Should handle large files with progress tracking and batch processing.
    """
    input_csv = generate_csv_with_n_contacts(10000)

    with progress_callback() as progress:
        result = import_contacts(input_csv, progress_callback=progress)

    assert len(result.contacts) == 10000
    assert progress.completed == 10000
    assert result.import_time_seconds < 60  # Performance check
```

#### Test 2.1.6: CSV with Special Characters
```python
def test_import_csv_special_characters():
    """
    Should handle Unicode, quotes, commas in fields.
    """
    input_csv = """
    name,email,industry
    "O'Brien, José",jose@example.com,"Tech, AI"
    """

    contacts = import_contacts(input_csv)

    assert contacts[0].name == "O'Brien, José"
    assert contacts[0].industry == "Tech, AI"
```

---

### 2.2 AI-Powered Contact Enrichment

#### Test 2.2.1: Successful Enrichment
```python
def test_enrich_contact_success():
    """
    GPT-4 should return title, company, painpoint, relevance_score.
    """
    contact = Contact(
        name="Alice Smith",
        email="alice@example.com",
        industry="Healthcare"
    )

    enriched = enrich_contact(contact, api_key=OPENAI_KEY)

    assert enriched.title is not None
    assert enriched.company is not None
    assert enriched.painpoint is not None
    assert 0 <= enriched.relevance_score <= 10
    assert enriched.status == ContactStatus.ENRICHED
```

#### Test 2.2.2: Enrichment with Minimal Info
```python
def test_enrich_contact_minimal_info():
    """
    Should handle contacts with only email (no name/industry).
    GPT should infer or mark as unknown.
    """
    contact = Contact(email="unknown@domain.com")

    enriched = enrich_contact(contact, api_key=OPENAI_KEY)

    assert enriched.status == ContactStatus.ENRICHED
    # May have low relevance_score or "Unknown" values
    assert enriched.relevance_score <= 3
```

#### Test 2.2.3: GPT-4 API Timeout
```python
def test_enrich_contact_api_timeout():
    """
    Should retry up to 3 times, then mark as ENRICHMENT_FAILED.
    """
    contact = Contact(name="Bob", email="bob@example.com", industry="Tech")

    with mock_openai_timeout():
        enriched = enrich_contact(contact, api_key=OPENAI_KEY)

    assert enriched.status == ContactStatus.ENRICHMENT_FAILED
    assert enriched.error_message == "API timeout after 3 retries"
    assert enriched.retry_count == 3
```

#### Test 2.2.4: GPT-4 Rate Limit Exceeded
```python
def test_enrich_contact_rate_limit():
    """
    Should implement exponential backoff and retry.
    If still failing, mark as RATE_LIMITED for later retry.
    """
    contacts = [Contact(name=f"User{i}", email=f"user{i}@example.com")
                for i in range(100)]

    with mock_openai_rate_limit(after_n_requests=50):
        results = enrich_contacts_batch(contacts, api_key=OPENAI_KEY)

    successful = [c for c in results if c.status == ContactStatus.ENRICHED]
    rate_limited = [c for c in results if c.status == ContactStatus.RATE_LIMITED]

    assert len(successful) >= 50
    assert len(rate_limited) > 0
```

#### Test 2.2.5: Invalid GPT-4 Response Format
```python
def test_enrich_contact_invalid_response():
    """
    If GPT returns malformed JSON or missing fields, should handle gracefully.
    """
    contact = Contact(name="Alice", email="alice@example.com")

    with mock_openai_response('{"invalid": "response"}'):
        enriched = enrich_contact(contact, api_key=OPENAI_KEY)

    assert enriched.status == ContactStatus.ENRICHMENT_FAILED
    assert "invalid response format" in enriched.error_message.lower()
```

#### Test 2.2.6: Relevance Score Validation
```python
def test_enrich_contact_relevance_score_bounds():
    """
    Relevance score must be 0-10. If GPT returns out-of-bounds, clamp it.
    """
    contact = Contact(name="Alice", email="alice@example.com")

    with mock_openai_response('{"relevance_score": 15, ...}'):
        enriched = enrich_contact(contact, api_key=OPENAI_KEY)

    assert enriched.relevance_score == 10  # Clamped to max
```

#### Test 2.2.7: Batch Enrichment with Progress
```python
def test_enrich_contacts_batch_with_progress():
    """
    Should process contacts in batches with progress updates.
    """
    contacts = [Contact(name=f"User{i}", email=f"user{i}@example.com")
                for i in range(50)]

    progress_updates = []

    def progress_cb(current, total):
        progress_updates.append((current, total))

    enriched = enrich_contacts_batch(
        contacts,
        api_key=OPENAI_KEY,
        batch_size=10,
        progress_callback=progress_cb
    )

    assert len(enriched) == 50
    assert len(progress_updates) >= 5
    assert progress_updates[-1] == (50, 50)
```

#### Test 2.2.8: Prompt Engineering - Output Quality
```python
def test_enrichment_prompt_quality():
    """
    Verify GPT prompt generates high-quality, relevant enrichments.
    Test with known contact data and validate output.
    """
    contact = Contact(
        name="Satya Nadella",
        email="satya@microsoft.com",
        industry="Technology"
    )

    enriched = enrich_contact(contact, api_key=OPENAI_KEY)

    # Assert semantic quality
    assert "microsoft" in enriched.company.lower()
    assert "ceo" in enriched.title.lower() or "chief" in enriched.title.lower()
    assert enriched.relevance_score >= 7  # High relevance for well-known figure
    assert len(enriched.painpoint) > 20  # Substantial painpoint description
```

---

### 2.3 Semantic Embedding & Clustering

#### Test 2.3.1: Generate Embeddings
```python
def test_generate_embeddings_success():
    """
    Should generate 1536-dim embeddings for each contact's enriched data.
    """
    contacts = [
        Contact(name="Alice", industry="Healthcare", painpoint="Patient data"),
        Contact(name="Bob", industry="Finance", painpoint="Fraud detection")
    ]

    embeddings = generate_embeddings(contacts, api_key=OPENAI_KEY)

    assert len(embeddings) == 2
    assert embeddings[0].shape == (1536,)
    assert embeddings[1].shape == (1536,)
```

#### Test 2.3.2: Cluster Similar Contacts
```python
def test_cluster_contacts_similarity():
    """
    Contacts with similar industries/painpoints should cluster together.
    """
    contacts = [
        Contact(name="Alice", industry="Healthcare", painpoint="EHR integration"),
        Contact(name="Bob", industry="Healthcare", painpoint="Patient portals"),
        Contact(name="Charlie", industry="Finance", painpoint="Risk analysis"),
        Contact(name="Diana", industry="Finance", painpoint="Compliance")
    ]

    clusters = cluster_contacts(contacts, api_key=OPENAI_KEY, n_clusters=2)

    assert len(clusters) == 2

    # Check that healthcare contacts are in same cluster
    healthcare_cluster = find_cluster_for_contact(clusters, "Alice")
    assert find_cluster_for_contact(clusters, "Bob") == healthcare_cluster

    # Check that finance contacts are in same cluster
    finance_cluster = find_cluster_for_contact(clusters, "Charlie")
    assert find_cluster_for_contact(clusters, "Diana") == finance_cluster
    assert finance_cluster != healthcare_cluster
```

#### Test 2.3.3: Single Contact Clustering
```python
def test_cluster_single_contact():
    """
    Edge case: 1 contact should form 1 cluster.
    """
    contacts = [Contact(name="Alice", industry="Tech")]

    clusters = cluster_contacts(contacts, api_key=OPENAI_KEY)

    assert len(clusters) == 1
    assert len(clusters[0].contacts) == 1
```

#### Test 2.3.4: All Contacts Identical
```python
def test_cluster_all_identical():
    """
    If all contacts have same data, should still cluster successfully.
    """
    contacts = [
        Contact(name=f"User{i}", industry="Tech", painpoint="Same problem")
        for i in range(10)
    ]

    clusters = cluster_contacts(contacts, api_key=OPENAI_KEY, n_clusters=2)

    # May result in 1 or 2 clusters depending on algorithm
    assert len(clusters) >= 1
    assert sum(len(c.contacts) for c in clusters) == 10
```

#### Test 2.3.5: Optimal Cluster Number Detection
```python
def test_cluster_auto_detect_optimal_k():
    """
    If n_clusters not specified, should use elbow method or silhouette score.
    """
    contacts = [Contact(name=f"User{i}", industry=f"Industry{i%3}")
                for i in range(30)]

    clusters = cluster_contacts(contacts, api_key=OPENAI_KEY, auto_k=True)

    # Should detect ~3 clusters
    assert 2 <= len(clusters) <= 5
```

#### Test 2.3.6: Embedding API Failure
```python
def test_embedding_api_failure():
    """
    If embedding API fails, should mark contacts and allow retry.
    """
    contacts = [Contact(name="Alice", industry="Tech")]

    with mock_openai_embedding_failure():
        result = generate_embeddings(contacts, api_key=OPENAI_KEY)

    assert result.status == "failed"
    assert "embedding api error" in result.error_message.lower()
```

#### Test 2.3.7: Cluster Labeling
```python
def test_cluster_label_generation():
    """
    Each cluster should get a human-readable label from common themes.
    """
    contacts = [
        Contact(name="Alice", industry="Healthcare", painpoint="EHR"),
        Contact(name="Bob", industry="Healthcare", painpoint="Telemedicine")
    ]

    clusters = cluster_contacts(contacts, api_key=OPENAI_KEY, generate_labels=True)

    assert clusters[0].label is not None
    assert "health" in clusters[0].label.lower()
```

---

### 2.4 Email Draft Generation

#### Test 2.4.1: Generate Personalized Email Draft
```python
def test_generate_email_draft_success():
    """
    Should use template + contact data to create personalized email.
    """
    contact = Contact(
        name="Alice Smith",
        title="VP of Engineering",
        company="TechCorp",
        painpoint="Scaling infrastructure"
    )

    template = EmailTemplate(
        subject="Help with {{company}} infrastructure",
        body="Hi {{name}}, I noticed {{company}} might benefit from..."
    )

    draft = generate_email_draft(contact, template, api_key=OPENAI_KEY)

    assert "Alice" in draft.body
    assert "TechCorp" in draft.body
    assert "Scaling infrastructure" in draft.body.lower() or "infrastructure" in draft.body.lower()
    assert draft.subject == "Help with TechCorp infrastructure"
    assert draft.status == DraftStatus.PENDING_APPROVAL
```

#### Test 2.4.2: Draft with Missing Contact Data
```python
def test_generate_email_draft_missing_fields():
    """
    If contact missing title/company, should use fallback or generic language.
    """
    contact = Contact(name="Bob", email="bob@example.com")  # No title, company

    template = EmailTemplate(
        subject="Quick question",
        body="Hi {{name}}, I noticed you work at {{company}}..."
    )

    draft = generate_email_draft(contact, template, api_key=OPENAI_KEY)

    assert "Bob" in draft.body
    assert "{{company}}" not in draft.body  # Should replace with fallback
    assert draft.body != ""  # Should still generate something
```

#### Test 2.4.3: Draft Length Validation
```python
def test_generate_email_draft_length_limit():
    """
    Email should be concise (recommended < 150 words).
    """
    contact = Contact(name="Alice", company="TechCorp")
    template = EmailTemplate(
        subject="Intro",
        body="Hi {{name}}, write a very long introduction..."
    )

    draft = generate_email_draft(
        contact,
        template,
        api_key=OPENAI_KEY,
        max_words=150
    )

    word_count = len(draft.body.split())
    assert word_count <= 160  # Allow 10 word buffer
```

#### Test 2.4.4: Subject Line Personalization
```python
def test_generate_email_subject_personalization():
    """
    Subject should be personalized and engaging, not generic.
    """
    contact = Contact(name="Alice", company="TechCorp", industry="Healthcare")

    draft = generate_email_draft(contact, template=None, api_key=OPENAI_KEY)

    assert len(draft.subject) > 0
    assert len(draft.subject) < 80  # Email client limit
    # Should reference something specific
    assert any(keyword in draft.subject.lower()
               for keyword in ["techcorp", "healthcare", "alice"])
```

#### Test 2.4.5: Bulk Draft Generation
```python
def test_generate_bulk_drafts():
    """
    Should generate drafts for multiple contacts efficiently.
    """
    contacts = [Contact(name=f"User{i}", email=f"user{i}@example.com")
                for i in range(20)]

    template = EmailTemplate(subject="Hi {{name}}", body="...")

    drafts = generate_email_drafts_bulk(contacts, template, api_key=OPENAI_KEY)

    assert len(drafts) == 20
    assert all(d.status == DraftStatus.PENDING_APPROVAL for d in drafts)
    assert all(contacts[i].name in drafts[i].body for i in range(20))
```

#### Test 2.4.6: Draft Tone Consistency
```python
def test_draft_tone_consistency():
    """
    All drafts should maintain professional, friendly tone.
    """
    contacts = [
        Contact(name="Alice", industry="Healthcare"),
        Contact(name="Bob", industry="Finance")
    ]

    drafts = generate_email_drafts_bulk(contacts, template=None, api_key=OPENAI_KEY)

    for draft in drafts:
        # Use tone analyzer or regex checks
        assert not contains_aggressive_language(draft.body)
        assert not contains_overly_casual_language(draft.body)
        assert has_professional_greeting(draft.body)
```

#### Test 2.4.7: HTML vs Plain Text
```python
def test_draft_format_plain_text():
    """
    Drafts should be plain text by default, with optional HTML.
    """
    contact = Contact(name="Alice")
    template = EmailTemplate(body="Hi {{name}}")

    draft_plain = generate_email_draft(contact, template, format="plain")
    draft_html = generate_email_draft(contact, template, format="html")

    assert "<html>" not in draft_plain.body
    assert "<html>" in draft_html.body or "<p>" in draft_html.body
```

---

### 2.5 Human-in-the-Loop Approval

#### Test 2.5.1: Single Draft Approval
```python
def test_approve_single_draft():
    """
    User approves draft, status changes to APPROVED.
    """
    draft = EmailDraft(contact_id=1, body="...", status=DraftStatus.PENDING_APPROVAL)
    db.save(draft)

    approve_draft(draft.id, user_id=1)

    updated = db.get_draft(draft.id)
    assert updated.status == DraftStatus.APPROVED
    assert updated.approved_at is not None
    assert updated.approved_by == 1
```

#### Test 2.5.2: Single Draft Rejection
```python
def test_reject_single_draft():
    """
    User rejects draft with reason, status changes to REJECTED.
    """
    draft = EmailDraft(contact_id=1, body="...", status=DraftStatus.PENDING_APPROVAL)
    db.save(draft)

    reject_draft(draft.id, reason="Not personalized enough", user_id=1)

    updated = db.get_draft(draft.id)
    assert updated.status == DraftStatus.REJECTED
    assert updated.rejection_reason == "Not personalized enough"
```

#### Test 2.5.3: Bulk Approve Multiple Drafts
```python
def test_approve_bulk_drafts():
    """
    User selects multiple drafts and approves all at once.
    """
    drafts = [EmailDraft(contact_id=i, body=f"Email {i}") for i in range(5)]
    for d in drafts:
        db.save(d)

    draft_ids = [d.id for d in drafts]
    approve_drafts_bulk(draft_ids, user_id=1)

    for draft_id in draft_ids:
        updated = db.get_draft(draft_id)
        assert updated.status == DraftStatus.APPROVED
```

#### Test 2.5.4: Edit Draft Before Approval
```python
def test_edit_draft_before_approval():
    """
    User edits draft content, then approves.
    """
    draft = EmailDraft(contact_id=1, body="Original body")
    db.save(draft)

    edit_draft(draft.id, new_body="Edited body", user_id=1)
    approve_draft(draft.id, user_id=1)

    updated = db.get_draft(draft.id)
    assert updated.body == "Edited body"
    assert updated.status == DraftStatus.APPROVED
    assert updated.edited == True
```

#### Test 2.5.5: Cannot Approve Already Sent Draft
```python
def test_cannot_approve_already_sent():
    """
    If draft already sent, approval should fail.
    """
    draft = EmailDraft(contact_id=1, body="...", status=DraftStatus.SENT)
    db.save(draft)

    with pytest.raises(InvalidStateTransition):
        approve_draft(draft.id, user_id=1)
```

#### Test 2.5.6: Approval with Notes
```python
def test_approve_draft_with_notes():
    """
    User can add notes when approving.
    """
    draft = EmailDraft(contact_id=1, body="...")
    db.save(draft)

    approve_draft(draft.id, user_id=1, notes="Looks great!")

    updated = db.get_draft(draft.id)
    assert updated.approval_notes == "Looks great!"
```

---

### 2.6 Email Sending

#### Test 2.6.1: Send Approved Draft via Gmail API
```python
def test_send_email_via_gmail_success():
    """
    Approved draft should be sent via Gmail API.
    """
    draft = EmailDraft(
        contact_id=1,
        to_email="recipient@example.com",
        subject="Test",
        body="Hello",
        status=DraftStatus.APPROVED
    )
    db.save(draft)

    with mock_gmail_api() as gmail:
        result = send_email(draft.id, gmail_credentials=GMAIL_CREDS)

    assert result.status == SendStatus.SENT
    assert result.message_id is not None

    updated = db.get_draft(draft.id)
    assert updated.status == DraftStatus.SENT
    assert updated.sent_at is not None
```

#### Test 2.6.2: Send Email - Gmail API Failure
```python
def test_send_email_gmail_api_failure():
    """
    If Gmail API fails, should retry 3 times then mark as SEND_FAILED.
    """
    draft = EmailDraft(contact_id=1, to_email="test@example.com", status=DraftStatus.APPROVED)
    db.save(draft)

    with mock_gmail_api_failure():
        result = send_email(draft.id, gmail_credentials=GMAIL_CREDS)

    assert result.status == SendStatus.SEND_FAILED
    assert result.retry_count == 3

    updated = db.get_draft(draft.id)
    assert updated.status == DraftStatus.SEND_FAILED
```

#### Test 2.6.3: Prevent Duplicate Sends
```python
def test_prevent_duplicate_send():
    """
    Cannot send same draft twice.
    """
    draft = EmailDraft(contact_id=1, status=DraftStatus.SENT, message_id="msg123")
    db.save(draft)

    with pytest.raises(DuplicateSendError):
        send_email(draft.id, gmail_credentials=GMAIL_CREDS)
```

#### Test 2.6.4: Send Only Approved Drafts
```python
def test_cannot_send_unapproved_draft():
    """
    Unapproved drafts should not be sent.
    """
    draft = EmailDraft(contact_id=1, status=DraftStatus.PENDING_APPROVAL)
    db.save(draft)

    with pytest.raises(DraftNotApprovedError):
        send_email(draft.id, gmail_credentials=GMAIL_CREDS)
```

#### Test 2.6.5: Mock Send Mode
```python
def test_mock_send_mode():
    """
    In test/dev mode, should log send without actually sending.
    """
    draft = EmailDraft(contact_id=1, to_email="test@example.com", status=DraftStatus.APPROVED)
    db.save(draft)

    result = send_email(draft.id, mock_mode=True)

    assert result.status == SendStatus.MOCK_SENT
    assert result.message_id.startswith("mock_")

    updated = db.get_draft(draft.id)
    assert updated.status == DraftStatus.SENT  # Still marked as sent
```

#### Test 2.6.6: Rate Limiting - Throttle Sends
```python
def test_send_rate_limiting():
    """
    Should not exceed Gmail API rate limits (e.g., 100 emails/day for free tier).
    """
    drafts = [EmailDraft(contact_id=i, status=DraftStatus.APPROVED)
              for i in range(150)]
    for d in drafts:
        db.save(d)

    results = send_emails_bulk(
        [d.id for d in drafts],
        gmail_credentials=GMAIL_CREDS,
        rate_limit=100
    )

    sent = [r for r in results if r.status == SendStatus.SENT]
    rate_limited = [r for r in results if r.status == SendStatus.RATE_LIMITED]

    assert len(sent) == 100
    assert len(rate_limited) == 50
```

#### Test 2.6.7: Track Sent Email Metadata
```python
def test_track_sent_email_metadata():
    """
    After sending, should store Gmail message_id and thread_id for tracking.
    """
    draft = EmailDraft(contact_id=1, status=DraftStatus.APPROVED)
    db.save(draft)

    with mock_gmail_api() as gmail:
        gmail.set_response(message_id="msg123", thread_id="thread456")
        send_email(draft.id, gmail_credentials=GMAIL_CREDS)

    updated = db.get_draft(draft.id)
    assert updated.message_id == "msg123"
    assert updated.thread_id == "thread456"
```

#### Test 2.6.8: Send with Attachment
```python
def test_send_email_with_attachment():
    """
    Should support optional attachments (e.g., PDF, calendar invite).
    """
    draft = EmailDraft(
        contact_id=1,
        status=DraftStatus.APPROVED,
        attachments=["proposal.pdf"]
    )
    db.save(draft)

    with mock_gmail_api() as gmail:
        send_email(draft.id, gmail_credentials=GMAIL_CREDS)

        sent_message = gmail.get_last_sent_message()
        assert "proposal.pdf" in sent_message.attachments
```

---

### 2.7 Reply Monitoring & Classification

#### Test 2.7.1: Fetch and Detect Reply
```python
def test_fetch_reply_success():
    """
    Should detect when recipient replies to sent email.
    """
    sent_draft = EmailDraft(
        contact_id=1,
        thread_id="thread123",
        status=DraftStatus.SENT
    )
    db.save(sent_draft)

    with mock_gmail_api() as gmail:
        gmail.add_reply(
            thread_id="thread123",
            from_email="recipient@example.com",
            body="Thanks for reaching out! I'm interested."
        )

        check_replies(gmail_credentials=GMAIL_CREDS)

    reply = db.get_reply_for_draft(sent_draft.id)
    assert reply is not None
    assert reply.body == "Thanks for reaching out! I'm interested."
```

#### Test 2.7.2: Classify Reply - Interested
```python
def test_classify_reply_interested():
    """
    GPT should classify positive replies as INTERESTED.
    """
    reply = Reply(
        draft_id=1,
        from_email="recipient@example.com",
        body="Yes, I'd love to learn more. Let's schedule a call."
    )

    classification = classify_reply_intent(reply, api_key=OPENAI_KEY)

    assert classification.intent == ReplyIntent.INTERESTED
    assert classification.confidence >= 0.8
```

#### Test 2.7.3: Classify Reply - Maybe
```python
def test_classify_reply_maybe():
    """
    Ambiguous replies should be classified as MAYBE.
    """
    reply = Reply(
        draft_id=1,
        body="Interesting, but not sure if this is right for us right now."
    )

    classification = classify_reply_intent(reply, api_key=OPENAI_KEY)

    assert classification.intent == ReplyIntent.MAYBE
```

#### Test 2.7.4: Classify Reply - Decline
```python
def test_classify_reply_decline():
    """
    Negative replies should be classified as DECLINE.
    """
    reply = Reply(
        draft_id=1,
        body="Thanks, but we're not interested at this time."
    )

    classification = classify_reply_intent(reply, api_key=OPENAI_KEY)

    assert classification.intent == ReplyIntent.DECLINE
```

#### Test 2.7.5: Classify Reply - Auto-reply
```python
def test_classify_reply_auto_reply():
    """
    Out-of-office and auto-replies should be detected.
    """
    reply = Reply(
        draft_id=1,
        body="I'm currently out of office and will respond when I return."
    )

    classification = classify_reply_intent(reply, api_key=OPENAI_KEY)

    assert classification.intent == ReplyIntent.AUTO_REPLY
```

#### Test 2.7.6: Handle Multi-message Thread
```python
def test_handle_multi_message_thread():
    """
    If recipient sends multiple replies, should track all.
    """
    sent_draft = EmailDraft(contact_id=1, thread_id="thread123", status=DraftStatus.SENT)
    db.save(sent_draft)

    with mock_gmail_api() as gmail:
        gmail.add_reply(thread_id="thread123", body="Initial interest")
        gmail.add_reply(thread_id="thread123", body="Follow-up question")

        check_replies(gmail_credentials=GMAIL_CREDS)

    replies = db.get_replies_for_draft(sent_draft.id)
    assert len(replies) == 2
    assert replies[0].body == "Initial interest"
    assert replies[1].body == "Follow-up question"
```

#### Test 2.7.7: Ignore Replies from Self
```python
def test_ignore_self_replies():
    """
    Should not treat own replies in thread as recipient reply.
    """
    sent_draft = EmailDraft(
        contact_id=1,
        thread_id="thread123",
        from_email="me@mycompany.com"
    )
    db.save(sent_draft)

    with mock_gmail_api() as gmail:
        gmail.add_reply(
            thread_id="thread123",
            from_email="me@mycompany.com",
            body="Following up"
        )

        check_replies(gmail_credentials=GMAIL_CREDS)

    replies = db.get_replies_for_draft(sent_draft.id)
    assert len(replies) == 0
```

#### Test 2.7.8: Reply with No Body (Attachment Only)
```python
def test_reply_with_only_attachment():
    """
    If reply has no body text, should still process.
    """
    reply = Reply(draft_id=1, body="", attachments=["document.pdf"])

    classification = classify_reply_intent(reply, api_key=OPENAI_KEY)

    # Should classify based on presence of attachment
    assert classification.intent in [ReplyIntent.INTERESTED, ReplyIntent.MAYBE]
```

---

### 2.8 Follow-up Automation

#### Test 2.8.1: Generate Follow-up After 7 Days
```python
def test_generate_followup_after_7_days():
    """
    If no reply after 7 days, suggest follow-up.
    """
    sent_draft = EmailDraft(
        contact_id=1,
        sent_at=datetime.now() - timedelta(days=7),
        status=DraftStatus.SENT
    )
    db.save(sent_draft)

    # Run daily cron job
    followups = check_and_generate_followups()

    assert len(followups) == 1
    assert followups[0].original_draft_id == sent_draft.id
    assert followups[0].status == DraftStatus.PENDING_APPROVAL
    assert "following up" in followups[0].body.lower()
```

#### Test 2.8.2: No Follow-up If Already Replied
```python
def test_no_followup_if_replied():
    """
    If recipient already replied, should not generate follow-up.
    """
    sent_draft = EmailDraft(
        contact_id=1,
        sent_at=datetime.now() - timedelta(days=7),
        status=DraftStatus.SENT
    )
    db.save(sent_draft)

    reply = Reply(draft_id=sent_draft.id, body="Thanks!")
    db.save(reply)

    followups = check_and_generate_followups()

    assert len(followups) == 0
```

#### Test 2.8.3: No Follow-up If Declined
```python
def test_no_followup_if_declined():
    """
    If recipient declined, respect their decision and don't follow up.
    """
    sent_draft = EmailDraft(
        contact_id=1,
        sent_at=datetime.now() - timedelta(days=7)
    )
    db.save(sent_draft)

    reply = Reply(draft_id=sent_draft.id, body="Not interested", intent=ReplyIntent.DECLINE)
    db.save(reply)

    followups = check_and_generate_followups()

    assert len(followups) == 0
```

#### Test 2.8.4: Multi-stage Follow-up Sequence
```python
def test_multistage_followup_sequence():
    """
    Support up to 2-3 follow-ups with increasing intervals.
    """
    sent_draft = EmailDraft(contact_id=1, sent_at=datetime.now() - timedelta(days=7))
    db.save(sent_draft)

    # First follow-up
    followups_1 = check_and_generate_followups()
    assert len(followups_1) == 1

    followup_1 = followups_1[0]
    approve_draft(followup_1.id, user_id=1)
    send_email(followup_1.id)

    # Mark as sent 7 days ago
    db.update_draft(followup_1.id, sent_at=datetime.now() - timedelta(days=7))

    # Second follow-up
    followups_2 = check_and_generate_followups()
    assert len(followups_2) == 1
    assert followups_2[0].followup_sequence_number == 2
```

#### Test 2.8.5: Max Follow-ups Limit
```python
def test_max_followups_limit():
    """
    Should not generate more than 2-3 follow-ups to avoid spam.
    """
    sent_draft = EmailDraft(contact_id=1, sent_at=datetime.now() - timedelta(days=7))
    db.save(sent_draft)

    # Generate and send 3 follow-ups
    for i in range(3):
        followups = check_and_generate_followups()
        if followups:
            f = followups[0]
            approve_draft(f.id, user_id=1)
            send_email(f.id)
            db.update_draft(f.id, sent_at=datetime.now() - timedelta(days=7))

    # Try to generate 4th follow-up
    followups_4 = check_and_generate_followups()

    assert len(followups_4) == 0  # Max limit reached
```

#### Test 2.8.6: Follow-up Personalization
```python
def test_followup_personalization():
    """
    Follow-up should reference original email and add new value.
    """
    sent_draft = EmailDraft(
        contact_id=1,
        subject="Original subject",
        body="Original body",
        sent_at=datetime.now() - timedelta(days=7)
    )
    db.save(sent_draft)

    followups = check_and_generate_followups(api_key=OPENAI_KEY)

    followup = followups[0]
    assert "following up" in followup.body.lower() or "touch base" in followup.body.lower()
    # Should add new insight or value, not just "checking in"
    assert len(followup.body) > len(sent_draft.body) * 0.5
```

#### Test 2.8.7: User Disable Follow-up for Contact
```python
def test_user_disable_followup():
    """
    User can mark contact as "do not follow up".
    """
    contact = Contact(id=1, name="Alice", do_not_followup=True)
    db.save(contact)

    sent_draft = EmailDraft(
        contact_id=1,
        sent_at=datetime.now() - timedelta(days=7)
    )
    db.save(sent_draft)

    followups = check_and_generate_followups()

    assert len(followups) == 0
```

---

### 2.9 Meeting Scheduling

#### Test 2.9.1: Suggest Meeting Times for Interested Reply
```python
def test_suggest_meeting_times_interested():
    """
    When reply is INTERESTED, suggest 3-5 meeting time slots.
    """
    reply = Reply(
        draft_id=1,
        body="I'd love to chat!",
        intent=ReplyIntent.INTERESTED
    )
    db.save(reply)

    availability_slots = [
        datetime(2025, 11, 15, 10, 0),
        datetime(2025, 11, 15, 14, 0),
        datetime(2025, 11, 16, 9, 0)
    ]

    suggestions = generate_meeting_suggestions(
        reply,
        availability_slots=availability_slots
    )

    assert len(suggestions) >= 3
    assert all(s in availability_slots for s in suggestions)
```

#### Test 2.9.2: Parse Availability from Reply
```python
def test_parse_availability_from_reply():
    """
    If recipient mentions availability, should extract times.
    """
    reply = Reply(
        draft_id=1,
        body="I'm free Tuesday at 2pm or Wednesday morning."
    )

    parsed = parse_availability_from_reply(reply, api_key=OPENAI_KEY)

    assert len(parsed.suggested_times) >= 2
    assert any("tuesday" in str(t).lower() for t in parsed.suggested_times)
    assert any("wednesday" in str(t).lower() for t in parsed.suggested_times)
```

#### Test 2.9.3: Generate Calendar Invite Draft
```python
def test_generate_calendar_invite():
    """
    Should generate .ics file or Google Calendar link.
    """
    meeting_time = datetime(2025, 11, 15, 10, 0)

    invite = generate_calendar_invite(
        contact_email="alice@example.com",
        meeting_time=meeting_time,
        duration_minutes=30,
        title="Intro Call"
    )

    assert invite.format == "ics"
    assert "alice@example.com" in invite.content
    assert "2025-11-15" in invite.content
```

#### Test 2.9.4: No Meeting Suggestions for Decline
```python
def test_no_meeting_suggestions_for_decline():
    """
    If reply is DECLINE, should not suggest meetings.
    """
    reply = Reply(draft_id=1, intent=ReplyIntent.DECLINE)
    db.save(reply)

    suggestions = generate_meeting_suggestions(reply)

    assert len(suggestions) == 0
```

#### Test 2.9.5: Timezone Handling
```python
def test_meeting_timezone_handling():
    """
    Should handle different timezones for sender and recipient.
    """
    contact = Contact(id=1, timezone="America/Los_Angeles")
    user_timezone = "America/New_York"

    availability_slots = [
        datetime(2025, 11, 15, 14, 0)  # 2pm ET
    ]

    suggestions = generate_meeting_suggestions_for_contact(
        contact,
        availability_slots,
        user_timezone=user_timezone
    )

    # Should convert to recipient's timezone (11am PT)
    assert "11:00 AM PST" in suggestions[0].display_time or "11am" in suggestions[0].display_time.lower()
```

---

### 2.10 Persistence & State Management

#### Test 2.10.1: Save and Retrieve Contact
```python
def test_save_and_retrieve_contact():
    """
    Contact should persist to database and be retrievable.
    """
    contact = Contact(name="Alice", email="alice@example.com", industry="Tech")

    contact_id = db.save_contact(contact)

    retrieved = db.get_contact(contact_id)
    assert retrieved.name == "Alice"
    assert retrieved.email == "alice@example.com"
```

#### Test 2.10.2: Update Contact Status
```python
def test_update_contact_status():
    """
    Should track contact status through lifecycle.
    """
    contact = Contact(name="Alice", status=ContactStatus.IMPORTED)
    contact_id = db.save_contact(contact)

    db.update_contact_status(contact_id, ContactStatus.ENRICHED)
    assert db.get_contact(contact_id).status == ContactStatus.ENRICHED

    db.update_contact_status(contact_id, ContactStatus.EMAIL_SENT)
    assert db.get_contact(contact_id).status == ContactStatus.EMAIL_SENT
```

#### Test 2.10.3: Transaction Rollback on Error
```python
def test_transaction_rollback():
    """
    If enrichment fails mid-batch, should rollback changes.
    """
    contacts = [Contact(name=f"User{i}") for i in range(5)]

    with pytest.raises(Exception):
        with db.transaction():
            for i, contact in enumerate(contacts):
                db.save_contact(contact)
                if i == 3:
                    raise Exception("Simulated error")

    # No contacts should be saved
    assert db.count_contacts() == 0
```

#### Test 2.10.4: Concurrent Access Handling
```python
def test_concurrent_draft_edits():
    """
    Two users editing same draft should handle conflicts.
    """
    draft = EmailDraft(contact_id=1, body="Original")
    draft_id = db.save_draft(draft)

    # User 1 edits
    user1_thread = Thread(target=lambda: db.update_draft(draft_id, body="User 1 edit"))

    # User 2 edits simultaneously
    user2_thread = Thread(target=lambda: db.update_draft(draft_id, body="User 2 edit"))

    user1_thread.start()
    user2_thread.start()
    user1_thread.join()
    user2_thread.join()

    # Last write wins, or optimistic locking raises error
    updated = db.get_draft(draft_id)
    assert updated.body in ["User 1 edit", "User 2 edit"]
```

#### Test 2.10.5: Soft Delete Contacts
```python
def test_soft_delete_contact():
    """
    Deleting contact should mark as deleted, not remove from DB.
    """
    contact = Contact(name="Alice")
    contact_id = db.save_contact(contact)

    db.delete_contact(contact_id)

    # Should not appear in normal queries
    assert db.get_contact(contact_id) is None

    # But should exist with deleted flag
    assert db.get_contact(contact_id, include_deleted=True).deleted == True
```

#### Test 2.10.6: Query Drafts by Status
```python
def test_query_drafts_by_status():
    """
    Should efficiently query drafts by status.
    """
    drafts = [
        EmailDraft(contact_id=1, status=DraftStatus.PENDING_APPROVAL),
        EmailDraft(contact_id=2, status=DraftStatus.APPROVED),
        EmailDraft(contact_id=3, status=DraftStatus.SENT)
    ]
    for d in drafts:
        db.save_draft(d)

    pending = db.get_drafts_by_status(DraftStatus.PENDING_APPROVAL)
    assert len(pending) == 1

    approved = db.get_drafts_by_status(DraftStatus.APPROVED)
    assert len(approved) == 1
```

#### Test 2.10.7: Audit Log for State Changes
```python
def test_audit_log_state_changes():
    """
    All status changes should be logged for audit.
    """
    contact = Contact(name="Alice", status=ContactStatus.IMPORTED)
    contact_id = db.save_contact(contact)

    db.update_contact_status(contact_id, ContactStatus.ENRICHED, user_id=1)
    db.update_contact_status(contact_id, ContactStatus.EMAIL_SENT, user_id=1)

    audit_log = db.get_audit_log(contact_id)

    assert len(audit_log) == 2
    assert audit_log[0].old_status == ContactStatus.IMPORTED
    assert audit_log[0].new_status == ContactStatus.ENRICHED
    assert audit_log[1].new_status == ContactStatus.EMAIL_SENT
```

#### Test 2.10.8: Database Migration Support
```python
def test_database_migration():
    """
    Schema changes should be handled via migrations.
    """
    # Add new column
    db.migrate("add_column_contact_score")

    contact = Contact(name="Alice", score=0.85)
    contact_id = db.save_contact(contact)

    retrieved = db.get_contact(contact_id)
    assert hasattr(retrieved, 'score')
    assert retrieved.score == 0.85
```

---

### 2.11 End-to-End Integration Tests

#### Test 2.11.1: Full Pipeline - Import to Send
```python
def test_full_pipeline_import_to_send():
    """
    End-to-end test: Import CSV → Enrich → Cluster → Draft → Approve → Send.
    """
    # 1. Import
    input_csv = """
    name,email,industry
    Alice Smith,alice@example.com,Healthcare
    Bob Jones,bob@example.com,Finance
    """
    contacts = import_contacts(input_csv)
    assert len(contacts) == 2

    # 2. Enrich
    enriched = enrich_contacts_batch(contacts, api_key=OPENAI_KEY)
    assert all(c.status == ContactStatus.ENRICHED for c in enriched)

    # 3. Cluster
    clusters = cluster_contacts(enriched, api_key=OPENAI_KEY)
    assert len(clusters) >= 1

    # 4. User selects cluster and contacts
    selected_contacts = clusters[0].contacts

    # 5. Generate drafts
    template = EmailTemplate(subject="Hi {{name}}", body="...")
    drafts = generate_email_drafts_bulk(selected_contacts, template, api_key=OPENAI_KEY)
    assert len(drafts) == len(selected_contacts)

    # 6. User approves
    for draft in drafts:
        approve_draft(draft.id, user_id=1)

    # 7. Send
    for draft in drafts:
        result = send_email(draft.id, mock_mode=True)
        assert result.status == SendStatus.MOCK_SENT
```

#### Test 2.11.2: Full Pipeline - Reply and Follow-up
```python
def test_full_pipeline_reply_and_followup():
    """
    End-to-end: Send email → Receive reply → Classify → No follow-up.
    """
    # 1. Send email
    draft = EmailDraft(contact_id=1, status=DraftStatus.APPROVED, thread_id="thread123")
    db.save(draft)
    send_email(draft.id, mock_mode=True)

    # 2. Simulate reply after 3 days
    with mock_gmail_api() as gmail:
        gmail.add_reply(
            thread_id="thread123",
            from_email="recipient@example.com",
            body="Thanks, I'm interested!"
        )
        check_replies(gmail_credentials=GMAIL_CREDS)

    # 3. Classify reply
    reply = db.get_reply_for_draft(draft.id)
    classification = classify_reply_intent(reply, api_key=OPENAI_KEY)
    assert classification.intent == ReplyIntent.INTERESTED

    # 4. Check no follow-up generated
    db.update_draft(draft.id, sent_at=datetime.now() - timedelta(days=7))
    followups = check_and_generate_followups()
    assert len(followups) == 0  # Already replied
```

#### Test 2.11.3: Multi-user Scenario
```python
def test_multiuser_scenario():
    """
    Multiple users managing separate campaigns.
    """
    # User 1
    contacts_1 = import_contacts(csv_1, user_id=1)
    drafts_1 = generate_email_drafts_bulk(contacts_1, template_1, user_id=1)

    # User 2
    contacts_2 = import_contacts(csv_2, user_id=2)
    drafts_2 = generate_email_drafts_bulk(contacts_2, template_2, user_id=2)

    # User 1 should only see their drafts
    user_1_drafts = db.get_drafts_by_user(user_id=1)
    assert len(user_1_drafts) == len(drafts_1)
    assert all(d.user_id == 1 for d in user_1_drafts)
```

#### Test 2.11.4: Error Recovery - Retry Failed Enrichments
```python
def test_error_recovery_retry_enrichments():
    """
    Failed enrichments should be retryable without re-importing.
    """
    contacts = [Contact(name=f"User{i}") for i in range(10)]

    # First attempt - some fail
    with mock_openai_partial_failure(fail_indices=[3, 7]):
        enriched = enrich_contacts_batch(contacts, api_key=OPENAI_KEY)

    failed = [c for c in enriched if c.status == ContactStatus.ENRICHMENT_FAILED]
    assert len(failed) == 2

    # Retry failed ones
    retry_result = retry_failed_enrichments(api_key=OPENAI_KEY)

    assert retry_result.success_count == 2
    assert db.count_contacts_by_status(ContactStatus.ENRICHMENT_FAILED) == 0
```

#### Test 2.11.5: Performance - 1000 Contacts Pipeline
```python
@pytest.mark.slow
def test_performance_1000_contacts():
    """
    Full pipeline with 1000 contacts should complete in reasonable time.
    """
    contacts = [Contact(name=f"User{i}", email=f"user{i}@example.com")
                for i in range(1000)]

    start_time = time.time()

    # Import
    for c in contacts:
        db.save_contact(c)

    # Enrich (with rate limiting)
    enriched = enrich_contacts_batch(contacts, api_key=OPENAI_KEY, batch_size=50)

    # Cluster
    clusters = cluster_contacts(enriched, api_key=OPENAI_KEY)

    # Draft
    drafts = generate_email_drafts_bulk(enriched[:100], template, api_key=OPENAI_KEY)

    elapsed = time.time() - start_time

    # Should complete in < 30 minutes with proper batching
    assert elapsed < 1800
```

---

### 2.12 Production Readiness - Tier 1 (Must-Have)

#### Test 2.12.1: Track OpenAI API Costs
```python
def test_track_openai_api_costs():
    """
    Should track costs for all OpenAI API calls (enrichment, embedding, drafts).
    """
    contacts = [Contact(name=f"User{i}") for i in range(10)]

    cost_tracker = CostTracker()

    # Enrich contacts
    enriched = enrich_contacts_batch(
        contacts,
        api_key=OPENAI_KEY,
        cost_tracker=cost_tracker
    )

    # Generate drafts
    drafts = generate_email_drafts_bulk(
        enriched,
        template,
        api_key=OPENAI_KEY,
        cost_tracker=cost_tracker
    )

    total_cost = cost_tracker.get_total_cost()

    assert total_cost > 0
    assert cost_tracker.enrichment_cost > 0
    assert cost_tracker.draft_generation_cost > 0

    # Should have detailed breakdown
    breakdown = cost_tracker.get_breakdown()
    assert "gpt-4-turbo" in breakdown
    assert "text-embedding-3-small" in breakdown
```

#### Test 2.12.2: Enforce Daily Budget Limit
```python
def test_enforce_daily_budget_limit():
    """
    Should stop operations when daily budget limit is reached.
    """
    config = Config(daily_budget_limit=10.00)  # $10/day
    cost_tracker = CostTracker(config=config)

    # Simulate operations that would exceed budget
    contacts = [Contact(name=f"User{i}") for i in range(1000)]

    result = enrich_contacts_batch(
        contacts,
        api_key=OPENAI_KEY,
        cost_tracker=cost_tracker
    )

    # Should stop before completing all
    assert result.completed_count < 1000
    assert result.stopped_reason == "BUDGET_LIMIT_REACHED"
    assert cost_tracker.get_total_cost() <= 10.00
```

#### Test 2.12.3: Cost Estimate Before Operation
```python
def test_estimate_cost_before_operation():
    """
    Provide cost estimate before running expensive operations.
    """
    contacts = [Contact(name=f"User{i}") for i in range(500)]

    estimate = estimate_enrichment_cost(
        num_contacts=500,
        model="gpt-4-turbo"
    )

    assert estimate.min_cost > 0
    assert estimate.max_cost > estimate.min_cost
    assert estimate.estimated_cost > 0
    assert "enrichment" in estimate.breakdown
    assert "embedding" in estimate.breakdown
```

#### Test 2.12.4: Unsubscribe Link in All Emails
```python
def test_unsubscribe_link_in_emails():
    """
    Every email must include unsubscribe link for CAN-SPAM compliance.
    """
    contact = Contact(id=1, name="Alice", email="alice@example.com")
    draft = generate_email_draft(contact, template, api_key=OPENAI_KEY)

    # Check for unsubscribe link
    assert "unsubscribe" in draft.body.lower()
    assert "{{unsubscribe_url}}" in draft.body or draft.unsubscribe_url is not None

    # When sent, unsubscribe URL should be unique per contact
    sent_email = send_email(draft.id, mock_mode=True)
    unsubscribe_token = extract_unsubscribe_token(sent_email.body)

    assert unsubscribe_token is not None
    assert len(unsubscribe_token) >= 32  # Secure token
```

#### Test 2.12.5: Process Unsubscribe Request
```python
def test_process_unsubscribe_request():
    """
    When user clicks unsubscribe, mark contact and prevent future emails.
    """
    contact = Contact(id=1, email="alice@example.com", unsubscribed=False)
    db.save(contact)

    # Simulate unsubscribe
    unsubscribe_token = generate_unsubscribe_token(contact.id)
    process_unsubscribe(unsubscribe_token)

    # Contact should be marked
    updated = db.get_contact(contact.id)
    assert updated.unsubscribed == True
    assert updated.unsubscribed_at is not None

    # Future drafts should fail
    with pytest.raises(ContactUnsubscribedError):
        generate_email_draft(updated, template)
```

#### Test 2.12.6: Honor Unsubscribe in Follow-ups
```python
def test_honor_unsubscribe_in_followups():
    """
    If contact unsubscribes after first email, don't send follow-ups.
    """
    # Send initial email
    draft = EmailDraft(contact_id=1, status=DraftStatus.SENT, sent_at=datetime.now() - timedelta(days=7))
    db.save(draft)

    # Contact unsubscribes
    contact = db.get_contact(1)
    contact.unsubscribed = True
    db.save(contact)

    # Follow-up should not be generated
    followups = check_and_generate_followups()

    assert len(followups) == 0
```

#### Test 2.12.7: Gmail Daily Send Quota
```python
def test_gmail_daily_send_quota():
    """
    Track and enforce Gmail daily send limits (500 for paid, 100 for free).
    """
    config = Config(gmail_daily_limit=100)
    quota_tracker = GmailQuotaTracker(config=config)

    # Approve 150 drafts
    drafts = [EmailDraft(contact_id=i, status=DraftStatus.APPROVED) for i in range(150)]
    for d in drafts:
        db.save(d)

    results = send_emails_bulk(
        [d.id for d in drafts],
        gmail_credentials=GMAIL_CREDS,
        quota_tracker=quota_tracker
    )

    sent = [r for r in results if r.status == SendStatus.SENT]
    quota_exceeded = [r for r in results if r.status == SendStatus.QUOTA_EXCEEDED]

    assert len(sent) == 100
    assert len(quota_exceeded) == 50

    # Check remaining quota
    assert quota_tracker.get_remaining_quota() == 0
```

#### Test 2.12.8: Reset Quota at Midnight
```python
def test_reset_quota_at_midnight():
    """
    Gmail quota should reset at midnight UTC.
    """
    quota_tracker = GmailQuotaTracker()

    # Use 50 quota
    for i in range(50):
        quota_tracker.increment()

    assert quota_tracker.get_used_quota() == 50

    # Simulate midnight reset
    quota_tracker.check_and_reset(current_time=datetime(2025, 11, 12, 0, 0, 1))

    assert quota_tracker.get_used_quota() == 0
    assert quota_tracker.get_remaining_quota() == quota_tracker.daily_limit
```

#### Test 2.12.9: Global Contact Deduplication
```python
def test_global_contact_deduplication():
    """
    Detect duplicates across all campaigns and imports.
    """
    # First campaign
    contact1 = Contact(name="Alice Smith", email="alice@example.com")
    db.save(contact1)

    # Second campaign (different user, same email)
    csv2 = """
    name,email,industry
    Alice S.,alice@example.com,Tech
    """

    result = import_contacts(csv2, user_id=2)

    # Should detect duplicate
    assert len(result.contacts) == 0
    assert len(result.duplicates) == 1
    assert "alice@example.com" in result.duplicates[0].email
    assert "already exists" in result.duplicates[0].reason.lower()
```

#### Test 2.12.10: Merge Duplicate Contacts
```python
def test_merge_duplicate_contacts():
    """
    Allow user to merge duplicate contact records.
    """
    contact1 = Contact(id=1, name="Alice", email="alice@example.com", industry="Tech")
    contact2 = Contact(id=2, name="Alice Smith", email="alice@example.com", company="TechCorp")

    db.save(contact1)
    db.save(contact2)

    # Merge contact2 into contact1
    merged = merge_contacts(primary_id=1, duplicate_id=2)

    # Should combine data
    assert merged.name == "Alice Smith"  # More complete name
    assert merged.industry == "Tech"
    assert merged.company == "TechCorp"

    # Duplicate should be soft-deleted
    assert db.get_contact(2) is None

    # History should point to merged contact
    drafts = db.get_drafts_for_contact(2)
    for draft in drafts:
        assert draft.contact_id == 1
```

#### Test 2.12.11: Cancel Pending Sends
```python
def test_cancel_pending_sends():
    """
    User can cancel approved drafts before they're sent.
    """
    drafts = [EmailDraft(contact_id=i, status=DraftStatus.APPROVED) for i in range(10)]
    for d in drafts:
        db.save(d)

    # User realizes mistake, cancels
    cancel_drafts([d.id for d in drafts[:5]], user_id=1)

    # Canceled drafts should revert to pending
    for i in range(5):
        updated = db.get_draft(drafts[i].id)
        assert updated.status == DraftStatus.PENDING_APPROVAL
        assert updated.cancel_reason == "Canceled by user"

    # Non-canceled should remain approved
    for i in range(5, 10):
        assert db.get_draft(drafts[i].id).status == DraftStatus.APPROVED
```

#### Test 2.12.12: Cannot Cancel Already Sent
```python
def test_cannot_cancel_already_sent():
    """
    Cannot cancel drafts that have already been sent.
    """
    draft = EmailDraft(contact_id=1, status=DraftStatus.SENT)
    db.save(draft)

    with pytest.raises(InvalidStateTransition):
        cancel_drafts([draft.id], user_id=1)
```

#### Test 2.12.13: Undo Bulk Approval
```python
def test_undo_bulk_approval():
    """
    Undo accidental bulk approval within 5 minute window.
    """
    drafts = [EmailDraft(contact_id=i) for i in range(50)]
    for d in drafts:
        db.save(d)

    # User accidentally approves all
    approval_result = approve_drafts_bulk([d.id for d in drafts], user_id=1)

    # Immediately undo (within 5 minutes)
    undo_result = undo_approval(approval_result.batch_id, user_id=1)

    assert undo_result.undone_count == 50

    # All should be back to pending
    for draft in drafts:
        updated = db.get_draft(draft.id)
        assert updated.status == DraftStatus.PENDING_APPROVAL
```

#### Test 2.12.14: Export All Contact Data
```python
def test_export_all_contact_data():
    """
    User can export all contacts and history to CSV.
    """
    contacts = [
        Contact(name="Alice", email="alice@example.com", status=ContactStatus.EMAIL_SENT),
        Contact(name="Bob", email="bob@example.com", status=ContactStatus.ENRICHED)
    ]
    for c in contacts:
        db.save(c)

    export_csv = export_contacts_to_csv(user_id=1)

    # Should include all data
    assert "Alice" in export_csv
    assert "alice@example.com" in export_csv
    assert "EMAIL_SENT" in export_csv

    # Should be valid CSV
    parsed = parse_csv(export_csv)
    assert len(parsed) == 2
```

#### Test 2.12.15: Export Campaign History
```python
def test_export_campaign_history():
    """
    Export all emails sent, replies, and outcomes.
    """
    # Create campaign with sent emails and replies
    draft1 = EmailDraft(contact_id=1, status=DraftStatus.SENT, sent_at=datetime.now())
    db.save(draft1)

    reply1 = Reply(draft_id=draft1.id, intent=ReplyIntent.INTERESTED)
    db.save(reply1)

    export_csv = export_campaign_history(user_id=1)

    # Should include sends and replies
    assert "SENT" in export_csv
    assert "INTERESTED" in export_csv

    # Should have timestamps
    assert str(datetime.now().date()) in export_csv
```

#### Test 2.12.16: Delete All User Data (GDPR)
```python
def test_delete_all_user_data():
    """
    User can permanently delete all their data (GDPR right to erasure).
    """
    user_id = 1

    # Create user data
    contacts = [Contact(name=f"User{i}", user_id=user_id) for i in range(10)]
    for c in contacts:
        db.save(c)

    # Delete everything
    deletion_result = delete_user_data(user_id=user_id, confirm=True)

    assert deletion_result.contacts_deleted == 10
    assert deletion_result.drafts_deleted >= 0

    # Verify deletion
    remaining_contacts = db.get_contacts_by_user(user_id)
    assert len(remaining_contacts) == 0
```

---

### 2.13 Production Readiness - Tier 2 (Should-Have)

#### Test 2.13.1: Check Email Spam Score
```python
def test_check_email_spam_score():
    """
    Analyze draft for spam triggers before sending.
    """
    spammy_draft = EmailDraft(
        contact_id=1,
        subject="URGENT!!! FREE MONEY $$$",
        body="Click here NOW!!! Limited time offer!!!"
    )

    spam_score = check_spam_score(spammy_draft)

    assert spam_score.score > 5.0  # High spam score (out of 10)
    assert "excessive caps" in spam_score.warnings
    assert "excessive punctuation" in spam_score.warnings
    assert spam_score.recommendation == "REVISE_DRAFT"
```

#### Test 2.13.2: Prevent Sending High Spam Score Emails
```python
def test_prevent_sending_high_spam_score():
    """
    Block sending emails with spam score > threshold.
    """
    config = Config(max_spam_score=5.0)

    spammy_draft = EmailDraft(
        contact_id=1,
        subject="BUY NOW!!!",
        body="FREE MONEY",
        status=DraftStatus.APPROVED
    )
    db.save(spammy_draft)

    with pytest.raises(SpamScoreExceededError):
        send_email(spammy_draft.id, config=config)
```

#### Test 2.13.3: Spam Score Suggestions
```python
def test_spam_score_suggestions():
    """
    Provide specific suggestions to improve spam score.
    """
    draft = EmailDraft(
        subject="Re: URGENT!!!",
        body="CLICK HERE for FREE offer!!!"
    )

    analysis = analyze_spam_factors(draft)

    assert len(analysis.suggestions) > 0
    assert any("reduce caps" in s.lower() for s in analysis.suggestions)
    assert any("punctuation" in s.lower() for s in analysis.suggestions)

    # Should suggest improvements
    assert analysis.improved_subject is not None
    assert "URGENT!!!" not in analysis.improved_subject
```

#### Test 2.13.4: Schedule Sends for Business Hours
```python
def test_schedule_sends_for_business_hours():
    """
    Don't send emails outside recipient's business hours.
    """
    contact = Contact(
        id=1,
        email="alice@example.com",
        timezone="America/New_York"
    )
    db.save(contact)

    draft = EmailDraft(contact_id=1, status=DraftStatus.APPROVED)
    db.save(draft)

    # Try to send at 11pm recipient time
    current_time = datetime(2025, 11, 15, 23, 0)  # 11pm

    result = send_email(
        draft.id,
        current_time=current_time,
        respect_business_hours=True
    )

    # Should schedule for next business day
    assert result.status == SendStatus.SCHEDULED
    assert result.scheduled_time.hour >= 9  # 9am or later
    assert result.scheduled_time.hour <= 17  # 5pm or earlier
```

#### Test 2.13.5: Respect Weekend Preferences
```python
def test_respect_weekend_preferences():
    """
    Skip weekends if configured.
    """
    config = Config(skip_weekends=True)

    draft = EmailDraft(contact_id=1, status=DraftStatus.APPROVED)
    db.save(draft)

    # Try to send on Saturday
    saturday = datetime(2025, 11, 15, 10, 0)  # Saturday 10am

    result = send_email(
        draft.id,
        current_time=saturday,
        config=config
    )

    # Should schedule for Monday
    assert result.status == SendStatus.SCHEDULED
    assert result.scheduled_time.weekday() == 0  # Monday
```

#### Test 2.13.6: Optimize Send Time by Industry
```python
def test_optimize_send_time_by_industry():
    """
    Send at optimal times based on recipient industry data.
    """
    contact = Contact(
        id=1,
        email="ceo@startup.com",
        industry="Technology",
        timezone="America/Los_Angeles"
    )

    optimal_time = calculate_optimal_send_time(contact)

    # Tech industry: early morning or late afternoon
    assert optimal_time.hour in [7, 8, 9, 16, 17, 18]

    # Healthcare might differ
    contact.industry = "Healthcare"
    optimal_time_healthcare = calculate_optimal_send_time(contact)

    # Should be different from tech
    assert optimal_time != optimal_time_healthcare
```

#### Test 2.13.7: Alert on High Failure Rate
```python
def test_alert_on_high_failure_rate():
    """
    Send alert if enrichment/send failure rate exceeds threshold.
    """
    alert_service = AlertService(failure_threshold=0.10)  # 10%

    # Simulate 50 enrichments, 8 failures (16% failure rate)
    contacts = [Contact(name=f"User{i}") for i in range(50)]

    with mock_openai_partial_failure(fail_indices=list(range(8))):
        result = enrich_contacts_batch(
            contacts,
            api_key=OPENAI_KEY,
            alert_service=alert_service
        )

    # Should trigger alert
    alerts = alert_service.get_sent_alerts()
    assert len(alerts) >= 1
    assert "high failure rate" in alerts[0].message.lower()
    assert "16%" in alerts[0].message
```

#### Test 2.13.8: Daily Summary Email
```python
def test_daily_summary_email():
    """
    Send daily summary of campaign activity.
    """
    user = User(id=1, email="user@example.com")

    # Simulate day's activity
    summary = generate_daily_summary(user_id=1, date=datetime.now().date())

    assert summary.emails_sent >= 0
    assert summary.replies_received >= 0
    assert summary.interested_count >= 0
    assert summary.declined_count >= 0
    assert summary.api_costs > 0

    # Email should be generated
    summary_email = format_summary_email(summary)
    assert "Emails sent:" in summary_email
    assert "Replies:" in summary_email
    assert "Cost:" in summary_email
```

#### Test 2.13.9: Real-time Failure Notifications
```python
def test_realtime_failure_notifications():
    """
    Notify user immediately of critical failures.
    """
    notification_service = NotificationService(user_email="user@example.com")

    # Simulate critical failure (all enrichments fail)
    contacts = [Contact(name=f"User{i}") for i in range(10)]

    with mock_openai_complete_failure():
        result = enrich_contacts_batch(
            contacts,
            api_key=OPENAI_KEY,
            notification_service=notification_service
        )

    # Should send immediate notification
    notifications = notification_service.get_sent_notifications()
    assert len(notifications) >= 1
    assert notifications[0].priority == "HIGH"
    assert "enrichment failed" in notifications[0].message.lower()
```

#### Test 2.13.10: Parse HTML Email Replies
```python
def test_parse_html_email_replies():
    """
    Extract text content from HTML emails.
    """
    html_reply = Reply(
        draft_id=1,
        body="""
        <html>
        <body>
            <p>Thanks for reaching out!</p>
            <p>I'd love to <b>learn more</b>.</p>
            <div>-- <br>Alice Smith</div>
        </body>
        </html>
        """
    )

    parsed = parse_reply_body(html_reply)

    # Should extract plain text
    assert "Thanks for reaching out!" in parsed.plain_text
    assert "learn more" in parsed.plain_text
    assert "<html>" not in parsed.plain_text
    assert "<p>" not in parsed.plain_text
```

#### Test 2.13.11: Handle Inline Images in Replies
```python
def test_handle_inline_images_in_replies():
    """
    Strip inline images, preserve text content.
    """
    reply = Reply(
        draft_id=1,
        body="""
        <html>
        <body>
            <p>See attached screenshot:</p>
            <img src="cid:image001.png@01DB1234">
            <p>Does this help?</p>
        </body>
        </html>
        """,
        has_inline_images=True
    )

    parsed = parse_reply_body(reply)

    # Should preserve text, note image
    assert "See attached screenshot" in parsed.plain_text
    assert "Does this help" in parsed.plain_text
    assert "[Image]" in parsed.plain_text or parsed.has_attachments
```

#### Test 2.13.12: Reply Threading with CC Recipients
```python
def test_reply_threading_with_cc():
    """
    Handle replies where recipient CCs their team.
    """
    sent_draft = EmailDraft(
        contact_id=1,
        to_email="alice@example.com",
        thread_id="thread123"
    )
    db.save(sent_draft)

    # Alice replies and CCs her team
    with mock_gmail_api() as gmail:
        gmail.add_reply(
            thread_id="thread123",
            from_email="alice@example.com",
            cc=["bob@example.com", "charlie@example.com"],
            body="Let me loop in my team."
        )

        check_replies(gmail_credentials=GMAIL_CREDS)

    reply = db.get_reply_for_draft(sent_draft.id)

    # Should track CC recipients
    assert reply is not None
    assert "bob@example.com" in reply.cc_recipients
    assert "charlie@example.com" in reply.cc_recipients
```

#### Test 2.13.13: Detect GPT Hallucinations in Enrichment
```python
def test_detect_enrichment_hallucinations():
    """
    Flag suspiciously generic or potentially fake enrichment data.
    """
    contact = Contact(
        name="John Smith",
        email="john@unknowndomain123.com",
        industry="Tech"
    )

    # Mock GPT returning generic data
    with mock_openai_response({
        "title": "Manager",
        "company": "Tech Company",
        "painpoint": "Looking for solutions",
        "relevance_score": 5
    }):
        enriched = enrich_contact(contact, api_key=OPENAI_KEY)

    validation = validate_enrichment_quality(enriched)

    # Should flag generic responses
    assert validation.quality_score < 0.5
    assert "generic" in validation.warnings
    assert validation.likely_hallucination == True
```

#### Test 2.13.14: Track Draft Quality Over Time
```python
def test_track_draft_quality_over_time():
    """
    Monitor draft quality metrics to detect regression.
    """
    quality_tracker = DraftQualityTracker()

    # Generate 100 drafts
    for i in range(100):
        contact = Contact(name=f"User{i}")
        draft = generate_email_draft(contact, template, api_key=OPENAI_KEY)

        quality_score = quality_tracker.score_draft(draft)
        quality_tracker.record_score(quality_score)

    metrics = quality_tracker.get_metrics()

    assert metrics.average_score >= 0
    assert metrics.average_score <= 10

    # Alert if quality drops
    if metrics.trend == "DECLINING":
        assert metrics.alert_triggered == True
```

#### Test 2.13.15: Validate Enrichment Against Public Data
```python
def test_validate_enrichment_against_public_data():
    """
    Cross-check enrichment against LinkedIn, company websites.
    """
    contact = Contact(
        name="Satya Nadella",
        email="satya@microsoft.com"
    )

    enriched = enrich_contact(contact, api_key=OPENAI_KEY)

    # Validate against known data
    validation = validate_enrichment_with_external_sources(enriched)

    # Should match public info
    assert validation.company_verified == True
    assert validation.title_verified == True
    assert validation.confidence_score >= 0.9
```

---

## 3. Coverage Summary

### 3.1 What IS Tested

✅ **Core Functionality**
- CSV import with validation
- AI enrichment with GPT-4 Turbo
- Embedding generation and clustering
- Email draft generation and personalization
- Human approval workflow
- Email sending via Gmail API
- Reply detection and intent classification
- Automated follow-up generation
- Meeting time suggestions
- State persistence and transitions

✅ **Edge Cases**
- Missing/malformed CSV fields
- API failures (timeout, rate limit, invalid response)
- Empty/single-item collections
- Duplicate detection
- Concurrent access
- Special characters and Unicode
- Multiple follow-ups
- Multi-message threads

✅ **Error Handling**
- Retry logic for API failures
- Graceful degradation
- Transaction rollback
- Validation errors
- State transition constraints

✅ **Non-functional Requirements**
- Rate limiting
- Performance with large datasets
- Audit logging
- Multi-user isolation

✅ **Production Readiness - Tier 1 (Must-Have)**
- OpenAI API cost tracking and budget limits
- Daily budget enforcement with auto-stop
- Cost estimation before operations
- Unsubscribe link in all emails (CAN-SPAM)
- Unsubscribe request processing
- Gmail daily send quota enforcement
- Quota reset at midnight
- Global contact deduplication across campaigns
- Contact merging for duplicates
- Cancel pending sends before execution
- Undo bulk approval within time window
- Export contacts and campaign history
- GDPR data deletion (right to erasure)

✅ **Production Readiness - Tier 2 (Should-Have)**
- Email spam score checking
- Block sending high spam score emails
- Spam score improvement suggestions
- Schedule sends for business hours
- Skip weekends if configured
- Optimize send time by industry
- Alert on high failure rates
- Daily summary email reports
- Real-time critical failure notifications
- Parse HTML email replies
- Handle inline images in replies
- Track CC recipients in threads
- Detect GPT hallucinations in enrichment
- Track draft quality over time
- Validate enrichment against public data

### 3.2 What is NOT Tested (and Why)

❌ **Security & Authentication**
- OAuth2 flow for Gmail API (requires browser interaction)
- API key rotation and management (infrastructure concern)
- XSS/injection attacks in email content (handled by email libraries)
- Encryption at rest for sensitive data
- Two-factor authentication for user accounts

**Rationale**: These require infrastructure setup, external systems, or security frameworks beyond unit/integration tests. Security audits should be conducted separately.

❌ **UI/UX Testing**
- Streamlit/React component rendering
- User interaction flows (click paths, form validation)
- Responsive design across devices
- Accessibility (WCAG compliance)
- Browser compatibility

**Rationale**: Frontend tests require Selenium/Cypress and are typically separate from backend API tests. UI testing frameworks handle these concerns.

❌ **Advanced AI Quality (Requires Human Evaluation)**
- Semantic coherence of GPT outputs across diverse industries
- Bias detection in enrichment (gender, race, nationality)
- Prompt injection attacks
- Adversarial input handling
- Cultural sensitivity in email drafting

**Rationale**: While we test for hallucinations and basic quality, comprehensive AI safety requires ongoing human evaluation, red-teaming, and evolving test sets.

❌ **Third-party Service Failures**
- OpenAI complete service outage lasting hours/days
- Gmail API deprecation or breaking changes
- Embedding model version changes affecting results
- DNS failures, network partitions

**Rationale**: We mock these services; real-world service failures require monitoring, alerting, and incident response procedures, not unit tests.

❌ **Extreme Scale**
- 1M+ contacts in single campaign
- Multi-region deployment and data replication
- Database replication lag and consistency
- Horizontal scaling and load balancing
- CDN and edge caching

**Rationale**: Performance at extreme scale requires load testing infrastructure (e.g., Locust, K6), production-like environments, and distributed systems expertise.

❌ **Email Infrastructure & Deliverability**
- Email deliverability rates and inbox placement
- SPF/DKIM/DMARC configuration
- IP reputation management
- Bounce handling and categorization (hard vs soft)
- Feedback loop processing (complaint handling)
- List-Unsubscribe header support

**Rationale**: Email deliverability requires integration with email infrastructure, ISP feedback loops, and third-party monitoring tools (SendGrid, Postmark, etc.).

❌ **Real-world Network Conditions**
- Slow network connections (3G, satellite)
- Packet loss and latency spikes
- Intermittent connectivity
- Proxy and firewall traversal

**Rationale**: Network condition testing requires specialized tools and environments. Application should use standard retry/timeout patterns.

### 3.3 Testing Strategy Recommendations

1. **Unit Tests**: 60-70% of tests above (pure logic, no external APIs)
2. **Integration Tests**: 20-30% (with mocked OpenAI/Gmail)
3. **E2E Tests**: 5-10% (full pipeline with real services in staging)
4. **Manual QA**: AI output quality, email tone, UX flows
5. **Monitoring**: Track real-world API failure rates, email reply rates, classification accuracy

### 3.4 Test Data Requirements

- **Mock CSV Files**: Small (10 rows), medium (1000 rows), large (10k rows)
- **Mock API Responses**: Valid, invalid, timeout, rate-limited
- **Mock Email Replies**: All intent types with variations
- **Test Email Accounts**: For Gmail API integration tests
- **Sample Availability Slots**: For meeting scheduling tests

---

## 4. Implementation Notes

### 4.1 Test Fixtures
```python
@pytest.fixture
def db():
    """In-memory SQLite database for tests."""
    db = Database(":memory:")
    db.migrate()
    yield db
    db.close()

@pytest.fixture
def mock_openai():
    """Mock OpenAI API responses."""
    with patch('openai.ChatCompletion.create') as mock:
        mock.return_value = {
            "choices": [{"message": {"content": '{"title": "Engineer", ...}'}}]
        }
        yield mock

@pytest.fixture
def mock_gmail():
    """Mock Gmail API client."""
    return MockGmailAPI()
```

### 4.2 Test Execution
```bash
# Run all tests
pytest tests/ -v

# Run specific category
pytest tests/test_enrichment.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run only fast tests (exclude slow/integration)
pytest tests/ -m "not slow"

# Run E2E tests
pytest tests/test_e2e.py -v --e2e
```

### 4.3 CI/CD Integration
- Run unit tests on every commit
- Run integration tests on every PR
- Run E2E tests nightly in staging environment
- Track test coverage (target: >80%)
- Fail build if critical tests fail

---

**End of Test Plan**

## Test Plan Summary

This enhanced test plan provides **production-ready** coverage of the AI-driven outreach engine with **131 comprehensive test cases** across 13 major categories:

### Test Count Breakdown:
- **Core Functionality** (65 tests): Data ingestion, enrichment, clustering, drafting, approval, sending, replies, follow-ups, meetings, persistence, E2E
- **Production Readiness - Tier 1** (16 tests): Cost control, compliance, quota management, deduplication, undo operations, data export
- **Production Readiness - Tier 2** (15 tests): Spam prevention, scheduling, monitoring, HTML parsing, quality validation

### Key Production Features Covered:
✅ **Cost Protection**: Budget limits, cost tracking, pre-operation estimates
✅ **Legal Compliance**: CAN-SPAM unsubscribe, GDPR data deletion
✅ **Operational Safety**: Quota enforcement, cancel/undo operations, failure alerts
✅ **Quality Assurance**: Spam score checking, hallucination detection, quality tracking
✅ **User Experience**: Business hours scheduling, daily summaries, HTML email handling

### Implementation Confidence:
A system that passes all 131 tests will be:
- ✅ **Safe to use** (won't blow through budget or violate regulations)
- ✅ **Recoverable** (can undo mistakes, cancel sends, export data)
- ✅ **Observable** (alerts, summaries, cost tracking)
- ✅ **Professional** (spam prevention, business hours, quality checks)
- ✅ **Production-ready** for real-world usage

Each test defines expected behavior clearly enough that code can be written to pass the tests. Implementing code that satisfies these tests will result in a robust, production-ready system suitable for actual outreach campaigns.

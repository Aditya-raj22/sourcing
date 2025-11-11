Purpose: Build an AI-driven outreach engine

Design Philosophy:

Lightweight. Build smart, using minimal lines of efficient code.Startup-style minimal viable product — no over-engineering, no unnecessary abstractions.

Human-in-the-loop. AI automates the drudgework (enrichment, clustering, draft emails, follow-ups) but user always approves sends.

Transparent. Every step (enrichment, scoring, draft) should be viewable and editable by the user.

Test-driven. Build exhaustive tests first; implementation must satisfy them exactly.

Fast iteration. Simple to run locally, minimal dependencies, modular structure.

Core Workflow:

Upload CSV (name, email, industry).

AI enrichment with GPT-4 Turbo → title, company, painpoint summary, relevance score.

Semantic clustering (text-embedding-3-large + HDBSCAN).

User selects cluster → picks people → AI drafts personalized emails from template.

User reviews → approve → send via Gmail API.

AI monitors replies, classifies intent, proposes follow-ups after 7 days.

For interested leads, drafts scheduling replies using provided availability slots.

Stack:

Backend: Python (Flask or FastAPI)

Frontend: Streamlit (minimal UI)

AI: OpenAI API (GPT-4 Turbo, text-embedding-3-large)

Database: SQLite / Firestore

Email: Gmail API (will provide for tests)

Scheduler: APScheduler or cron

Environment: .env for API keys, email credentials

Tone / Style for Claude Code:

Concise, readable, and modular code — no generic boilerplate.

Use docstrings to explain intent, not just function signatures.

Use clear naming: enrich_contact(), cluster_contacts(), draft_email(), parse_reply(), etc.

When uncertain, bias toward explicitness and testability.

Prefer readable data models over heavy frameworks.

All logs and errors should be human-interpretable (friendly for a student founder debugging).

Deliverables Expected:

Full test suite covering all modules.

Passing implementation code.

Local setup guide.
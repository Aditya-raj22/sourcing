#!/usr/bin/env python3
"""
Test SMTP email sending with Duke email.
Make sure server is running (python main.py) before running this.
"""

import requests
import json
import sys

BASE = "http://localhost:8000"

def test_smtp_duke_email():
    """Test full workflow with Duke SMTP email."""

    print("🧪 Testing Duke Email via SMTP\n")

    # Check server
    try:
        r = requests.get(f"{BASE}/health", timeout=2)
        print(f"✅ Server is running: {r.json()}")
    except:
        print("❌ Server not running! Start it with: python main.py")
        sys.exit(1)

    print()

    # 1. Create a test contact
    print("1️⃣  Creating test contact...")
    r = requests.post(f"{BASE}/api/contacts/", json={
        "name": "Test Recipient",
        "email": "your.email@example.com",  # ⚠️ Change this to your test email!
        "company": "TestCo",
        "industry": "Technology"
    })

    if r.status_code == 200:
        contact = r.json()
        contact_id = contact['id']
        print(f"   ✅ Contact created: {contact['name']} (ID: {contact_id})")
    else:
        print(f"   ❌ Failed to create contact: {r.status_code}")
        print(f"   {r.text}")
        return

    print()

    # 2. Create email draft
    print("2️⃣  Creating email draft...")
    r = requests.post(f"{BASE}/api/drafts/", json={
        "contact_id": contact_id,
        "subject": "Test from Duke Outreach Engine",
        "body": """Hi Test Recipient,

This is a test email from the AI-driven outreach engine at Duke.

The system is now working with Duke email via SMTP!

Best regards,
Aditya
Duke University

---
To unsubscribe: (link will be auto-added)"""
    })

    if r.status_code == 200:
        draft = r.json()
        draft_id = draft['id']
        print(f"   ✅ Draft created: ID {draft_id}")
        print(f"   Subject: {draft['subject']}")
    else:
        print(f"   ❌ Failed to create draft: {r.status_code}")
        print(f"   {r.text}")
        return

    print()

    # 3. Check spam score
    print("3️⃣  Checking spam score...")
    r = requests.get(f"{BASE}/api/drafts/{draft_id}/spam-score")

    if r.status_code == 200:
        spam = r.json()
        print(f"   ✅ Spam score: {spam['score']}/10")
        print(f"   Recommendation: {spam['recommendation']}")
    else:
        print(f"   ⚠️  Could not check spam score")

    print()

    # 4. Approve draft
    print("4️⃣  Approving draft...")
    r = requests.post(f"{BASE}/api/drafts/{draft_id}/approve",
                     json={"notes": "Test send via Duke SMTP"})

    if r.status_code == 200:
        print(f"   ✅ Draft approved!")
    else:
        print(f"   ❌ Failed to approve: {r.status_code}")
        return

    print()

    # 5. Send email
    print("5️⃣  Sending email via Duke SMTP...")
    print("   ⚠️  MOCK MODE: Set to True for testing without actually sending")

    # ⚠️ Change mock_mode to False to actually send!
    mock_mode = True  # Set False to send real email

    r = requests.post(f"{BASE}/api/drafts/{draft_id}/send",
                     json={"mock_mode": mock_mode})

    if r.status_code == 200:
        result = r.json()
        print(f"   ✅ Email {'sent' if not mock_mode else 'mock sent'}!")
        print(f"   Status: {result['status']}")
        print(f"   Message ID: {result['message_id']}")

        if mock_mode:
            print()
            print("   💡 To send a real email:")
            print("      1. Change recipient email above to a real address")
            print("      2. Set mock_mode = False in this script")
            print("      3. Ensure SMTP credentials are in .env")
            print("      4. Run again!")
    else:
        print(f"   ❌ Failed to send: {r.status_code}")
        print(f"   {r.text}")

    print()
    print("✅ Duke SMTP Test Complete!")
    print()
    print("📧 Your Duke email (a.raj@duke.edu) is ready to send outreach emails!")

if __name__ == "__main__":
    test_smtp_duke_email()

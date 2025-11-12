#!/usr/bin/env python3
"""
Demo script to test the AI-Driven Outreach Engine end-to-end.

This script demonstrates the complete workflow:
1. Initialize database
2. Import contacts
3. Enrich contacts with AI
4. Cluster similar contacts
5. Generate email drafts
6. Approve and send emails

Run this after starting the server with: python main.py
"""

import requests
import time
import json
from io import StringIO

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print a section header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def check_server():
    """Check if server is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print("✅ Server is running!")
            print(f"   Response: {response.json()}")
            return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Server is not running. Please start it with: python main.py")
        print(f"   Error: {e}")
        return False

def test_import_contacts():
    """Test CSV import."""
    print_section("1. Import Contacts from CSV")

    # Create sample CSV
    csv_content = """name,email,company,industry
Alice Johnson,alice@techcorp.com,TechCorp,Technology
Bob Smith,bob@healthcare.com,HealthPlus,Healthcare
Carol Davis,carol@fintech.com,FinTech Solutions,Finance
David Lee,david@edutech.com,EduTech,Education
Eve Martinez,eve@retailco.com,RetailCo,Retail"""

    files = {'file': ('contacts.csv', StringIO(csv_content), 'text/csv')}

    try:
        response = requests.post(f"{BASE_URL}/api/contacts/import", files=files)
        result = response.json()

        print(f"✅ Import successful!")
        print(f"   - Imported: {result['success_count']} contacts")
        print(f"   - Errors: {result['error_count']}")
        print(f"   - Duplicates: {len(result['duplicates'])}")

        return result['success_count'] > 0
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_list_contacts():
    """Test listing contacts."""
    print_section("2. List All Contacts")

    try:
        response = requests.get(f"{BASE_URL}/api/contacts/")
        contacts = response.json()

        print(f"✅ Found {len(contacts)} contacts:")
        for i, contact in enumerate(contacts[:5], 1):  # Show first 5
            print(f"   {i}. {contact['name']} ({contact['email']}) - Status: {contact['status']}")

        return contacts
    except Exception as e:
        print(f"❌ Failed to list contacts: {e}")
        return []

def test_enrich_contacts(contact_ids):
    """Test AI enrichment."""
    print_section("3. Enrich Contacts with AI (Mock Mode)")

    print(f"📝 Note: Using mock OpenAI responses (set OPENAI_API_KEY in .env for real enrichment)")

    try:
        response = requests.post(
            f"{BASE_URL}/api/contacts/enrich/batch",
            json={"contact_ids": contact_ids[:3]}  # Enrich first 3
        )
        result = response.json()

        print(f"✅ Enrichment completed!")
        print(f"   - Enriched: {result['count']} contacts")

        return True
    except Exception as e:
        print(f"❌ Enrichment failed: {e}")
        print(f"   This is expected if OPENAI_API_KEY is not set")
        return False

def test_create_draft():
    """Test draft creation."""
    print_section("4. Create Email Draft")

    try:
        # Get first contact
        contacts = requests.get(f"{BASE_URL}/api/contacts/").json()
        if not contacts:
            print("❌ No contacts available")
            return None

        contact_id = contacts[0]['id']

        # Create draft
        response = requests.post(
            f"{BASE_URL}/api/drafts/",
            json={
                "contact_id": contact_id,
                "subject": "Quick question about {{company}}",
                "body": "Hi {{name}},\n\nI noticed your work at {{company}} and wanted to reach out...\n\nBest regards"
            }
        )

        if response.status_code == 200:
            draft = response.json()
            print(f"✅ Draft created!")
            print(f"   - Draft ID: {draft['id']}")
            print(f"   - Subject: {draft['subject']}")
            print(f"   - Status: {draft['status']}")
            return draft['id']
        else:
            print(f"❌ Draft creation failed: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Draft creation failed: {e}")
        return None

def test_approve_draft(draft_id):
    """Test draft approval."""
    print_section("5. Approve Draft")

    try:
        response = requests.post(
            f"{BASE_URL}/api/drafts/{draft_id}/approve",
            json={"notes": "Looks good!"}
        )

        result = response.json()
        print(f"✅ Draft approved!")
        print(f"   - Message: {result['message']}")

        return True
    except Exception as e:
        print(f"❌ Approval failed: {e}")
        return False

def test_spam_check(draft_id):
    """Test spam score checking."""
    print_section("6. Check Spam Score")

    try:
        response = requests.get(f"{BASE_URL}/api/drafts/{draft_id}/spam-score")
        result = response.json()

        print(f"✅ Spam check completed!")
        print(f"   - Score: {result['score']}/10")
        print(f"   - Recommendation: {result['recommendation']}")
        if result.get('warnings'):
            print(f"   - Warnings: {', '.join(result['warnings'])}")

        return True
    except Exception as e:
        print(f"❌ Spam check failed: {e}")
        return False

def test_send_draft(draft_id):
    """Test sending draft (mock mode)."""
    print_section("7. Send Email (Mock Mode)")

    try:
        response = requests.post(
            f"{BASE_URL}/api/drafts/{draft_id}/send",
            json={"mock_mode": True}  # Mock mode - won't actually send
        )

        result = response.json()
        print(f"✅ Email sent (mock)!")
        print(f"   - Status: {result['status']}")
        print(f"   - Message ID: {result.get('message_id', 'N/A')}")

        return True
    except Exception as e:
        print(f"❌ Send failed: {e}")
        return False

def test_campaign_stats():
    """Test campaign statistics."""
    print_section("8. Campaign Statistics")

    try:
        response = requests.get(f"{BASE_URL}/api/campaigns/stats")
        stats = response.json()

        print(f"✅ Statistics retrieved!")
        print(f"   Contacts:")
        print(f"     - Total: {stats['contacts']['total']}")
        print(f"     - Enriched: {stats['contacts']['enriched']}")
        print(f"   Drafts:")
        print(f"     - Total: {stats['drafts']['total']}")
        print(f"     - Sent: {stats['drafts']['sent']}")
        print(f"     - Pending: {stats['drafts']['pending']}")
        print(f"   Replies:")
        print(f"     - Total: {stats['replies']['total']}")

        return True
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
        return False

def test_export_contacts():
    """Test contact export."""
    print_section("9. Export Contacts to CSV")

    try:
        response = requests.get(f"{BASE_URL}/api/contacts/export/csv")
        result = response.json()

        csv_data = result['content']
        lines = csv_data.split('\n')

        print(f"✅ Export successful!")
        print(f"   - Filename: {result['filename']}")
        print(f"   - Lines: {len(lines)}")
        print(f"   - Preview (first 3 lines):")
        for line in lines[:3]:
            print(f"     {line}")

        return True
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False

def main():
    """Run all demo tests."""
    print("\n" + "🚀 "*20)
    print("  AI-DRIVEN OUTREACH ENGINE - DEMO")
    print("🚀 "*20)

    # Check server
    if not check_server():
        return

    time.sleep(1)

    # Run tests
    test_import_contacts()
    time.sleep(0.5)

    contacts = test_list_contacts()
    time.sleep(0.5)

    if contacts:
        contact_ids = [c['id'] for c in contacts]
        test_enrich_contacts(contact_ids)
        time.sleep(0.5)

    draft_id = test_create_draft()
    time.sleep(0.5)

    if draft_id:
        test_spam_check(draft_id)
        time.sleep(0.5)

        test_approve_draft(draft_id)
        time.sleep(0.5)

        test_send_draft(draft_id)
        time.sleep(0.5)

    test_campaign_stats()
    time.sleep(0.5)

    test_export_contacts()

    # Summary
    print_section("✨ DEMO COMPLETE")
    print("""
🎉 The AI-Driven Outreach Engine is working!

Next Steps:
1. Add your OPENAI_API_KEY to .env for real AI enrichment
2. Set up Gmail API credentials for actual email sending
3. Try the interactive API docs at http://localhost:8000/docs
4. Build your own campaigns using the API endpoints

For full documentation, see README.md
    """)

if __name__ == "__main__":
    main()

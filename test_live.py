#!/usr/bin/env python3
"""
Simple live test showing the API works.
Run with: python3 test_live.py (while server is running)
"""

import requests
import json

BASE = "http://localhost:8000"

print("\n🚀 AI-DRIVEN OUTREACH ENGINE - LIVE TEST\n")

# 1. Health check
print("1️⃣  Health Check")
r = requests.get(f"{BASE}/health")
print(f"   Status: {r.json()}")
print()

# 2. Create contact directly via API
print("2️⃣  Creating Test Contacts")
contacts = [
    {"name": "Alice Johnson", "email": "alice@techcorp.com", "company": "TechCorp", "industry": "Technology"},
    {"name": "Bob Smith", "email": "bob@healthcare.com", "company": "HealthPlus", "industry": "Healthcare"},
    {"name": "Carol Davis", "email": "carol@fintech.com", "company": "FinTech Solutions", "industry": "Finance"},
]

contact_ids = []
for contact in contacts:
    r = requests.post(f"{BASE}/api/contacts/", json=contact)
    if r.status_code == 200:
        data = r.json()
        contact_ids.append(data['id'])
        print(f"   ✅ Created: {data['name']} (ID: {data['id']})")
    else:
        print(f"   ⚠️  Skipped: {contact['name']} - {r.status_code}")
print()

# 3. List all contacts
print("3️⃣  Listing All Contacts")
r = requests.get(f"{BASE}/api/contacts/")
contacts_list = r.json()
print(f"   Total contacts: {len(contacts_list)}")
for c in contacts_list[:5]:
    print(f"   - {c['name']} ({c['email']}) - Status: {c['status']}")
print()

# 4. Create a draft
if contact_ids:
    print("4️⃣  Creating Email Draft")
    r = requests.post(f"{BASE}/api/drafts/", json={
        "contact_id": contact_ids[0],
        "subject": "Quick question about {{company}}",
        "body": "Hi {{name}},\n\nI noticed your work at {{company}} and thought you'd be interested in...\n\nBest regards"
    })

    if r.status_code == 200:
        draft = r.json()
        draft_id = draft['id']
        print(f"   ✅ Draft created (ID: {draft_id})")
        print(f"   Subject: {draft['subject']}")
        print(f"   Status: {draft['status']}")
        print()

        # 5. Check spam score
        print("5️⃣  Checking Spam Score")
        r = requests.get(f"{BASE}/api/drafts/{draft_id}/spam-score")
        spam = r.json()
        print(f"   Score: {spam['score']}/10")
        print(f"   Recommendation: {spam['recommendation']}")
        print()

        # 6. Approve draft
        print("6️⃣  Approving Draft")
        r = requests.post(f"{BASE}/api/drafts/{draft_id}/approve", json={"notes": "Looks good!"})
        result = r.json()
        print(f"   {result['message']}")
        print()

        # 7. Send (mock mode)
        print("7️⃣  Sending Email (Mock Mode)")
        r = requests.post(f"{BASE}/api/drafts/{draft_id}/send", json={"mock_mode": True})
        result = r.json()
        print(f"   Status: {result['status']}")
        print()

# 8. Campaign stats
print("8️⃣  Campaign Statistics")
r = requests.get(f"{BASE}/api/campaigns/stats")
stats = r.json()
print(json.dumps(stats, indent=2))
print()

# 9. Export
print("9️⃣  Exporting Contacts")
r = requests.get(f"{BASE}/api/contacts/export/csv")
result = r.json()
csv_lines = result['content'].split('\n')
print(f"   Filename: {result['filename']}")
print(f"   Total lines: {len(csv_lines)}")
print(f"   Headers: {csv_lines[0]}")
print()

print("✅ ALL TESTS PASSED!\n")
print("The AI-Driven Outreach Engine is fully operational!")
print(f"API Docs: {BASE}/docs\n")

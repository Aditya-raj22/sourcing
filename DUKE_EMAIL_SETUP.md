# Using Duke Email with the Outreach Engine

The system now supports **Duke email (a.raj@duke.edu)** via SMTP! No admin permissions or API setup required.

## 🚀 Quick Setup (2 minutes)

### Step 1: Update `.env` file

```bash
# Copy the example if you haven't already
cp .env.example .env
```

Edit `.env` and set these values:

```env
# Email Provider
EMAIL_PROVIDER=smtp

# Duke Email SMTP Settings
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=a.raj@duke.edu
SMTP_PASSWORD=your_duke_password
SMTP_USE_TLS=true

# Optional: Add your OpenAI API key
OPENAI_API_KEY=your_openai_key_here
```

### Step 2: Test it!

```bash
# Start the server
python main.py

# In another terminal, test sending
python test_smtp.py
```

## 📧 How It Works

**SMTP (Simple Mail Transfer Protocol)** is the standard email protocol. Duke's Microsoft 365 email supports it out of the box.

- ✅ **No API keys needed** (besides OpenAI for enrichment)
- ✅ **No admin permissions** required
- ✅ **Works immediately** with your Duke password
- ✅ **500+ emails/day** (typical Duke limit)
- ✅ **All features work** (drafts, approvals, scheduling, etc.)

## 🔒 Security Notes

### Option 1: Use your Duke password directly
```env
SMTP_PASSWORD=your_duke_password
```
⚠️ Keep `.env` secure and private!

### Option 2: Use App Password (Recommended)
If Duke requires 2FA (two-factor authentication):

1. Go to Microsoft account settings
2. Security → Advanced security options
3. Create "App password" for email
4. Use that instead of your real password

```env
SMTP_PASSWORD=your_app_password_here
```

## 🧪 Testing

Create `test_smtp.py`:

```python
#!/usr/bin/env python3
import requests

BASE = "http://localhost:8000"

# 1. Create a contact
print("Creating test contact...")
r = requests.post(f"{BASE}/api/contacts/", json={
    "name": "Test Recipient",
    "email": "test@example.com",  # Change to real email for testing
    "company": "TestCo"
})
contact = r.json()
print(f"✅ Contact created: ID {contact['id']}")

# 2. Create a draft
print("\nCreating email draft...")
r = requests.post(f"{BASE}/api/drafts/", json={
    "contact_id": contact['id'],
    "subject": "Test from Duke Outreach Engine",
    "body": "Hi,\n\nThis is a test email from the AI outreach engine.\n\nBest,\nAditya"
})
draft = r.json()
print(f"✅ Draft created: ID {draft['id']}")

# 3. Approve the draft
print("\nApproving draft...")
r = requests.post(f"{BASE}/api/drafts/{draft['id']}/approve",
                 json={"notes": "Test send"})
print(f"✅ Draft approved")

# 4. Send via SMTP
print("\nSending email via Duke SMTP...")
r = requests.post(f"{BASE}/api/drafts/{draft['id']}/send",
                 json={"mock_mode": False})  # Set True for testing without sending

result = r.json()
print(f"✅ Email sent! Status: {result['status']}")
print(f"   Message ID: {result['message_id']}")
```

Run it:
```bash
python test_smtp.py
```

## 🔥 Common Issues

### "Authentication failed"
- Check `SMTP_USER` is your full Duke email (a.raj@duke.edu)
- Check `SMTP_PASSWORD` is correct
- Try creating an App Password if you have 2FA

### "Connection refused"
- Check `SMTP_HOST=smtp.office365.com` (not smtp.duke.edu)
- Check `SMTP_PORT=587` (not 465 or 25)
- Ensure `SMTP_USE_TLS=true`

### "Email not sending"
- Check server logs: `tail -f logs/app.log`
- Try mock mode first: `{"mock_mode": True}`
- Verify Duke email is working (try sending from Outlook)

## 🎯 Full Workflow Example

```python
import requests

BASE = "http://localhost:8000"

# 1. Import contacts from CSV
with open('contacts.csv', 'rb') as f:
    r = requests.post(f"{BASE}/api/contacts/import", files={'file': f})
    print(f"Imported {r.json()['success_count']} contacts")

# 2. Generate drafts
r = requests.post(f"{BASE}/api/campaigns/drafts/bulk", json={
    "contact_ids": [1, 2, 3],
    "template_id": 1
})
draft_ids = r.json()["draft_ids"]

# 3. Approve all drafts
for draft_id in draft_ids:
    requests.post(f"{BASE}/api/drafts/{draft_id}/approve")

# 4. Send via Duke email (SMTP)
r = requests.post(f"{BASE}/api/drafts/send/bulk", json={
    "draft_ids": draft_ids
})
print(f"Sent {len(r.json()['results'])} emails via Duke SMTP!")
```

## 💡 Tips

**Daily Limits:**
- Duke typically allows 500 emails/day
- The system tracks this automatically
- Exceeding quota will queue emails for next day

**Testing:**
- Use `mock_mode: true` to test without actually sending
- Send to yourself first: change recipient to a.raj@duke.edu
- Check spam folder if test emails don't arrive

**Production:**
- Emails have unsubscribe links (CAN-SPAM compliant)
- Respects business hours (9AM-5PM recipient timezone)
- Checks spam scores before sending

## 📚 Switching Back to Gmail

If you want to use Gmail API instead:

```env
EMAIL_PROVIDER=gmail  # Change from smtp

# Add Gmail API credentials
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
```

## ✅ That's It!

You're now sending emails from your Duke account with zero API setup. Just username and password!

Questions? Check the main README.md or server logs.

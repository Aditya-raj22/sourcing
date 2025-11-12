# Duke Email with Power Automate (DUO 2FA Support)

**The easiest way to send from Duke email with DUO 2FA - no Azure setup required!**

## 🎯 Why Power Automate?

- ✅ **No Azure app registration needed**
- ✅ **No OAuth2 complexity**
- ✅ **DUO 2FA already handled** (you log into Power Automate once)
- ✅ **Free for Duke students** (included with Microsoft 365)
- ✅ **5-minute setup**
- ✅ **Just needs a webhook URL**

## 🚀 Setup (5 minutes)

### Step 1: Create Power Automate Flow

1. **Go to Power Automate:**
   - Visit: https://make.powerautomate.com
   - Sign in with **a.raj@duke.edu** (complete DUO 2FA once)

2. **Create New Flow:**
   - Click "Create" → "Instant cloud flow"
   - Name it: "Outreach Engine Email Sender"
   - Choose trigger: "When an HTTP request is received"
   - Click "Create"

3. **Configure HTTP Trigger:**
   - The trigger will ask for a JSON schema
   - Click "Use sample payload to generate schema"
   - Paste this:
   ```json
   {
     "to_email": "recipient@example.com",
     "subject": "Email subject",
     "body": "Email body text",
     "draft_id": 123
   }
   ```
   - Click "Done"

4. **Add Send Email Action:**
   - Click "+ New step"
   - Search for "Send an email (V2)"
   - Select "Office 365 Outlook" connector
   - Configure:
     - **To:** Click in field → Select "to_email" from dynamic content
     - **Subject:** Click in field → Select "subject" from dynamic content
     - **Body:** Click in field → Select "body" from dynamic content
   - Leave "From (Send as)" empty (uses your Duke email)

5. **Save and Get Webhook URL:**
   - Click "Save" at the top
   - Go back to the HTTP trigger step
   - Copy the "HTTP POST URL" - it looks like:
     ```
     https://prod-xx.eastus.logic.azure.com:443/workflows/abc123.../triggers/manual/paths/invoke?api-version=2016&sp=...&sig=...
     ```
   - ⚠️ **Keep this URL secure!** Anyone with it can send emails as you.

### Step 2: Configure Your Application

1. **Update `.env` file:**

```env
# Email Provider
EMAIL_PROVIDER=powerautomate

# Power Automate Webhook URL (paste the URL you copied)
POWER_AUTOMATE_WEBHOOK_URL=https://prod-xx.eastus.logic.azure.com:443/workflows/.../triggers/manual/...
```

2. **That's it!** No other configuration needed.

### Step 3: Test It

```bash
# Start server
python main.py

# Run test (in another terminal)
python test_smtp.py
```

The test will:
- Create a draft
- Call Power Automate webhook
- Power Automate sends from a.raj@duke.edu
- Success!

## 📧 How It Works

```
┌─────────────────┐
│ Outreach Engine │
│   (Your App)    │
└────────┬────────┘
         │ HTTP POST
         │ {to_email, subject, body}
         ▼
┌─────────────────┐
│ Power Automate  │
│   (Microsoft)   │
└────────┬────────┘
         │ Send via Outlook
         ▼
┌─────────────────┐
│  a.raj@duke.edu │
│   (Duke Email)  │
└─────────────────┘
```

**Flow:**
1. Your app creates email draft
2. Calls Power Automate webhook with email data
3. Power Automate sends it from your Duke email
4. Returns success confirmation

## 🎨 Power Automate Flow Visual

```
[HTTP Request Received]
        ↓
   Parse JSON
   - to_email
   - subject
   - body
   - draft_id
        ↓
[Send Email (V2)]
   From: a.raj@duke.edu
   To: @{to_email}
   Subject: @{subject}
   Body: @{body}
        ↓
    [Success]
```

## 🔧 Advanced Configuration

### Add Email Template Formatting

In Power Automate, after the HTTP trigger, add a "Compose" action:

```
Body:
Hi there,

@{triggerBody()?['body']}

Best regards,
Aditya Raj
Duke University
a.raj@duke.edu

---
To unsubscribe, reply with "unsubscribe"
```

### Add Error Handling

1. Click "..." on "Send an email (V2)"
2. Select "Configure run after"
3. Add a parallel branch for "has failed"
4. Add action: "Respond to a Power Automate"
5. Set Status Code: 500
6. Set Body: "Email send failed"

### Add Logging

1. After "Send an email", add "Compose" action
2. Content:
```json
{
  "draft_id": @{triggerBody()?['draft_id']},
  "sent_to": @{triggerBody()?['to_email']},
  "timestamp": @{utcNow()},
  "status": "success"
}
```

## 📊 Monitoring

### View Send History
1. Go to https://make.powerautomate.com
2. Click "My flows"
3. Click your "Outreach Engine Email Sender" flow
4. See all runs with status (success/failed)
5. Click any run to see details

### Check Errors
- Failed runs show in red
- Click to see what went wrong
- Common issues:
  - Invalid email address
  - Network timeout
  - Permissions issue

## 🔒 Security Best Practices

### Secure Your Webhook

**Option 1: Add API Key Validation (Recommended)**

1. In Power Automate, after HTTP trigger add "Condition":
   - Left: `@{triggerBody()?['api_key']}`
   - Equals: `your_secret_key_here`
2. If yes → Send email
3. If no → Terminate with error

Update your app payload:
```python
payload = {
    "api_key": "your_secret_key_here",  # Add this
    "to_email": draft.to_email,
    "subject": draft.subject,
    "body": draft.body
}
```

**Option 2: IP Whitelist**
- In Power Automate trigger settings
- Add "IP filtering"
- Only allow your server IP

**Option 3: Regenerate Webhook**
- If URL leaked, delete and recreate flow
- Get new webhook URL

### Rate Limiting

Power Automate free tier limits:
- **750 runs/day** (more than enough!)
- 5-minute timeout per run
- 100 MB data transfer/day

## 🎯 Comparison: Power Automate vs Other Methods

| Method | Setup Time | Complexity | Duke IT Needed | Cost |
|--------|------------|------------|----------------|------|
| **Power Automate** | **5 min** | **Easy** | **No** | **Free** |
| OAuth2 | 30+ min | Hard | Yes (Azure app) | Free |
| SMTP Password | 2 min | Easy | No (but breaks with DUO) | Free |
| SendGrid API | 10 min | Medium | No (external service) | Free 100/day |

## 🧪 Testing Tips

### Test with Mock Mode First
```python
# Set mock_mode=True to test without actually sending
r = requests.post(f"{BASE}/api/drafts/{draft_id}/send",
                 json={"mock_mode": True})
```

### Send Test Email to Yourself
```python
# Change recipient to your own email first
r = requests.post(f"{BASE}/api/contacts/", json={
    "name": "Test",
    "email": "a.raj@duke.edu"  # Your Duke email
})
```

### Check Power Automate Run History
- Every send appears in Power Automate
- See exact payloads sent
- Debug failures easily

## ❓ Troubleshooting

### "Power Automate webhook failed: 404"
- Webhook URL incorrect
- Check URL copied completely (they're very long!)
- No spaces or line breaks in URL

### "Power Automate webhook failed: 401"
- Flow might be turned off
- Go to Power Automate → Turn flow ON

### "Power Automate webhook failed: 500"
- Check flow run history in Power Automate
- Look for error message
- Common: Invalid email format

### "Emails not sending"
- Check flow is enabled (not turned off)
- Verify Duke email permissions
- Check Power Automate run history for errors

### "POWER_AUTOMATE_WEBHOOK_URL not configured"
- Check `.env` has the webhook URL
- Restart server after updating `.env`

## 📈 Scaling

### Multiple Flows for Different Campaigns
Create separate flows for:
- Outreach emails
- Follow-up emails
- Reply templates

Each gets its own webhook URL.

### Batch Processing
Power Automate can handle concurrent requests:
- Multiple drafts sending at once
- Automatic queuing
- No rate limit issues

## 🎓 For Duke Students

### Getting Help
- **Duke OIT**: If Power Automate isn't working
- **Power Automate Support**: https://powerusers.microsoft.com/
- **This project**: Check main README.md

### Duke-Specific Notes
- Uses Duke's Microsoft 365 subscription
- No additional cost
- DUO 2FA handled automatically
- Emails show as from a.raj@duke.edu
- Complies with Duke email policies

## ✅ Success Checklist

- [ ] Power Automate flow created
- [ ] HTTP trigger configured with JSON schema
- [ ] "Send an email (V2)" action added
- [ ] Flow saved and enabled
- [ ] Webhook URL copied
- [ ] `.env` updated with `EMAIL_PROVIDER=powerautomate`
- [ ] `.env` updated with `POWER_AUTOMATE_WEBHOOK_URL`
- [ ] Test email sent successfully
- [ ] Flow run shows success in Power Automate

---

**🎉 Done!** You can now send Duke emails despite DUO 2FA - no Azure complexity!

**Next:** See main README.md for full API usage and campaign workflows.

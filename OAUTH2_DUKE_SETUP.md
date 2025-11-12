# Duke Email OAuth2 Setup (With DUO 2FA)

Complete guide to set up OAuth2 authentication for Duke email when you have DUO two-factor authentication.

## 🎯 Why OAuth2?

Duke requires DUO 2FA, which breaks basic SMTP password authentication. OAuth2 solves this by:
- ✅ Works with DUO 2FA
- ✅ More secure than passwords
- ✅ No need for app passwords
- ✅ Enterprise-grade authentication

## 📋 Prerequisites

1. Duke email account (a.raj@duke.edu)
2. Access to Azure Portal (or ask Duke IT)
3. 10 minutes of setup time

## 🚀 Step 1: Register Azure Application

### Option A: Through Duke IT (Recommended)
1. Email Duke IT support
2. Request: "Azure app registration for email automation project"
3. Provide: Your NetID, app name ("Outreach Engine"), redirect URI (`http://localhost:8000/auth/callback`)
4. They'll give you: Client ID, Client Secret, Tenant ID

### Option B: Self-Service (If you have Azure access)

1. **Go to Azure Portal:**
   - Visit: https://portal.azure.com
   - Sign in with a.raj@duke.edu + DUO

2. **Navigate to App Registrations:**
   - Search for "Azure Active Directory"
   - Click "App registrations" → "New registration"

3. **Register App:**
   ```
   Name: Duke Outreach Engine
   Supported account types: Accounts in this organizational directory only (Duke only)
   Redirect URI:
     - Platform: Web
     - URI: http://localhost:8000/auth/callback
   ```

4. **Get Client ID:**
   - After creation, copy the "Application (client) ID"
   - This is your `MICROSOFT_CLIENT_ID`

5. **Get Tenant ID:**
   - On the same page, copy "Directory (tenant) ID"
   - This is your `MICROSOFT_TENANT_ID`

6. **Create Client Secret:**
   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Description: "Outreach Engine Secret"
   - Expires: 24 months (or custom)
   - Copy the **Value** (not the ID!)
   - This is your `MICROSOFT_CLIENT_SECRET`
   - ⚠️ **Copy it now** - you can't see it again!

7. **Add API Permissions:**
   - Go to "API permissions"
   - Click "Add a permission"
   - Choose "Office 365 Exchange Online"
   - Select "Delegated permissions"
   - Add: `SMTP.Send`
   - Click "Add permissions"
   - Click "Grant admin consent for Duke" (if you have permissions)

## 🔧 Step 2: Configure Your Application

1. **Update `.env` file:**

```env
# Email Configuration
EMAIL_PROVIDER=smtp
SMTP_AUTH_METHOD=oauth2  # ← Important! Change from "password" to "oauth2"

# SMTP Settings (keep existing)
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=a.raj@duke.edu
SMTP_USE_TLS=true

# Microsoft OAuth2 Settings (NEW)
MICROSOFT_CLIENT_ID=your-client-id-from-azure
MICROSOFT_CLIENT_SECRET=your-client-secret-from-azure
MICROSOFT_TENANT_ID=your-tenant-id-from-azure
MICROSOFT_REDIRECT_URI=http://localhost:8000/auth/callback
OAUTH_TOKEN_FILE=.oauth_token.json
```

2. **Install OAuth2 dependency:**

```bash
pip install msal==1.26.0
```

## 🔐 Step 3: Authenticate (One-time)

Run the OAuth2 setup script:

```bash
python -m src.services.oauth2_auth
```

This will:
1. Open your browser
2. Redirect to Duke login
3. Prompt for Duke credentials (a.raj@duke.edu)
4. Complete DUO 2FA verification
5. Grant permissions for email sending
6. Save access token to `.oauth_token.json`

**Example output:**
```
🔐 DUKE EMAIL OAUTH2 AUTHENTICATION
============================================================

Opening browser for Duke login...
1. Log in with your Duke credentials (a.raj@duke.edu)
2. Complete DUO 2FA verification
3. Grant permissions for email sending

After completing authentication:
Paste the full redirect URL here: http://localhost:8000/auth/callback?code=...

✅ Authentication successful! Token saved.
```

**If browser doesn't open automatically:**
- The URL will be printed in terminal
- Copy and paste it into your browser manually
- Complete authentication
- Copy the full redirect URL (starts with `http://localhost:8000/auth/callback?code=...`)
- Paste it back into the terminal

## ✅ Step 4: Test It!

1. **Start the server:**
```bash
python main.py
```

2. **Run the test:**
```bash
python test_smtp.py
```

The test will:
- Create a contact
- Generate an email draft
- Authenticate with OAuth2
- Send via Duke SMTP

**Successful output:**
```
🧪 Testing Duke Email via SMTP

✅ Server is running
1️⃣  Creating test contact...
   ✅ Contact created: Test Recipient (ID: 1)
2️⃣  Creating email draft...
   ✅ Draft created: ID 1
5️⃣  Sending email via Duke SMTP...
   ✅ Email sent!
   Status: SENT
   Message ID: smtp_1_1234567890

✅ Duke SMTP Test Complete!
```

## 🔄 Token Refresh

OAuth2 tokens expire but refresh automatically:

- **Access tokens**: Valid for 1 hour
- **Refresh tokens**: Valid for 90 days
- **Auto-refresh**: Happens automatically when sending emails
- **Re-authentication**: Only needed every 90 days

If you see:
```
OAuth2: No valid token. Starting interactive authentication...
```

Just run the setup again:
```bash
python -m src.services.oauth2_auth
```

## 🐛 Troubleshooting

### "MICROSOFT_CLIENT_ID not configured"
- Check `.env` file has `MICROSOFT_CLIENT_ID`
- Make sure you're using the Azure Application (client) ID, not Tenant ID

### "Authentication failed: invalid_client"
- Check `MICROSOFT_CLIENT_SECRET` is correct
- Secret might have expired - create a new one in Azure
- Make sure you copied the **Value**, not the **Secret ID**

### "redirect_uri_mismatch"
- In Azure Portal, check redirect URI is exactly: `http://localhost:8000/auth/callback`
- Check `.env` has matching `MICROSOFT_REDIRECT_URI`
- No trailing slash!

### "AADSTS65001: User consent required"
- In Azure Portal → API permissions
- Click "Grant admin consent for Duke"
- Or: Have admin grant consent for your app

### "SMTP authentication failed"
- Verify `SMTP_AUTH_METHOD=oauth2` in `.env`
- Check token file exists: `ls -la .oauth_token.json`
- Re-authenticate: `python -m src.services.oauth2_auth`

### "Failed to obtain OAuth2 access token"
- Delete old token: `rm .oauth_token.json`
- Re-authenticate from scratch
- Check Azure app has `SMTP.Send` permission

## 🔒 Security Notes

**Token File (`.oauth_token.json`):**
- Contains sensitive access/refresh tokens
- File permissions automatically set to 0600 (owner read/write only)
- **Never commit to git** (already in `.gitignore`)
- If compromised, revoke in Azure Portal → App registrations → Your app → Tokens

**Client Secret:**
- Store only in `.env` (never commit)
- Rotate every 6-12 months
- If exposed, generate new secret in Azure immediately

## 📊 Comparison: Password vs OAuth2

| Feature | Password Auth | OAuth2 Auth |
|---------|--------------|-------------|
| Works with DUO 2FA | ❌ No | ✅ Yes |
| Security | Basic | Enterprise-grade |
| Token expiry | Never | 90 days |
| Revocable | Must change password | Revoke in Azure |
| Setup complexity | Easy | Moderate |
| Duke IT support | Limited | Full support |

## 🎓 For Duke Students

If you're a Duke student and can't access Azure Portal:

1. **Contact Duke OIT:**
   - Email: oit-help@duke.edu
   - Subject: "Azure App Registration for Email Automation"
   - Explain: Academic project for automated outreach engine

2. **Provide them:**
   - Your NetID (aditya.raj)
   - App name: "Outreach Engine"
   - Redirect URI: `http://localhost:8000/auth/callback`
   - Required permission: `SMTP.Send` (delegated)

3. **They'll send you:**
   - Client ID
   - Client Secret
   - Tenant ID

## 🚀 Once Setup is Complete

You can now:

```python
import requests

BASE = "http://localhost:8000"

# Send emails normally - OAuth2 happens behind the scenes!
r = requests.post(f"{BASE}/api/drafts/1/send")

# No need to think about DUO or passwords
# OAuth2 handles everything automatically
```

## 📚 Additional Resources

- **Azure App Registration**: https://portal.azure.com/#blade/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/RegisteredApps
- **Duke OIT**: https://oit.duke.edu
- **Microsoft Graph API**: https://docs.microsoft.com/en-us/graph/auth-v2-user
- **MSAL Python**: https://github.com/AzureAD/microsoft-authentication-library-for-python

## ✅ Success Checklist

- [ ] Azure app registered (or Duke IT provided credentials)
- [ ] `.env` file updated with OAuth2 settings
- [ ] `SMTP_AUTH_METHOD=oauth2` set
- [ ] Ran `python -m src.services.oauth2_auth` successfully
- [ ] `.oauth_token.json` file exists
- [ ] Test email sent via `python test_smtp.py`
- [ ] Server can send emails through API

---

**🎉 You're all set!** Duke email now works with DUO 2FA via OAuth2.

Questions? Check the main README.md or contact Duke OIT for Azure support.

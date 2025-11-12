"""
Microsoft OAuth2 authentication for Duke email (with DUO 2FA support).
"""

import json
import os
from pathlib import Path
from typing import Optional
import msal
import webbrowser
from src.config import config
import logging

logger = logging.getLogger(__name__)


class MicrosoftOAuth2:
    """Handle Microsoft OAuth2 authentication for Duke email."""

    SCOPES = [
        "https://outlook.office365.com/SMTP.Send",
        "offline_access"  # For refresh tokens
    ]

    def __init__(self):
        self.client_id = config.MICROSOFT_CLIENT_ID
        self.client_secret = config.MICROSOFT_CLIENT_SECRET
        self.tenant_id = config.MICROSOFT_TENANT_ID
        self.redirect_uri = config.MICROSOFT_REDIRECT_URI
        self.token_file = Path(config.OAUTH_TOKEN_FILE)

        if not self.client_id:
            raise ValueError("MICROSOFT_CLIENT_ID not configured in .env")

        # Create MSAL app
        self.app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret
        )

    def get_access_token(self) -> Optional[str]:
        """
        Get access token for SMTP.Send permission.

        Returns cached token if valid, otherwise refreshes or prompts for auth.
        """
        # Try to load cached token
        token_data = self._load_token()

        if token_data:
            # Try to use refresh token
            result = self.app.acquire_token_by_refresh_token(
                token_data.get("refresh_token"),
                scopes=self.SCOPES
            )

            if "access_token" in result:
                self._save_token(result)
                logger.info("OAuth2: Access token refreshed")
                return result["access_token"]

        # No valid token - need interactive auth
        logger.warning("OAuth2: No valid token. Starting interactive authentication...")
        return self._interactive_auth()

    def _interactive_auth(self) -> Optional[str]:
        """
        Perform interactive OAuth2 flow.

        Opens browser for user to authenticate with Duke credentials + DUO.
        """
        # Get authorization URL
        flow = self.app.initiate_auth_code_flow(
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )

        if "auth_uri" not in flow:
            raise ValueError("Failed to create auth flow")

        auth_url = flow["auth_uri"]

        print("\n" + "="*60)
        print("🔐 DUKE EMAIL OAUTH2 AUTHENTICATION")
        print("="*60)
        print("\nOpening browser for Duke login...")
        print("1. Log in with your Duke credentials (a.raj@duke.edu)")
        print("2. Complete DUO 2FA verification")
        print("3. Grant permissions for email sending")
        print("\nIf browser doesn't open, visit this URL:")
        print(f"\n{auth_url}\n")
        print("="*60)

        # Open browser
        webbrowser.open(auth_url)

        # Wait for user to complete auth and paste redirect URL
        print("\nAfter completing authentication:")
        redirect_response = input("Paste the full redirect URL here: ").strip()

        # Extract auth code from redirect
        if "code=" not in redirect_response:
            raise ValueError("Invalid redirect URL. Should contain 'code=' parameter")

        # Complete the flow
        result = self.app.acquire_token_by_auth_code_flow(
            flow,
            {"code": redirect_response.split("code=")[1].split("&")[0]}
        )

        if "access_token" in result:
            self._save_token(result)
            logger.info("OAuth2: Authentication successful!")
            print("\n✅ Authentication successful! Token saved.")
            return result["access_token"]
        else:
            error = result.get("error_description", result.get("error"))
            raise ValueError(f"Authentication failed: {error}")

    def _load_token(self) -> Optional[dict]:
        """Load cached token from file."""
        if not self.token_file.exists():
            return None

        try:
            with open(self.token_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
            return None

    def _save_token(self, token_data: dict):
        """Save token to file."""
        try:
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            # Secure the token file
            os.chmod(self.token_file, 0o600)
            logger.info("OAuth2: Token saved successfully")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")

    def revoke_token(self):
        """Revoke and delete cached token."""
        if self.token_file.exists():
            self.token_file.unlink()
            logger.info("OAuth2: Token revoked")


def get_oauth2_access_token() -> str:
    """
    Convenience function to get OAuth2 access token for Duke email.

    Returns:
        Access token string
    """
    oauth = MicrosoftOAuth2()
    token = oauth.get_access_token()

    if not token:
        raise ValueError("Failed to obtain OAuth2 access token")

    return token


def setup_oauth2():
    """
    Interactive setup for Duke OAuth2 authentication.

    Run this once to authenticate and cache tokens.
    """
    print("\n🚀 Setting up Duke Email OAuth2 Authentication\n")

    oauth = MicrosoftOAuth2()

    try:
        token = oauth.get_access_token()
        print(f"\n✅ Setup complete! Access token obtained.")
        print(f"   Token cached in: {oauth.token_file}")
        print(f"\nYou can now send emails from {config.SMTP_USER}")
        return True

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check MICROSOFT_CLIENT_ID in .env")
        print("2. Ensure your Azure app has SMTP.Send permission")
        print("3. Make sure redirect URI matches Azure app settings")
        return False


if __name__ == "__main__":
    # Run OAuth2 setup when executed directly
    setup_oauth2()

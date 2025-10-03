
import base64, email.message
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from libs import cosmos

def send_gmail(to_addr: str, subject: str, html: str):
    """Send email using stored Google OAuth tokens"""
    # Get stored tokens
    token_doc = cosmos.get_by_id("oauthTokens", "user-google", partition="google")
    if not token_doc:
        raise Exception("Google OAuth not configured. Please authenticate first.")
    
    creds = Credentials(
        token=token_doc["accessToken"],
        refresh_token=token_doc.get("refreshToken"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token_doc.get("clientId"),
        client_secret=token_doc.get("clientSecret")
    )
    
    service = build("gmail", "v1", credentials=creds)
    msg = email.message.EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["From"] = "me"
    msg.set_content("See HTML part")
    msg.add_alternative(html, subtype="html")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result.get("id")

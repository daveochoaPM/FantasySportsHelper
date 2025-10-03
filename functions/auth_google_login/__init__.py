import azure.functions as func
import os
import urllib.parse
from itsdangerous import URLSafeTimedSerializer

def main(req: func.HttpRequest) -> func.HttpResponse:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GMAIL_REDIRECT_URI")
    
    if not client_id or not redirect_uri:
        return func.HttpResponse("Google OAuth not configured", status_code=500)
    
    # Generate state parameter for CSRF protection
    secret_key = os.getenv("GOOGLE_CLIENT_SECRET", "dev-secret")
    serializer = URLSafeTimedSerializer(secret_key)
    state = serializer.dumps({"provider": "google"})
    
    # Build Google OAuth URL
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "scope": "https://www.googleapis.com/auth/gmail.send",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    
    return func.HttpResponse(status_code=302, headers={"Location": auth_url})

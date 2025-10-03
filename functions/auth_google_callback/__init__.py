import azure.functions as func
import os
import requests
import json
from itsdangerous import URLSafeTimedSerializer
from libs import cosmos

def main(req: func.HttpRequest) -> func.HttpResponse:
    code = req.params.get("code")
    state = req.params.get("state")
    error = req.params.get("error")
    
    if error:
        return func.HttpResponse(f"OAuth error: {error}", status_code=400)
    
    if not code or not state:
        return func.HttpResponse("Missing code or state parameter", status_code=400)
    
    # Verify state parameter
    secret_key = os.getenv("GOOGLE_CLIENT_SECRET", "dev-secret")
    serializer = URLSafeTimedSerializer(secret_key)
    try:
        state_data = serializer.loads(state, max_age=600)  # 10 minutes
    except:
        return func.HttpResponse("Invalid state parameter", status_code=400)
    
    # Exchange code for tokens
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GMAIL_REDIRECT_URI")
    
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    response = requests.post("https://oauth2.googleapis.com/token", data=token_data)
    
    if response.status_code != 200:
        return func.HttpResponse(f"Token exchange failed: {response.text}", status_code=400)
    
    tokens = response.json()
    
    # Store tokens in Cosmos
    token_doc = {
        "id": "user-google",
        "provider": "google",
        "accessToken": tokens["access_token"],
        "refreshToken": tokens.get("refresh_token"),
        "expiresAt": tokens.get("expires_in", 3600)
    }
    
    cosmos.upsert("oauthTokens", token_doc, partition="google")
    
    return func.HttpResponse("Google OAuth successful! You can now close this window.", status_code=200)

import azure.functions as func
import os
import urllib.parse
from itsdangerous import URLSafeTimedSerializer

def main(req: func.HttpRequest) -> func.HttpResponse:
    client_id = os.getenv("YAHOO_CLIENT_ID")
    redirect_uri = os.getenv("YAHOO_REDIRECT_URI")
    
    if not client_id or not redirect_uri:
        return func.HttpResponse("Yahoo OAuth not configured", status_code=500)
    
    # Generate state parameter for CSRF protection
    secret_key = os.getenv("YAHOO_CLIENT_SECRET", "dev-secret")
    serializer = URLSafeTimedSerializer(secret_key)
    state = serializer.dumps({"provider": "yahoo"})
    
    # Build Yahoo OAuth URL
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "scope": "fspt-r"
    }
    
    auth_url = f"https://api.login.yahoo.com/oauth2/request_auth?{urllib.parse.urlencode(params)}"
    
    return func.HttpResponse(status_code=302, headers={"Location": auth_url})

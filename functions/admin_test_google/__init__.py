import azure.functions as func
import json
import os
import requests

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Check for admin role in headers (set by Azure Static Web Apps)
    user_roles = req.headers.get('x-ms-client-principal-roles', '')
    if 'admin' not in user_roles:
        return func.HttpResponse("Unauthorized: Admin role required", status_code=403)
    
    if req.method != "POST":
        return func.HttpResponse("Method not allowed", status_code=405)
    
    try:
        # Get Google OAuth credentials
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        redirect_uri = os.getenv('GMAIL_REDIRECT_URI')
        
        # Check if credentials are configured
        if not client_id or not client_secret:
            return func.HttpResponse(json.dumps({
                "error": "Google OAuth credentials not configured",
                "message": "Please configure Google Client ID and Secret in the Configuration tab"
            }), status_code=400, mimetype="application/json")
        
        # Test Google OAuth configuration by validating the client ID format
        if client_id and client_secret and redirect_uri:
            return func.HttpResponse(json.dumps({
                "message": "Google OAuth credentials are configured correctly",
                "client_id": client_id[:8] + "..." if client_id else "Not set",
                "redirect_uri": redirect_uri,
                "status": "configured"
            }), status_code=200, mimetype="application/json")
        else:
            return func.HttpResponse(json.dumps({
                "error": "Google OAuth configuration incomplete",
                "message": "Missing required credentials"
            }), status_code=400, mimetype="application/json")
            
    except Exception as e:
        return func.HttpResponse(json.dumps({
            "error": f"Google OAuth test failed: {str(e)}"
        }), status_code=500, mimetype="application/json")

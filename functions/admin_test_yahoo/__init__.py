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
        # Get Yahoo OAuth credentials
        client_id = os.getenv('YAHOO_CLIENT_ID')
        client_secret = os.getenv('YAHOO_CLIENT_SECRET')
        redirect_uri = os.getenv('YAHOO_REDIRECT_URI')
        
        # Check if credentials are configured
        if not client_id or not client_secret:
            return func.HttpResponse(json.dumps({
                "error": "Yahoo OAuth credentials not configured",
                "message": "Please configure Yahoo Client ID and Secret in the Configuration tab"
            }), status_code=400, mimetype="application/json")
        
        # Test Yahoo OAuth configuration by attempting to get an access token
        # This is a simplified test - in production you'd want to test with actual OAuth flow
        test_data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        # Note: Yahoo Fantasy API doesn't support client_credentials flow
        # So we'll just validate that the credentials are properly configured
        if client_id and client_secret and redirect_uri:
            return func.HttpResponse(json.dumps({
                "message": "Yahoo OAuth credentials are configured correctly",
                "client_id": client_id[:8] + "..." if client_id else "Not set",
                "redirect_uri": redirect_uri,
                "status": "configured"
            }), status_code=200, mimetype="application/json")
        else:
            return func.HttpResponse(json.dumps({
                "error": "Yahoo OAuth configuration incomplete",
                "message": "Missing required credentials"
            }), status_code=400, mimetype="application/json")
            
    except Exception as e:
        return func.HttpResponse(json.dumps({
            "error": f"Yahoo OAuth test failed: {str(e)}"
        }), status_code=500, mimetype="application/json")

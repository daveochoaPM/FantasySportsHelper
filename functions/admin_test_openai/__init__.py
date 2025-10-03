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
        # Get OpenAI API key
        openai_key = os.getenv('OPENAI_API_KEY')
        
        # Check if API key is configured
        if not openai_key:
            return func.HttpResponse(json.dumps({
                "error": "OpenAI API key not configured",
                "message": "OpenAI API key is optional. Configure it in the Configuration tab if you want AI-powered guidance enhancement."
            }), status_code=200, mimetype="application/json")  # Not an error, just optional
        
        # Test OpenAI API by making a simple request
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json"
        }
        
        # Test with a simple completion request
        test_payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Test connection"}
            ],
            "max_tokens": 10
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=test_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            return func.HttpResponse(json.dumps({
                "message": "OpenAI API key is valid and working",
                "status": "working",
                "model": "gpt-3.5-turbo"
            }), status_code=200, mimetype="application/json")
        elif response.status_code == 401:
            return func.HttpResponse(json.dumps({
                "error": "OpenAI API key is invalid",
                "message": "Please check your API key in the Configuration tab"
            }), status_code=400, mimetype="application/json")
        elif response.status_code == 429:
            return func.HttpResponse(json.dumps({
                "error": "OpenAI API rate limit exceeded",
                "message": "API key is valid but rate limited. Try again later."
            }), status_code=400, mimetype="application/json")
        else:
            return func.HttpResponse(json.dumps({
                "error": f"OpenAI API test failed with status {response.status_code}",
                "message": response.text
            }), status_code=400, mimetype="application/json")
            
    except requests.exceptions.Timeout:
        return func.HttpResponse(json.dumps({
            "error": "OpenAI API test timed out",
            "message": "API key may be valid but request timed out"
        }), status_code=400, mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({
            "error": f"OpenAI API test failed: {str(e)}"
        }), status_code=500, mimetype="application/json")

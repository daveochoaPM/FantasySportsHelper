import azure.functions as func
import json
import os
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from libs import cosmos

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Check for admin role in headers (set by Azure Static Web Apps)
    user_roles = req.headers.get('x-ms-client-principal-roles', '')
    if 'admin' not in user_roles:
        return func.HttpResponse("Unauthorized: Admin role required", status_code=403)
    
    if req.method == "GET":
        # Get current configuration status
        try:
            # Check if Key Vault is enabled
            use_keyvault = os.getenv('YAHOO_CLIENT_ID', '').startswith('@Microsoft.KeyVault')
            
            if use_keyvault:
                # Try to get Key Vault client
                try:
                    credential = DefaultAzureCredential()
                    keyvault_url = os.getenv('KEY_VAULT_URL', '')
                    if keyvault_url:
                        client = SecretClient(vault_url=keyvault_url, credential=credential)
                        
                        config = {
                            'yahooClientId': get_secret_or_empty(client, 'YAHOO-CLIENT-ID'),
                            'yahooClientSecret': get_secret_or_empty(client, 'YAHOO-CLIENT-SECRET'),
                            'googleClientId': get_secret_or_empty(client, 'GOOGLE-CLIENT-ID'),
                            'googleClientSecret': get_secret_or_empty(client, 'GOOGLE-CLIENT-SECRET'),
                            'openaiApiKey': get_secret_or_empty(client, 'OPENAI-API-KEY'),
                            'yahooRedirectUri': os.getenv('YAHOO_REDIRECT_URI', ''),
                            'googleRedirectUri': os.getenv('GMAIL_REDIRECT_URI', ''),
                            'useKeyVault': True
                        }
                    else:
                        config = get_config_from_env()
                except Exception as e:
                    # Fallback to environment variables
                    config = get_config_from_env()
            else:
                config = get_config_from_env()
            
            return func.HttpResponse(json.dumps(config), status_code=200, mimetype="application/json")
            
        except Exception as e:
            return func.HttpResponse(f"Error loading configuration: {str(e)}", status_code=500)
    
    elif req.method == "POST":
        # Update configuration
        try:
            data = req.get_json()
            
            # Check if Key Vault is enabled
            use_keyvault = os.getenv('YAHOO_CLIENT_ID', '').startswith('@Microsoft.KeyVault')
            
            if use_keyvault:
                # Update Key Vault secrets
                try:
                    credential = DefaultAzureCredential()
                    keyvault_url = os.getenv('KEY_VAULT_URL', '')
                    if keyvault_url:
                        client = SecretClient(vault_url=keyvault_url, credential=credential)
                        
                        # Update secrets if provided
                        if data.get('yahooClientId'):
                            client.set_secret('YAHOO-CLIENT-ID', data['yahooClientId'])
                        if data.get('yahooClientSecret'):
                            client.set_secret('YAHOO-CLIENT-SECRET', data['yahooClientSecret'])
                        if data.get('googleClientId'):
                            client.set_secret('GOOGLE-CLIENT-ID', data['googleClientId'])
                        if data.get('googleClientSecret'):
                            client.set_secret('GOOGLE-CLIENT-SECRET', data['googleClientSecret'])
                        if data.get('openaiApiKey'):
                            client.set_secret('OPENAI-API-KEY', data['openaiApiKey'])
                        
                        return func.HttpResponse(json.dumps({
                            "message": "Configuration updated in Key Vault successfully"
                        }), status_code=200, mimetype="application/json")
                    else:
                        return func.HttpResponse("Key Vault URL not configured", status_code=500)
                except Exception as e:
                    return func.HttpResponse(f"Error updating Key Vault: {str(e)}", status_code=500)
            else:
                # Update Function App settings directly
                return func.HttpResponse(json.dumps({
                    "message": "Key Vault not enabled. Please configure secrets manually in Function App settings.",
                    "instructions": "Go to Azure Portal → Function App → Configuration → Application settings"
                }), status_code=200, mimetype="application/json")
                
        except Exception as e:
            return func.HttpResponse(f"Error updating configuration: {str(e)}", status_code=500)
    
    else:
        return func.HttpResponse("Method not allowed", status_code=405)

def get_secret_or_empty(client, secret_name):
    """Get secret from Key Vault or return empty string"""
    try:
        secret = client.get_secret(secret_name)
        return secret.value if secret else ""
    except:
        return ""

def get_config_from_env():
    """Get configuration from environment variables"""
    return {
        'yahooClientId': os.getenv('YAHOO_CLIENT_ID', ''),
        'yahooClientSecret': '••••••••' if os.getenv('YAHOO_CLIENT_SECRET') else '',
        'googleClientId': os.getenv('GOOGLE_CLIENT_ID', ''),
        'googleClientSecret': '••••••••' if os.getenv('GOOGLE_CLIENT_SECRET') else '',
        'openaiApiKey': '••••••••' if os.getenv('OPENAI_API_KEY') else '',
        'yahooRedirectUri': os.getenv('YAHOO_REDIRECT_URI', ''),
        'googleRedirectUri': os.getenv('GMAIL_REDIRECT_URI', ''),
        'useKeyVault': False
    }

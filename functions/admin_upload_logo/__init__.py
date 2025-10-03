import azure.functions as func
import json
import os
import uuid
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from libs import cosmos

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Check for admin role in headers (set by Azure Static Web Apps)
    user_roles = req.headers.get('x-ms-client-principal-roles', '')
    if 'admin' not in user_roles:
        return func.HttpResponse("Unauthorized: Admin role required", status_code=403)
    
    if req.method != "POST":
        return func.HttpResponse("Method not allowed", status_code=405)
    
    try:
        # Get the uploaded file
        files = req.files.getlist('logo')
        if not files or len(files) == 0:
            return func.HttpResponse(json.dumps({
                "error": "No file uploaded"
            }), status_code=400, mimetype="application/json")
        
        file = files[0]
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            return func.HttpResponse(json.dumps({
                "error": "File must be an image"
            }), status_code=400, mimetype="application/json")
        
        # Validate file size (2MB max)
        file_content = file.read()
        if len(file_content) > 2 * 1024 * 1024:  # 2MB
            return func.HttpResponse(json.dumps({
                "error": "File size must be less than 2MB"
            }), status_code=400, mimetype="application/json")
        
        # Get storage account connection string
        storage_connection_string = os.getenv('AzureWebJobsStorage')
        if not storage_connection_string:
            return func.HttpResponse(json.dumps({
                "error": "Storage account not configured"
            }), status_code=500, mimetype="application/json")
        
        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
        
        # Generate unique filename
        logo_id = f"logo-{uuid.uuid4()}"
        file_extension = os.path.splitext(file.filename)[1] if file.filename else '.png'
        blob_name = f"logos/{logo_id}{file_extension}"
        
        # Upload to blob storage
        blob_client = blob_service_client.get_blob_client(container="fantasy-helper", blob=blob_name)
        blob_client.upload_blob(file_content, overwrite=True, content_type=file.content_type)
        
        # Get the blob URL
        logo_url = blob_client.url
        
        # Store logo metadata in Cosmos DB
        logo_doc = {
            "id": logo_id,
            "filename": file.filename,
            "contentType": file.content_type,
            "blobName": blob_name,
            "blobUrl": logo_url,
            "uploadedAt": datetime.now().isoformat()
        }
        
        cosmos.upsert("logos", logo_doc, partition="default")
        
        # Return success response
        return func.HttpResponse(json.dumps({
            "message": "Logo uploaded successfully",
            "logoId": logo_id,
            "logoUrl": logo_url
        }), status_code=200, mimetype="application/json")
        
    except Exception as e:
        return func.HttpResponse(json.dumps({
            "error": f"Logo upload failed: {str(e)}"
        }), status_code=500, mimetype="application/json")

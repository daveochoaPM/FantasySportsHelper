import azure.functions as func
import json
import os
from libs import cosmos

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Check for admin role in headers (set by Azure Static Web Apps)
    user_roles = req.headers.get('x-ms-client-principal-roles', '')
    if 'admin' not in user_roles:
        return func.HttpResponse("Unauthorized: Admin role required", status_code=403)
    
    if req.method == "GET":
        # Get report ID from URL
        report_id = req.route_params.get('reportId')
        if not report_id:
            return func.HttpResponse("Missing report ID", status_code=400)
        
        try:
            # Get report from Cosmos DB
            report = cosmos.get("reports", report_id, partition=report_id.split('-')[1])  # Use league ID as partition
            
            if not report:
                return func.HttpResponse("Report not found", status_code=404)
            
            # Get HTML content
            html_content = report.get("htmlContent", "")
            
            if not html_content:
                return func.HttpResponse("Report content not found", status_code=404)
            
            # Return HTML content with appropriate headers
            return func.HttpResponse(
                html_content,
                status_code=200,
                headers={
                    "Content-Type": "text/html; charset=utf-8",
                    "Content-Disposition": f"inline; filename=\"{report.get('title', 'fantasy-report')}.html\""
                }
            )
            
        except Exception as e:
            return func.HttpResponse(json.dumps({
                "error": f"Failed to download report: {str(e)}"
            }), status_code=500, mimetype="application/json")
    
    else:
        return func.HttpResponse("Method not allowed", status_code=405)

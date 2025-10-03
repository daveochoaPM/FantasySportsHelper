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
            
            # Add print-specific CSS
            print_css = """
            <style>
                @media print {
                    body { margin: 0; }
                    .page { page-break-after: always; }
                    .page:last-child { page-break-after: avoid; }
                    .no-print { display: none; }
                }
                @page {
                    margin: 0.5in;
                    size: letter;
                }
            </style>
            """
            
            # Insert print CSS into HTML
            html_with_print = html_content.replace('<head>', f'<head>{print_css}')
            
            # Return HTML content with print styling
            return func.HttpResponse(
                html_with_print,
                status_code=200,
                headers={
                    "Content-Type": "text/html; charset=utf-8",
                    "Content-Disposition": f"inline; filename=\"{report.get('title', 'fantasy-report')}-print.html\""
                }
            )
            
        except Exception as e:
            return func.HttpResponse(json.dumps({
                "error": f"Failed to load print view: {str(e)}"
            }), status_code=500, mimetype="application/json")
    
    else:
        return func.HttpResponse("Method not allowed", status_code=405)

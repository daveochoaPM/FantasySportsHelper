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
        # List all reports
        try:
            reports = cosmos.query("reports", "SELECT * FROM c ORDER BY c.createdAt DESC")
            
            # Format reports for display
            formatted_reports = []
            for report in reports:
                formatted_reports.append({
                    "id": report["id"],
                    "title": report.get("title", f"Report {report['id']}"),
                    "leagueId": report["leagueId"],
                    "week": report["week"],
                    "totalTeams": report["totalTeams"],
                    "generatedReports": report.get("generatedReports", 0),
                    "failedReports": report.get("failedReports", 0),
                    "createdAt": report["createdAt"],
                    "downloadUrl": f"/api/admin/reports/{report['id']}/download",
                    "printUrl": f"/api/admin/reports/{report['id']}/print"
                })
            
            return func.HttpResponse(json.dumps(formatted_reports), status_code=200, mimetype="application/json")
            
        except Exception as e:
            return func.HttpResponse(json.dumps({
                "error": f"Failed to load reports: {str(e)}"
            }), status_code=500, mimetype="application/json")
    
    else:
        return func.HttpResponse("Method not allowed", status_code=405)

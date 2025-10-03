import azure.functions as func
import json
from libs import cosmos

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Check for admin role in headers (set by Azure Static Web Apps)
    user_roles = req.headers.get('x-ms-client-principal-roles', '')
    if 'admin' not in user_roles:
        return func.HttpResponse("Unauthorized: Admin role required", status_code=403)
    if req.method == "POST":
        # Create/update manager mapping
        data = req.get_json()
        league_id = data.get("leagueId")
        team_id = data.get("teamId")
        email = data.get("email")
        
        if not all([league_id, team_id, email]):
            return func.HttpResponse("Missing required fields: leagueId, teamId, email", status_code=400)
        
        manager_doc = {
            "id": f"mgr-{team_id}",
            "leagueId": league_id,
            "teamId": team_id,
            "email": email,
            "name": data.get("name", "")
        }
        
        cosmos.upsert("managers", manager_doc, partition=league_id)
        
        return func.HttpResponse(json.dumps({
            "message": "Manager created/updated", 
            "teamId": team_id,
            "email": email
        }), status_code=200, mimetype="application/json")
    
    elif req.method == "GET":
        league_id = req.route_params.get("leagueId")
        team_id = req.params.get("teamId")
        
        if league_id and team_id:
            # Get specific manager
            manager_doc = cosmos.get_by_id("managers", f"mgr-{team_id}", partition=league_id)
            if not manager_doc:
                return func.HttpResponse("Manager not found", status_code=404)
            return func.HttpResponse(json.dumps(manager_doc), status_code=200, mimetype="application/json")
        elif league_id:
            # Get all managers for league
            managers = cosmos.query("managers",
                                  "SELECT * FROM c WHERE c.leagueId = @leagueId",
                                  [{"name": "@leagueId", "value": league_id}])
            return func.HttpResponse(json.dumps(managers), status_code=200, mimetype="application/json")
        else:
            # Get all managers across all leagues
            managers = cosmos.query("managers", "SELECT * FROM c")
            return func.HttpResponse(json.dumps(managers), status_code=200, mimetype="application/json")
    
    else:
        return func.HttpResponse("Method not allowed", status_code=405)

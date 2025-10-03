import azure.functions as func
import json
from libs import cosmos

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Check for admin role in headers (set by Azure Static Web Apps)
    user_roles = req.headers.get('x-ms-client-principal-roles', '')
    if 'admin' not in user_roles:
        return func.HttpResponse("Unauthorized: Admin role required", status_code=403)
    if req.method == "POST":
        # Create/update league
        data = req.get_json()
        league_id = data.get("leagueId")
        
        if not league_id:
            return func.HttpResponse("Missing leagueId", status_code=400)
        
        league_doc = {
            "id": f"league-{league_id}",
            "leagueId": league_id,
            "sport": data.get("sport", "nhl"),
            "provider": data.get("provider", "yahoo"),
            "name": data.get("name", ""),
            "settings": data.get("settings", {})
        }
        
        cosmos.upsert("leagues", league_doc, partition=league_id)
        
        return func.HttpResponse(json.dumps({"message": "League created/updated", "leagueId": league_id}), 
                                status_code=200, mimetype="application/json")
    
    elif req.method == "GET":
        league_id = req.route_params.get("leagueId")
        
        if league_id:
            # Get specific league info
            league_doc = cosmos.get_by_id("leagues", f"league-{league_id}", partition=league_id)
            
            if not league_doc:
                return func.HttpResponse("League not found", status_code=404)
            
            # Get teams for this league
            teams = cosmos.query("teams", 
                               "SELECT * FROM c WHERE c.leagueId = @leagueId",
                               [{"name": "@leagueId", "value": league_id}])
            
            # Get managers for this league
            managers = cosmos.query("managers",
                                  "SELECT * FROM c WHERE c.leagueId = @leagueId", 
                                  [{"name": "@leagueId", "value": league_id}])
            
            response = {
                "league": league_doc,
                "teams": teams,
                "managers": managers
            }
            
            return func.HttpResponse(json.dumps(response), status_code=200, mimetype="application/json")
        else:
            # Get all leagues
            leagues = cosmos.query("leagues", "SELECT * FROM c")
            return func.HttpResponse(json.dumps(leagues), status_code=200, mimetype="application/json")
    
    else:
        return func.HttpResponse("Method not allowed", status_code=405)

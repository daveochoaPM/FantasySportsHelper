
import azure.functions as func
import json
from libs.yahoo_client import YahooClient
from libs import cosmos

def main(req: func.HttpRequest) -> func.HttpResponse:
    league_id = req.route_params.get("leagueId")
    yc = YahooClient(league_id)
    
    # Get league info and settings
    week = yc.current_week()
    league_settings = yc.league_settings()
    
    # Store league settings
    cosmos.upsert("leagues", {
        "id": f"league-{league_id}",
        "leagueId": league_id,
        "sport": "nhl",
        "provider": "yahoo",
        "currentWeek": week,
        "settings": league_settings
    }, partition=league_id)
    
    # Get and store teams
    teams = yc.teams()
    for t in teams:
        cosmos.upsert("teams", {
            "id": f"team-{t.get('team_id','')}",
            "leagueId": league_id,
            "teamId": t.get("team_id",""),
            "name": t.get("name",""),
            "manager": t.get("manager", "")
        }, partition=league_id)
        
        # Get and store roster
        roster = yc.roster(t.get("team_id",""), week)
        cosmos.upsert("rosters", {
            "id": f"roster-{t.get('team_id','')}-{week}",
            "leagueId": league_id,
            "teamId": t.get("team_id",""),
            "week": week,
            "players": roster
        }, partition=t.get("team_id",""))
    
    return func.HttpResponse(json.dumps({
        "week": week, 
        "teams": len(teams),
        "scoringType": league_settings.get("type", "unknown")
    }), status_code=200, mimetype="application/json")

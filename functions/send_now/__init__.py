
import azure.functions as func
import json, datetime as dt
from libs.yahoo_client import YahooClient
from libs.nhl_client import fetch_schedule, season_code, map_team_to_code
from libs import cosmos
from engine.guidance import compute_guidance, tl_dr
from engine.llm import rewrite

def main(req: func.HttpRequest) -> func.HttpResponse:
    league_id = req.route_params.get("leagueId")
    team_id = req.params.get("teamId")
    week = int(req.params.get("week", 1))
    
    today = dt.date.today()
    current_season = season_code(today)
    last_season = f"{int(current_season[:4])-1}{current_season[:4]}"
    
    # Load league settings
    league_doc = cosmos.get_by_id("leagues", f"league-{league_id}", partition=league_id)
    league_settings = league_doc.get("settings", {}) if league_doc else {}
    
    # Load roster
    roster_doc = cosmos.get_by_id("rosters", f"roster-{team_id}-{week}", partition=team_id) or {"players":[]}
    
    # Build schedule for all players' NHL teams
    schedule = []
    for player in roster_doc["players"]:
        nhl_team = player.get("nhl_team", "UNK")
        if nhl_team != "UNK":
            # Get week start/end dates (simplified - you'd want to calculate actual week boundaries)
            week_start = today
            week_end = today + dt.timedelta(days=7)
            team_schedule = fetch_schedule(nhl_team, week_start, week_end)
            schedule.extend(team_schedule)
    
    # Remove duplicates
    schedule = list({game["gameId"]: game for game in schedule}.values())
    
    # Compute guidance with league settings
    items = compute_guidance(
        roster_doc["players"], 
        schedule, 
        {}, 
        {}, 
        current_season, 
        last_season,
        league_settings
    )
    
    bullets = tl_dr(items)
    pretty = rewrite(bullets)
    
    guidance = {
        "teamId": team_id, 
        "week": week,
        "items": items, 
        "tl_dr": pretty,
        "scoringType": league_settings.get("type", "unknown")
    }
    
    cosmos.upsert("guidanceRuns", {
        "id": f"guid-{league_id}-{team_id}-{today.isoformat()}",
        "leagueId": league_id,
        "teamId": team_id,
        "date": today.isoformat(),
        "payload": guidance
    }, partition=league_id)
    
    return func.HttpResponse(json.dumps(guidance), status_code=200, mimetype="application/json")

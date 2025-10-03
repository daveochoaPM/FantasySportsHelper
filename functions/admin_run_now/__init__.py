import azure.functions as func
import json, datetime as dt
from libs.yahoo_client import YahooClient
from libs.nhl_client import fetch_schedule, season_code
from libs import cosmos
from libs.gmail_client import send_gmail
from engine.guidance import compute_guidance, tl_dr
from engine.llm import rewrite
from jinja2 import Template
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Check for admin role in headers (set by Azure Static Web Apps)
    user_roles = req.headers.get('x-ms-client-principal-roles', '')
    if 'admin' not in user_roles:
        return func.HttpResponse("Unauthorized: Admin role required", status_code=403)
    if req.method != "POST":
        return func.HttpResponse("Method not allowed", status_code=405)
    
    data = req.get_json()
    league_id = data.get("leagueId")
    team_id = data.get("teamId")
    week = data.get("week", 1)
    email_override = data.get("emailOverride")
    
    if not league_id or not team_id:
        return func.HttpResponse("Missing leagueId or teamId", status_code=400)
    
    try:
        # Get manager email (use override if provided)
        if email_override:
            to_email = email_override
        else:
            manager_doc = cosmos.get_by_id("managers", f"mgr-{team_id}", partition=league_id)
            if not manager_doc:
                return func.HttpResponse("Manager not found. Please set up manager email first.", status_code=404)
            to_email = manager_doc["email"]
        
        # Get team name
        team_doc = cosmos.get_by_id("teams", f"team-{team_id}", partition=league_id)
        team_name = team_doc.get("name", f"Team {team_id}") if team_doc else f"Team {team_id}"
        
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
                week_start = dt.date.today()
                week_end = week_start + dt.timedelta(days=7)
                team_schedule = fetch_schedule(nhl_team, week_start, week_end)
                schedule.extend(team_schedule)
        
        # Remove duplicates
        schedule = list({game.get("gameId", f"{game.get('homeTeam', {}).get('abbrev', '')}-{game.get('awayTeam', {}).get('abbrev', '')}-{game.get('gameDate', '')}"): game for game in schedule}.values())
        
        # Compute guidance
        today = dt.date.today()
        current_season = season_code(today)
        last_season = f"{int(current_season[:4])-1}{current_season[:4]}"
        
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
        
        # Render email template
        template_path = os.path.join(os.path.dirname(__file__), "..", "..", "engine", "templates", "email.html.j2")
        with open(template_path, 'r') as f:
            template = Template(f.read())
        
        # Separate recommendations and insights
        recommendations = [item for item in items if item["type"] == "start_bench"]
        insights = [item for item in items if item["type"] == "schedule_insight"]
        
        html = template.render(
            week=week,
            team_name=team_name,
            tl_dr=pretty,
            recommendations=recommendations,
            insights=insights,
            source_season=current_season,
            fallback_reason=None,
            scoring_type=league_settings.get("type", "unknown")
        )
        
        # Send email
        subject = f"Fantasy NHL Guidance - Week {week} - {team_name}"
        message_id = send_gmail(to_email, subject, html)
        
        # Store guidance run
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
        
        return func.HttpResponse(json.dumps({
            "message": "Guidance sent successfully",
            "messageId": message_id,
            "email": to_email,
            "preview": pretty[:3]  # First 3 bullets as preview
        }), status_code=200, mimetype="application/json")
        
    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)

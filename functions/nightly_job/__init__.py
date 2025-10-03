
import datetime, logging
import azure.functions as func
from libs import cosmos
from libs.yahoo_client import YahooClient
from libs.nhl_client import fetch_schedule, season_code
from libs.gmail_client import send_gmail
from engine.guidance import compute_guidance, tl_dr
from engine.llm import rewrite
from jinja2 import Template
import os

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    logging.info(f"Nightly job executed at {utc_timestamp}")
    
    try:
        # Get all configured leagues
        leagues = cosmos.query("leagues", "SELECT * FROM c")
        
        for league_doc in leagues:
            league_id = league_doc["leagueId"]
            logging.info(f"Processing league {league_id}")
            
            try:
                # Sync league data
                yc = YahooClient(league_id)
                week = yc.current_week()
                league_settings = yc.league_settings()
                
                # Update league settings
                league_doc["currentWeek"] = week
                league_doc["settings"] = league_settings
                cosmos.upsert("leagues", league_doc, partition=league_id)
                
                # Get teams and sync rosters
                teams = yc.teams()
                for team in teams:
                    team_id = team["team_id"]
                    
                    # Update team info
                    cosmos.upsert("teams", {
                        "id": f"team-{team_id}",
                        "leagueId": league_id,
                        "teamId": team_id,
                        "name": team["name"],
                        "manager": team.get("manager", "")
                    }, partition=league_id)
                    
                    # Get and store roster
                    roster = yc.roster(team_id, week)
                    cosmos.upsert("rosters", {
                        "id": f"roster-{team_id}-{week}",
                        "leagueId": league_id,
                        "teamId": team_id,
                        "week": week,
                        "players": roster
                    }, partition=team_id)
                
                # Process each team with a manager email
                managers = cosmos.query("managers", 
                                      "SELECT * FROM c WHERE c.leagueId = @leagueId",
                                      [{"name": "@leagueId", "value": league_id}])
                
                for manager in managers:
                    team_id = manager["teamId"]
                    email = manager["email"]
                    
                    try:
                        # Get team name
                        team_doc = cosmos.get_by_id("teams", f"team-{team_id}", partition=league_id)
                        team_name = team_doc.get("name", f"Team {team_id}") if team_doc else f"Team {team_id}"
                        
                        # Get roster
                        roster_doc = cosmos.get_by_id("rosters", f"roster-{team_id}-{week}", partition=team_id)
                        if not roster_doc:
                            logging.warning(f"No roster found for team {team_id} in league {league_id}")
                            continue
                        
                        # Build schedule
                        schedule = []
                        for player in roster_doc["players"]:
                            nhl_team = player.get("nhl_team", "UNK")
                            if nhl_team != "UNK":
                                week_start = datetime.date.today()
                                week_end = week_start + datetime.timedelta(days=7)
                                team_schedule = fetch_schedule(nhl_team, week_start, week_end)
                                schedule.extend(team_schedule)
                        
                        # Remove duplicates
                        schedule = list({game.get("gameId", f"{game.get('homeTeam', {}).get('abbrev', '')}-{game.get('awayTeam', {}).get('abbrev', '')}-{game.get('gameDate', '')}"): game for game in schedule}.values())
                        
                        # Compute guidance
                        today = datetime.date.today()
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
                        
                        # Render email
                        template_path = os.path.join(os.path.dirname(__file__), "..", "..", "engine", "templates", "email.html.j2")
                        with open(template_path, 'r') as f:
                            template = Template(f.read())
                        
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
                        message_id = send_gmail(email, subject, html)
                        
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
                        
                        logging.info(f"Sent guidance to {email} for team {team_id} (message: {message_id})")
                        
                    except Exception as e:
                        logging.error(f"Error processing team {team_id}: {str(e)}")
                        continue
                
                logging.info(f"Completed processing league {league_id}")
                
            except Exception as e:
                logging.error(f"Error processing league {league_id}: {str(e)}")
                continue
        
        logging.info("Nightly job completed successfully")
        
    except Exception as e:
        logging.error(f"Nightly job failed: {str(e)}")
        raise

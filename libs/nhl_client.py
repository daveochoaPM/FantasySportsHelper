
import requests, datetime as dt
from typing import List, Dict, Any, Optional
from libs import cosmos

API_WEB = "https://api-web.nhle.com/v1"

# NHL team code mapping (Yahoo team names to NHL codes)
TEAM_MAPPING = {
    "Anaheim Ducks": "ANA", "Arizona Coyotes": "ARI", "Boston Bruins": "BOS",
    "Buffalo Sabres": "BUF", "Calgary Flames": "CGY", "Carolina Hurricanes": "CAR",
    "Chicago Blackhawks": "CHI", "Colorado Avalanche": "COL", "Columbus Blue Jackets": "CBJ",
    "Dallas Stars": "DAL", "Detroit Red Wings": "DET", "Edmonton Oilers": "EDM",
    "Florida Panthers": "FLA", "Los Angeles Kings": "LAK", "Minnesota Wild": "MIN",
    "Montreal Canadiens": "MTL", "Nashville Predators": "NSH", "New Jersey Devils": "NJD",
    "New York Islanders": "NYI", "New York Rangers": "NYR", "Ottawa Senators": "OTT",
    "Philadelphia Flyers": "PHI", "Pittsburgh Penguins": "PIT", "San Jose Sharks": "SJS",
    "Seattle Kraken": "SEA", "St. Louis Blues": "STL", "Tampa Bay Lightning": "TBL",
    "Toronto Maple Leafs": "TOR", "Vancouver Canucks": "VAN", "Vegas Golden Knights": "VGK",
    "Washington Capitals": "WSH", "Winnipeg Jets": "WPG"
}

def season_code(today: dt.date) -> str:
    # ex: 20252026 for 2025-26
    if today.month >= 9:
        return f"{today.year}{today.year+1}"
    else:
        return f"{today.year-1}{today.year}"

def map_team_to_code(team_name: str) -> Optional[str]:
    """Map Yahoo team name to NHL team code"""
    return TEAM_MAPPING.get(team_name)

def cache_schedule(team_code: str, season: str) -> None:
    """Cache team schedule in Cosmos DB"""
    url = f"{API_WEB}/club-schedule-season/{team_code}/{season}"
    data = requests.get(url, timeout=15).json()
    
    schedule_doc = {
        "id": f"sched-{team_code}-{season}",
        "season": season,
        "teamCode": team_code,
        "games": data.get("games", [])
    }
    
    cosmos.upsert("schedules", schedule_doc, partition=season)

def fetch_schedule(nhl_team_code: str, start: dt.date, end: dt.date) -> List[Dict[str, Any]]:
    """Fetch and filter team schedule for date range with B2B detection"""
    season = season_code(start)
    
    # Try to get from cache first
    cached = cosmos.get_by_id("schedules", f"sched-{nhl_team_code}-{season}", partition=season)
    if cached:
        games = cached.get("games", [])
    else:
        # Cache if not found
        cache_schedule(nhl_team_code, season)
        cached = cosmos.get_by_id("schedules", f"sched-{nhl_team_code}-{season}", partition=season)
        games = cached.get("games", []) if cached else []
    
    # Filter to date range and add B2B flags
    filtered_games = []
    for game in games:
        game_date = dt.datetime.fromisoformat(game["gameDate"].replace("Z", "+00:00")).date()
        if start <= game_date <= end:
            # Add B2B flag (simplified: check if previous game was within 24 hours)
            b2b = False
            if filtered_games:
                prev_game_date = dt.datetime.fromisoformat(filtered_games[-1]["gameDate"].replace("Z", "+00:00")).date()
                if (game_date - prev_game_date).days == 1:
                    b2b = True
                    # Mark previous game as B2B too
                    if filtered_games:
                        filtered_games[-1]["backToBack"] = True
            
            game["backToBack"] = b2b
            filtered_games.append(game)
    
    return filtered_games


from typing import List, Dict, Any
import datetime as dt
from collections import defaultdict

THRESHOLDS = {"skater_gp": 8, "goalie_gs": 5}

def compute_guidance(roster: List[Dict[str, Any]], schedule: List[Dict[str, Any]],
                     current_splits: Dict[str, Any], last_splits: Dict[str, Any],
                     current_season: str, last_season: str, league_settings: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Compute fantasy guidance based on roster, schedule, and league scoring settings"""
    items = []
    
    # Extract scoring categories from league settings
    scoring_categories = []
    if league_settings and "categories" in league_settings:
        scoring_categories = list(league_settings["categories"].keys())
    
    # Group players by position
    players_by_pos = defaultdict(list)
    for player in roster:
        if player.get("status") == "active":
            pos = player.get("position", "UNKNOWN")
            players_by_pos[pos].append(player)
    
    # For each position, analyze game volume and make recommendations
    for position, players in players_by_pos.items():
        if len(players) < 2:  # Need at least 2 players to make start/bench decisions
            continue
            
        # Count games for each player in the target week
        player_games = {}
        for player in players:
            nhl_team = player.get("nhl_team", "UNK")
            if nhl_team != "UNK":
                # Count games for this player's NHL team
                team_games = [g for g in schedule if g.get("homeTeam", {}).get("abbrev") == nhl_team or 
                            g.get("awayTeam", {}).get("abbrev") == nhl_team]
                player_games[player["name"]] = {
                    "games": len(team_games),
                    "b2b_games": sum(1 for g in team_games if g.get("backToBack", False)),
                    "nhl_team": nhl_team
                }
        
        # Sort by game count (descending)
        sorted_players = sorted(player_games.items(), key=lambda x: x[1]["games"], reverse=True)
        
        if len(sorted_players) >= 2:
            # Recommend starting players with more games
            for i in range(len(sorted_players) - 1):
                player_in = sorted_players[i]
                player_out = sorted_players[i + 1]
                
                if player_in[1]["games"] > player_out[1]["games"]:
                    reason_parts = [f"{player_in[1]['games']} games vs {player_out[1]['games']}"]
                    
                    if player_in[1]["b2b_games"] > 0:
                        reason_parts.append(f"B2B games: {player_in[1]['b2b_games']}")
                    
                    # Add scoring-specific insights
                    if scoring_categories:
                        if "G" in scoring_categories and "A" in scoring_categories:
                            reason_parts.append("More games = more scoring opportunities")
                        elif "SOG" in scoring_categories:
                            reason_parts.append("More games = more shots on goal")
                        elif "HIT" in scoring_categories:
                            reason_parts.append("More games = more hits")
                        elif "BLK" in scoring_categories:
                            reason_parts.append("More games = more blocks")
                    
                    reason = "; ".join(reason_parts)
                    
                    items.append({
                        "type": "start_bench",
                        "playerIn": player_in[0],
                        "playerOut": player_out[0],
                        "reason": reason,
                        "sourceSeason": current_season,
                        "fallbackReason": None
                    })
    
    # Add general schedule insights
    total_games = len(schedule)
    b2b_games = sum(1 for g in schedule if g.get("backToBack", False))
    
    if b2b_games > 0:
        items.append({
            "type": "schedule_insight",
            "message": f"Week has {total_games} total games with {b2b_games} back-to-back games",
            "sourceSeason": current_season,
            "fallbackReason": None
        })
    
    return items

def tl_dr(items: List[Dict[str, Any]]) -> List[str]:
    """Generate TL;DR bullets from guidance items"""
    bullets = []
    for item in items:
        if item["type"] == "start_bench":
            bullets.append(f"Start {item['playerIn']} over {item['playerOut']} ({item['reason']})")
        elif item["type"] == "schedule_insight":
            bullets.append(item["message"])
    return bullets

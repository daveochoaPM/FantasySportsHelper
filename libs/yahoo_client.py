
from typing import Dict, Any, List
import os
import requests
from libs.providers.base import FantasyProvider
from libs import cosmos

class YahooClient(FantasyProvider):
    def __init__(self, league_id: str):
        self.league_id = league_id
        self._access_token = None
        self._refresh_token = None
        self._load_tokens()
    
    def _load_tokens(self):
        """Load OAuth tokens from Cosmos DB"""
        token_doc = cosmos.get_by_id("oauthTokens", "user-yahoo", partition="yahoo")
        if token_doc:
            self._access_token = token_doc.get("accessToken")
            self._refresh_token = token_doc.get("refreshToken")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for Yahoo API"""
        if not self._access_token:
            raise Exception("Yahoo OAuth not configured. Please authenticate first.")
        return {"Authorization": f"Bearer {self._access_token}"}
    
    def _make_request(self, url: str) -> Dict[str, Any]:
        """Make authenticated request to Yahoo API"""
        headers = self._get_auth_headers()
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def current_week(self) -> int:
        """Get current week of the season"""
        url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{self.league_id}"
        data = self._make_request(url)
        league = data["fantasy_content"]["league"][0]
        return int(league["current_week"])
    
    def league_settings(self) -> Dict[str, Any]:
        """Get league scoring settings and rules"""
        url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{self.league_id}/settings"
        data = self._make_request(url)
        settings = data["fantasy_content"]["league"][1]["settings"]
        
        # Extract scoring settings
        scoring_settings = {}
        for setting in settings:
            if setting.get("name") == "scoring_type":
                scoring_settings["type"] = setting.get("value")
            elif setting.get("name") == "scoring_settings":
                scoring_settings["categories"] = setting.get("value", {})
        
        return scoring_settings
    
    def teams(self) -> List[Dict[str, Any]]:
        """Get all teams in the league"""
        url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{self.league_id}/teams"
        data = self._make_request(url)
        teams = []
        for team_data in data["fantasy_content"]["league"][1]["teams"]:
            if "team" in team_data:
                team = team_data["team"][0]
                teams.append({
                    "team_id": team["team_id"],
                    "name": team["name"],
                    "manager": team.get("managers", [{}])[0].get("manager", {}).get("nickname", "")
                })
        return teams
    
    def roster(self, team_id: str, week: int) -> List[Dict[str, Any]]:
        """Get roster for a specific team and week"""
        url = f"https://fantasysports.yahooapis.com/fantasy/v2/team/{self.league_id}.t.{team_id}/roster;week={week}"
        data = self._make_request(url)
        roster = []
        
        if "roster" in data["fantasy_content"]["team"][1]:
            for player_data in data["fantasy_content"]["team"][1]["roster"]["0"]["players"]:
                if "player" in player_data:
                    player = player_data["player"][0]
                    # Extract NHL team code from eligible positions or player details
                    nhl_team = self._extract_nhl_team(player)
                    roster.append({
                        "player_id": player["player_id"],
                        "name": player["name"]["full"],
                        "position": player["display_position"],
                        "nhl_team": nhl_team,
                        "status": player.get("status", "active")
                    })
        return roster
    
    def _extract_nhl_team(self, player: Dict[str, Any]) -> str:
        """Extract NHL team code from player data"""
        # Try to get team from eligible positions
        if "eligible_positions" in player:
            for pos in player["eligible_positions"]:
                if "position" in pos and "team" in pos["position"]:
                    return pos["position"]["team"]
        
        # Fallback: try to extract from player name or other fields
        # This is a simplified mapping - in practice you'd want a more robust solution
        return "UNK"  # Unknown team

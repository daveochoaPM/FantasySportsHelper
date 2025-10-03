from abc import ABC, abstractmethod
from typing import List, Dict, Any

class FantasyProvider(ABC):
    """Base interface for fantasy sports providers"""
    
    @abstractmethod
    def current_week(self) -> int:
        """Get the current week of the season"""
        pass
    
    @abstractmethod
    def teams(self) -> List[Dict[str, Any]]:
        """Get all teams in the league"""
        pass
    
    @abstractmethod
    def roster(self, team_id: str, week: int) -> List[Dict[str, Any]]:
        """Get roster for a specific team and week"""
        pass

"""
Data Dragon service for fetching game static data (champions, items, runes)
"""
import requests
import json
from typing import Dict, Any
from ..config import Config


class DataDragonService:
    """Service to fetch and cache Data Dragon static data"""
    
    def __init__(self):
        self.version = Config.DDRAGON_VERSION
        self.base_url = Config.DDRAGON_DATA
        self._champions_cache = None
        self._items_cache = None
        self._runes_cache = None
        
    def get_champions(self) -> Dict[str, Any]:
        """Fetch all champions data from Data Dragon"""
        if self._champions_cache:
            return self._champions_cache
            
        url = f"{self.base_url}/champion.json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        self._champions_cache = data['data']
        return self._champions_cache
    
    def get_champion_detail(self, champion_id: str) -> Dict[str, Any]:
        """Fetch detailed champion data including abilities"""
        url = f"{self.base_url}/champion/{champion_id}.json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['data'][champion_id]
    
    def get_items(self) -> Dict[str, Any]:
        """Fetch all items data from Data Dragon"""
        if self._items_cache:
            return self._items_cache
            
        url = f"{self.base_url}/item.json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        self._items_cache = data['data']
        return self._items_cache
    
    def get_runes(self) -> Dict[str, Any]:
        """Fetch all runes/perks data from Data Dragon"""
        if self._runes_cache:
            return self._runes_cache
            
        url = f"{Config.DDRAGON_BASE}/data/en_US/runesReforged.json"
        response = requests.get(url)
        response.raise_for_status()
        self._runes_cache = response.json()
        return self._runes_cache
    
    def get_summoner_spells(self) -> Dict[str, Any]:
        """Fetch summoner spells data"""
        url = f"{self.base_url}/summoner.json"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()['data']


# Singleton instance
data_dragon = DataDragonService()


"""
Service for fetching and caching Data Dragon data across multiple patches
"""
import requests
from typing import Dict, Any
from .patch_manager import patch_manager


class MultiPatchDataService:
    """Service to fetch Data Dragon data for multiple patches"""
    
    def __init__(self):
        self.cache = {}  # {patch_version: {champions, items, runes}}
        
    def _get_cache_key(self, patch: str, data_type: str) -> str:
        """Generate cache key"""
        return f"{patch}:{data_type}"
    
    def get_champions_for_patch(self, patch: str) -> Dict[str, Any]:
        """Fetch champions data for a specific patch"""
        cache_key = self._get_cache_key(patch, 'champions')
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        ddragon_version = patch_manager.get_ddragon_version(patch)
        url = f"https://ddragon.leagueoflegends.com/cdn/{ddragon_version}/data/en_US/champion.json"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.cache[cache_key] = data['data']
            return self.cache[cache_key]
        except Exception as e:
            print(f"Error fetching champions for patch {patch}: {e}")
            return {}
    
    def get_champion_detail_for_patch(self, patch: str, champion_id: str) -> Dict[str, Any]:
        """Fetch detailed champion data for a specific patch"""
        cache_key = self._get_cache_key(patch, f'champion:{champion_id}')
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        ddragon_version = patch_manager.get_ddragon_version(patch)
        url = f"https://ddragon.leagueoflegends.com/cdn/{ddragon_version}/data/en_US/champion/{champion_id}.json"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            champion_data = data['data'][champion_id]
            self.cache[cache_key] = champion_data
            return champion_data
        except Exception as e:
            print(f"Error fetching {champion_id} detail for patch {patch}: {e}")
            return {}
    
    def get_items_for_patch(self, patch: str) -> Dict[str, Any]:
        """Fetch items data for a specific patch"""
        cache_key = self._get_cache_key(patch, 'items')
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        ddragon_version = patch_manager.get_ddragon_version(patch)
        url = f"https://ddragon.leagueoflegends.com/cdn/{ddragon_version}/data/en_US/item.json"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.cache[cache_key] = data['data']
            return self.cache[cache_key]
        except Exception as e:
            print(f"Error fetching items for patch {patch}: {e}")
            return {}
    
    def get_runes_for_patch(self, patch: str) -> Dict[str, Any]:
        """Fetch runes data for a specific patch"""
        cache_key = self._get_cache_key(patch, 'runes')
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        ddragon_version = patch_manager.get_ddragon_version(patch)
        url = f"https://ddragon.leagueoflegends.com/cdn/{ddragon_version}/data/en_US/runesReforged.json"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            self.cache[cache_key] = response.json()
            return self.cache[cache_key]
        except Exception as e:
            print(f"Error fetching runes for patch {patch}: {e}")
            return {}
    
    def clear_cache(self):
        """Clear the cache"""
        self.cache = {}


# Singleton instance
multi_patch_data = MultiPatchDataService()


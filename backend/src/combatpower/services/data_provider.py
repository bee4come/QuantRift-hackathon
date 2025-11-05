"""
Smart data provider that uses local cache when available, falls back to online fetch
"""
import os
from typing import Dict, Any

# Try to use local cache first, fall back to online fetch
USE_LOCAL_CACHE = os.path.exists('data/patches/metadata.json')

if USE_LOCAL_CACHE:
    print("Using local cached data")
    from .local_data_loader import local_data_loader as data_source
else:
    print("Using online Data Dragon (run fetch_and_cache_data.py to cache locally)")
    from .multi_patch_data import multi_patch_data as data_source


class DataProvider:
    """Unified data provider interface"""
    
    def __init__(self):
        self.source = data_source
    
    def get_champions_for_patch(self, patch: str) -> Dict[str, Any]:
        """Get champions data for a patch"""
        return self.source.get_champions_for_patch(patch)
    
    def get_champion_detail_for_patch(self, patch: str, champion_id: str) -> Dict[str, Any]:
        """Get detailed champion data for a patch"""
        return self.source.get_champion_detail_for_patch(patch, champion_id)
    
    def get_items_for_patch(self, patch: str) -> Dict[str, Any]:
        """Get items data for a patch"""
        return self.source.get_items_for_patch(patch)
    
    def get_runes_for_patch(self, patch: str) -> Dict[str, Any]:
        """Get runes data for a patch"""
        return self.source.get_runes_for_patch(patch)
    
    def is_using_local_cache(self) -> bool:
        """Check if using local cache"""
        return USE_LOCAL_CACHE


# Singleton instance
data_provider = DataProvider()


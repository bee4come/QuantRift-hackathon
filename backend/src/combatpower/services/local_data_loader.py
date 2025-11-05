"""
Load cached Data Dragon data from local files
"""
import os
import json
from typing import Dict, Any, Optional


class LocalDataLoader:
    """Load pre-cached Data Dragon data from local files"""
    
    def __init__(self, cache_dir='data/patches'):
        self.cache_dir = cache_dir
        self.memory_cache = {}
        
        # Check if cache directory exists
        if not os.path.exists(cache_dir):
            raise FileNotFoundError(
                f"Cache directory not found: {cache_dir}\n"
                f"Please run 'python fetch_and_cache_data.py' first to download data."
            )
    
    def get_champions_for_patch(self, patch: str) -> Dict[str, Any]:
        """Load champions data for a specific patch from local cache"""
        cache_key = f"{patch}:champions"
        
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        file_path = os.path.join(self.cache_dir, patch, 'champions.json')
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Champions data not found for patch {patch}: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.memory_cache[cache_key] = data['data']
        return data['data']
    
    def get_champion_detail_for_patch(self, patch: str, champion_id: str) -> Dict[str, Any]:
        """Load detailed champion data from local cache"""
        cache_key = f"{patch}:champion:{champion_id}"
        
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        file_path = os.path.join(self.cache_dir, patch, 'champions_detail', f'{champion_id}.json')
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Champion detail not found: {champion_id} in patch {patch}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        champion_data = data['data'][champion_id]
        self.memory_cache[cache_key] = champion_data
        return champion_data
    
    def get_items_for_patch(self, patch: str) -> Dict[str, Any]:
        """Load items data for a specific patch from local cache"""
        cache_key = f"{patch}:items"
        
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        file_path = os.path.join(self.cache_dir, patch, 'items.json')
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Items data not found for patch {patch}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.memory_cache[cache_key] = data['data']
        return data['data']
    
    def get_runes_for_patch(self, patch: str) -> Dict[str, Any]:
        """Load runes data for a specific patch from local cache"""
        cache_key = f"{patch}:runes"
        
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        file_path = os.path.join(self.cache_dir, patch, 'runes.json')
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Runes data not found for patch {patch}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.memory_cache[cache_key] = data
        return data
    
    def is_patch_cached(self, patch: str) -> bool:
        """Check if a patch has been cached locally"""
        patch_dir = os.path.join(self.cache_dir, patch)
        
        required_files = [
            os.path.join(patch_dir, 'champions.json'),
            os.path.join(patch_dir, 'items.json'),
            os.path.join(patch_dir, 'runes.json')
        ]
        
        return all(os.path.exists(f) for f in required_files)
    
    def get_cached_patches(self) -> list:
        """Get list of all cached patches"""
        if not os.path.exists(self.cache_dir):
            return []
        
        patches = []
        for item in os.listdir(self.cache_dir):
            item_path = os.path.join(self.cache_dir, item)
            if os.path.isdir(item_path) and self.is_patch_cached(item):
                patches.append(item)
        
        return sorted(patches)
    
    def clear_memory_cache(self):
        """Clear the in-memory cache"""
        self.memory_cache = {}


# Singleton instance
local_data_loader = LocalDataLoader()


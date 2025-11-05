"""
OP.GG Build Data Service
Fetches lane-specific builds for champions from OP.GG
"""
import requests
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta


class OPGGBuildService:
    """
    Service to fetch and cache lane-specific builds from OP.GG
    """
    
    def __init__(self):
        self.cache_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 
            'opgg_lane_builds.json'
        )
        self.cache = self._load_cache()
        self.base_url = "https://lol-web-api.op.gg/api/v1.0/internal/bypass"
        
    def _load_cache(self) -> Dict:
        """Load cached build data"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Save build data to cache"""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def get_champion_lane_build(
        self, 
        champion_name: str, 
        lane: str,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get lane-specific build for a champion
        
        Args:
            champion_name: Champion name (e.g., 'Yasuo')
            lane: Lane name ('TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT')
            force_refresh: Force fetch from OP.GG even if cached
            
        Returns:
            Dict with 'items', 'runes', 'primary_style', 'sub_style', 'skill_order'
        """
        cache_key = f"{champion_name}_{lane}"
        
        # Check cache
        if not force_refresh and cache_key in self.cache:
            cached_data = self.cache[cache_key]
            # Check if cache is less than 7 days old
            if 'timestamp' in cached_data:
                cache_time = datetime.fromisoformat(cached_data['timestamp'])
                if datetime.now() - cache_time < timedelta(days=7):
                    return cached_data.get('build')
        
        # Fetch from OP.GG
        build_data = self._fetch_from_opgg(champion_name, lane)
        
        if build_data:
            # Cache the result
            self.cache[cache_key] = {
                'build': build_data,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache()
        
        return build_data
    
    def _fetch_from_opgg(self, champion_name: str, lane: str) -> Optional[Dict[str, Any]]:
        """
        Fetch build data from OP.GG API
        
        Note: OP.GG API structure may change. This is a reference implementation.
        """
        try:
            # Convert lane to OP.GG format
            lane_mapping = {
                'TOP': 'top',
                'JUNGLE': 'jungle',
                'MID': 'mid',
                'ADC': 'adc',
                'SUPPORT': 'support'
            }
            opgg_lane = lane_mapping.get(lane, lane.lower())
            
            # Format champion name for OP.GG (lowercase, no spaces)
            opgg_champion = champion_name.lower().replace(' ', '')
            
            # Try to fetch champion stats
            url = f"{self.base_url}/champion-stats/analyze/{opgg_champion}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract lane-specific build
                if 'data' in data and opgg_lane in data['data']:
                    lane_data = data['data'][opgg_lane]
                    
                    # Extract items
                    items = []
                    if 'items' in lane_data and 'core' in lane_data['items']:
                        items = [item['id'] for item in lane_data['items']['core'][:6]]
                    
                    # Extract runes
                    runes = []
                    primary_style = None
                    sub_style = None
                    
                    if 'runes' in lane_data:
                        rune_data = lane_data['runes']
                        primary_style = rune_data.get('primary_style')
                        sub_style = rune_data.get('sub_style')
                        
                        # Get primary runes
                        if 'primary' in rune_data:
                            runes.extend([r['id'] for r in rune_data['primary']])
                        
                        # Get secondary runes
                        if 'secondary' in rune_data:
                            runes.extend([r['id'] for r in rune_data['secondary']])
                        
                        # Get stat shards
                        if 'shards' in rune_data:
                            runes.extend([s['id'] for s in rune_data['shards']])
                    
                    return {
                        'items': items,
                        'runes': runes,
                        'primary_style': primary_style,
                        'sub_style': sub_style,
                        'skill_order': lane_data.get('skill_order', []),
                        'win_rate': lane_data.get('win_rate', 0),
                        'pick_rate': lane_data.get('pick_rate', 0),
                        'ban_rate': lane_data.get('ban_rate', 0)
                    }
            
            print(f"Failed to fetch OP.GG data for {champion_name} {lane}: Status {response.status_code}")
            return None
            
        except Exception as e:
            print(f"Error fetching OP.GG data for {champion_name} {lane}: {e}")
            return None
    
    def get_all_lane_builds_for_champion(
        self, 
        champion_name: str, 
        lanes: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get builds for all specified lanes for a champion
        
        Args:
            champion_name: Champion name
            lanes: List of lane names
            
        Returns:
            Dict mapping lane -> build data
        """
        results = {}
        
        for lane in lanes:
            build = self.get_champion_lane_build(champion_name, lane)
            if build:
                results[lane] = build
        
        return results
    
    def refresh_all_cache(self, champions_data: Dict[str, Any]):
        """
        Refresh cache for all champions and their lanes
        This should be run periodically (e.g., weekly)
        """
        from .tier_system import tier_system
        
        print("Refreshing OP.GG build cache for all champions...")
        
        for champ_name, champ_data in champions_data.items():
            lanes = tier_system.classify_champion_lane(champ_data)
            
            for lane in lanes:
                print(f"Fetching {champ_name} - {lane}...")
                self.get_champion_lane_build(champ_name, lane, force_refresh=True)
        
        print("Cache refresh complete!")


# Global instance
opgg_builds = OPGGBuildService()


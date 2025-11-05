"""
Build Tracker Service
Extracts most popular 6-item builds from build_tracker_data.json
This provides real OP.GG data for combat power calculations
"""
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter


class BuildTrackerService:
    """
    Service to extract popular builds from build tracker data
    Provides the most popular 6-item builds and rune sets per champion
    """
    
    def __init__(self):
        self.data_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 
            'build_tracker_data.json'
        )
        self.build_data = self._load_build_data()
        self.valid_item_ids = self._load_valid_items()
    
    def _load_build_data(self) -> Dict[str, Any]:
        """Load build tracker data from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading build tracker data: {e}")
                return {}
        return {}
    
    def _load_valid_items(self) -> set:
        """Load valid item IDs from current patch"""
        try:
            from .data_dragon import data_dragon
            items_data = data_dragon.get_items()
            return {int(item_id) for item_id in items_data.keys()}
        except Exception as e:
            print(f"Warning: Could not load valid items: {e}")
        # Fallback to empty set (will disable validation)
        return set()
    
    def _validate_items(self, items: List[int]) -> bool:
        """Check if all items are valid in current patch"""
        if not self.valid_item_ids:
            return True  # Skip validation if we couldn't load valid items
        
        # Check if all items exist
        for item_id in items:
            if item_id not in self.valid_item_ids:
                return False
        
        # Check for duplicate boots (items with IDs in 3000-3999 range that are boots)
        boot_ids = {3006, 3009, 3020, 3047, 3111, 3117, 3158}  # Common boot IDs
        boot_count = sum(1 for item_id in items if item_id in boot_ids)
        if boot_count > 1:
            return False
        
        return True
    
    def get_most_popular_build(self, champion_name: str, patch: str = None) -> Optional[Dict[str, Any]]:
        """
        Get the most popular 6-item build for a champion
        
        Args:
            champion_name: Champion name (e.g., 'Yasuo')
            patch: Patch version (e.g., '14.19'). If None, uses latest available patch
            
        Returns:
            Dict with 'items', 'runes', 'primary_style', 'sub_style', 'pick_rate'
        """
        if not self.build_data:
            return None
        
        # Find the best patch to use
        target_patch = patch
        if not target_patch:
            # Use the latest patch available
            patches = [p for p in self.build_data.keys() if p != '_note' and p != '_last_updated']
            if patches:
                target_patch = sorted(patches)[-1]  # Latest patch
        
        if not target_patch or target_patch not in self.build_data:
            return None
        
        patch_data = self.build_data[target_patch]
        if champion_name not in patch_data:
            return None
        
        champion_data = patch_data[champion_name]
        
        # Get most popular item set (6 items)
        item_sets = champion_data.get('item_sets', {})
        if not item_sets:
            return None
        
        # Find the most popular item set
        most_popular_items = None
        max_games = 0
        
        for item_set_str, games_count in item_sets.items():
            if games_count > max_games:
                # Parse the item set string (e.g., "[3003, 3006, 3020, 3027, 3136, 3157]")
                try:
                    items = json.loads(item_set_str)
                    if len(items) == 6:  # Ensure it's a 6-item build
                        most_popular_items = items
                        max_games = games_count
                except:
                    continue
        
        if not most_popular_items:
            return None
        
        # Validate items are current and valid
        if not self._validate_items(most_popular_items):
            print(f"Invalid items for {champion_name}: {most_popular_items} - using fallback")
            return None
        
        # Get most popular rune set
        rune_sets = champion_data.get('rune_sets', {})
        most_popular_runes = None
        max_rune_games = 0
        
        for rune_set_str, games_count in rune_sets.items():
            if games_count > max_rune_games:
                # Parse rune set string (e.g., "8000_8400_[5002, 5008, 5008, 8010, 8014, 8242, 8473, 9104, 9111]")
                try:
                    parts = rune_set_str.split('_')
                    if len(parts) >= 3:
                        primary_style = int(parts[0])
                        sub_style = int(parts[1])
                        runes_str = '_'.join(parts[2:])
                        runes = json.loads(runes_str)
                        
                        most_popular_runes = {
                            'runes': runes,
                            'primary_style': primary_style,
                            'sub_style': sub_style
                        }
                        max_rune_games = games_count
                except:
                    continue
        
        # Calculate pick rate
        total_games = champion_data.get('total_games', 1)
        item_pick_rate = (max_games / total_games) * 100 if total_games > 0 else 0
        rune_pick_rate = (max_rune_games / total_games) * 100 if total_games > 0 else 0
        
        return {
            'items': most_popular_items,
            'runes': most_popular_runes['runes'] if most_popular_runes else [],
            'primary_style': most_popular_runes['primary_style'] if most_popular_runes else None,
            'sub_style': most_popular_runes['sub_style'] if most_popular_runes else None,
            'item_pick_rate': item_pick_rate,
            'rune_pick_rate': rune_pick_rate,
            'total_games': total_games,
            'patch': target_patch,
            'source': 'build_tracker'
        }
    
    def get_all_champions_builds(self, patch: str = None) -> Dict[str, Dict[str, Any]]:
        """
        Get most popular builds for all champions
        
        Args:
            patch: Patch version. If None, uses latest available patch
            
        Returns:
            Dict mapping champion names to their most popular builds
        """
        if not self.build_data:
            return {}
        
        # Find the best patch to use
        target_patch = patch
        if not target_patch:
            patches = [p for p in self.build_data.keys() if p != '_note' and p != '_last_updated']
            if patches:
                target_patch = sorted(patches)[-1]
        
        if not target_patch or target_patch not in self.build_data:
            return {}
        
        patch_data = self.build_data[target_patch]
        result = {}
        
        for champion_name in patch_data.keys():
            build = self.get_most_popular_build(champion_name, target_patch)
            if build:
                result[champion_name] = build
        
        return result
    
    def get_available_patches(self) -> List[str]:
        """Get list of available patches in the build data"""
        if not self.build_data:
            return []
        
        patches = [p for p in self.build_data.keys() if p != '_note' and p != '_last_updated']
        return sorted(patches)
    
    def get_champion_stats(self, champion_name: str, patch: str = None) -> Optional[Dict[str, Any]]:
        """
        Get build statistics for a champion
        
        Args:
            champion_name: Champion name
            patch: Patch version. If None, uses latest available patch
            
        Returns:
            Dict with build statistics
        """
        if not self.build_data:
            return None
        
        target_patch = patch
        if not target_patch:
            patches = [p for p in self.build_data.keys() if p != '_note' and p != '_last_updated']
            if patches:
                target_patch = sorted(patches)[-1]
        
        if not target_patch or target_patch not in self.build_data:
            return None
        
        patch_data = self.build_data[target_patch]
        if champion_name not in patch_data:
            return None
        
        champion_data = patch_data[champion_name]
        
        # Analyze item diversity
        item_sets = champion_data.get('item_sets', {})
        unique_builds = len(item_sets)
        
        # Get top 3 most popular builds
        top_builds = []
        for item_set_str, games_count in item_sets.items():
            try:
                items = json.loads(item_set_str)
                if len(items) == 6:
                    top_builds.append({
                        'items': items,
                        'games': games_count,
                        'pick_rate': (games_count / champion_data.get('total_games', 1)) * 100
                    })
            except:
                continue
        
        top_builds.sort(key=lambda x: x['games'], reverse=True)
        
        return {
            'champion': champion_name,
            'patch': target_patch,
            'total_games': champion_data.get('total_games', 0),
            'unique_builds': unique_builds,
            'top_builds': top_builds[:3],  # Top 3 builds
            'most_popular_build': self.get_most_popular_build(champion_name, target_patch)
        }


# Singleton instance
build_tracker_service = BuildTrackerService()

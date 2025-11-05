"""
Service for tracking and analyzing popular builds per champion per patch
"""
import json
import os
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from .patch_manager import patch_manager


class BuildTracker:
    """Tracks popular builds (items + runes) per champion per patch"""
    
    def __init__(self):
        self.builds = defaultdict(lambda: defaultdict(lambda: {
            'item_sets': defaultdict(int),
            'rune_sets': defaultdict(int),
            'total_games': 0
        }))
        self.data_file = 'data/build_tracker_data.json'
        self.load_data()
    
    def add_match(self, patch: str, champion: str, items: List[int], rune_ids: List[int], primary_style: int, sub_style: int):
        """
        Add a match to the build tracker
        
        Args:
            patch: Patch version
            champion: Champion name
            items: List of item IDs
            rune_ids: List of rune IDs
            primary_style: Primary rune path ID
            sub_style: Secondary rune path ID
        """
        # Filter out empty items and sort for consistency
        item_set = tuple(sorted([item for item in items if item > 0]))
        
        # Create rune signature
        rune_set = (primary_style, sub_style, tuple(sorted(rune_ids)))
        
        # Track this build
        self.builds[patch][champion]['item_sets'][item_set] += 1
        self.builds[patch][champion]['rune_sets'][rune_set] += 1
        self.builds[patch][champion]['total_games'] += 1
    
    def get_popular_build(self, patch: str, champion: str, min_games: int = 1) -> Dict[str, Any]:
        """
        Get the most popular build for a champion in a specific patch
        Now uses custom build manager for user-defined builds
        
        Args:
            patch: Patch version
            champion: Champion name
            min_games: Minimum games required (ignored, using custom builds)
            
        Returns:
            Dictionary with custom items and runes
        """
        # Import here to avoid circular imports
        from custom_build_manager import custom_build_manager
        
        custom_build = custom_build_manager.get_champion_build(champion, patch)
        
        return {
            'has_data': True,
            'items': custom_build['items'],
            'runes': custom_build['runes']['perk_ids'],
            'primary_style': custom_build['runes']['primary_style'],
            'sub_style': custom_build['runes']['sub_style'],
            'total_games': 1,  # Custom builds don't have game count
            'item_frequency': 1,
            'rune_frequency': 1,
            'item_pick_rate': 100.0,
            'rune_pick_rate': 100.0,
            'is_custom': True
        }
    
    def analyze_matches(self, matches: List[Dict[str, Any]], puuid: str) -> Dict[str, Any]:
        """
        Analyze matches and populate build data
        
        Args:
            matches: List of match data
            puuid: Player PUUID
            
        Returns:
            Statistics about builds per patch
        """
        patch_stats = defaultdict(lambda: {'games': 0, 'champions': set()})
        
        for match in matches:
            # Get match timestamp and determine patch
            timestamp = match['info']['gameCreation']
            patch = patch_manager.get_patch_for_timestamp(timestamp)
            
            # Find player data
            for participant in match['info']['participants']:
                if participant['puuid'] == puuid:
                    champion = participant['championName']
                    items = [
                        participant.get(f'item{i}', 0) 
                        for i in range(7)
                    ]
                    
                    # Get runes
                    perks = participant.get('perks', {})
                    styles = perks.get('styles', [])
                    
                    rune_ids = []
                    primary_style = None
                    sub_style = None
                    
                    if len(styles) >= 2:
                        primary_style = styles[0].get('style')
                        sub_style = styles[1].get('style')
                        
                        for style in styles:
                            for selection in style.get('selections', []):
                                rune_ids.append(selection.get('perk'))
                    
                    # Add to tracker
                    if primary_style and sub_style:
                        self.add_match(patch, champion, items, rune_ids, primary_style, sub_style)
                    
                    # Update stats
                    patch_stats[patch]['games'] += 1
                    patch_stats[patch]['champions'].add(champion)
                    break
        
        # Convert sets to counts
        result = {}
        for patch, stats in patch_stats.items():
            result[patch] = {
                'games': stats['games'],
                'unique_champions': len(stats['champions']),
                'champion_list': list(stats['champions'])
            }
        
        return result
    
    def save_data(self):
        """Save build data to JSON file"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            
            # Convert defaultdict to regular dict for JSON serialization
            export_data = {}
            for patch, patch_data in self.builds.items():
                export_data[patch] = {}
                for champion, champ_data in patch_data.items():
                    # Convert tuple keys to string keys for JSON serialization
                    item_sets = {}
                    for item_tuple, count in champ_data['item_sets'].items():
                        item_sets[str(list(item_tuple))] = count
                    
                    rune_sets = {}
                    for rune_tuple, count in champ_data['rune_sets'].items():
                        primary_style, sub_style, rune_ids = rune_tuple
                        rune_sets[f"{primary_style}_{sub_style}_{str(list(rune_ids))}"] = count
                    
                    export_data[patch][champion] = {
                        'item_sets': item_sets,
                        'rune_sets': rune_sets,
                        'total_games': champ_data['total_games']
                    }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving build data: {e}")
    
    def load_data(self):
        """Load build data from JSON file"""
        try:
            if not os.path.exists(self.data_file):
                return
            
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for patch, patch_data in data.items():
                for champion, champ_data in patch_data.items():
                    # Restore defaultdict structure
                    self.builds[patch][champion] = {
                        'item_sets': defaultdict(int),
                        'rune_sets': defaultdict(int),
                        'total_games': champ_data['total_games']
                    }
                    
                    # Restore item sets
                    for item_str, count in champ_data['item_sets'].items():
                        # Convert string back to tuple
                        item_list = eval(item_str)  # Convert "[1,2,3]" back to [1,2,3]
                        item_tuple = tuple(item_list)
                        self.builds[patch][champion]['item_sets'][item_tuple] = count
                    
                    # Restore rune sets
                    for rune_str, count in champ_data['rune_sets'].items():
                        # Parse "8000_8200_[8005,9111]" format
                        parts = rune_str.split('_')
                        if len(parts) >= 3:
                            primary_style = int(parts[0])
                            sub_style = int(parts[1])
                            rune_ids_str = '_'.join(parts[2:])
                            rune_ids = eval(rune_ids_str)  # Convert "[8005,9111]" back to [8005,9111]
                            rune_tuple = (primary_style, sub_style, tuple(rune_ids))
                            self.builds[patch][champion]['rune_sets'][rune_tuple] = count
                            
        except Exception as e:
            print(f"Error loading build data: {e}")


# Global instance for tracking builds across requests
build_tracker = BuildTracker()

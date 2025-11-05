"""
Patch-specific build overrides
Only tracks when champion builds ACTUALLY change between patches
Uses smart fallback to most recent available build data
"""
from typing import Dict, List, Any, Optional
from datetime import datetime


class PatchSpecificBuilds:
    """
    Smart system for tracking patch-specific build changes
    
    Instead of storing every build for every patch, we only store:
    1. Base/current meta builds (in meta_builds.py)
    2. Patch-specific OVERRIDES when builds change
    3. Smart fallback logic to find the right build for any patch
    
    Example:
    - Draven uses IE/BT/PD build from 14.19 to 14.23
    - In patch 14.24, he switches to Lethality build (OVERRIDE)
    - In patch 25.S1.1, he switches back to Crit (OVERRIDE)
    - All other patches use the base build
    """
    
    def __init__(self):
        """
        Initialize patch-specific build overrides
        
        Format:
        {
            'ChampionName': {
                'patch_version': {
                    'items': [item_ids],
                    'runes': [rune_ids],
                    'primary_style': int,
                    'sub_style': int,
                    'reason': 'Why this build changed'
                }
            }
        }
        """
        self.patch_overrides = {
            # Example: Draven build changes
            'Draven': {
                '14.24': {
                    'items': [3142, 6676, 3814, 6691, 3036, 3111],  # Switched to Lethality
                    'runes': [8112, 8139, 8138, 8135, 8234, 8237, 5008, 5008, 5002],  # Electrocute
                    'primary_style': 8100,
                    'sub_style': 8200,
                    'reason': 'Crit items nerfed, Lethality became meta'
                },
                '25.S1.1': {
                    'items': [3031, 3072, 3046, 3094, 3508, 3006],  # Back to Crit
                    'runes': [8010, 9111, 9104, 8014, 8473, 8242, 5008, 5008, 5002],  # Conqueror
                    'primary_style': 8000,
                    'sub_style': 8400,
                    'reason': 'Crit items buffed, returned to traditional build'
                }
            },
            
            # Example: Tank item rework affects all tanks
            'Ornn': {
                '14.20': {
                    'items': [3068, 3075, 3143, 3065, 3110, 3047],  # Added Frozen Heart
                    'runes': [8437, 8401, 8473, 8242, 9111, 8014, 5008, 5002, 5002],
                    'primary_style': 8400,
                    'sub_style': 8000,
                    'reason': 'Frozen Heart buffed, became core item'
                }
            },
            
            # Add more patch-specific overrides as needed
            # These can be populated from:
            # 1. Manual tracking of major patch changes
            # 2. API calls to U.GG / OP.GG / Lolalytics
            # 3. Automated patch note parsing
            # 4. Community data aggregation
        }
        
        # Track which patches have significant meta shifts (for bulk updates)
        self.meta_shift_patches = {
            '14.20': 'Tank item rework',
            '14.24': 'ADC item changes',
            '25.S1.1': 'Season 2025 start - major balance changes',
            '25.04': 'Mid-season update'
        }
    
    def get_build_for_patch(
        self, 
        champion_name: str, 
        patch: str, 
        base_build: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get the correct build for a champion in a specific patch
        
        Logic:
        1. Check if there's a patch-specific override for this exact patch
        2. If not, find the most recent override before this patch
        3. If no overrides exist, use base build
        
        Args:
            champion_name: Champion name
            patch: Patch version (e.g., '14.24')
            base_build: Default/current meta build from meta_builds.py
            
        Returns:
            Build dictionary with items and runes
        """
        # No overrides for this champion, use base build
        if champion_name not in self.patch_overrides:
            return base_build
        
        champion_patches = self.patch_overrides[champion_name]
        
        # Exact match for this patch
        if patch in champion_patches:
            override = champion_patches[patch].copy()
            override['role'] = base_build.get('role', 'Unknown')
            override['notes'] = override.get('reason', 'Patch-specific build')
            return override
        
        # Find most recent override before this patch
        # This handles cases where a build change persists across multiple patches
        from .patch_manager import patch_manager
        
        try:
            all_patches = patch_manager.get_all_patches()
            current_patch_index = all_patches.index(patch)
            
            # Look backwards through patches for the most recent override
            for i in range(current_patch_index - 1, -1, -1):
                previous_patch = all_patches[i]
                if previous_patch in champion_patches:
                    override = champion_patches[previous_patch].copy()
                    override['role'] = base_build.get('role', 'Unknown')
                    override['notes'] = f"Build from {previous_patch}: {override.get('reason', 'N/A')}"
                    return override
        except (ValueError, IndexError):
            pass
        
        # No relevant overrides found, use base build
        return base_build
    
    def add_patch_override(
        self,
        champion_name: str,
        patch: str,
        items: List[int],
        runes: List[int],
        primary_style: int,
        sub_style: int,
        reason: str = ""
    ):
        """Add a new patch-specific override"""
        if champion_name not in self.patch_overrides:
            self.patch_overrides[champion_name] = {}
        
        self.patch_overrides[champion_name][patch] = {
            'items': items,
            'runes': runes,
            'primary_style': primary_style,
            'sub_style': sub_style,
            'reason': reason
        }
    
    def get_build_changes_summary(self, champion_name: str) -> Dict[str, str]:
        """Get a summary of all build changes for a champion across patches"""
        if champion_name not in self.patch_overrides:
            return {}
        
        return {
            patch: data.get('reason', 'Build changed')
            for patch, data in self.patch_overrides[champion_name].items()
        }
    
    def list_champions_with_overrides(self) -> List[str]:
        """Get list of champions that have patch-specific overrides"""
        return list(self.patch_overrides.keys())
    
    def export_for_api_integration(self) -> str:
        """
        Export instructions for integrating with build data APIs
        
        This provides guidance on how to populate patch-specific builds
        from external sources like U.GG, OP.GG, or Lolalytics
        """
        return """
        API Integration Guide for Automated Build Data
        ===============================================
        
        Instead of manually tracking every build change, you can:
        
        1. **U.GG API** (https://u.gg/api)
           - Provides champion builds by patch
           - High quality data with pick rates
           - Example: GET /lol/champions/{champion_id}/builds?patch={patch}
        
        2. **OP.GG** (Web scraping or unofficial API)
           - Korean data, often ahead of meta
           - Champion builds with runes and items
        
        3. **Lolalytics** (https://lolalytics.com)
           - Historical data by patch
           - Can export build data programmatically
        
        4. **Community Dragon** (Riot's unofficial CDN)
           - Has some meta game data
           - Not build-specific but item popularity
        
        5. **Riot Match API**
           - Analyze actual player builds from high ELO matches
           - Calculate most popular builds per patch
           - More accurate but requires more processing
        
        Implementation Example:
        ```python
        def fetch_builds_from_ugg(champion_name, patch):
            # Call U.GG API
            # Parse response
            # Return items + runes
            
        def update_patch_overrides():
            for patch in new_patches:
                for champion in all_champions:
                    build = fetch_builds_from_ugg(champion, patch)
                    if build != previous_build:
                        add_patch_override(champion, patch, build.items, ...)
        ```
        """


# Singleton instance
patch_specific_builds = PatchSpecificBuilds()


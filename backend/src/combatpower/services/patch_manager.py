"""
Patch management system for tracking patch releases and mapping matches to patches
"""
from datetime import datetime
from typing import Dict, List, Optional


class PatchManager:
    """Manages patch versions and their release dates"""
    
    # Patch release dates (using user's preferred naming)
    PATCH_DATES = {
        # 2024 Season patches (14.1 - 14.24)
        '14.1': datetime(2024, 1, 10),
        '14.2': datetime(2024, 1, 24),
        '14.3': datetime(2024, 2, 7),
        '14.4': datetime(2024, 2, 21),
        '14.5': datetime(2024, 3, 6),
        '14.6': datetime(2024, 3, 20),
        '14.7': datetime(2024, 4, 3),
        '14.8': datetime(2024, 4, 17),
        '14.9': datetime(2024, 5, 1),
        '14.10': datetime(2024, 5, 15),
        '14.11': datetime(2024, 5, 29),
        '14.12': datetime(2024, 6, 12),
        '14.13': datetime(2024, 6, 26),
        '14.14': datetime(2024, 7, 17),
        '14.15': datetime(2024, 7, 31),
        '14.16': datetime(2024, 8, 14),
        '14.17': datetime(2024, 8, 28),
        '14.18': datetime(2024, 9, 11),
        '14.19': datetime(2024, 9, 24),
        '14.20': datetime(2024, 10, 8),
        '14.21': datetime(2024, 10, 22),
        '14.22': datetime(2024, 11, 5),
        '14.23': datetime(2024, 11, 19),
        '14.24': datetime(2024, 12, 10),
        '25.S1.1': datetime(2025, 1, 7),
        '25.S1.2': datetime(2025, 1, 22),
        '2025.S1.3': datetime(2025, 2, 5),
        '25.04': datetime(2025, 2, 19),
        '25.05': datetime(2025, 3, 4),
        '25.06': datetime(2025, 3, 18),
        '25.07': datetime(2025, 4, 1),
        '25.08': datetime(2025, 4, 15),
        '25.09': datetime(2025, 4, 29),
        '25.10': datetime(2025, 5, 13),
        '25.11': datetime(2025, 5, 27),
        '25.12': datetime(2025, 6, 10),
        '25.13': datetime(2025, 6, 24),
        '25.14': datetime(2025, 7, 15),
        '25.15': datetime(2025, 7, 29),
        '25.16': datetime(2025, 8, 12),
        '25.17': datetime(2025, 8, 26),
        '25.18': datetime(2025, 9, 10),
        '25.19': datetime(2025, 9, 23),
        '25.20': datetime(2025, 10, 7),
    }
    
    # Map user's patch names to Data Dragon versions
    DDRAGON_VERSIONS = {
        '14.1': '14.1.1',
        '14.2': '14.2.1',
        '14.3': '14.3.1',
        '14.4': '14.4.1',
        '14.5': '14.5.1',
        '14.6': '14.6.1',
        '14.7': '14.7.1',
        '14.8': '14.8.1',
        '14.9': '14.9.1',
        '14.10': '14.10.1',
        '14.11': '14.11.1',
        '14.12': '14.12.1',
        '14.13': '14.13.1',
        '14.14': '14.14.1',
        '14.15': '14.15.1',
        '14.16': '14.16.1',
        '14.17': '14.17.1',
        '14.18': '14.18.1',
        '14.19': '14.19.1',
        '14.20': '14.20.1',
        '14.21': '14.21.1',
        '14.22': '14.22.1',
        '14.23': '14.23.1',
        '14.24': '14.24.1',
        '25.S1.1': '15.1.1',
        '25.S1.2': '15.2.1',
        '2025.S1.3': '15.3.1',
        '25.04': '15.4.1',
        '25.05': '15.5.1',
        '25.06': '15.6.1',
        '25.07': '15.7.1',
        '25.08': '15.8.1',
        '25.09': '15.9.1',
        '25.10': '15.10.1',
        '25.11': '15.11.1',
        '25.12': '15.12.1',
        '25.13': '15.13.1',
        '25.14': '15.14.1',
        '25.15': '15.15.1',
        '25.16': '15.16.1',
        '25.17': '15.17.1',
        '25.18': '15.18.1',
        '25.19': '15.19.1',
        '25.20': '15.20.1',
    }
    
    def __init__(self):
        # Sort patches by date for easy lookup
        self.sorted_patches = sorted(
            self.PATCH_DATES.items(),
            key=lambda x: x[1]
        )
    
    def get_patch_for_timestamp(self, timestamp_ms: int) -> str:
        """
        Get the patch version for a given match timestamp
        
        Args:
            timestamp_ms: Match timestamp in milliseconds
            
        Returns:
            Patch version string (e.g., '14.19')
        """
        match_date = datetime.fromtimestamp(timestamp_ms / 1000)
        
        # Find the patch active at this date
        for i in range(len(self.sorted_patches) - 1, -1, -1):
            patch_version, patch_date = self.sorted_patches[i]
            if match_date >= patch_date:
                return patch_version
        
        # If before all known patches, return the earliest
        return self.sorted_patches[0][0]
    
    def get_ddragon_version(self, patch: str) -> str:
        """
        Get the Data Dragon version for a patch
        
        Args:
            patch: Patch version (e.g., '14.19')
            
        Returns:
            Data Dragon version (e.g., '14.19.1')
        """
        return self.DDRAGON_VERSIONS.get(patch, f"{patch}.1")
    
    def get_patch_date(self, patch: str) -> Optional[datetime]:
        """Get the release date for a patch"""
        return self.PATCH_DATES.get(patch)
    
    def get_patches_in_range(self, start_date: datetime, end_date: datetime) -> List[str]:
        """
        Get all patches released within a date range
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of patch versions
        """
        patches = []
        for patch, patch_date in self.sorted_patches:
            if start_date <= patch_date <= end_date:
                patches.append(patch)
        return patches
    
    def get_all_patches(self) -> List[str]:
        """Get all available patch versions"""
        return [patch for patch, _ in self.sorted_patches]


# Singleton instance
patch_manager = PatchManager()


"""
Patch Mapping System

Provides temporal mapping for patch versions to support time-based queries.
Enhanced to work with DDragon version data for accurate patch timing.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PatchInfo:
    """Information about a specific patch version"""
    version: str
    release_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    season: Optional[int] = None
    major_changes: Optional[List[str]] = None
    notes: Optional[str] = None

class PatchMapper:
    """Maps timestamps to appropriate patch versions"""

    def __init__(self, ddragon_loader=None):
        """Initialize patch mapper with DDragon integration"""

        # Import DDragon loader
        if ddragon_loader is None:
            try:
                from .ddragon_loader import ddragon
                self.ddragon = ddragon
                logger.info("DDragon loader integrated for patch mapping")
            except ImportError:
                logger.warning("DDragon loader not available for patch mapping")
                self.ddragon = None
        else:
            self.ddragon = ddragon_loader

        self.patches: Dict[str, PatchInfo] = {}
        self._load_patch_timeline()

    def get_patch_for_timestamp(self, timestamp: Union[str, datetime]) -> str:
        """Get appropriate patch version for a given timestamp"""

        if isinstance(timestamp, str):
            try:
                # Handle various timestamp formats
                if timestamp.endswith('Z'):
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    dt = datetime.fromisoformat(timestamp)
            except ValueError:
                logger.warning(f"Could not parse timestamp: {timestamp}")
                return self.get_latest_patch()
        else:
            dt = timestamp

        # Convert to naive datetime for comparison
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        # Simple date-based mapping for now
        if dt >= datetime(2025, 1, 1):
            return "15.1.1"
        elif dt >= datetime(2024, 11, 20):
            return "14.23.1"
        elif dt >= datetime(2024, 10, 1):
            return "14.20.1"
        elif dt >= datetime(2024, 7, 1):
            return "14.14.1"
        else:
            return "14.10.1"

    def get_latest_patch(self) -> str:
        """Get the latest available patch version"""
        if self.ddragon:
            return self.ddragon.get_latest_version()
        return "15.1.1"

    def _load_patch_timeline(self) -> None:
        """Load patch timeline data"""
        # Simplified for now
        pass


# Global instance for convenience
patch_mapper = PatchMapper()
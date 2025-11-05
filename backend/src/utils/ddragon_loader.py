"""
DDragon Data Loader

Provides standardized access to DDragon champion and item data across patches.
Replaces hardcoded data with real game values for accurate quantitative analysis.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from functools import lru_cache

logger = logging.getLogger(__name__)

class DDragonLoader:
    """Loads and provides access to DDragon champion and item data"""

    def __init__(self, data_path: str = "/home/zty/rift_rewind/experiment/data/ddragon"):
        """Initialize DDragon loader with data path"""
        self.data_path = Path(data_path)
        self._all_data = None
        self._version_list = None
        self._load_summary()

    def _load_summary(self) -> None:
        """Load summary information about available versions"""
        summary_path = self.data_path / "summary.json"
        if summary_path.exists():
            with open(summary_path, 'r') as f:
                summary = json.load(f)
                self._version_list = summary.get("versions", [])
                logger.info(f"Loaded DDragon summary: {summary['total_versions']} versions available")
        else:
            logger.warning("DDragon summary.json not found, will discover versions dynamically")

    @property
    @lru_cache(maxsize=1)
    def all_data(self) -> Dict[str, Any]:
        """Lazy load all versions data"""
        if self._all_data is None:
            all_data_path = self.data_path / "all_versions_data.json"
            if all_data_path.exists():
                with open(all_data_path, 'r') as f:
                    self._all_data = json.load(f)
                logger.info(f"Loaded all_versions_data.json with {len(self._all_data)} versions")
            else:
                logger.error("all_versions_data.json not found!")
                self._all_data = {}
        return self._all_data

    def get_available_versions(self) -> List[str]:
        """Get list of available patch versions"""
        if self._version_list:
            return self._version_list
        return list(self.all_data.keys())

    def get_latest_version(self) -> str:
        """Get the latest available patch version"""
        versions = self.get_available_versions()
        if versions:
            return versions[0]  # Versions are sorted in descending order
        return "14.23.1"  # Fallback

    def version_exists(self, version: str) -> bool:
        """Check if a specific version exists in the data"""
        return version in self.all_data

    def get_champion_data(self, version: str = None) -> Dict[str, Any]:
        """Get champion data for a specific version"""
        if version is None:
            version = self.get_latest_version()

        if version not in self.all_data:
            logger.warning(f"Version {version} not found, using latest available")
            version = self.get_latest_version()

        version_data = self.all_data.get(version, {})
        champions = version_data.get("champions", {})

        if isinstance(champions, dict) and "data" in champions:
            return champions["data"]
        return champions

    def get_item_data(self, version: str = None) -> Dict[str, Any]:
        """Get item data for a specific version"""
        if version is None:
            version = self.get_latest_version()

        if version not in self.all_data:
            logger.warning(f"Version {version} not found, using latest available")
            version = self.get_latest_version()

        version_data = self.all_data.get(version, {})
        items = version_data.get("items", {})

        if isinstance(items, dict) and "data" in items:
            return items["data"]
        return items

    def get_champion_by_id(self, champion_id: Union[int, str], version: str = None) -> Optional[Dict[str, Any]]:
        """Get specific champion data by ID or key"""
        champions = self.get_champion_data(version)

        # Try by key (string ID like "266" for Aatrox)
        champion_id_str = str(champion_id)
        for champ_name, champ_data in champions.items():
            if champ_data.get("key") == champion_id_str:
                return champ_data

        # Try by name if it's a string
        if isinstance(champion_id, str) and champion_id in champions:
            return champions[champion_id]

        logger.warning(f"Champion with ID/key {champion_id} not found")
        return None

    def get_champion_by_name(self, champion_name: str, version: str = None) -> Optional[Dict[str, Any]]:
        """Get champion data by name"""
        champions = self.get_champion_data(version)
        return champions.get(champion_name)

    def get_item_by_id(self, item_id: Union[int, str], version: str = None) -> Optional[Dict[str, Any]]:
        """Get specific item data by ID"""
        items = self.get_item_data(version)
        item_id_str = str(item_id)
        return items.get(item_id_str)

    def get_champion_stats(self, champion_id: Union[int, str], version: str = None) -> Dict[str, float]:
        """Get champion base stats"""
        champion = self.get_champion_by_id(champion_id, version)
        if not champion:
            return {}

        stats = champion.get("stats", {})
        return {
            "hp": stats.get("hp", 0),
            "hp_per_level": stats.get("hpperlevel", 0),
            "mp": stats.get("mp", 0),
            "mp_per_level": stats.get("mpperlevel", 0),
            "attack_damage": stats.get("attackdamage", 0),
            "attack_damage_per_level": stats.get("attackdamageperlevel", 0),
            "armor": stats.get("armor", 0),
            "armor_per_level": stats.get("armorperlevel", 0),
            "magic_resistance": stats.get("spellblock", 0),
            "magic_resistance_per_level": stats.get("spellblockperlevel", 0),
            "attack_speed": stats.get("attackspeed", 0),
            "attack_speed_per_level": stats.get("attackspeedperlevel", 0),
            "movement_speed": stats.get("movespeed", 0),
            "attack_range": stats.get("attackrange", 0),
            "hp_regen": stats.get("hpregen", 0),
            "hp_regen_per_level": stats.get("hpregenperlevel", 0),
            "mp_regen": stats.get("mpregen", 0),
            "mp_regen_per_level": stats.get("mpregenperlevel", 0),
            "crit": stats.get("crit", 0),
            "crit_per_level": stats.get("critperlevel", 0)
        }

    def get_item_stats(self, item_id: Union[int, str], version: str = None) -> Dict[str, float]:
        """Get item stats in standardized format"""
        item = self.get_item_by_id(item_id, version)
        if not item:
            return {}

        stats = item.get("stats", {})

        # Standardize stat names to common format
        standardized = {}

        # Map DDragon stat names to standardized names
        stat_mappings = {
            "FlatHPPoolMod": "health",
            "FlatMPPoolMod": "mana",
            "FlatPhysicalDamageMod": "attack_damage",
            "FlatMagicDamageMod": "ability_power",
            "FlatArmorMod": "armor",
            "FlatSpellBlockMod": "magic_resistance",
            "FlatCritChanceMod": "critical_strike_chance",
            "FlatMovementSpeedMod": "movement_speed",
            "PercentAttackSpeedMod": "attack_speed",
            "PercentLifeStealMod": "life_steal",
            "FlatSpellVampMod": "omnivamp",
            "PercentMovementSpeedMod": "movement_speed_percent"
        }

        for ddragon_stat, value in stats.items():
            std_name = stat_mappings.get(ddragon_stat, ddragon_stat.lower())
            standardized[std_name] = float(value)

        return standardized

    def get_item_cost(self, item_id: Union[int, str], version: str = None) -> Dict[str, int]:
        """Get item cost information"""
        item = self.get_item_by_id(item_id, version)
        if not item:
            return {"total": 0, "base": 0, "sell": 0}

        gold = item.get("gold", {})
        return {
            "total": gold.get("total", 0),
            "base": gold.get("base", 0),
            "sell": gold.get("sell", 0),
            "purchasable": gold.get("purchasable", True)
        }

    def find_patch_by_timestamp(self, timestamp: Union[str, datetime]) -> str:
        """Find appropriate patch version for a given timestamp"""
        # This is a simplified implementation
        # In a real system, you'd want patch_mappings.json with release dates

        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                # Fallback to latest version if parsing fails
                return self.get_latest_version()
        else:
            dt = timestamp

        # Simple heuristic based on date ranges
        # This should be replaced with real patch timeline data
        if dt.year == 2024:
            if dt.month >= 11:
                return "14.23.1"
            elif dt.month >= 10:
                return "14.20.1"
            elif dt.month >= 9:
                return "14.18.1"
            elif dt.month >= 7:
                return "14.14.1"
            else:
                return "14.10.1"
        else:
            return self.get_latest_version()

    def get_champion_list(self, version: str = None) -> List[Dict[str, Any]]:
        """Get list of all champions with basic info"""
        champions = self.get_champion_data(version)

        result = []
        for name, data in champions.items():
            result.append({
                "id": data.get("key"),
                "name": name,
                "title": data.get("title", ""),
                "tags": data.get("tags", []),
                "difficulty": data.get("info", {}).get("difficulty", 1)
            })

        return sorted(result, key=lambda x: x["name"])

    def get_item_list(self, version: str = None,
                     include_consumables: bool = False,
                     include_trinkets: bool = False) -> List[Dict[str, Any]]:
        """Get list of all items with basic info"""
        items = self.get_item_data(version)

        result = []
        for item_id, data in items.items():
            # Filter out consumables and trinkets if requested
            tags = data.get("tags", [])
            maps_info = data.get("maps", {})

            # Skip if consumable/trinket filtering is enabled
            if not include_consumables and "Consumable" in tags:
                continue
            if not include_trinkets and "Trinket" in tags:
                continue

            # Skip if not available on Summoner's Rift (map 11)
            if not maps_info.get("11", True):
                continue

            gold = data.get("gold", {})
            result.append({
                "id": int(item_id),
                "name": data.get("name", ""),
                "description": data.get("plaintext", ""),
                "tags": tags,
                "cost": gold.get("total", 0),
                "purchasable": gold.get("purchasable", True)
            })

        return sorted(result, key=lambda x: x["name"])


# Global instance for convenience
ddragon = DDragonLoader()
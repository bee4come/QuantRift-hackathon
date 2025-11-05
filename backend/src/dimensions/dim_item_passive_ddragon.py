#!/usr/bin/env python3
"""
DimItemPassive: Enhanced dimension table for item statistics using DDragon

Provides real item stats and gold efficiency calculations.
Enhanced to use actual DDragon item data instead of hardcoded approximations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
from utils import generate_row_id, format_output_precision

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ItemStats:
    """Enhanced item statistics record with DDragon integration"""
    item_id: int
    item_name: str
    cost: int
    stats: Dict[str, float]
    passive_effects: List[str]
    item_class: str
    valid_from_patch: str
    valid_to_patch: Optional[str] = None
    notes: Optional[str] = None

    # Enhanced with DDragon data
    description: Optional[str] = None
    plaintext: Optional[str] = None
    tags: Optional[List[str]] = None
    gold_info: Optional[Dict[str, Any]] = None
    validated_with_ddragon: bool = False

class DimItemPassive:
    """Manages item statistics enhanced with DDragon item data"""

    def __init__(self, ddragon_loader=None):
        """Initialize with item stat mappings and DDragon integration"""
        self.items = {}

        # Import DDragon loader
        if ddragon_loader is None:
            try:
                from ..utils.ddragon_loader import ddragon
                self.ddragon = ddragon
                logger.info("DDragon loader integrated successfully")
            except ImportError:
                logger.warning("DDragon loader not available, using fallback data")
                self.ddragon = None
        else:
            self.ddragon = ddragon_loader

        self._load_enhanced_items()

    def _get_appropriate_patch(self) -> str:
        """Get appropriate patch version based on DDragon availability"""
        if self.ddragon:
            return self.ddragon.get_latest_version()
        return "14.23.1"  # Fallback

    def _load_top_50_items(self) -> List[int]:
        """Load the top 50 items list"""
        top_items_file = Path(__file__).parent / "top_50_items.json"

        if top_items_file.exists():
            with open(top_items_file, 'r') as f:
                top_data = json.load(f)
            return [item['item_id'] for item in top_data['top_items']]
        else:
            logger.warning("Top 50 items file not found, using comprehensive item list")
            # Return common item IDs if file doesn't exist
            return [
                3364, 3363, 1055, 3340, 3158, 1082, 3006, 3047, 2055, 1056,
                3031, 3078, 3869, 1036, 3111, 3107, 3020, 6610, 3171, 6692,
                1058, 3152, 3190, 3009, 3161, 1052, 6672, 6653, 3071, 3877,
                3142, 3067, 3040, 3089, 1054, 4645, 1028, 3042, 6676, 3032,
                4628, 3157, 6655, 3153, 1018, 6333, 3870, 3036, 2503, 3115
            ]

    def _classify_item(self, item_data: Dict[str, Any]) -> str:
        """Classify item based on DDragon tags and cost"""
        tags = item_data.get("tags", [])
        gold = item_data.get("gold", {})
        cost = gold.get("total", 0)

        if "Trinket" in tags:
            return "trinket"
        elif "Consumable" in tags:
            return "consumable"
        elif "Boots" in tags:
            return "boots"
        elif cost >= 3000:
            return "legendary"
        elif cost >= 1200:
            return "epic"
        elif cost > 0:
            return "basic"
        else:
            return "other"

    def _extract_passive_effects(self, item_data: Dict[str, Any]) -> List[str]:
        """Extract passive effects from item description"""
        description = item_data.get("description", "").lower()
        passive_effects = []

        # Pattern matching for common passive effects
        if "unique" in description and "passive" in description:
            if "damage" in description:
                passive_effects.append("damage_passive")
            if "heal" in description or "life steal" in description:
                passive_effects.append("healing_passive")
            if "shield" in description:
                passive_effects.append("shield_passive")
            if "movement speed" in description:
                passive_effects.append("movement_passive")
            if "cooldown" in description:
                passive_effects.append("cooldown_passive")

        # Specific item passive detection
        item_name = item_data.get("name", "").lower()
        if "infinity edge" in item_name:
            passive_effects.append("crit_damage_amplification")
        elif "trinity force" in item_name:
            passive_effects.append("spellblade")
        elif "zhonya" in item_name:
            passive_effects.append("stasis_active")
        elif "guardian angel" in item_name:
            passive_effects.append("revive_passive")

        return passive_effects if passive_effects else ["unknown"]

    def _load_enhanced_items(self) -> None:
        """Load item data enhanced with DDragon information"""
        patch_version = self._get_appropriate_patch()
        top_item_ids = self._load_top_50_items()

        if not self.ddragon:
            logger.warning("DDragon not available, creating minimal item data")
            self._create_fallback_items(top_item_ids)
            return

        # Get DDragon item data
        ddragon_items = self.ddragon.get_item_data(patch_version)
        if not ddragon_items:
            logger.error("No DDragon item data available")
            self._create_fallback_items(top_item_ids)
            return

        logger.info(f"Processing {len(top_item_ids)} items with DDragon data")

        for item_id in top_item_ids:
            item_data = self.ddragon.get_item_by_id(item_id, patch_version)

            if not item_data:
                logger.warning(f"Item {item_id} not found in DDragon, creating placeholder")
                self._create_placeholder_item(item_id, patch_version)
                continue

            # Extract real DDragon data
            item_name = item_data.get("name", f"Item {item_id}")
            gold_info = item_data.get("gold", {})
            cost = gold_info.get("total", 0)

            # Get standardized stats
            stats = self.ddragon.get_item_stats(item_id, patch_version)

            # Extract passive effects
            passive_effects = self._extract_passive_effects(item_data)

            # Classify item
            item_class = self._classify_item(item_data)

            # Create enhanced ItemStats
            item_stats = ItemStats(
                item_id=item_id,
                item_name=item_name,
                cost=cost,
                stats=stats,
                passive_effects=passive_effects,
                item_class=item_class,
                valid_from_patch=patch_version,
                description=item_data.get("description", ""),
                plaintext=item_data.get("plaintext", ""),
                tags=item_data.get("tags", []),
                gold_info=gold_info,
                validated_with_ddragon=True,
                notes=f"Enhanced from DDragon {patch_version}"
            )

            self.items[item_id] = item_stats
            logger.debug(f"Enhanced item {item_id}: {item_name} with DDragon data")

        logger.info(f"Successfully loaded {len(self.items)} items with DDragon enhancement")

    def _create_fallback_items(self, item_ids: List[int]) -> None:
        """Create fallback items when DDragon is not available"""
        for item_id in item_ids:
            self.items[item_id] = ItemStats(
                item_id=item_id,
                item_name=f"Fallback Item {item_id}",
                cost=0,
                stats={},
                passive_effects=["unknown"],
                item_class="unknown",
                valid_from_patch="14.23.1",
                notes="Fallback - DDragon not available"
            )

    def _create_placeholder_item(self, item_id: int, patch_version: str) -> None:
        """Create placeholder for missing DDragon items"""
        self.items[item_id] = ItemStats(
            item_id=item_id,
            item_name=f"Unknown Item {item_id}",
            cost=0,
            stats={},
            passive_effects=["unknown"],
            item_class="unknown",
            valid_from_patch=patch_version,
            notes="Placeholder - not found in DDragon"
        )

    def get_item_stats(self, item_id: int) -> Optional[ItemStats]:
        """Get stats for a specific item"""
        return self.items.get(item_id)

    def get_item_stat_vector(self, item_id: int) -> Dict[str, float]:
        """Get standardized stat vector for an item"""
        item = self.items.get(item_id)
        if not item:
            return {}
        return item.stats.copy()

    def calculate_gold_efficiency(self, item_id: int,
                                 stat_values: Dict[str, float] = None) -> Dict[str, float]:
        """Calculate gold efficiency using real DDragon cost data

        Args:
            item_id: Item ID
            stat_values: Gold value per stat point (default values used if None)
        """
        item = self.items.get(item_id)
        if not item:
            return {"efficiency": 0.0, "raw_stats_value": 0.0, "total_cost": 0.0}

        # Default stat gold values (approximate)
        if stat_values is None:
            stat_values = {
                "attack_damage": 35.0,  # Long Sword cost per AD
                "ability_power": 21.75,  # Amplifying Tome cost per AP
                "health": 2.67,  # Ruby Crystal cost per HP
                "armor": 20.0,  # Cloth Armor cost per armor
                "magic_resistance": 20.0,  # Null-Magic Mantle cost per MR
                "attack_speed": 30.0,  # Dagger cost per 12% AS, so 2.5 per 1%
                "critical_strike_chance": 40.0,  # Cloak cost per 15% crit, so 2.67 per 1%
                "movement_speed": 13.0,  # Boots cost per 25 MS, so 0.52 per 1 MS
                "life_steal": 55.0,  # Vampiric Scepter cost per 10% LS, so 5.5 per 1%
                "omnivamp": 55.0,  # Similar to life steal
                "mana": 1.4,  # Sapphire Crystal cost per mana
                "ability_haste": 26.67,  # Kindlegem cost per 10 AH, so 2.67 per 1 AH
            }

        # Calculate raw stats value
        raw_value = 0.0
        for stat_name, stat_amount in item.stats.items():
            gold_per_point = stat_values.get(stat_name, 0)
            raw_value += stat_amount * gold_per_point

        # Calculate efficiency
        total_cost = item.cost
        if total_cost <= 0:
            return {"efficiency": 0.0, "raw_stats_value": raw_value, "total_cost": total_cost}

        efficiency = (raw_value / total_cost) * 100  # Percentage

        return {
            "efficiency": round(efficiency, 2),
            "raw_stats_value": round(raw_value, 2),
            "total_cost": total_cost,
            "passive_value_estimate": max(0, total_cost - raw_value)  # Estimated passive value
        }

    def calculate_item_combat_power(self, item_id: int, level: int = 15) -> Dict[str, float]:
        """Calculate combat power contribution using real DDragon stats"""
        item = self.items.get(item_id)
        if not item:
            return {"damage": 0.0, "survivability": 0.0, "crowd_control": 0.0, "mobility": 0.0}

        stats = item.stats

        # Combat power weights
        k_dmg = 1.0
        k_surv = 0.6
        k_cc = 0.4
        k_mob = 0.2

        # Calculate damage component using real stats
        damage = 0.0
        damage += stats.get("attack_damage", 0) * 1.0
        damage += stats.get("ability_power", 0) * 0.8
        damage += stats.get("attack_speed", 0) * 0.5  # AS as percentage
        damage += stats.get("critical_strike_chance", 0) * 1.2  # Crit as percentage
        damage += stats.get("lethality", 0) * 1.5
        damage += stats.get("magic_penetration", 0) * 1.5

        # Calculate survivability component using real stats
        survivability = 0.0
        survivability += stats.get("health", 0) * 0.4
        survivability += stats.get("armor", 0) * 2.5
        survivability += stats.get("magic_resistance", 0) * 2.5
        survivability += stats.get("life_steal", 0) * 3.0
        survivability += stats.get("omnivamp", 0) * 3.0

        # Calculate crowd control component
        crowd_control = 0.0
        crowd_control += stats.get("ability_haste", 0) * 1.5

        # Calculate mobility component
        mobility = 0.0
        mobility += stats.get("movement_speed", 0) * 2.0
        mobility += stats.get("movement_speed_percent", 0) * 100.0  # % MS is much more valuable

        # Add passive effect bonuses based on detected passives
        damage_passives = ["damage_passive", "crit_damage_amplification", "spellblade"]
        surv_passives = ["healing_passive", "shield_passive", "stasis_active", "revive_passive"]
        cc_passives = ["cooldown_passive"]
        mob_passives = ["movement_passive"]

        for passive in item.passive_effects:
            if passive in damage_passives:
                damage += 50
            elif passive in surv_passives:
                survivability += 30
            elif passive in cc_passives:
                crowd_control += 20
            elif passive in mob_passives:
                mobility += 25

        return {
            "damage": damage * k_dmg,
            "survivability": survivability * k_surv,
            "crowd_control": crowd_control * k_cc,
            "mobility": mobility * k_mob
        }

    def get_items_by_class(self, item_class: str) -> List[ItemStats]:
        """Get all items of a specific class"""
        return [item for item in self.items.values() if item.item_class == item_class]

    def get_items_by_cost_range(self, min_cost: int, max_cost: int) -> List[ItemStats]:
        """Get items within a cost range"""
        return [item for item in self.items.values()
                if min_cost <= item.cost <= max_cost]

    def find_most_efficient_items(self, stat_focus: str = "damage",
                                 top_n: int = 10) -> List[Dict[str, Any]]:
        """Find most efficient items for a specific stat focus"""
        efficiency_data = []

        for item_id, item in self.items.items():
            if item.cost <= 0:  # Skip free items
                continue

            efficiency = self.calculate_gold_efficiency(item_id)
            combat_power = self.calculate_item_combat_power(item_id)

            efficiency_data.append({
                "item_id": item_id,
                "item_name": item.item_name,
                "cost": item.cost,
                "gold_efficiency": efficiency["efficiency"],
                "combat_power": combat_power,
                "stat_focus_power": combat_power.get(stat_focus, 0),
                "validated_with_ddragon": item.validated_with_ddragon
            })

        # Sort by stat focus power and gold efficiency
        sorted_items = sorted(efficiency_data,
                             key=lambda x: (x["stat_focus_power"], x["gold_efficiency"]),
                             reverse=True)

        return sorted_items[:top_n]

    def export_to_json(self, output_path: str = None) -> Dict[str, Any]:
        """Export enhanced item data to JSON format"""
        if output_path is None:
            output_path = Path("dimensions/data/item_passive_enhanced.json")
        else:
            output_path = Path(output_path)

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to serializable format
        export_data = {
            "metadata": {
                "table_name": "DimItemPassive",
                "description": "Item statistics and passive effects enhanced with DDragon data",
                "last_updated": datetime.now().isoformat(),
                "record_count": len(self.items),
                "ddragon_enhanced": self.ddragon is not None,
                "ddragon_version": self.ddragon.get_latest_version() if self.ddragon else None,
                "validated_items": sum(1 for item in self.items.values() if item.validated_with_ddragon)
            },
            "records": []
        }

        for item_id, item in self.items.items():
            record = {
                "row_id": f"item_{item_id}_{item.valid_from_patch}_{item.item_class}",
                "item_id": item_id,
                "item_name": item.item_name,
                "cost": item.cost,
                "stats": item.stats,
                "passive_effects": item.passive_effects,
                "item_class": item.item_class,
                "valid_from_patch": item.valid_from_patch,
                "valid_to_patch": item.valid_to_patch,
                "description": item.description,
                "plaintext": item.plaintext,
                "tags": item.tags,
                "gold_info": item.gold_info,
                "validated_with_ddragon": item.validated_with_ddragon,
                "notes": item.notes
            }
            export_data["records"].append(record)

        # Save to file
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported {len(self.items)} enhanced item records to {output_path}")
        return export_data
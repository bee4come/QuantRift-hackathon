#!/usr/bin/env python3
"""
DimAbility: Enhanced dimension table for champion ability data using DDragon

Provides damage values and cooldowns for damage efficiency calculations.
Enhanced to use real DDragon champion data while maintaining curated ability information.
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
class AbilityData:
    """Single ability data record enhanced with DDragon integration"""
    champion_id: int
    champion_name: str
    ability_key: str  # "Q", "W", "E", "R"
    ability_name: str
    base_damage: float  # At level 9/max rank
    ad_ratio: float  # Bonus AD scaling
    ap_ratio: float  # AP scaling
    cooldown: float  # At level 9/max rank
    valid_from_patch: str
    ability_type: str  # "damage", "utility", "mixed"
    damage_type: str  # "physical", "magic", "true"
    valid_to_patch: Optional[str] = None
    notes: Optional[str] = None

    # Enhanced with DDragon data
    champion_title: Optional[str] = None
    champion_tags: Optional[List[str]] = None
    validated_with_ddragon: bool = False

class DimAbility:
    """Manages champion ability data enhanced with DDragon champion information"""

    def __init__(self, ddragon_loader=None):
        """Initialize with champion ability data and DDragon integration"""
        self.abilities = {}

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

        self._load_enhanced_abilities()

    def _get_appropriate_patch(self) -> str:
        """Get appropriate patch version based on DDragon availability"""
        if self.ddragon:
            return self.ddragon.get_latest_version()
        return "14.23.1"  # Fallback

    def _get_champion_stats_at_level(self, champion_id: int, level: int = 9,
                                   patch_version: str = None) -> Dict[str, float]:
        """Get champion stats at specific level using DDragon data"""
        default_stats = {"ad": 100, "ap": 60, "bonus_ad": 70}  # Fallback

        if not self.ddragon:
            return default_stats

        champion_stats = self.ddragon.get_champion_stats(champion_id, patch_version)
        if not champion_stats:
            return default_stats

        # Calculate stats at level
        base_ad = champion_stats.get("attack_damage", 60)
        ad_per_level = champion_stats.get("attack_damage_per_level", 3)

        total_ad = base_ad + (ad_per_level * (level - 1))
        bonus_ad = max(0, total_ad - base_ad)  # Simplified bonus AD calculation

        return {
            "ad": total_ad,
            "ap": 60,  # Assume some AP from items/runes
            "bonus_ad": bonus_ad,
            "base_ad": base_ad,
            "hp": champion_stats.get("hp", 600) + (champion_stats.get("hp_per_level", 90) * (level - 1)),
            "armor": champion_stats.get("armor", 30) + (champion_stats.get("armor_per_level", 3) * (level - 1)),
            "mr": champion_stats.get("magic_resistance", 30) + (champion_stats.get("magic_resistance_per_level", 1) * (level - 1))
        }

    def _load_enhanced_abilities(self) -> None:
        """Load curated ability data enhanced with DDragon champion information"""

        # Curated ability data based on real game values
        # This data is maintained manually as DDragon lacks spell information
        default_abilities = [
            # JINX (Champion ID: 222) - High attach rate ADC
            AbilityData(222, "Jinx", "Q", "Switcheroo!", 0.0, 1.1, 0.0, 0.9, "14.23.1",
                       "utility", "physical", notes="AS steroid + range toggle"),
            AbilityData(222, "Jinx", "W", "Zap!", 160.0, 1.6, 0.0, 8.0, "14.23.1",
                       "damage", "physical", notes="Long range poke"),
            AbilityData(222, "Jinx", "E", "Flame Chompers!", 120.0, 1.0, 0.0, 20.0, "14.23.1",
                       "utility", "magic", notes="CC + damage"),
            AbilityData(222, "Jinx", "R", "Super Mega Death Rocket!", 350.0, 1.5, 0.0, 75.0, "14.23.1",
                       "damage", "physical", notes="Global execute"),

            # CAITLYN (Champion ID: 51) - High attach rate ADC
            AbilityData(51, "Caitlyn", "Q", "Piltover Peacemaker", 130.0, 1.3, 0.0, 7.5, "14.23.1",
                       "damage", "physical", notes="Linear skillshot"),
            AbilityData(51, "Caitlyn", "W", "Yordle Snap Trap", 80.0, 0.6, 0.0, 14.0, "14.23.1",
                       "utility", "magic", notes="Trap CC + damage"),
            AbilityData(51, "Caitlyn", "E", "90 Caliber Net", 100.0, 0.8, 0.0, 12.0, "14.23.1",
                       "damage", "magic", notes="Escape + slow"),
            AbilityData(51, "Caitlyn", "R", "Ace in the Hole", 400.0, 2.0, 0.0, 90.0, "14.23.1",
                       "damage", "physical", notes="Long range execute"),

            # ASHE (Champion ID: 22) - High attach rate ADC
            AbilityData(22, "Ashe", "Q", "Ranger's Focus", 0.0, 1.05, 0.0, 0.0, "14.23.1",
                       "utility", "physical", notes="AS + damage steroid"),
            AbilityData(22, "Ashe", "W", "Volley", 40.0, 1.05, 0.0, 12.0, "14.23.1",
                       "damage", "physical", notes="Cone of arrows"),
            AbilityData(22, "Ashe", "E", "Hawkshot", 0.0, 0.0, 0.0, 90.0, "14.23.1",
                       "utility", "physical", notes="Vision utility"),
            AbilityData(22, "Ashe", "R", "Enchanted Crystal Arrow", 250.0, 1.0, 0.0, 100.0, "14.23.1",
                       "damage", "magic", notes="Global stun"),

            # YASUO (Champion ID: 157) - High attach rate melee
            AbilityData(157, "Yasuo", "Q", "Steel Tempest", 20.0, 1.05, 0.0, 4.0, "14.23.1",
                       "damage", "physical", notes="Linear skill, tornado on 3rd"),
            AbilityData(157, "Yasuo", "W", "Wind Wall", 0.0, 0.0, 0.0, 26.0, "14.23.1",
                       "utility", "physical", notes="Projectile block"),
            AbilityData(157, "Yasuo", "E", "Sweeping Blade", 60.0, 0.6, 0.0, 0.5, "14.23.1",
                       "damage", "magic", notes="Dash with damage"),
            AbilityData(157, "Yasuo", "R", "Last Breath", 200.0, 1.5, 0.0, 80.0, "14.23.1",
                       "damage", "physical", notes="AOE knockup follow-up"),

            # EZREAL (Champion ID: 81) - High attach rate ADC
            AbilityData(81, "Ezreal", "Q", "Mystic Shot", 25.0, 1.3, 0.15, 5.5, "14.23.1",
                       "damage", "physical", notes="CD reduction on hit"),
            AbilityData(81, "Ezreal", "W", "Essence Flux", 70.0, 0.8, 0.7, 12.0, "14.23.1",
                       "damage", "magic", notes="Mark + detonation"),
            AbilityData(81, "Ezreal", "E", "Arcane Shift", 80.0, 0.5, 0.75, 19.0, "14.23.1",
                       "damage", "magic", notes="Blink + damage"),
            AbilityData(81, "Ezreal", "R", "Trueshot Barrage", 350.0, 1.0, 0.9, 120.0, "14.23.1",
                       "damage", "magic", notes="Global wave"),

            # VAYNE (Champion ID: 67) - High attach rate ADC
            AbilityData(67, "Vayne", "Q", "Tumble", 0.0, 0.7, 0.0, 3.5, "14.23.1",
                       "utility", "physical", notes="Next AA enhanced"),
            AbilityData(67, "Vayne", "W", "Silver Bolts", 50.0, 0.0, 0.0, 0.0, "14.23.1",
                       "damage", "true", notes="3-hit true damage"),
            AbilityData(67, "Vayne", "E", "Condemn", 50.0, 0.5, 0.0, 16.0, "14.23.1",
                       "damage", "physical", notes="Knockback + wall stun"),
            AbilityData(67, "Vayne", "R", "Final Hour", 0.0, 0.0, 0.0, 100.0, "14.23.1",
                       "utility", "physical", notes="Stealth + AD steroid"),

            # SYNDRA (Champion ID: 134) - High attach rate mage
            AbilityData(134, "Syndra", "Q", "Dark Sphere", 95.0, 0.0, 0.75, 4.0, "14.23.1",
                       "damage", "magic", notes="Sphere creation"),
            AbilityData(134, "Syndra", "W", "Force of Will", 90.0, 0.0, 0.7, 12.0, "14.23.1",
                       "damage", "magic", notes="Grab + throw"),
            AbilityData(134, "Syndra", "E", "Scatter the Weak", 85.0, 0.0, 0.6, 15.0, "14.23.1",
                       "damage", "magic", notes="Knockback + stun"),
            AbilityData(134, "Syndra", "R", "Unleashed Power", 90.0, 0.0, 0.2, 100.0, "14.23.1",
                       "damage", "magic", notes="Sphere execution"),

            # Add more champions as needed...
        ]

        for ability in default_abilities:
            key = f"{ability.champion_id}_{ability.ability_key}_{ability.valid_from_patch}"

            # Enhance with DDragon data if available
            if self.ddragon:
                champion_data = self.ddragon.get_champion_by_id(ability.champion_id)
                if champion_data:
                    # Update with accurate DDragon information
                    ability.champion_name = champion_data.get("name", ability.champion_name)
                    ability.champion_title = champion_data.get("title", "")
                    ability.champion_tags = champion_data.get("tags", [])
                    ability.validated_with_ddragon = True
                    logger.debug(f"Enhanced {ability.champion_name} {ability.ability_key} with DDragon data")
                else:
                    logger.warning(f"Champion ID {ability.champion_id} not found in DDragon")

            self.abilities[key] = ability

    def get_ability_data(self, champion_id: int, ability_key: str,
                        patch_version: str = None) -> Optional[AbilityData]:
        """Get ability data for specific champion and ability

        Args:
            champion_id: Champion ID (DDragon key)
            ability_key: Q, W, E, or R
            patch_version: Patch version (auto-detected if None)
        """
        if patch_version is None:
            patch_version = self._get_appropriate_patch()

        # Validate champion exists in DDragon
        if self.ddragon:
            champion_data = self.ddragon.get_champion_by_id(champion_id, patch_version)
            if not champion_data:
                logger.warning(f"Champion ID {champion_id} not found in DDragon data")

        key = f"{champion_id}_{ability_key}_{patch_version}"
        if key in self.abilities:
            return self.abilities[key]

        # Fallback to other available patches for this champion+ability
        for stored_key, ability in self.abilities.items():
            if (stored_key.startswith(f"{champion_id}_{ability_key}_") and
                ability.champion_id == champion_id and
                ability.ability_key == ability_key):
                return ability

        logger.warning(f"No ability data found for champion_id: {champion_id}, ability: {ability_key}")
        return None

    def get_champion_abilities(self, champion_id: int,
                              patch_version: str = None) -> List[AbilityData]:
        """Get all abilities for a specific champion

        Enhanced with DDragon champion validation.
        """
        if patch_version is None:
            patch_version = self._get_appropriate_patch()

        # Validate champion exists
        if self.ddragon:
            champion_data = self.ddragon.get_champion_by_id(champion_id, patch_version)
            if champion_data:
                logger.debug(f"Found champion {champion_data['name']} for ID {champion_id}")

        abilities = []
        for key, ability in self.abilities.items():
            if (ability.champion_id == champion_id and
                ability.valid_from_patch == patch_version):
                abilities.append(ability)

        # If no abilities found for specific patch, get any available
        if not abilities:
            for key, ability in self.abilities.items():
                if ability.champion_id == champion_id:
                    abilities.append(ability)

        return sorted(abilities, key=lambda x: x.ability_key)

    def calculate_damage_per_cooldown(self, champion_id: int, ability_key: str,
                                    player_stats: Dict[str, float] = None,
                                    patch_version: str = None,
                                    level: int = 9) -> float:
        """Calculate damage per second of cooldown for an ability

        Enhanced with DDragon champion stats for more accurate base values.

        Args:
            champion_id: Champion ID
            ability_key: Q, W, E, or R
            player_stats: Player stats override
            patch_version: Patch version
            level: Champion level for scaling
        """
        if patch_version is None:
            patch_version = self._get_appropriate_patch()

        ability = self.get_ability_data(champion_id, ability_key, patch_version)
        if not ability or ability.cooldown == 0:
            return 0.0

        if player_stats is None:
            # Use DDragon data for more accurate base stats
            player_stats = self._get_champion_stats_at_level(champion_id, level, patch_version)

        # Calculate total damage
        total_damage = ability.base_damage
        total_damage += ability.ad_ratio * player_stats.get("bonus_ad", 70)
        total_damage += ability.ap_ratio * player_stats.get("ap", 60)

        # Return damage per second of cooldown
        return total_damage / ability.cooldown

    def get_damage_abilities_for_champion(self, champion_id: int,
                                        patch_version: str = None) -> List[AbilityData]:
        """Get only damage-dealing abilities for a champion

        Enhanced with DDragon validation.
        """
        if patch_version is None:
            patch_version = self._get_appropriate_patch()

        all_abilities = self.get_champion_abilities(champion_id, patch_version)
        return [ability for ability in all_abilities
                if ability.ability_type in ["damage", "mixed"]]

    def add_patch_abilities(self, patch_version: str,
                          abilities_update: List[AbilityData]) -> None:
        """Add or update abilities for a new patch"""
        for ability in abilities_update:
            ability.valid_from_patch = patch_version

            # Enhance with DDragon data
            if self.ddragon:
                champion_data = self.ddragon.get_champion_by_id(ability.champion_id, patch_version)
                if champion_data:
                    ability.champion_name = champion_data.get("name", ability.champion_name)
                    ability.champion_title = champion_data.get("title", "")
                    ability.champion_tags = champion_data.get("tags", [])
                    ability.validated_with_ddragon = True

            key = f"{ability.champion_id}_{ability.ability_key}_{patch_version}"
            self.abilities[key] = ability

    def get_champions_with_abilities(self) -> Dict[int, Dict[str, Any]]:
        """Get list of champions that have ability data with DDragon enhancement"""
        champions = {}

        for ability in self.abilities.values():
            champ_id = ability.champion_id
            if champ_id not in champions:
                champions[champ_id] = {
                    "champion_id": champ_id,
                    "champion_name": ability.champion_name,
                    "champion_title": ability.champion_title,
                    "champion_tags": ability.champion_tags,
                    "validated_with_ddragon": ability.validated_with_ddragon,
                    "abilities": []
                }
            champions[champ_id]["abilities"].append(ability.ability_key)

        return champions

    def export_to_json(self, output_path: str = None) -> Dict[str, Any]:
        """Export enhanced ability data to JSON format"""
        if output_path is None:
            output_path = Path("dimensions/data/abilities_enhanced.json")
        else:
            output_path = Path(output_path)

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to serializable format
        export_data = {
            "metadata": {
                "table_name": "DimAbility",
                "description": "Champion ability damage and cooldown data enhanced with DDragon",
                "last_updated": datetime.now().isoformat(),
                "record_count": len(self.abilities),
                "ddragon_enhanced": self.ddragon is not None,
                "ddragon_version": self.ddragon.get_latest_version() if self.ddragon else None
            },
            "records": []
        }

        for key, ability in self.abilities.items():
            record = {
                "row_id": f"ability_{ability.champion_id}_{ability.ability_key}_{ability.valid_from_patch}",
                "champion_id": ability.champion_id,
                "champion_name": ability.champion_name,
                "champion_title": ability.champion_title,
                "champion_tags": ability.champion_tags,
                "ability_key": ability.ability_key,
                "ability_name": ability.ability_name,
                "base_damage": round(ability.base_damage, 3),
                "ad_ratio": round(ability.ad_ratio, 3),
                "ap_ratio": round(ability.ap_ratio, 3),
                "cooldown": round(ability.cooldown, 3),
                "valid_from_patch": ability.valid_from_patch,
                "valid_to_patch": ability.valid_to_patch,
                "ability_type": ability.ability_type,
                "damage_type": ability.damage_type,
                "validated_with_ddragon": ability.validated_with_ddragon,
                "notes": ability.notes
            }
            export_data["records"].append(record)

        # Save to file
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported {len(self.abilities)} enhanced ability records to {output_path}")
        return export_data
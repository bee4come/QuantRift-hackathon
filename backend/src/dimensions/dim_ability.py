#!/usr/bin/env python3
"""
DimAbility: Static dimension table for champion ability data
Provides damage values and cooldowns for damage efficiency calculations
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))
from utils import generate_row_id, format_output_precision

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AbilityData:
    """Single ability data record"""
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

class DimAbility:
    """Manages champion ability data for damage efficiency calculations"""

    def __init__(self):
        """Initialize with champion ability data"""
        self.abilities = {}
        self._load_default_abilities()

    def _load_default_abilities(self) -> None:
        """Load default ability data for high-frequency champions"""
        # Based on attach_rate analysis top champions
        default_abilities = [
            # JINX (Champion ID: 222)
            AbilityData(222, "Jinx", "Q", "Switcheroo!", 0.0, 1.1, 0.0, 0.9, "14.1",
                       "utility", "physical", notes="AS steroid + range toggle"),
            AbilityData(222, "Jinx", "W", "Zap!", 160.0, 1.6, 0.0, 8.0, "14.1",
                       "damage", "physical", notes="Long range poke"),
            AbilityData(222, "Jinx", "E", "Flame Chompers!", 120.0, 1.0, 0.0, 20.0, "14.1",
                       "utility", "magic", notes="CC + damage"),
            AbilityData(222, "Jinx", "R", "Super Mega Death Rocket!", 350.0, 1.5, 0.0, 75.0, "14.1",
                       "damage", "physical", notes="Global execute"),

            # CAITLYN (Champion ID: 51)
            AbilityData(51, "Caitlyn", "Q", "Piltover Peacemaker", 130.0, 1.3, 0.0, 7.5, "14.1",
                       "damage", "physical", notes="Linear skillshot"),
            AbilityData(51, "Caitlyn", "W", "Yordle Snap Trap", 80.0, 0.6, 0.0, 14.0, "14.1",
                       "utility", "magic", notes="Trap CC + damage"),
            AbilityData(51, "Caitlyn", "E", "90 Caliber Net", 100.0, 0.8, 0.0, 12.0, "14.1",
                       "damage", "magic", notes="Escape + slow"),
            AbilityData(51, "Caitlyn", "R", "Ace in the Hole", 400.0, 2.0, 0.0, 90.0, "14.1",
                       "damage", "physical", notes="Long range execute"),

            # ASHE (Champion ID: 22)
            AbilityData(22, "Ashe", "Q", "Ranger's Focus", 0.0, 1.05, 0.0, 0.0, "14.1",
                       "utility", "physical", notes="AS + damage steroid"),
            AbilityData(22, "Ashe", "W", "Volley", 40.0, 1.05, 0.0, 12.0, "14.1",
                       "damage", "physical", notes="Cone of arrows"),
            AbilityData(22, "Ashe", "E", "Hawkshot", 0.0, 0.0, 0.0, 90.0, "14.1",
                       "utility", "physical", notes="Vision utility"),
            AbilityData(22, "Ashe", "R", "Enchanted Crystal Arrow", 250.0, 1.0, 0.0, 100.0, "14.1",
                       "damage", "magic", notes="Global stun"),

            # YASUO (Champion ID: 157)
            AbilityData(157, "Yasuo", "Q", "Steel Tempest", 20.0, 1.05, 0.0, 4.0, "14.1",
                       "damage", "physical", notes="Linear skill, tornado on 3rd"),
            AbilityData(157, "Yasuo", "W", "Wind Wall", 0.0, 0.0, 0.0, 26.0, "14.1",
                       "utility", "physical", notes="Projectile block"),
            AbilityData(157, "Yasuo", "E", "Sweeping Blade", 60.0, 0.6, 0.0, 0.5, "14.1",
                       "damage", "magic", notes="Dash with damage"),
            AbilityData(157, "Yasuo", "R", "Last Breath", 200.0, 1.5, 0.0, 80.0, "14.1",
                       "damage", "physical", notes="AOE knockup follow-up"),

            # EZREAL (Champion ID: 81)
            AbilityData(81, "Ezreal", "Q", "Mystic Shot", 25.0, 1.3, 0.15, 5.5, "14.1",
                       "damage", "physical", notes="CD reduction on hit"),
            AbilityData(81, "Ezreal", "W", "Essence Flux", 70.0, 0.8, 0.7, 12.0, "14.1",
                       "damage", "magic", notes="Mark + detonation"),
            AbilityData(81, "Ezreal", "E", "Arcane Shift", 80.0, 0.5, 0.75, 19.0, "14.1",
                       "damage", "magic", notes="Blink + damage"),
            AbilityData(81, "Ezreal", "R", "Trueshot Barrage", 350.0, 1.0, 0.9, 120.0, "14.1",
                       "damage", "magic", notes="Global wave"),

            # VAYNE (Champion ID: 67)
            AbilityData(67, "Vayne", "Q", "Tumble", 0.0, 0.7, 0.0, 3.5, "14.1",
                       "utility", "physical", notes="Next AA enhanced"),
            AbilityData(67, "Vayne", "W", "Silver Bolts", 50.0, 0.0, 0.0, 0.0, "14.1",
                       "damage", "true", notes="3-hit true damage"),
            AbilityData(67, "Vayne", "E", "Condemn", 50.0, 0.5, 0.0, 16.0, "14.1",
                       "damage", "physical", notes="Knockback + wall stun"),
            AbilityData(67, "Vayne", "R", "Final Hour", 0.0, 0.0, 0.0, 100.0, "14.1",
                       "utility", "physical", notes="Stealth + AD steroid"),

            # SYNDRA (Champion ID: 134)
            AbilityData(134, "Syndra", "Q", "Dark Sphere", 95.0, 0.0, 0.75, 4.0, "14.1",
                       "damage", "magic", notes="Sphere creation"),
            AbilityData(134, "Syndra", "W", "Force of Will", 90.0, 0.0, 0.7, 12.0, "14.1",
                       "damage", "magic", notes="Grab + throw"),
            AbilityData(134, "Syndra", "E", "Scatter the Weak", 85.0, 0.0, 0.6, 15.0, "14.1",
                       "damage", "magic", notes="Knockback + stun"),
            AbilityData(134, "Syndra", "R", "Unleashed Power", 90.0, 0.0, 0.2, 100.0, "14.1",
                       "damage", "magic", notes="Sphere execution"),

            # ZILLEAN (Champion ID: 26)
            AbilityData(26, "Zillean", "Q", "Time Bomb", 90.0, 0.0, 0.9, 8.5, "14.1",
                       "damage", "magic", notes="Double bomb stun"),
            AbilityData(26, "Zillean", "W", "Rewind", 0.0, 0.0, 0.0, 14.0, "14.1",
                       "utility", "magic", notes="CD reduction"),
            AbilityData(26, "Zillean", "E", "Time Warp", 0.0, 0.0, 0.0, 15.0, "14.1",
                       "utility", "magic", notes="Speed boost/slow"),
            AbilityData(26, "Zillean", "R", "Chronoshift", 0.0, 0.0, 0.0, 120.0, "14.1",
                       "utility", "magic", notes="Death prevention"),

            # MORGANA (Champion ID: 25)
            AbilityData(25, "Morgana", "Q", "Dark Binding", 80.0, 0.0, 0.9, 10.0, "14.1",
                       "damage", "magic", notes="Root + damage"),
            AbilityData(25, "Morgana", "W", "Tormented Shadow", 24.0, 0.0, 0.22, 12.0, "14.1",
                       "damage", "magic", notes="DoT pool per second"),
            AbilityData(25, "Morgana", "E", "Black Shield", 0.0, 0.0, 0.0, 26.0, "14.1",
                       "utility", "magic", notes="Magic immunity"),
            AbilityData(25, "Morgana", "R", "Soul Shackles", 150.0, 0.0, 0.7, 120.0, "14.1",
                       "damage", "magic", notes="AOE slow + stun"),

            # LULU (Champion ID: 117)
            AbilityData(117, "Lulu", "Q", "Glitterlance", 80.0, 0.0, 0.5, 7.0, "14.1",
                       "damage", "magic", notes="Piercing slow"),
            AbilityData(117, "Lulu", "W", "Whimsy", 65.0, 0.0, 0.45, 15.0, "14.1",
                       "utility", "magic", notes="Polymorph or buff"),
            AbilityData(117, "Lulu", "E", "Help, Pix!", 80.0, 0.0, 0.6, 10.0, "14.1",
                       "damage", "magic", notes="Shield ally or damage enemy"),
            AbilityData(117, "Lulu", "R", "Wild Growth", 0.0, 0.0, 0.0, 110.0, "14.1",
                       "utility", "magic", notes="Size + health increase"),

            # LEE SIN (Champion ID: 64)
            AbilityData(64, "Lee Sin", "Q", "Sonic Wave", 100.0, 1.15, 0.0, 10.0, "14.1",
                       "damage", "physical", notes="Skillshot + dash"),
            AbilityData(64, "Lee Sin", "W", "Safeguard", 0.0, 0.0, 0.0, 12.0, "14.1",
                       "utility", "magic", notes="Shield + dash"),
            AbilityData(64, "Lee Sin", "E", "Tempest", 100.0, 1.0, 0.0, 8.0, "14.1",
                       "damage", "magic", notes="AOE + slow"),
            AbilityData(64, "Lee Sin", "R", "Dragon's Rage", 200.0, 2.0, 0.0, 90.0, "14.1",
                       "damage", "physical", notes="Kick + displacement"),

            # GAREN (Champion ID: 86)
            AbilityData(86, "Garen", "Q", "Decisive Strike", 30.0, 1.5, 0.0, 8.0, "14.1",
                       "damage", "physical", notes="Silence + enhanced AA"),
            AbilityData(86, "Garen", "W", "Courage", 0.0, 0.0, 0.0, 23.0, "14.1",
                       "utility", "physical", notes="Damage reduction"),
            AbilityData(86, "Garen", "E", "Judgment", 16.0, 0.4, 0.0, 9.0, "14.1",
                       "damage", "physical", notes="Spin damage per second"),
            AbilityData(86, "Garen", "R", "Demacian Justice", 175.0, 0.0, 0.0, 120.0, "14.1",
                       "damage", "true", notes="Missing health execution"),

            # DARIUS (Champion ID: 122)
            AbilityData(122, "Darius", "Q", "Decimate", 130.0, 1.3, 0.0, 9.0, "14.1",
                       "damage", "physical", notes="Outer ring heal"),
            AbilityData(122, "Darius", "W", "Crippling Strike", 50.0, 1.5, 0.0, 5.0, "14.1",
                       "damage", "physical", notes="Enhanced AA + slow"),
            AbilityData(122, "Darius", "E", "Apprehend", 0.0, 0.0, 0.0, 24.0, "14.1",
                       "utility", "physical", notes="Pull + armor pen"),
            AbilityData(122, "Darius", "R", "Noxian Guillotine", 100.0, 0.75, 0.0, 100.0, "14.1",
                       "damage", "true", notes="Execute + reset"),

            # KAI'SA (Champion ID: 145)
            AbilityData(145, "Kai'Sa", "Q", "Icathian Rain", 45.0, 0.5, 0.25, 8.0, "14.1",
                       "damage", "physical", notes="Multi-missile"),
            AbilityData(145, "Kai'Sa", "W", "Void Seeker", 45.0, 1.3, 0.45, 18.0, "14.1",
                       "damage", "magic", notes="Long range mark"),
            AbilityData(145, "Kai'Sa", "E", "Supercharge", 0.0, 0.0, 0.0, 16.0, "14.1",
                       "utility", "magic", notes="AS + MS steroid"),
            AbilityData(145, "Kai'Sa", "R", "Killer Instinct", 0.0, 0.0, 0.0, 100.0, "14.1",
                       "utility", "magic", notes="Dash to marked target"),

            # ALISTAR (Champion ID: 12)
            AbilityData(12, "Alistar", "Q", "Pulverize", 90.0, 0.0, 0.5, 15.0, "14.1",
                       "damage", "magic", notes="AOE knockup"),
            AbilityData(12, "Alistar", "W", "Headbutt", 85.0, 0.0, 0.7, 14.0, "14.1",
                       "damage", "magic", notes="Single target knockback"),
            AbilityData(12, "Alistar", "E", "Trample", 80.0, 0.0, 0.4, 12.0, "14.1",
                       "damage", "magic", notes="AOE over time"),
            AbilityData(12, "Alistar", "R", "Unbreakable Will", 0.0, 0.0, 0.0, 120.0, "14.1",
                       "utility", "magic", notes="Damage reduction"),
        ]

        for ability in default_abilities:
            key = f"{ability.champion_id}_{ability.ability_key}_{ability.valid_from_patch}"
            self.abilities[key] = ability

    def get_ability_data(self, champion_id: int, ability_key: str, patch_version: str = "14.1") -> Optional[AbilityData]:
        """Get ability data for specific champion and ability"""
        key = f"{champion_id}_{ability_key}_{patch_version}"
        if key in self.abilities:
            return self.abilities[key]

        # Fallback to default patch
        key = f"{champion_id}_{ability_key}_14.1"
        if key in self.abilities:
            return self.abilities[key]

        logger.warning(f"No ability data found for champion_id: {champion_id}, ability: {ability_key}")
        return None

    def get_champion_abilities(self, champion_id: int, patch_version: str = "14.1") -> List[AbilityData]:
        """Get all abilities for a specific champion"""
        abilities = []

        for key, ability in self.abilities.items():
            if (ability.champion_id == champion_id and
                ability.valid_from_patch == patch_version):
                abilities.append(ability)

        return sorted(abilities, key=lambda x: x.ability_key)

    def calculate_damage_per_cooldown(self, champion_id: int, ability_key: str,
                                    player_stats: Dict[str, float] = None,
                                    patch_version: str = "14.1") -> float:
        """Calculate damage per second of cooldown for an ability"""
        ability = self.get_ability_data(champion_id, ability_key, patch_version)
        if not ability or ability.cooldown == 0:
            return 0.0

        if player_stats is None:
            player_stats = {"ad": 100, "ap": 60, "bonus_ad": 70}  # Level 9 defaults

        # Calculate total damage
        total_damage = ability.base_damage
        total_damage += ability.ad_ratio * player_stats.get("bonus_ad", 70)
        total_damage += ability.ap_ratio * player_stats.get("ap", 60)

        # Return damage per second of cooldown
        return total_damage / ability.cooldown

    def get_damage_abilities_for_champion(self, champion_id: int, patch_version: str = "14.1") -> List[AbilityData]:
        """Get only damage-dealing abilities for a champion"""
        all_abilities = self.get_champion_abilities(champion_id, patch_version)
        return [ability for ability in all_abilities if ability.ability_type in ["damage", "mixed"]]

    def add_patch_abilities(self, patch_version: str, abilities_update: List[AbilityData]) -> None:
        """Add or update abilities for a new patch"""
        for ability in abilities_update:
            ability.valid_from_patch = patch_version
            key = f"{ability.champion_id}_{ability.ability_key}_{patch_version}"
            self.abilities[key] = ability

    def export_to_json(self, output_path: str = None) -> Dict[str, Any]:
        """Export ability data to JSON format"""
        if output_path is None:
            output_path = Path("dimensions/data/abilities.json")
        else:
            output_path = Path(output_path)

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to serializable format
        export_data = {
            "metadata": {
                "table_name": "DimAbility",
                "description": "Champion ability damage and cooldown data",
                "last_updated": datetime.now().isoformat(),
                "record_count": len(self.abilities)
            },
            "records": []
        }

        for key, ability in self.abilities.items():
            record = {
                "row_id": f"ability_{ability.champion_id}_{ability.ability_key}_{ability.valid_from_patch}",
                "champion_id": ability.champion_id,
                "champion_name": ability.champion_name,
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
                "notes": ability.notes
            }
            export_data["records"].append(record)

        # Save to file
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported {len(self.abilities)} ability records to {output_path}")
        return export_data

def main():
    """Test ability dimension table"""
    dim_abilities = DimAbility()

    # Test ability lookup
    jinx_q = dim_abilities.get_ability_data(222, "Q")
    if jinx_q:
        print(f"Jinx Q: {jinx_q.base_damage} base, {jinx_q.ad_ratio} AD ratio, {jinx_q.cooldown}s CD")

    # Test champion abilities
    jinx_abilities = dim_abilities.get_champion_abilities(222)
    print(f"Jinx abilities: {[a.ability_key + ':' + a.ability_name for a in jinx_abilities]}")

    # Test damage per cooldown
    damage_per_cd = dim_abilities.calculate_damage_per_cooldown(222, "W", {"bonus_ad": 120, "ap": 0})
    print(f"Jinx W damage per CD second: {damage_per_cd:.1f}")

    # Test damage abilities only
    syndra_damage = dim_abilities.get_damage_abilities_for_champion(134)
    print(f"Syndra damage abilities: {[a.ability_key for a in syndra_damage]}")

    # Export data
    data = dim_abilities.export_to_json()
    print(f"Exported {data['metadata']['record_count']} ability records")

if __name__ == "__main__":
    main()
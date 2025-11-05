#!/usr/bin/env python3
"""
DimRuneValue: Static dimension table for rune value calculations
Provides keystone and secondary rune values with trigger rate models
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
class RuneValue:
    """Single rune value record"""
    rune_id: int
    rune_name: str
    rune_type: str  # "keystone", "secondary"
    tree_name: str  # "Precision", "Domination", etc.
    trigger_rate_per_min: float
    value_per_proc: float
    scaling_type: str  # "ad_ratio", "ap_ratio", "level", "fixed"
    valid_from_patch: str
    champion_roles: List[str]  # ["adc", "mid", "jungle", "top", "support"]
    valid_to_patch: Optional[str] = None
    notes: Optional[str] = None

class DimRuneValue:
    """Manages rune values for quantitative analysis"""

    def __init__(self):
        """Initialize with base rune values"""
        self.runes = {}
        self._load_default_runes()

    def _load_default_runes(self) -> None:
        """Load default rune values based on meta analysis"""
        # Major keystones with trigger rates and values
        default_runes = [
            # PRECISION TREE
            RuneValue(8005, "Press the Attack", "keystone", "Precision",
                     3.2, 180.0, "ad_ratio", "14.1", ["adc", "jungle", "top"],
                     notes="3-hit proc, 120+12%AD damage"),

            RuneValue(8008, "Lethal Tempo", "keystone", "Precision",
                     2.8, 0.0, "fixed", "14.1", ["adc", "top"],
                     notes="Attack speed steroid, no direct damage"),

            RuneValue(8021, "Fleet Footwork", "keystone", "Precision",
                     4.5, 85.0, "level", "14.1", ["adc", "mid"],
                     notes="Heal + movement speed, 30-240+30%bAD+30%AP"),

            RuneValue(8010, "Conqueror", "keystone", "Precision",
                     2.1, 220.0, "ad_ratio", "14.1", ["top", "jungle", "mid"],
                     notes="Stacking AD + healing, high value when stacked"),

            # DOMINATION TREE
            RuneValue(8112, "Electrocute", "keystone", "Domination",
                     2.8, 195.0, "ap_ratio", "14.1", ["mid", "jungle", "support"],
                     notes="3 separate attacks, 30-180+50%bAD+25%AP"),

            RuneValue(8124, "Predator", "keystone", "Domination",
                     1.2, 150.0, "level", "14.1", ["jungle"],
                     notes="Active ganking tool, 40-120+25%bAD+15%AP"),

            RuneValue(8128, "Dark Harvest", "keystone", "Domination",
                     3.8, 160.0, "ap_ratio", "14.1", ["mid", "jungle"],
                     notes="Scaling execution, 20-60+25%bAD+15%AP per soul"),

            RuneValue(9923, "Hail of Blades", "keystone", "Domination",
                     2.5, 0.0, "fixed", "14.1", ["adc", "jungle"],
                     notes="Attack speed burst, no direct damage"),

            # SORCERY TREE
            RuneValue(8214, "Summon Aery", "keystone", "Sorcery",
                     8.5, 65.0, "ap_ratio", "14.1", ["support", "mid"],
                     notes="Poke/shield, 10-40+10%AP+15%bAD"),

            RuneValue(8229, "Arcane Comet", "keystone", "Sorcery",
                     4.2, 110.0, "ap_ratio", "14.1", ["mid", "support"],
                     notes="Skillshot follow-up, 30-100+20%AP+35%bAD"),

            RuneValue(8230, "Phase Rush", "keystone", "Sorcery",
                     1.8, 0.0, "fixed", "14.1", ["mid", "top"],
                     notes="Movement speed utility, no direct damage"),

            # RESOLVE TREE
            RuneValue(8437, "Grasp of the Undying", "keystone", "Resolve",
                     3.5, 95.0, "level", "14.1", ["top", "support"],
                     notes="Sustain in extended trades, 4%maxHP damage"),

            RuneValue(8439, "Aftershock", "keystone", "Resolve",
                     2.1, 140.0, "level", "14.1", ["support", "jungle", "top"],
                     notes="Post-CC burst, 25-120+8%bHP"),

            RuneValue(8465, "Guardian", "keystone", "Resolve",
                     1.9, 120.0, "level", "14.1", ["support"],
                     notes="Shield ally, 50-130+15%bAD+25%AP"),

            # INSPIRATION TREE
            RuneValue(8360, "Unsealed Spellbook", "keystone", "Inspiration",
                     0.8, 0.0, "fixed", "14.1", ["top", "support"],
                     notes="Utility keystone, no direct damage value"),

            RuneValue(8351, "Glacial Augment", "keystone", "Inspiration",
                     2.3, 45.0, "ap_ratio", "14.1", ["support", "mid"],
                     notes="Slow utility with damage, 15-45+5%AP"),

            RuneValue(8358, "First Strike", "keystone", "Inspiration",
                     2.7, 175.0, "ad_ratio", "14.1", ["mid", "adc", "top"],
                     notes="Damage amp + gold, 10%+8%AD/12%AP extra damage"),

            # HIGH-VALUE SECONDARY RUNES
            RuneValue(8009, "Presence of Mind", "secondary", "Precision",
                     6.0, 35.0, "level", "14.1", ["mid", "adc"],
                     notes="Mana sustain + max mana/energy"),

            RuneValue(8014, "Coup de Grace", "secondary", "Precision",
                     4.5, 85.0, "ad_ratio", "14.1", ["adc", "mid", "jungle"],
                     notes="Execute damage, 8% extra damage <40% HP"),

            RuneValue(8126, "Cheap Shot", "secondary", "Domination",
                     5.2, 45.0, "ap_ratio", "14.1", ["mid", "jungle", "support"],
                     notes="CC follow-up, 10-45 true damage"),

            RuneValue(8139, "Taste of Blood", "secondary", "Domination",
                     3.8, 28.0, "ap_ratio", "14.1", ["mid", "top"],
                     notes="Sustain, 16-30+15%bAD+8%AP heal"),

            RuneValue(8237, "Scorch", "secondary", "Sorcery",
                     6.8, 32.0, "ap_ratio", "14.1", ["mid", "support"],
                     notes="Poke enhancement, 15-35+10%AP"),

            RuneValue(8232, "Waterwalking", "secondary", "Sorcery",
                     0.0, 0.0, "fixed", "14.1", ["jungle"],
                     notes="River movement + AD/AP, no direct damage"),

            RuneValue(8444, "Second Wind", "secondary", "Resolve",
                     4.2, 18.0, "level", "14.1", ["top", "mid"],
                     notes="Sustain after damage, 6+4%missing HP heal"),

            RuneValue(8451, "Overgrowth", "secondary", "Resolve",
                     0.0, 0.0, "fixed", "14.1", ["top", "jungle", "support"],
                     notes="Scaling health, no direct damage value"),
        ]

        for rune in default_runes:
            key = f"{rune.rune_id}_{rune.valid_from_patch}"
            self.runes[key] = rune

    def get_rune_value(self, rune_id: int, patch_version: str = "14.1") -> Optional[RuneValue]:
        """Get rune value data for specific rune and patch"""
        key = f"{rune_id}_{patch_version}"
        if key in self.runes:
            return self.runes[key]

        # Fallback to default patch
        key = f"{rune_id}_14.1"
        if key in self.runes:
            return self.runes[key]

        logger.warning(f"No rune value found for rune_id: {rune_id}")
        return None

    def get_keystones_for_role(self, role: str, patch_version: str = "14.1") -> List[RuneValue]:
        """Get all keystones suitable for a specific role"""
        keystones = []

        for key, rune in self.runes.items():
            if (rune.rune_type == "keystone" and
                rune.valid_from_patch == patch_version and
                role in rune.champion_roles):
                keystones.append(rune)

        return keystones

    def calculate_rune_expected_value(self, rune_id: int, game_duration_min: float = 25.0,
                                    player_stats: Dict[str, float] = None,
                                    patch_version: str = "14.1") -> float:
        """Calculate expected value of a rune over game duration"""
        rune = self.get_rune_value(rune_id, patch_version)
        if not rune:
            return 0.0

        if player_stats is None:
            player_stats = {"ad": 100, "ap": 60, "level": 11}  # Mid-game defaults

        # Calculate total triggers over game duration
        total_triggers = rune.trigger_rate_per_min * game_duration_min

        # Calculate value per trigger based on scaling type
        value_per_trigger = rune.value_per_proc

        if rune.scaling_type == "ad_ratio":
            # Assume 50% AD scaling for keystones
            value_per_trigger += 0.5 * player_stats.get("ad", 100)
        elif rune.scaling_type == "ap_ratio":
            # Assume 25% AP scaling for keystones
            value_per_trigger += 0.25 * player_stats.get("ap", 60)
        elif rune.scaling_type == "level":
            # Level-based scaling
            level = player_stats.get("level", 11)
            value_per_trigger += (level - 1) * 5  # ~5 damage per level

        return total_triggers * value_per_trigger

    def add_patch_runes(self, patch_version: str, runes_update: List[RuneValue]) -> None:
        """Add or update runes for a new patch"""
        for rune in runes_update:
            rune.valid_from_patch = patch_version
            key = f"{rune.rune_id}_{patch_version}"
            self.runes[key] = rune

    def export_to_json(self, output_path: str = None) -> Dict[str, Any]:
        """Export rune values to JSON format"""
        if output_path is None:
            output_path = Path("dimensions/data/rune_values.json")
        else:
            output_path = Path(output_path)

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to serializable format
        export_data = {
            "metadata": {
                "table_name": "DimRuneValue",
                "description": "Rune trigger rates and values for quantitative analysis",
                "last_updated": datetime.now().isoformat(),
                "record_count": len(self.runes)
            },
            "records": []
        }

        for key, rune in self.runes.items():
            record = {
                "row_id": f"rune_value_{rune.rune_id}_{rune.valid_from_patch}",
                "rune_id": rune.rune_id,
                "rune_name": rune.rune_name,
                "rune_type": rune.rune_type,
                "tree_name": rune.tree_name,
                "trigger_rate_per_min": round(rune.trigger_rate_per_min, 3),
                "value_per_proc": round(rune.value_per_proc, 3),
                "scaling_type": rune.scaling_type,
                "valid_from_patch": rune.valid_from_patch,
                "valid_to_patch": rune.valid_to_patch,
                "champion_roles": rune.champion_roles,
                "notes": rune.notes
            }
            export_data["records"].append(record)

        # Save to file
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported {len(self.runes)} rune values to {output_path}")
        return export_data

def main():
    """Test rune value dimension table"""
    dim_runes = DimRuneValue()

    # Test keystone lookup
    conqueror = dim_runes.get_rune_value(8010)
    if conqueror:
        print(f"Conqueror: {conqueror.trigger_rate_per_min} procs/min, {conqueror.value_per_proc} base value")

    # Test role-based keystones
    adc_keystones = dim_runes.get_keystones_for_role("adc")
    print(f"ADC keystones: {[k.rune_name for k in adc_keystones]}")

    # Test expected value calculation
    expected_value = dim_runes.calculate_rune_expected_value(8010, 25.0, {"ad": 150, "level": 12})
    print(f"Conqueror expected value (25min game): {expected_value:.1f}")

    # Export data
    data = dim_runes.export_to_json()
    print(f"Exported {data['metadata']['record_count']} rune records")

if __name__ == "__main__":
    main()
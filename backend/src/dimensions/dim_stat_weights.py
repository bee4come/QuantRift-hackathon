#!/usr/bin/env python3
"""
DimStatWeights: Static dimension table for stat gold values
Provides versioned stat weights for item gold efficiency calculations
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
class StatWeight:
    """Single stat weight record"""
    stat_name: str
    gold_value: float
    unit: str  # "flat", "percent", "per_second"
    valid_from_patch: str
    valid_to_patch: Optional[str] = None
    notes: Optional[str] = None


class DimStatWeights:
    """Manages stat weights for gold efficiency calculations"""
    
    def __init__(self):
        """Initialize with base stat weights"""
        self.weights = {}
        self._load_default_weights()
        
    def _load_default_weights(self) -> None:
        """Load default stat weights based on provided values"""
        # Base values provided by user
        default_weights = [
            StatWeight("attack_damage", 35.0, "flat", "14.1", None, "Base AD gold value"),
            StatWeight("ability_power", 21.0, "flat", "14.1", None, "Base AP gold value"),
            StatWeight("attack_speed", 25.0, "percent", "14.1", None, "AS per 1% value"),
            StatWeight("health", 2.5, "flat", "14.1", None, "HP per point value"),
            StatWeight("armor", 18.0, "flat", "14.1", None, "Armor per point value"),
            StatWeight("magic_resistance", 18.0, "flat", "14.1", None, "MR per point value"),
            StatWeight("ability_haste", 90.0, "flat", "14.1", None, "Haste per point value"),
            
            # Additional common stats (standard values)
            StatWeight("mana", 1.4, "flat", "14.1", None, "Mana per point value"),
            StatWeight("health_regen", 36.0, "flat", "14.1", None, "Health regen per point"),
            StatWeight("mana_regen", 60.0, "flat", "14.1", None, "Mana regen per point"),
            StatWeight("movement_speed", 39.5, "flat", "14.1", None, "Movement speed per point"),
            StatWeight("critical_strike_chance", 40.0, "percent", "14.1", None, "Crit chance per 1%"),
            StatWeight("critical_strike_damage", 40.0, "percent", "14.1", None, "Crit damage per 1%"),
            StatWeight("life_steal", 55.0, "percent", "14.1", None, "Life steal per 1%"),
            StatWeight("omnivamp", 55.0, "percent", "14.1", None, "Omnivamp per 1%"),
            StatWeight("lethality", 5.0, "flat", "14.1", None, "Lethality per point"),
            StatWeight("magic_penetration", 5.0, "flat", "14.1", None, "Magic pen per point"),
            StatWeight("armor_penetration", 35.0, "percent", "14.1", None, "Armor pen per 1%"),
            StatWeight("magic_penetration_percent", 35.0, "percent", "14.1", None, "Magic pen per 1%"),
        ]
        
        for weight in default_weights:
            key = f"{weight.stat_name}_{weight.valid_from_patch}"
            self.weights[key] = weight
            
    def get_stat_weight(self, stat_name: str, patch_version: str = "14.1") -> Optional[float]:
        """Get gold value for a specific stat and patch"""
        # For now, use the default patch if specific version not found
        key = f"{stat_name}_{patch_version}"
        if key in self.weights:
            return self.weights[key].gold_value
            
        # Fallback to default patch
        key = f"{stat_name}_14.1"
        if key in self.weights:
            return self.weights[key].gold_value
            
        logger.warning(f"No weight found for stat: {stat_name}")
        return None
        
    def get_all_weights_for_patch(self, patch_version: str = "14.1") -> Dict[str, float]:
        """Get all stat weights for a specific patch"""
        result = {}
        
        for key, weight in self.weights.items():
            if weight.valid_from_patch == patch_version:
                result[weight.stat_name] = weight.gold_value
                
        # If no patch-specific weights found, use default
        if not result:
            for key, weight in self.weights.items():
                if weight.valid_from_patch == "14.1":
                    result[weight.stat_name] = weight.gold_value
                    
        return result
        
    def add_patch_weights(self, patch_version: str, weights_update: Dict[str, float]) -> None:
        """Add or update weights for a new patch"""
        for stat_name, gold_value in weights_update.items():
            weight = StatWeight(
                stat_name=stat_name,
                gold_value=gold_value,
                unit="flat",  # Default, should be specified
                valid_from_patch=patch_version,
                notes=f"Updated for patch {patch_version}"
            )
            key = f"{stat_name}_{patch_version}"
            self.weights[key] = weight
            
    def export_to_json(self, output_path: str = None) -> Dict[str, Any]:
        """Export stat weights to JSON format"""
        if output_path is None:
            output_path = Path("dimensions/data/stat_weights.json")
        else:
            output_path = Path(output_path)
            
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable format
        export_data = {
            "metadata": {
                "table_name": "DimStatWeights",
                "description": "Stat gold values for efficiency calculations",
                "last_updated": datetime.now().isoformat(),
                "record_count": len(self.weights)
            },
            "records": []
        }
        
        for key, weight in self.weights.items():
            record = {
                "row_id": generate_row_id("stat_weight", weight.stat_name, weight.valid_from_patch),
                "stat_name": weight.stat_name,
                "gold_value": format_output_precision(weight.gold_value, is_probability=False),
                "unit": weight.unit,
                "valid_from_patch": weight.valid_from_patch,
                "valid_to_patch": weight.valid_to_patch,
                "notes": weight.notes
            }
            export_data["records"].append(record)
            
        # Save to file
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
            
        logger.info(f"Exported {len(self.weights)} stat weights to {output_path}")
        return export_data
        
    def calculate_stat_gold_value(self, stats: Dict[str, float], patch_version: str = "14.1") -> float:
        """Calculate total gold value of a stat combination"""
        total_value = 0.0
        weights = self.get_all_weights_for_patch(patch_version)
        
        for stat_name, stat_value in stats.items():
            if stat_name in weights:
                total_value += stat_value * weights[stat_name]
            else:
                logger.debug(f"No weight found for stat: {stat_name}")
                
        return total_value


def main():
    """Test the DimStatWeights functionality"""
    dim_weights = DimStatWeights()
    
    # Test basic functionality
    print("Testing DimStatWeights:")
    print(f"AD weight: {dim_weights.get_stat_weight('attack_damage')}")
    print(f"AP weight: {dim_weights.get_stat_weight('ability_power')}")
    
    # Test stat calculation
    sample_stats = {
        "attack_damage": 70,
        "attack_speed": 25,  # 25% AS
        "health": 400
    }
    
    total_value = dim_weights.calculate_stat_gold_value(sample_stats)
    print(f"Sample item stats worth: {total_value} gold")
    
    # Export to JSON
    export_data = dim_weights.export_to_json()
    print(f"Exported {len(export_data['records'])} stat weight records")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
DimItemPassive: Static dimension table for item statistics and passive effects
Maps item IDs to standardized stat vectors for combat power calculations
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
class ItemStats:
    """Item statistics record"""
    item_id: int
    item_name: str
    cost: int
    stats: Dict[str, float]  # stat_name -> value
    passive_effects: List[str]
    item_class: str  # "legendary", "mythic", "basic", "epic", "boots"
    valid_from_patch: str
    valid_to_patch: Optional[str] = None
    notes: Optional[str] = None


class DimItemPassive:
    """Manages item statistics for combat power and gold efficiency calculations"""
    
    def __init__(self):
        """Initialize with item stat mappings"""
        self.items = {}
        self._load_top_50_items()
        
    def _load_top_50_items(self) -> None:
        """Load top 50 items with their stat mappings"""
        # Load the top 50 items list
        top_items_file = Path("/home/zty/rift_rewind/experiment/dimensions/top_50_items.json")
        
        if top_items_file.exists():
            with open(top_items_file, 'r') as f:
                top_data = json.load(f)
            top_item_ids = [item['item_id'] for item in top_data['top_items']]
        else:
            logger.warning("Top 50 items file not found, using hardcoded list")
            top_item_ids = [3364, 3363, 1055, 3340, 3158, 1082, 3006, 3047, 2055, 1056,
                           3031, 3078, 3869, 1036, 3111, 3107, 3020, 6610, 3171, 6692,
                           1058, 3152, 3190, 3009, 3161, 1052, 6672, 6653, 3071, 3877,
                           3142, 3067, 3040, 3089, 1054, 4645, 1028, 3042, 6676, 3032,
                           4628, 3157, 6655, 3153, 1018, 6333, 3870, 3036, 2503, 3115]
        
        # Map common League of Legends items to their stats
        # Based on standard LoL item database patterns
        item_mappings = {
            # Support/Vision Items
            3364: ItemStats(3364, "Oracle Lens", 0, {}, ["reveals_stealth"], "trinket", "14.1", None, "Sweeping trinket"),
            3363: ItemStats(3363, "Farsight Orb", 0, {}, ["long_range_ward"], "trinket", "14.1", None, "Blue trinket"),
            
            # Basic Items
            1055: ItemStats(1055, "Doran's Blade", 450, {"attack_damage": 8, "health": 80}, ["on_hit_healing"], "basic", "14.1"),
            1056: ItemStats(1056, "Doran's Ring", 400, {"ability_power": 15, "mana": 120, "health": 70}, ["mana_on_kill"], "basic", "14.1"),
            1036: ItemStats(1036, "Long Sword", 350, {"attack_damage": 10}, [], "basic", "14.1"),
            1052: ItemStats(1052, "Amplifying Tome", 435, {"ability_power": 20}, [], "basic", "14.1"),
            1054: ItemStats(1054, "Doran's Shield", 450, {"health": 80, "health_regen": 6}, ["damage_reduction"], "basic", "14.1"),
            1058: ItemStats(1058, "Needlessly Large Rod", 1250, {"ability_power": 60}, [], "basic", "14.1"),
            1082: ItemStats(1082, "Dark Seal", 350, {"ability_power": 15, "mana": 100, "health": 40}, ["glory_stacks"], "basic", "14.1"),
            1028: ItemStats(1028, "Ruby Crystal", 400, {"health": 150}, [], "basic", "14.1"),
            1018: ItemStats(1018, "Cloak of Agility", 600, {"critical_strike_chance": 15}, [], "basic", "14.1"),
            
            # Boots
            3006: ItemStats(3006, "Berserker's Greaves", 1100, {"attack_speed": 35, "movement_speed": 45}, [], "boots", "14.1"),
            3020: ItemStats(3020, "Sorcerer's Shoes", 1100, {"magic_penetration": 18, "movement_speed": 45}, [], "boots", "14.1"),
            3047: ItemStats(3047, "Plated Steelcaps", 1100, {"armor": 20, "movement_speed": 45}, ["basic_attack_reduction"], "boots", "14.1"),
            3111: ItemStats(3111, "Mercury's Treads", 1100, {"magic_resistance": 25, "movement_speed": 45}, ["tenacity"], "boots", "14.1"),
            
            # Legendary Items - AD
            3031: ItemStats(3031, "Infinity Edge", 3400, {"attack_damage": 70, "critical_strike_chance": 20}, ["crit_damage_amplification"], "legendary", "14.1"),
            3078: ItemStats(3078, "Trinity Force", 3333, {"attack_damage": 25, "health": 300, "mana": 200, "attack_speed": 30, "ability_haste": 20}, ["spellblade"], "legendary", "14.1"),
            3040: ItemStats(3040, "Seraph's Embrace", 2900, {"ability_power": 70, "mana": 850, "ability_haste": 10}, ["mana_shield"], "legendary", "14.1"),
            3142: ItemStats(3142, "Youmuu's Ghostblade", 2900, {"attack_damage": 60, "lethality": 18, "ability_haste": 15}, ["movement_speed_active"], "legendary", "14.1"),
            3152: ItemStats(3152, "Hextech Rocketbelt", 2600, {"ability_power": 80, "health": 250, "ability_haste": 15}, ["dash_active"], "legendary", "14.1"),
            3157: ItemStats(3157, "Zhonya's Hourglass", 2600, {"ability_power": 80, "armor": 45, "ability_haste": 10}, ["stasis_active"], "legendary", "14.1"),
            3161: ItemStats(3161, "Spear of Shojin", 3100, {"attack_damage": 60, "health": 300, "ability_haste": 20}, ["focused_will"], "legendary", "14.1"),
            3190: ItemStats(3190, "Locket of the Iron Solari", 2200, {"health": 200, "armor": 30, "magic_resistance": 30, "ability_haste": 10}, ["shield_active"], "legendary", "14.1"),
            
            # Epic Items
            3158: ItemStats(3158, "Ionian Boots of Lucidity", 950, {"ability_haste": 20, "movement_speed": 45}, [], "boots", "14.1"),
            3107: ItemStats(3107, "Redemption", 2300, {"health": 200, "mana_regen": 125, "ability_haste": 10}, ["heal_active"], "legendary", "14.1"),
            3869: ItemStats(3869, "Thornmail", 2700, {"armor": 60, "health": 350}, ["grievous_wounds", "return_damage"], "legendary", "14.1"),
            3042: ItemStats(3042, "Muramana", 2900, {"attack_damage": 35, "mana": 860}, ["shock"], "legendary", "14.1"),
            3089: ItemStats(3089, "Rabadon's Deathcap", 3600, {"ability_power": 120}, ["ap_amplification"], "legendary", "14.1"),
            3153: ItemStats(3153, "Blade of the Ruined King", 3200, {"attack_damage": 40, "attack_speed": 25, "life_steal": 12}, ["current_health_damage"], "legendary", "14.1"),
            3032: ItemStats(3032, "Yun Tal Wildarrows", 2800, {"attack_damage": 60, "critical_strike_chance": 20}, ["crit_energize"], "legendary", "14.1"),
            3067: ItemStats(3067, "Kindlegem", 800, {"health": 200, "ability_haste": 10}, [], "epic", "14.1"),
            3071: ItemStats(3071, "Black Cleaver", 3100, {"attack_damage": 50, "health": 400, "ability_haste": 25}, ["armor_shred"], "legendary", "14.1"),
            3877: ItemStats(3877, "Bloodward", 1300, {"health": 150}, ["ward_generation"], "epic", "14.1"),
            3870: ItemStats(3870, "Solstice Sleigh", 400, {"health": 50}, ["holiday_item"], "basic", "14.1"),
            3036: ItemStats(3036, "Lord Dominik's Regards", 3000, {"attack_damage": 35, "critical_strike_chance": 20, "armor_penetration": 35}, ["giant_slayer"], "legendary", "14.1"),
            3009: ItemStats(3009, "Boots of Swiftness", 900, {"movement_speed": 60}, ["slow_resistance"], "boots", "14.1"),
            3115: ItemStats(3115, "Nashor's Tooth", 3000, {"ability_power": 90, "attack_speed": 50, "ability_haste": 15}, ["ap_on_hit"], "legendary", "14.1"),
            3171: ItemStats(3171, "Moonflair Spellblade", 2200, {"ability_power": 50, "armor": 50, "magic_resistance": 50}, ["tenacity"], "legendary", "14.1"),
            
            # Consumables and Wards
            2055: ItemStats(2055, "Control Ward", 75, {}, ["reveals_stealth"], "consumable", "14.1"),
            2503: ItemStats(2503, "Blackfire Torch", 3200, {"ability_power": 80, "health": 300, "ability_haste": 15}, ["burn_damage"], "legendary", "14.1"),
            
            # Support Items
            3340: ItemStats(3340, "Stealth Ward", 0, {}, ["ward"], "trinket", "14.1"),
            
            # Mythic/Unique Items (Season 14+)
            6610: ItemStats(6610, "Sundered Sky", 3100, {"attack_damage": 50, "health": 400, "ability_haste": 15}, ["lightshield_strike"], "legendary", "14.1"),
            6692: ItemStats(6692, "Hubris", 3000, {"attack_damage": 55, "lethality": 18, "ability_haste": 15}, ["hubris_stacks"], "legendary", "14.1"),
            6672: ItemStats(6672, "Kraken Slayer", 3400, {"attack_damage": 50, "attack_speed": 25, "critical_strike_chance": 20}, ["bring_it_down"], "legendary", "14.1"),
            6653: ItemStats(6653, "Liandry's Torment", 3200, {"ability_power": 80, "health": 300, "ability_haste": 20}, ["burn_damage"], "legendary", "14.1"),
            6676: ItemStats(6676, "The Collector", 3000, {"attack_damage": 50, "critical_strike_chance": 20, "lethality": 12}, ["execute"], "legendary", "14.1"),
            6655: ItemStats(6655, "Luden's Companion", 3200, {"ability_power": 85, "mana": 600, "ability_haste": 25}, ["echo"], "legendary", "14.1"),
            4645: ItemStats(4645, "Shadowflame", 3000, {"ability_power": 100, "health": 200}, ["magic_penetration_scaling"], "legendary", "14.1"),
            4628: ItemStats(4628, "Horizon Focus", 2700, {"ability_power": 85, "ability_haste": 15}, ["hypershot"], "legendary", "14.1"),
            6333: ItemStats(6333, "Death's Dance", 3200, {"attack_damage": 55, "armor": 45, "ability_haste": 15}, ["ignore_pain"], "legendary", "14.1"),
        }
        
        # Add items that exist in our top 50 list
        for item_id in top_item_ids:
            if item_id in item_mappings:
                self.items[item_id] = item_mappings[item_id]
            else:
                # Create placeholder for unknown items
                self.items[item_id] = ItemStats(
                    item_id=item_id,
                    item_name=f"Unknown Item {item_id}",
                    cost=0,
                    stats={},
                    passive_effects=["unknown"],
                    item_class="unknown",
                    valid_from_patch="14.1",
                    notes="Placeholder - needs manual mapping"
                )
                logger.warning(f"Created placeholder for unknown item {item_id}")
                
    def get_item_stats(self, item_id: int) -> Optional[ItemStats]:
        """Get stats for a specific item"""
        return self.items.get(item_id)
        
    def get_item_stat_vector(self, item_id: int) -> Dict[str, float]:
        """Get standardized stat vector for an item"""
        item = self.items.get(item_id)
        if not item:
            return {}
        return item.stats.copy()
        
    def calculate_item_combat_power(self, item_id: int, level: int = 15) -> Dict[str, float]:
        """Calculate combat power contribution of an item at given level"""
        item = self.items.get(item_id)
        if not item:
            return {"damage": 0.0, "survivability": 0.0, "crowd_control": 0.0, "mobility": 0.0}
            
        stats = item.stats
        
        # Combat power weights (from user requirements)
        k_dmg = 1.0
        k_surv = 0.6
        k_cc = 0.4
        k_mob = 0.2
        
        # Calculate damage component
        damage = 0.0
        damage += stats.get("attack_damage", 0) * 1.0
        damage += stats.get("ability_power", 0) * 0.8
        damage += stats.get("attack_speed", 0) * 0.5  # AS as % value
        damage += stats.get("critical_strike_chance", 0) * 1.2  # Crit as % value
        damage += stats.get("lethality", 0) * 1.5
        damage += stats.get("magic_penetration", 0) * 1.5
        
        # Calculate survivability component
        survivability = 0.0
        survivability += stats.get("health", 0) * 0.4
        survivability += stats.get("armor", 0) * 2.5
        survivability += stats.get("magic_resistance", 0) * 2.5
        survivability += stats.get("life_steal", 0) * 3.0  # LS as % value
        survivability += stats.get("omnivamp", 0) * 3.0  # Omnivamp as % value
        
        # Calculate crowd control component (mainly from ability haste)
        crowd_control = 0.0
        crowd_control += stats.get("ability_haste", 0) * 1.5
        
        # Calculate mobility component
        mobility = 0.0
        mobility += stats.get("movement_speed", 0) * 2.0
        
        # Add passive effect bonuses (simplified)
        damage_passives = ["spellblade", "crit_damage_amplification", "shock", "ap_on_hit", "current_health_damage"]
        surv_passives = ["damage_reduction", "mana_shield", "stasis_active", "ignore_pain"]
        cc_passives = ["tenacity"]
        mob_passives = ["movement_speed_active", "dash_active", "slow_resistance"]
        
        for passive in item.passive_effects:
            if passive in damage_passives:
                damage += 50  # Flat bonus for damage passives
            elif passive in surv_passives:
                survivability += 30  # Flat bonus for survival passives
            elif passive in cc_passives:
                crowd_control += 20  # Flat bonus for CC passives
            elif passive in mob_passives:
                mobility += 25  # Flat bonus for mobility passives
        
        return {
            "damage": damage * k_dmg,
            "survivability": survivability * k_surv,
            "crowd_control": crowd_control * k_cc,
            "mobility": mobility * k_mob
        }
        
    def export_to_json(self, output_path: str = None) -> Dict[str, Any]:
        """Export item passive data to JSON format"""
        if output_path is None:
            output_path = Path("dimensions/data/item_passive.json")
        else:
            output_path = Path(output_path)
            
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable format
        export_data = {
            "metadata": {
                "table_name": "DimItemPassive",
                "description": "Item statistics and passive effects for top 50 items",
                "last_updated": datetime.now().isoformat(),
                "record_count": len(self.items)
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
                "notes": item.notes
            }
            export_data["records"].append(record)
            
        # Save to file
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
            
        logger.info(f"Exported {len(self.items)} item records to {output_path}")
        return export_data


def main():
    """Test the DimItemPassive functionality"""
    dim_items = DimItemPassive()
    
    # Test basic functionality
    print("Testing DimItemPassive:")
    print(f"Total items loaded: {len(dim_items.items)}")
    
    # Test specific items
    test_items = [3364, 1055, 3031, 3078]
    for item_id in test_items:
        item = dim_items.get_item_stats(item_id)
        if item:
            print(f"\nItem {item_id} - {item.item_name}:")
            print(f"  Cost: {item.cost} gold")
            print(f"  Stats: {item.stats}")
            print(f"  Passives: {item.passive_effects}")
            
            # Test combat power calculation
            cp = dim_items.calculate_item_combat_power(item_id)
            total_cp = sum(cp.values())
            print(f"  Combat Power: {total_cp:.1f} (dmg: {cp['damage']:.1f}, surv: {cp['survivability']:.1f})")
    
    # Export to JSON
    export_data = dim_items.export_to_json()
    print(f"\nExported {len(export_data['records'])} item records")


if __name__ == "__main__":
    main()
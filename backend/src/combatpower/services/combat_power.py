"""
Combat Power calculation system with multi-patch support
"""
import math
from typing import Dict, Any, List, Optional
from .data_dragon import data_dragon
from .data_provider import data_provider
from .meta_builds import meta_builds_db


class CombatPowerCalculator:
    """
    Calculate champion combat power based on:
    1. Base stats (attack, defense, health, growth)
    2. Abilities (damage, cooldown, CC duration, range)
    3. Items (stats + passive effects)
    4. Runes (stats + effects)
    
    Formula converts everything to equivalent damage/survivability per minute
    """
    
    # Conversion rates for combat power
    ATTACK_DAMAGE_RATE = 2.0  # 1 AD = 2 combat power
    ABILITY_POWER_RATE = 1.5  # 1 AP = 1.5 combat power
    ARMOR_RATE = 1.5  # 1 Armor = 1.5 combat power
    MAGIC_RESIST_RATE = 1.5  # 1 MR = 1.5 combat power
    HEALTH_RATE = 0.5  # 1 HP = 0.5 combat power
    ATTACK_SPEED_RATE = 25.0  # 1% AS = 25 combat power
    CRIT_CHANCE_RATE = 30.0  # 1% Crit = 30 combat power
    CRIT_DAMAGE_RATE = 20.0  # 1% Crit Dmg = 20 combat power
    LIFESTEAL_RATE = 20.0  # 1% Lifesteal = 20 combat power
    OMNIVAMP_RATE = 25.0  # 1% Omnivamp = 25 combat power
    ABILITY_HASTE_RATE = 3.0  # 1 AH = 3 combat power
    LETHALITY_RATE = 4.0  # 1 Lethality = 4 combat power
    ARMOR_PEN_RATE = 3.5  # 1% Armor Pen = 3.5 combat power
    MAGIC_PEN_RATE = 5.0  # 1 Magic Pen = 5 combat power
    MOVE_SPEED_RATE = 1.0  # 1 MS = 1 combat power
    
    def __init__(self):
        self.champions_cache = {}
        self.items_cache = {}
        self.runes_cache = {}
        
    def calculate_base_stats_power(self, champion_stats: Dict[str, Any], level: int = 18) -> float:
        """
        Calculate combat power from champion base stats at given level
        """
        stats = champion_stats
        
        # Get base and per-level stats
        base_hp = float(stats.get('hp', 0))
        hp_per_level = float(stats.get('hpperlevel', 0))
        base_ad = float(stats.get('attackdamage', 0))
        ad_per_level = float(stats.get('attackdamageperlevel', 0))
        base_armor = float(stats.get('armor', 0))
        armor_per_level = float(stats.get('armorperlevel', 0))
        base_mr = float(stats.get('spellblock', 0))
        mr_per_level = float(stats.get('spellblockperlevel', 0))
        base_as = float(stats.get('attackspeed', 0.625))
        as_per_level = float(stats.get('attackspeedperlevel', 0))
        
        # Calculate level-scaled stats
        hp = base_hp + (hp_per_level * (level - 1))
        ad = base_ad + (ad_per_level * (level - 1))
        armor = base_armor + (armor_per_level * (level - 1))
        mr = base_mr + (mr_per_level * (level - 1))
        attack_speed = base_as * (1 + (as_per_level / 100) * (level - 1))
        
        # Calculate combat power
        power = 0.0
        power += hp * self.HEALTH_RATE
        power += ad * self.ATTACK_DAMAGE_RATE
        power += armor * self.ARMOR_RATE
        power += mr * self.MAGIC_RESIST_RATE
        power += (attack_speed - 0.625) * 100 * self.ATTACK_SPEED_RATE  # Bonus AS as percentage
        
        return power
    
    def calculate_skill_power(self, champion_detail: Dict[str, Any]) -> float:
        """
        Calculate combat power from champion skills (Q, W, E, R, Passive)
        Simplified: uses skill damage and base values
        """
        power = 0.0
        spells = champion_detail.get('spells', [])
        
        for spell in spells:
            # Get max rank damage
            damage = spell.get('effectBurn', [])
            cooldown = spell.get('cooldownBurn', '0')
            
            # Parse cooldown (take last value for max rank)
            try:
                cd_values = [float(x) for x in cooldown.split('/')]
                cd = cd_values[-1] if cd_values else 8.0
            except:
                cd = 8.0
                
            # Estimate damage per cast (simplified)
            if damage and len(damage) > 0:
                try:
                    # First effect is usually damage
                    dmg_str = damage[0] if isinstance(damage[0], str) else '0'
                    dmg_value = float(dmg_str.replace('%', ''))
                    # Damage per minute = damage / cooldown * 60
                    dpm = (dmg_value / max(cd, 1)) * 60
                    power += dpm * 0.1  # Scale down to reasonable values
                except:
                    pass
        
        # Passive ability bonus
        passive = champion_detail.get('passive', {})
        if passive:
            power += 100  # Flat bonus for having a passive
            
        return power
    
    def calculate_item_power(self, item_ids: List[int]) -> float:
        """
        Calculate combat power from items
        """
        items = data_dragon.get_items()
        power = 0.0
        
        for item_id in item_ids:
            item_str = str(item_id)
            if item_str not in items:
                continue
                
            item = items[item_str]
            stats = item.get('stats', {})
            
            # Add stat bonuses
            power += stats.get('FlatPhysicalDamageMod', 0) * self.ATTACK_DAMAGE_RATE
            power += stats.get('FlatMagicDamageMod', 0) * self.ABILITY_POWER_RATE
            power += stats.get('FlatHPPoolMod', 0) * self.HEALTH_RATE
            power += stats.get('FlatArmorMod', 0) * self.ARMOR_RATE
            power += stats.get('FlatSpellBlockMod', 0) * self.MAGIC_RESIST_RATE
            power += stats.get('PercentAttackSpeedMod', 0) * 100 * self.ATTACK_SPEED_RATE
            power += stats.get('FlatCritChanceMod', 0) * 100 * self.CRIT_CHANCE_RATE
            power += stats.get('PercentLifeStealMod', 0) * 100 * self.LIFESTEAL_RATE
            power += stats.get('FlatMovementSpeedMod', 0) * self.MOVE_SPEED_RATE
            
        return power
    
    def calculate_rune_power(self, rune_ids: List[int], primary_style: int, sub_style: int) -> float:
        """
        Calculate combat power from runes
        Simplified: assigns fixed values to rune paths
        """
        power = 0.0
        
        # Rune path bonuses (simplified)
        rune_path_power = {
            8000: 150,  # Precision
            8100: 120,  # Domination
            8200: 130,  # Sorcery
            8300: 140,  # Inspiration
            8400: 160,  # Resolve
        }
        
        power += rune_path_power.get(primary_style, 100)
        power += rune_path_power.get(sub_style, 50) * 0.5
        
        # Additional power per selected rune
        power += len(rune_ids) * 20
        
        return power
    
    def calculate_total_combat_power(
        self,
        champion_name: str,
        level: int = 18,
        item_ids: List[int] = None,
        rune_ids: List[int] = None,
        primary_style: int = None,
        sub_style: int = None,
        patch: Optional[str] = None
    ) -> float:
        """
        Calculate total combat power for a champion with items and runes
        
        Args:
            champion_name: Champion name
            level: Champion level
            item_ids: List of item IDs
            rune_ids: List of rune IDs
            primary_style: Primary rune path ID
            sub_style: Secondary rune path ID
            patch: Specific patch version (e.g., '14.19'). If None, uses default Data Dragon
        """
        # Get champion data (patch-specific or default)
        if patch:
            champions = data_provider.get_champions_for_patch(patch)
            champion_detail = data_provider.get_champion_detail_for_patch(patch, champion_name)
        else:
            champions = data_dragon.get_champions()
            champion_detail = data_dragon.get_champion_detail(champion_name)
        
        if champion_name not in champions:
            return 0.0
            
        champion_stats = champions[champion_name]['stats']
        
        # Calculate components
        base_power = self.calculate_base_stats_power(champion_stats, level)
        skill_power = self.calculate_skill_power(champion_detail)
        
        item_power = 0.0
        if item_ids:
            item_power = self.calculate_item_power(item_ids)
            
        rune_power = 0.0
        if rune_ids and primary_style and sub_style:
            rune_power = self.calculate_rune_power(rune_ids, primary_style, sub_style)
            
        total_power = base_power + skill_power + item_power + rune_power
        
        return total_power
    
    def calculate_all_champions_base_stats_only(self, patch: Optional[str] = None) -> Dict[str, float]:
        """
        Calculate base stats power for all champions (FAST - no skill power calculation)
        Used for player classification where we only need relative strength, not absolute power

        Args:
            patch: Specific patch version

        Returns:
            Dictionary of champion name to base stats power
        """
        if patch:
            champions = data_provider.get_champions_for_patch(patch)
        else:
            champions = data_dragon.get_champions()

        result = {}

        for champion_name in champions.keys():
            try:
                champion_stats = champions[champion_name]['stats']
                # Only calculate base stats power (no skill calculation = FAST)
                power = self.calculate_base_stats_power(champion_stats, 18)
                result[champion_name] = power
            except Exception as e:
                print(f"Error calculating base power for {champion_name}: {e}")
                result[champion_name] = 1000.0  # Default fallback

        return result

    def calculate_all_champions_base_power(self, include_builds: bool = False, patch: Optional[str] = None) -> Dict[str, float]:
        """
        Calculate combat power for all champions

        Args:
            include_builds: If True, includes meta items and runes
            patch: Specific patch version

        Returns:
            Dictionary of champion name to combat power
        """
        if patch:
            champions = data_provider.get_champions_for_patch(patch)
        else:
            champions = data_dragon.get_champions()

        result = {}

        for champion_name in champions.keys():
            try:
                if patch:
                    champion_detail = data_provider.get_champion_detail_for_patch(patch, champion_name)
                else:
                    champion_detail = data_dragon.get_champion_detail(champion_name)

                champion_stats = champions[champion_name]['stats']

                if include_builds:
                    # Get meta build for this champion (with champion detail for intelligent classification)
                    meta_build = meta_builds_db.get_meta_build(champion_name, patch, champion_detail)

                    power = self.calculate_total_combat_power(
                        champion_name=champion_name,
                        level=18,
                        item_ids=meta_build['items'],
                        rune_ids=meta_build['runes'],
                        primary_style=meta_build['primary_style'],
                        sub_style=meta_build['sub_style'],
                        patch=patch
                    )
                else:
                    base_power = self.calculate_base_stats_power(champion_stats, 18)
                    skill_power = self.calculate_skill_power(champion_detail)
                    power = base_power + skill_power

                result[champion_name] = power
            except Exception as e:
                print(f"Error calculating power for {champion_name}: {e}")
                result[champion_name] = 1000.0  # Default fallback

        return result


# Singleton instance
combat_power_calculator = CombatPowerCalculator()


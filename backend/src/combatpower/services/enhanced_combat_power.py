"""
Enhanced Combat Power Calculator
Improves skill power, item synergy, and rune system calculations
"""
import math
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from .data_dragon import data_dragon
from .data_provider import data_provider


class EnhancedCombatPowerCalculator:
    """
    Enhanced combat power calculation with:
    1. Advanced skill power (CC, range, AoE, interactions)
    2. Item synergy bonuses
    3. Individual rune analysis with champion scaling
    """
    
    # Base conversion rates (unchanged)
    ATTACK_DAMAGE_RATE = 2.0
    ABILITY_POWER_RATE = 1.5
    ARMOR_RATE = 1.5
    MAGIC_RESIST_RATE = 1.5
    HEALTH_RATE = 0.5
    ATTACK_SPEED_RATE = 25.0
    CRIT_CHANCE_RATE = 30.0
    CRIT_DAMAGE_RATE = 20.0
    LIFESTEAL_RATE = 20.0
    OMNIVAMP_RATE = 25.0
    ABILITY_HASTE_RATE = 3.0
    LETHALITY_RATE = 4.0
    ARMOR_PEN_RATE = 3.5
    MAGIC_PEN_RATE = 5.0
    MOVE_SPEED_RATE = 1.0
    
    # Enhanced skill power rates
    BASE_DAMAGE_RATE = 0.1
    CC_DURATION_RATE = 50.0  # Per second of CC
    RANGE_BONUS_RATE = 0.5   # Per 100 units of range
    AOE_BONUS_RATE = 0.3     # Per 100 units of AoE radius
    SKILL_INTERACTION_BONUS = 25.0  # For skill combos
    
    def __init__(self):
        self.champions_cache = {}
        self.items_cache = {}
        self.runes_cache = {}
        self.item_synergies = self._load_item_synergies()
        self.rune_power_map = self._load_rune_power_map()
        
    def _load_item_synergies(self) -> Dict[str, Dict[str, float]]:
        """Load item synergy bonuses"""
        return {
            # Critical Strike Synergies
            "crit_synergy": {
                "items": [3031, 3036, 3508, 3094],  # IE, RFC, ER, Stormrazor
                "bonus_per_item": 50.0,
                "max_items": 3
            },
            # Lethality Synergies  
            "lethality_synergy": {
                "items": [6691, 6692, 6693, 6694],  # Duskblade, Youmuu's, Edge of Night, Serpent's Fang
                "bonus_per_item": 40.0,
                "max_items": 3
            },
            # Tank Synergies
            "tank_synergy": {
                "items": [3065, 3071, 3748, 3111],  # Thornmail, Randuin's, Dead Man's, Warmog's
                "bonus_per_item": 60.0,
                "max_items": 3
            },
            # AP Synergies
            "ap_synergy": {
                "items": [3089, 3135, 3157, 4645],  # Rabadon's, Void Staff, Zhonya's, Cosmic Drive
                "bonus_per_item": 45.0,
                "max_items": 3
            },
            # Support Synergies
            "support_synergy": {
                "items": [2065, 3107, 3504, 6616],  # Shurelya's, Redemption, Ardent Censer, Staff of Flowing Water
                "bonus_per_item": 35.0,
                "max_items": 3
            }
        }
    
    def _load_rune_power_map(self) -> Dict[int, Dict[str, Any]]:
        """Load individual rune power values"""
        return {
            # Precision Tree (8000)
            8005: {"name": "Press the Attack", "base_power": 80, "scaling": "ad"},
            8008: {"name": "Lethal Tempo", "base_power": 70, "scaling": "as"},
            8010: {"name": "Conqueror", "base_power": 90, "scaling": "ad"},
            8021: {"name": "Fleet Footwork", "base_power": 60, "scaling": "ms"},
            9111: {"name": "Triumph", "base_power": 40, "scaling": "sustain"},
            9104: {"name": "Legend: Alacrity", "base_power": 35, "scaling": "as"},
            8014: {"name": "Coup de Grace", "base_power": 30, "scaling": "ad"},
            
            # Domination Tree (8100)
            8112: {"name": "Electrocute", "base_power": 85, "scaling": "ap"},
            8128: {"name": "Dark Harvest", "base_power": 75, "scaling": "ap"},
            9923: {"name": "Hail of Blades", "base_power": 65, "scaling": "as"},
            8139: {"name": "Cheap Shot", "base_power": 25, "scaling": "true_damage"},
            8135: {"name": "Taste of Blood", "base_power": 20, "scaling": "sustain"},
            8138: {"name": "Eyeball Collection", "base_power": 30, "scaling": "ad"},
            
            # Sorcery Tree (8200)
            8214: {"name": "Summon Aery", "base_power": 50, "scaling": "ap"},
            8229: {"name": "Arcane Comet", "base_power": 70, "scaling": "ap"},
            8230: {"name": "Phase Rush", "base_power": 55, "scaling": "ms"},
            8234: {"name": "Nullifying Orb", "base_power": 25, "scaling": "mr"},
            8237: {"name": "Manaflow Band", "base_power": 20, "scaling": "mana"},
            8242: {"name": "Transcendence", "base_power": 40, "scaling": "cdr"},
            
            # Resolve Tree (8400)
            8437: {"name": "Grasp of the Undying", "base_power": 60, "scaling": "hp"},
            8439: {"name": "Aftershock", "base_power": 80, "scaling": "tank"},
            8465: {"name": "Guardian", "base_power": 45, "scaling": "support"},
            8473: {"name": "Bone Plating", "base_power": 30, "scaling": "tank"},
            8444: {"name": "Second Wind", "base_power": 25, "scaling": "sustain"},
            8451: {"name": "Overgrowth", "base_power": 35, "scaling": "hp"},
            
            # Inspiration Tree (8300)
            8351: {"name": "Glacial Augment", "base_power": 50, "scaling": "utility"},
            8360: {"name": "Unsealed Spellbook", "base_power": 40, "scaling": "utility"},
            8358: {"name": "First Strike", "base_power": 70, "scaling": "gold"},
            8304: {"name": "Hextech Flashtraption", "base_power": 20, "scaling": "utility"},
            8313: {"name": "Perfect Timing", "base_power": 15, "scaling": "utility"},
            8321: {"name": "Future's Market", "base_power": 10, "scaling": "gold"},
            
            # Stat Shards
            5002: {"name": "Adaptive Force", "base_power": 15, "scaling": "adaptive"},
            5005: {"name": "Attack Speed", "base_power": 12, "scaling": "as"},
            5008: {"name": "Armor", "base_power": 10, "scaling": "armor"},
            5001: {"name": "Health", "base_power": 8, "scaling": "hp"},
            5003: {"name": "Magic Resist", "base_power": 10, "scaling": "mr"},
            5007: {"name": "Ability Haste", "base_power": 12, "scaling": "cdr"}
        }
    
    def calculate_enhanced_skill_power(self, champion_detail: Dict[str, Any], champion_stats: Dict[str, Any]) -> float:
        """
        Enhanced skill power calculation considering:
        - All active abilities (Q, W, E, R)
        - Champion passive abilities
        - CC duration and type
        - Range and AoE
        - Skill interactions
        - Scaling ratios
        """
        power = 0.0
        spells = champion_detail.get('spells', [])
        
        # Analyze each active skill (Q, W, E, R)
        skill_data = []
        for i, spell in enumerate(spells):
            skill_info = self._analyze_skill(spell, champion_stats)
            skill_data.append(skill_info)
            power += skill_info['base_power']
        
        # Calculate skill interaction bonuses
        interaction_bonus = self._calculate_skill_interactions(skill_data)
        power += interaction_bonus
        
        # Enhanced passive ability analysis
        passive_power = self._analyze_champion_passive(champion_detail.get('passive', {}), champion_stats, champion_detail)
        power += passive_power
        
        return power
    
    def _analyze_skill(self, spell: Dict[str, Any], champion_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze individual active skill for power calculation"""
        power = 0.0
        
        # Base damage analysis
        damage_values = spell.get('effectBurn', [])
        if damage_values:
            try:
                # Get max rank damage (last value)
                dmg_str = damage_values[0] if isinstance(damage_values[0], str) else '0'
                base_damage = float(dmg_str.replace('%', ''))
                power += base_damage * self.BASE_DAMAGE_RATE
            except:
                pass
        
        # Cooldown analysis
        cooldown = spell.get('cooldownBurn', '0')
        try:
            cd_values = [float(x) for x in cooldown.split('/')]
            cd = cd_values[-1] if cd_values else 8.0
            # Lower cooldown = higher power
            power += max(0, (10 - cd) * 5)
        except:
            pass
        
        # Range analysis
        range_values = spell.get('rangeBurn', [])
        if range_values:
            try:
                range_val = float(range_values[0])
                power += (range_val / 100) * self.RANGE_BONUS_RATE
            except:
                pass
        
        # Enhanced CC analysis (from tooltip)
        tooltip = spell.get('tooltip', '')
        cc_power = self._extract_cc_power(tooltip)
        power += cc_power
        
        # Enhanced AoE analysis
        aoe_power = self._extract_aoe_power(tooltip)
        power += aoe_power
        
        # Skill type bonus (Ultimate gets bonus)
        if spell.get('name', '').endswith('Ultimate') or 'ultimate' in spell.get('name', '').lower():
            power += 50  # Ultimate bonus
        
        # Scaling analysis
        scaling_power = self._analyze_scaling(spell, champion_stats)
        power += scaling_power
        
        return {
            'name': spell.get('name', 'Unknown'),
            'base_power': power,
            'cooldown': cd if 'cd' in locals() else 8.0,
            'range': range_val if 'range_val' in locals() else 0,
            'cc_duration': cc_power / self.CC_DURATION_RATE,
            'aoe_radius': aoe_power / self.AOE_BONUS_RATE,
            'is_ultimate': spell.get('name', '').endswith('Ultimate') or 'ultimate' in spell.get('name', '').lower()
        }
    
    def _extract_cc_power(self, tooltip: str) -> float:
        """Extract CC duration from tooltip text"""
        cc_keywords = {
            'stun': 1.5, 'root': 1.0, 'slow': 0.5, 'silence': 1.0,
            'fear': 1.5, 'charm': 1.0, 'knockup': 1.0, 'knockback': 0.5,
            'taunt': 1.0, 'sleep': 2.0, 'suppress': 2.5
        }
        
        power = 0.0
        tooltip_lower = tooltip.lower()
        
        for cc_type, duration in cc_keywords.items():
            if cc_type in tooltip_lower:
                power += duration * self.CC_DURATION_RATE
        
        return power
    
    def _analyze_scaling(self, spell: Dict[str, Any], champion_stats: Dict[str, Any]) -> float:
        """Analyze skill scaling ratios"""
        power = 0.0
        
        # Look for scaling ratios in tooltip
        tooltip = spell.get('tooltip', '')
        
        # AD scaling
        ad_scaling = self._extract_scaling_ratio(tooltip, ['attack damage', 'ad', 'physical damage'])
        if ad_scaling > 0:
            base_ad = float(champion_stats.get('attackdamage', 0))
            power += ad_scaling * base_ad * 0.1
        
        # AP scaling
        ap_scaling = self._extract_scaling_ratio(tooltip, ['ability power', 'ap', 'magic damage'])
        if ap_scaling > 0:
            # Use attack damage as proxy for AP scaling potential
            base_ad = float(champion_stats.get('attackdamage', 0))
            power += ap_scaling * (100 - base_ad) * 0.1
        
        return power
    
    def _extract_scaling_ratio(self, tooltip: str, keywords: List[str]) -> float:
        """Extract scaling ratio from tooltip"""
        import re
        
        tooltip_lower = tooltip.lower()
        for keyword in keywords:
            # Look for percentage scaling
            pattern = rf'{keyword}[^%]*(\d+(?:\.\d+)?)%'
            matches = re.findall(pattern, tooltip_lower)
            if matches:
                try:
                    return float(matches[0]) / 100  # Convert percentage to ratio
                except:
                    pass
        
        return 0.0
    
    def _extract_aoe_power(self, tooltip: str) -> float:
        """Extract AoE radius from tooltip text"""
        import re
        
        # Common AoE patterns
        radius_patterns = [
            r'(\d+)\s*units?\s*(?:radius|range)',
            r'radius\s*of\s*(\d+)',
            r'(\d+)\s*unit\s*area'
        ]
        
        power = 0.0
        for pattern in radius_patterns:
            matches = re.findall(pattern, tooltip.lower())
            if matches:
                try:
                    radius = float(matches[0])
                    power += (radius / 100) * self.AOE_BONUS_RATE
                except:
                    pass
        
        return power
    
    def _calculate_skill_interactions(self, skill_data: List[Dict[str, Any]]) -> float:
        """Calculate bonuses for skill combinations"""
        bonus = 0.0
        
        # Check for skill combos (simplified)
        if len(skill_data) >= 2:
            # Bonus for having multiple skills with CC
            cc_skills = sum(1 for skill in skill_data if skill['cc_duration'] > 0)
            if cc_skills >= 2:
                bonus += self.SKILL_INTERACTION_BONUS
            
            # Bonus for having multiple AoE skills
            aoe_skills = sum(1 for skill in skill_data if skill['aoe_radius'] > 0)
            if aoe_skills >= 2:
                bonus += self.SKILL_INTERACTION_BONUS * 0.5
        
        return bonus
    
    def _analyze_champion_passive(self, passive: Dict[str, Any], champion_stats: Dict[str, Any], champion_detail: Dict[str, Any]) -> float:
        """Enhanced champion passive ability analysis"""
        if not passive:
            return 0.0
        
        power = 100.0  # Base passive power (increased from 50)
        
        # Analyze passive description for additional power
        description = passive.get('description', '').lower()
        name = passive.get('name', '').lower()
        
        # Passive bonuses based on description keywords
        if 'damage' in description or 'damage' in name:
            power += 50
        if 'heal' in description or 'regeneration' in description or 'heal' in name:
            power += 40
        if 'shield' in description or 'shield' in name:
            power += 35
        if 'movement' in description or 'speed' in description or 'dash' in description:
            power += 30
        if 'cooldown' in description or 'ability' in description:
            power += 25
        if 'critical' in description or 'crit' in description:
            power += 45
        if 'attack speed' in description or 'attackspeed' in description:
            power += 35
        if 'lifesteal' in description or 'vamp' in description:
            power += 30
        if 'armor' in description or 'magic resist' in description or 'defense' in description:
            power += 25
        if 'true damage' in description:
            power += 60  # True damage is very powerful
        
        # Champion-specific passive bonuses
        champion_name = champion_detail.get('name', '').lower()
        if 'yasuo' in champion_name:
            power += 30  # Double crit chance
        elif 'vayne' in champion_name:
            power += 40  # Silver Bolts true damage
        elif 'jinx' in champion_name:
            power += 35  # Get Excited movement speed
        elif 'darius' in champion_name:
            power += 50  # Hemorrhage stacks
        elif 'garen' in champion_name:
            power += 30  # Regeneration
        
        return power
    
    def calculate_item_synergy_power(self, item_ids: List[int]) -> float:
        """Calculate synergy bonuses for item combinations"""
        synergy_power = 0.0
        
        for synergy_name, synergy_data in self.item_synergies.items():
            synergy_items = synergy_data['items']
            bonus_per_item = synergy_data['bonus_per_item']
            max_items = synergy_data['max_items']
            
            # Count how many synergy items are present
            synergy_count = sum(1 for item_id in item_ids if item_id in synergy_items)
            
            if synergy_count >= 2:  # Minimum 2 items for synergy
                # Apply diminishing returns
                effective_items = min(synergy_count, max_items)
                synergy_bonus = bonus_per_item * (effective_items - 1)  # -1 because first item doesn't give synergy
                synergy_power += synergy_bonus
        
        return synergy_power
    
    def calculate_enhanced_rune_power(self, rune_ids: List[int], primary_style: int, sub_style: int, champion_stats: Dict[str, Any]) -> float:
        """Enhanced rune power calculation with individual rune analysis and champion scaling"""
        power = 0.0
        
        # Calculate individual rune power
        for rune_id in rune_ids:
            if rune_id in self.rune_power_map:
                rune_data = self.rune_power_map[rune_id]
                base_power = rune_data['base_power']
                scaling_type = rune_data['scaling']
                
                # Apply champion-specific scaling
                scaled_power = self._apply_rune_scaling(base_power, scaling_type, champion_stats)
                power += scaled_power
        
        # Primary/Secondary path bonuses
        path_bonuses = {
            8000: 50,  # Precision
            8100: 40,  # Domination  
            8200: 45,  # Sorcery
            8300: 35,  # Inspiration
            8400: 55   # Resolve
        }
        
        power += path_bonuses.get(primary_style, 30)
        power += path_bonuses.get(sub_style, 20) * 0.5
        
        return power
    
    def _apply_rune_scaling(self, base_power: float, scaling_type: str, champion_stats: Dict[str, Any]) -> float:
        """Apply champion-specific scaling to rune power"""
        scaling_multiplier = 1.0
        
        if scaling_type == 'ad':
            # AD scaling champions get more from AD runes
            base_ad = float(champion_stats.get('attackdamage', 0))
            scaling_multiplier = 1.0 + (base_ad - 50) / 200  # Scale around 50 base AD
        
        elif scaling_type == 'ap':
            # AP scaling champions get more from AP runes
            # Use attack damage as proxy for AP scaling (simplified)
            base_ad = float(champion_stats.get('attackdamage', 0))
            scaling_multiplier = 1.0 + (100 - base_ad) / 200  # Inverse relationship
        
        elif scaling_type == 'tank':
            # Tank champions get more from defensive runes
            base_hp = float(champion_stats.get('hp', 0))
            scaling_multiplier = 1.0 + (base_hp - 500) / 1000  # Scale around 500 base HP
        
        elif scaling_type == 'as':
            # Attack speed scaling
            base_as = float(champion_stats.get('attackspeed', 0.625))
            scaling_multiplier = 1.0 + (base_as - 0.625) * 2
        
        # Clamp scaling multiplier
        scaling_multiplier = max(0.5, min(2.0, scaling_multiplier))
        
        return base_power * scaling_multiplier
    
    def calculate_total_enhanced_combat_power(
        self,
        champion_name: str,
        level: int = 18,
        item_ids: List[int] = None,
        rune_ids: List[int] = None,
        primary_style: int = None,
        sub_style: int = None,
        patch: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate total enhanced combat power with detailed breakdown
        
        Returns:
            Dict with detailed power breakdown
        """
        # Get champion data
        if patch:
            champions = data_provider.get_champions_for_patch(patch)
            champion_detail = data_provider.get_champion_detail_for_patch(patch, champion_name)
        else:
            champions = data_dragon.get_champions()
            champion_detail = data_dragon.get_champion_detail(champion_name)
        
        if champion_name not in champions:
            return {'total': 0.0, 'base_stats': 0.0, 'skills': 0.0, 'items': 0.0, 'runes': 0.0, 'synergies': 0.0}
        
        champion_stats = champions[champion_name]['stats']
        
        # Calculate components
        base_power = self.calculate_base_stats_power(champion_stats, level)
        skill_power = self.calculate_enhanced_skill_power(champion_detail, champion_stats)
        
        item_power = 0.0
        synergy_power = 0.0
        if item_ids:
            item_power = self.calculate_item_power(item_ids)
            synergy_power = self.calculate_item_synergy_power(item_ids)
        
        rune_power = 0.0
        if rune_ids and primary_style and sub_style:
            rune_power = self.calculate_enhanced_rune_power(rune_ids, primary_style, sub_style, champion_stats)
        
        total_power = base_power + skill_power + item_power + rune_power + synergy_power
        
        return {
            'total': total_power,
            'base_stats': base_power,
            'skills': skill_power,
            'items': item_power,
            'runes': rune_power,
            'synergies': synergy_power
        }
    
    def calculate_base_stats_power(self, champion_stats: Dict[str, Any], level: int = 18) -> float:
        """Base stats calculation (unchanged from original)"""
        stats = champion_stats
        
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
        
        hp = base_hp + (hp_per_level * (level - 1))
        ad = base_ad + (ad_per_level * (level - 1))
        armor = base_armor + (armor_per_level * (level - 1))
        mr = base_mr + (mr_per_level * (level - 1))
        attack_speed = base_as * (1 + (as_per_level / 100) * (level - 1))
        
        power = 0.0
        power += hp * self.HEALTH_RATE
        power += ad * self.ATTACK_DAMAGE_RATE
        power += armor * self.ARMOR_RATE
        power += mr * self.MAGIC_RESIST_RATE
        power += (attack_speed - 0.625) * 100 * self.ATTACK_SPEED_RATE
        
        return power
    
    def calculate_item_power(self, item_ids: List[int]) -> float:
        """Enhanced item power calculation including actives and passives"""
        items = data_dragon.get_items()
        power = 0.0
        
        for item_id in item_ids:
            item_str = str(item_id)
            if item_str not in items:
                continue
                
            item = items[item_str]
            stats = item.get('stats', {})
            
            # Base stat bonuses (unchanged)
            power += stats.get('FlatPhysicalDamageMod', 0) * self.ATTACK_DAMAGE_RATE
            power += stats.get('FlatMagicDamageMod', 0) * self.ABILITY_POWER_RATE
            power += stats.get('FlatHPPoolMod', 0) * self.HEALTH_RATE
            power += stats.get('FlatArmorMod', 0) * self.ARMOR_RATE
            power += stats.get('FlatSpellBlockMod', 0) * self.MAGIC_RESIST_RATE
            power += stats.get('PercentAttackSpeedMod', 0) * 100 * self.ATTACK_SPEED_RATE
            power += stats.get('FlatCritChanceMod', 0) * 100 * self.CRIT_CHANCE_RATE
            power += stats.get('PercentLifeStealMod', 0) * 100 * self.LIFESTEAL_RATE
            power += stats.get('FlatMovementSpeedMod', 0) * self.MOVE_SPEED_RATE
            
            # Enhanced: Item passive abilities
            passive_power = self._analyze_item_passive(item)
            power += passive_power
            
            # Enhanced: Item active abilities
            active_power = self._analyze_item_active(item)
            power += active_power
            
        return power
    
    def _analyze_item_passive(self, item: Dict[str, Any]) -> float:
        """Analyze item passive abilities"""
        power = 0.0
        
        # Get item description
        description = item.get('description', '').lower()
        name = item.get('name', '').lower()
        
        # Passive ability bonuses
        if 'unique' in description:
            power += 20  # Unique passives are powerful
        
        # Specific passive bonuses
        if 'critical strike' in description or 'crit' in description:
            power += 30
        if 'lifesteal' in description or 'vamp' in description:
            power += 25
        if 'movement speed' in description or 'ms' in description:
            power += 20
        if 'attack speed' in description or 'as' in description:
            power += 25
        if 'cooldown' in description or 'cdr' in description:
            power += 30
        if 'armor penetration' in description or 'lethality' in description:
            power += 35
        if 'magic penetration' in description or 'magic pen' in description:
            power += 35
        if 'shield' in description:
            power += 40
        if 'heal' in description or 'regeneration' in description:
            power += 30
        if 'damage' in description and 'bonus' in description:
            power += 25
        if 'true damage' in description:
            power += 50  # True damage is very powerful
        
        # Item-specific bonuses
        if 'infinity edge' in name:
            power += 40  # Double crit damage
        elif 'rabadon' in name:
            power += 50  # AP amplification
        elif 'void staff' in name:
            power += 35  # Magic penetration
        elif 'lord dominik' in name:
            power += 40  # Armor penetration
        elif 'thornmail' in name:
            power += 45  # Reflect damage
        elif 'randuin' in name:
            power += 35  # Attack speed reduction
        elif 'zhonya' in name:
            power += 60  # Stasis active
        elif 'guardian angel' in name:
            power += 80  # Revive passive
        
        return power
    
    def _analyze_item_active(self, item: Dict[str, Any]) -> float:
        """Analyze item active abilities"""
        power = 0.0
        
        description = item.get('description', '').lower()
        name = item.get('name', '').lower()
        
        # Active ability bonuses
        if 'active' in description:
            power += 30  # Base active bonus
        
        # Specific active bonuses
        if 'dash' in description or 'blink' in description:
            power += 40  # Mobility actives
        if 'damage' in description and 'active' in description:
            power += 35  # Damage actives
        if 'slow' in description and 'active' in description:
            power += 25  # CC actives
        if 'shield' in description and 'active' in description:
            power += 45  # Shield actives
        if 'heal' in description and 'active' in description:
            power += 40  # Heal actives
        if 'stun' in description and 'active' in description:
            power += 50  # Stun actives
        
        # Item-specific active bonuses
        if 'youmuu' in name:
            power += 50  # Ghostblade active
        elif 'botrk' in name or 'blade of the ruined king' in name:
            power += 60  # BORK active
        elif 'hextech' in name:
            power += 45  # Hextech actives
        elif 'shurelya' in name:
            power += 55  # Shurelya's active
        elif 'redemption' in name:
            power += 70  # Redemption active
        elif 'zhonya' in name:
            power += 80  # Zhonya's stasis
        elif 'qss' in name or 'quicksilver' in name:
            power += 60  # QSS cleanse
        
        return power


# Singleton instance
enhanced_combat_power_calculator = EnhancedCombatPowerCalculator()

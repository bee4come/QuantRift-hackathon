"""
Tier System for Champion Classification
Maps combat power to tier rankings (S, A, B, C, D) and validates against meta data
"""
import json
import os
from typing import Dict, List, Any, Optional, Tuple


class TierSystem:
    """
    Manages tier classification for champions based on combat power
    and validates against real meta leaderboard data
    """
    
    def __init__(self):
        # Load last changed patch data
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        with open(os.path.join(data_dir, 'champion_last_changed.json'), 'r') as f:
            self.last_changed_patches = json.load(f)
    
    def assign_tier_by_combat_power(self, combat_powers: Dict[str, float]) -> Dict[str, Tuple[int, str]]:
        """
        Assign tiers based on combat power distribution
        
        Args:
            combat_powers: Dict of champion_name -> combat_power
            
        Returns:
            Dict of champion_name -> (tier_num, tier_label)
            tier_num: 1=S, 2=A, 3=B, 4=C, 5=D
            tier_label: 'S', 'A', 'B', 'C', 'D'
        """
        if not combat_powers:
            return {}
        
        # Sort champions by combat power
        sorted_champs = sorted(combat_powers.items(), key=lambda x: x[1], reverse=True)
        total_champs = len(sorted_champs)
        
        tiers = {}
        
        for i, (champ_name, power) in enumerate(sorted_champs):
            percentile = (i / total_champs) * 100
            
            # Tier distribution:
            # S tier: Top 15% (exceptional)
            # A tier: 15-35% (strong)
            # B tier: 35-65% (balanced)
            # C tier: 65-85% (below average)
            # D tier: 85-100% (weak)
            
            if percentile < 15:
                tier_num, tier_label = 1, 'S'
            elif percentile < 35:
                tier_num, tier_label = 2, 'A'
            elif percentile < 65:
                tier_num, tier_label = 3, 'B'
            elif percentile < 85:
                tier_num, tier_label = 4, 'C'
            else:
                tier_num, tier_label = 5, 'D'
            
            tiers[champ_name] = (tier_num, tier_label)
        
        return tiers
    
    def classify_champion_lane(self, champion_data: Dict[str, Any]) -> List[str]:
        """
        Determine which lane(s) a champion is best suited for
        
        Args:
            champion_data: Champion data from Data Dragon
            
        Returns:
            List of suitable lanes: ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT']
        """
        tags = champion_data.get('tags', [])
        stats = champion_data.get('stats', {})
        name = champion_data.get('name', '')
        
        # Get key stats
        attack_range = stats.get('attackrange', 125)
        hp = stats.get('hp', 500)
        armor = stats.get('armor', 20)
        attack_damage = stats.get('attackdamage', 50)
        movespeed = stats.get('movespeed', 325)
        
        lanes = []
        
        # Marksman = ADC (with a few exceptions)
        if 'Marksman' in tags:
            if name in ['Graves', 'Kindred']:
                lanes.append('JUNGLE')
            else:
                lanes.append('ADC')
        
        # Support
        if 'Support' in tags or name in ['Janna', 'Soraka', 'Nami', 'Lulu', 'Thresh', 'Blitzcrank', 'Leona', 'Nautilus', 'Braum', 'Alistar', 'Bard', 'Rakan', 'Taric', 'Yuumi', 'Milio', 'Renata']:
            lanes.append('SUPPORT')
        
        # Jungle-specific champions
        jungle_champs = ['Shyvana', 'MasterYi', 'Warwick', 'Amumu', 'Rammus', 'Nunu', 'JarvanIV', 
                        'XinZhao', 'LeeSin', 'Elise', 'RekSai', 'Nidalee', 'Kindred', 'Graves', 
                        'Khazix', 'Rengar', 'Evelynn', 'Kayn', 'Hecarim', 'Vi', 'Nocturne', 
                        'Sejuani', 'Zac', 'Gragas', 'Ivern', 'Karthus', 'Lillia', 'Viego', 
                        'Belveth', 'Briar', 'Naafiri']
        if name in jungle_champs:
            if 'JUNGLE' not in lanes:
                lanes.append('JUNGLE')
        
        # Assassin logic
        if 'Assassin' in tags:
            if name in ['Pyke']:
                if 'SUPPORT' not in lanes:
                    lanes.append('SUPPORT')
            elif attack_range < 300:  # Melee assassin
                if 'MID' not in lanes:
                    lanes.append('MID')
                if name in ['Talon', 'Zed', 'Qiyana'] and 'JUNGLE' not in lanes:
                    lanes.append('JUNGLE')
            else:  # Ranged assassin
                if 'MID' not in lanes:
                    lanes.append('MID')
        
        # Mage logic
        if 'Mage' in tags:
            if 'SUPPORT' not in lanes:
                if name in ['Brand', 'Xerath', 'Velkoz', 'Zyra', 'Swain', 'Lux']:
                    lanes.append('SUPPORT')
            if 'MID' not in lanes:
                lanes.append('MID')
        
        # Tank logic
        if 'Tank' in tags:
            if hp > 600:  # Beefy tanks
                if 'SUPPORT' not in lanes and name in ['Alistar', 'Braum', 'Leona', 'Nautilus', 'Thresh', 'TahmKench', 'Rell']:
                    if 'SUPPORT' not in lanes:
                        lanes.append('SUPPORT')
                elif 'TOP' not in lanes:
                    lanes.append('TOP')
            if name in jungle_champs and 'JUNGLE' not in lanes:
                lanes.append('JUNGLE')
        
        # Fighter logic
        if 'Fighter' in tags:
            if attack_range < 200:  # Melee fighter
                if 'TOP' not in lanes:
                    lanes.append('TOP')
                # Some fighters can jungle
                if name in jungle_champs and 'JUNGLE' not in lanes:
                    lanes.append('JUNGLE')
            else:
                if 'TOP' not in lanes:
                    lanes.append('TOP')
        
        # Special cases for versatile champions
        versatile_top_mid = ['Yasuo', 'Yone', 'Irelia', 'Akali', 'Sylas', 'Gangplank', 'Jayce', 'Kennen']
        if name in versatile_top_mid:
            if 'TOP' not in lanes:
                lanes.append('TOP')
            if 'MID' not in lanes:
                lanes.append('MID')
        
        # Default to MID if no lanes detected (many mages/assassins)
        if not lanes:
            if attack_range > 400:
                lanes.append('MID')
            else:
                lanes.append('TOP')
        
        return lanes
    
    def get_top_champions_by_lane(
        self, 
        champions_data: Dict[str, Any],
        combat_power_calculator,
        meta_builds_db,
        top_n: int = 10,
        patch: Optional[str] = None,
        use_opgg: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get top N champions for each lane with tier information and lane-specific builds
        
        Args:
            champions_data: Full champion data from Data Dragon
            combat_power_calculator: Combat power calculator instance
            meta_builds_db: Meta builds database instance
            top_n: Number of top champions per lane
            patch: Specific patch version
            use_opgg: Whether to use OP.GG builds (lane-specific)
            
        Returns:
            Dict of lane -> list of champion info dicts
            Also includes 'ALL' key with each champion's primary lane only
        """
        from .enhanced_combat_power import enhanced_combat_power_calculator
        from .build_tracker_service import build_tracker_service
        from .opgg_winrate_fetcher import opgg_winrate_fetcher
        
        # Get primary lanes from OP.GG win rate data
        primary_lanes_map = opgg_winrate_fetcher.get_all_primary_lanes()
        
        # Calculate lane-specific combat power
        lane_champions = {
            'TOP': [],
            'JUNGLE': [],
            'MID': [],
            'ADC': [],
            'SUPPORT': [],
            'ALL': []  # Will contain each champion's primary lane only
        }
        
        all_lane_powers = []  # For tier assignment
        champion_primary_data = {}  # Track each champion's primary lane data
        
        for champ_name, champ_data in champions_data.items():
            lanes = self.classify_champion_lane(champ_data)
            
            # Get primary lane from OP.GG if available
            opgg_primary_lane = primary_lanes_map.get(champ_name)
            
            for lane in lanes:
                if lane not in ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT']:
                    continue
                
                # Get lane-specific build from build tracker (real OP.GG data)
                if use_opgg:
                    build_data = build_tracker_service.get_most_popular_build(champ_name, patch)
                    
                    if build_data and build_data.get('items'):
                        items = build_data.get('items', [])
                        runes = build_data.get('runes', [])
                        primary_style = build_data.get('primary_style')
                        sub_style = build_data.get('sub_style')
                    else:
                        # Fallback to meta builds if no build tracker data
                        meta_build = meta_builds_db.get_meta_build(champ_name, patch, champ_data)
                        items = meta_build.get('items', [])
                        runes = meta_build.get('runes', [])
                        primary_style = meta_build.get('primary_style')
                        sub_style = meta_build.get('sub_style')
                else:
                    meta_build = meta_builds_db.get_meta_build(champ_name, patch, champ_data)
                    items = meta_build.get('items', [])
                    runes = meta_build.get('runes', [])
                    primary_style = meta_build.get('primary_style')
                    sub_style = meta_build.get('sub_style')
                
                # Calculate enhanced combat power with lane-specific build
                try:
                    power_result = enhanced_combat_power_calculator.calculate_total_enhanced_combat_power(
                        champion_name=champ_name,
                        level=18,
                        item_ids=items,
                        rune_ids=runes,
                        primary_style=primary_style,
                        sub_style=sub_style,
                        patch=patch
                    )
                    power = power_result['total']
                except Exception as e:
                    print(f"Error calculating enhanced power for {champ_name} in {lane}: {e}")
                    # Fallback to original calculator
                    try:
                        power = combat_power_calculator.calculate_total_combat_power(
                            champion_name=champ_name,
                            level=18,
                            item_ids=items,
                            rune_ids=runes,
                            primary_style=primary_style,
                            sub_style=sub_style,
                            patch=patch
                        )
                    except Exception as e2:
                        print(f"Fallback calculation also failed: {e2}")
                        power = 0
                
                champ_info = {
                    'name': champ_name,
                    'combatPower': round(power, 2),
                    'lane': lane,
                    'items': items,
                    'runes': runes,
                    'primary_style': primary_style,
                    'sub_style': sub_style,
                    'lastChanged': self.last_changed_patches.get(champ_name, 'Unknown')
                }
                
                lane_champions[lane].append(champ_info)
                all_lane_powers.append((f"{champ_name}_{lane}", power))
                
                # Track primary lane data
                # Priority: OP.GG primary > highest combat power
                if opgg_primary_lane == lane:
                    champion_primary_data[champ_name] = champ_info.copy()
                elif champ_name not in champion_primary_data:
                    # If no OP.GG data, use first lane or highest CP lane
                    if champ_name not in champion_primary_data or power > champion_primary_data[champ_name]['combatPower']:
                        champion_primary_data[champ_name] = champ_info.copy()
        
        # Get OP.GG tier data (official tier rankings)
        opgg_winrates = opgg_winrate_fetcher.load_from_cache()
        
        # Map tier labels to numbers for fallback calculation
        tier_label_to_num = {'S': 1, 'A': 2, 'B': 3, 'C': 4, 'D': 5}
        
        # Assign tiers - prefer OP.GG data, fallback to calculated tiers
        all_powers_dict = dict(all_lane_powers)
        calculated_tiers = self.assign_tier_by_combat_power(all_powers_dict)
        
        # Add tier information and sort
        result = {}
        for lane in ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT']:
            champions = lane_champions[lane]
            # Add tier info
            for champ in champions:
                champ_name = champ['name']
                
                # Try to get OP.GG tier data first
                opgg_tier = None
                opgg_rank = 999
                if champ_name in opgg_winrates:
                    lane_data = opgg_winrates[champ_name].get(lane, {})
                    if lane_data:
                        opgg_tier = lane_data.get('tier')
                        opgg_rank = lane_data.get('rank', 999)
                
                # Use OP.GG tier if available, otherwise use calculated tier
                if opgg_tier:
                    tier_label = opgg_tier
                    tier_num = tier_label_to_num.get(tier_label, 3)
                else:
                    # Fallback to calculated tier
                    tier_key = f"{champ_name}_{lane}"
                    tier_num, tier_label = calculated_tiers.get(tier_key, (3, 'B'))
                
                champ['tier'] = tier_label
                champ['tierLabel'] = tier_label
                champ['rank'] = opgg_rank
            
            # Sort by combat power and take top N
            sorted_champs = sorted(champions, key=lambda x: x['combatPower'], reverse=True)[:top_n]
            
            # Re-assign tiers for champions without OP.GG data based on their position in top_n
            for i, champ in enumerate(sorted_champs):
                # Skip if champion has OP.GG tier (keep official tier)
                if champ['rank'] < 900:  # Has valid OP.GG rank
                    continue
                
                # Calculate tier based on position in top_n list
                percentile = (i / top_n) * 100 if top_n > 0 else 0
                
                if percentile < 15:
                    tier_label = 'S'
                elif percentile < 35:
                    tier_label = 'A'
                elif percentile < 65:
                    tier_label = 'B'
                elif percentile < 85:
                    tier_label = 'C'
                else:
                    tier_label = 'D'
                
                champ['tier'] = tier_label
                champ['tierLabel'] = tier_label
            
            result[lane] = sorted_champs
        
        # Create ALL view with each champion's primary lane only
        all_champions = []
        for champ_name, champ_info in champion_primary_data.items():
            lane = champ_info['lane']
            
            # Try to get OP.GG tier data first
            opgg_tier = None
            opgg_rank = 999
            if champ_name in opgg_winrates:
                lane_data = opgg_winrates[champ_name].get(lane, {})
                if lane_data:
                    opgg_tier = lane_data.get('tier')
                    opgg_rank = lane_data.get('rank', 999)
            
            # Use OP.GG tier if available, otherwise use calculated tier
            if opgg_tier:
                tier_label = opgg_tier
                tier_num = tier_label_to_num.get(tier_label, 3)
            else:
                # Fallback to calculated tier
                tier_key = f"{champ_name}_{lane}"
                tier_num, tier_label = calculated_tiers.get(tier_key, (3, 'B'))
            
            champ_info['tier'] = tier_label
            champ_info['tierLabel'] = tier_label
            champ_info['rank'] = opgg_rank
            all_champions.append(champ_info)
        
        # Sort ALL by combat power
        sorted_all = sorted(all_champions, key=lambda x: x['combatPower'], reverse=True)
        
        # Re-assign tiers for ALL view based on the actual top_n champions
        # This ensures proper S/A/B/C/D distribution in the displayed list
        for i, champ in enumerate(sorted_all[:top_n]):
            # Skip if champion has OP.GG tier (keep official tier)
            if champ['rank'] < 900:  # Has valid OP.GG rank
                continue
            
            # Calculate tier based on position in top_n list
            percentile = (i / top_n) * 100 if top_n > 0 else 0
            
            if percentile < 15:
                tier_label = 'S'
            elif percentile < 35:
                tier_label = 'A'
            elif percentile < 65:
                tier_label = 'B'
            elif percentile < 85:
                tier_label = 'C'
            else:
                tier_label = 'D'
            
            champ['tier'] = tier_label
            champ['tierLabel'] = tier_label
        
        result['ALL'] = sorted_all[:top_n]
        
        return result


# Global instance
tier_system = TierSystem()


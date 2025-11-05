"""
Intelligent Build Provider
Automatically determines appropriate builds for ANY champion based on their stats and role
"""
from typing import Dict, List, Any, Optional


class IntelligentBuildProvider:
    """
    Smart system that provides appropriate builds for any champion
    Uses champion stats and tags to determine role and assign suitable build
    """
    
    def __init__(self):
        """Initialize role-based build templates"""
        
        # Precision (8000)
        self.PRECISION_RUNES = [8010, 9111, 9104, 8014, 8473, 8242, 5008, 5008, 5002]  # Conqueror
        self.PRECISION_AS_RUNES = [8008, 9111, 9104, 8014, 8139, 8135, 5005, 5008, 5002]  # Lethal Tempo
        self.PTA_RUNES = [8005, 9111, 9104, 8014, 8234, 8237, 5008, 5008, 5002]  # Press the Attack
        
        # Domination (8100)
        self.ELECTROCUTE_RUNES = [8112, 8139, 8138, 8135, 8234, 8237, 5008, 5008, 5002]
        self.HOB_RUNES = [9923, 8139, 8138, 8135, 9111, 8014, 5005, 5008, 5002]
        
        # Sorcery (8200)
        self.COMET_RUNES = [8229, 8226, 8210, 8237, 8347, 8410, 5008, 5008, 5002]
        self.AERY_RUNES = [8214, 8226, 8210, 8237, 8347, 8410, 5008, 5008, 5002]
        
        # Resolve (8400)
        self.GRASP_RUNES = [8437, 8401, 8473, 8242, 9111, 8014, 5008, 5002, 5002]
        self.AFTERSHOCK_RUNES = [8439, 8401, 8473, 8242, 8347, 8410, 5008, 5002, 5002]
        
        # Role-based builds
        self.role_builds = {
            'ADC_CRIT': {
                'items': [3031, 3072, 3046, 3094, 3508, 3006],  # IE, BT, PD, RFC, ER, Berserker's
                'runes': self.PRECISION_AS_RUNES,
                'primary_style': 8000,
                'sub_style': 8100
            },
            'ADC_ONHIT': {
                'items': [3153, 3124, 3085, 3091, 3046, 3006],  # BORK, Rageblade, Runaan's, Wit's End, PD, Berserker's
                'runes': self.PRECISION_AS_RUNES,
                'primary_style': 8000,
                'sub_style': 8100
            },
            'ASSASSIN_AD': {
                'items': [3142, 6691, 6676, 3814, 3036, 3111],  # Youmuu's, Duskblade, Collector, Edge, LDR, Mercs
                'runes': self.ELECTROCUTE_RUNES,
                'primary_style': 8100,
                'sub_style': 8200
            },
            'ASSASSIN_AP': {
                'items': [3152, 4645, 3157, 3135, 3089, 3020],  # Rocketbelt, Shadowflame, Zhonya's, Void, Rabadon's, Sorc
                'runes': self.ELECTROCUTE_RUNES,
                'primary_style': 8100,
                'sub_style': 8200
            },
            'MAGE_BURST': {
                'items': [6653, 4645, 3135, 3089, 3157, 3020],  # Liandry's, Shadowflame, Void, Rabadon's, Zhonya's, Sorc
                'runes': self.COMET_RUNES,
                'primary_style': 8200,
                'sub_style': 8300
            },
            'MAGE_BATTLEMAGE': {
                'items': [4633, 3116, 3135, 3089, 3157, 3020],  # Riftmaker, Rylai's, Void, Rabadon's, Zhonya's, Sorc
                'runes': self.PRECISION_RUNES,
                'primary_style': 8000,
                'sub_style': 8200
            },
            'TANK': {
                'items': [3068, 3075, 3143, 3065, 3748, 3047],  # Sunfire, Thornmail, Randuin's, Spirit Visage, Titanic, Plated
                'runes': self.GRASP_RUNES,
                'primary_style': 8400,
                'sub_style': 8000
            },
            'TANK_SUPPORT': {
                'items': [3190, 3109, 3068, 3075, 3065, 3047],  # Locket, Knight's Vow, Sunfire, Thornmail, Spirit Visage, Plated
                'runes': self.AFTERSHOCK_RUNES,
                'primary_style': 8400,
                'sub_style': 8300
            },
            'FIGHTER_AD': {
                'items': [6630, 3071, 3748, 3065, 3053, 3111],  # Goredrinker, Black Cleaver, Titanic, Spirit Visage, Sterak's, Mercs
                'runes': self.PRECISION_RUNES,
                'primary_style': 8000,
                'sub_style': 8400
            },
            'FIGHTER_ONHIT': {
                'items': [3078, 3153, 3748, 3091, 3026, 3111],  # Trinity, BORK, Titanic, Wit's End, Guardian Angel, Mercs
                'runes': self.PRECISION_RUNES,
                'primary_style': 8000,
                'sub_style': 8400
            },
            'SUPPORT_ENCHANTER': {
                'items': [3504, 3107, 3011, 3050, 3222, 3020],  # Ardent, Redemption, Chemtech, Zeke's, Mikael's, Sorc
                'runes': self.AERY_RUNES,
                'primary_style': 8200,
                'sub_style': 8300
            },
            'SKIRMISHER': {
                'items': [6692, 3071, 3748, 3156, 3026, 3111],  # Eclipse, Black Cleaver, Titanic, Maw, GA, Mercs
                'runes': self.PRECISION_RUNES,
                'primary_style': 8000,
                'sub_style': 8100
            }
        }
    
    def classify_champion(self, champion_data: Dict[str, Any]) -> str:
        """
        Classify champion into a build category based on their stats and tags
        
        Args:
            champion_data: Champion data from Data Dragon
            
        Returns:
            Build category string (e.g., 'ADC_CRIT', 'TANK', 'MAGE_BURST')
        """
        tags = champion_data.get('tags', [])
        stats = champion_data.get('stats', {})
        
        # Get key stats
        attack_range = stats.get('attackrange', 125)
        attack_damage = stats.get('attackdamage', 50)
        hp = stats.get('hp', 500)
        armor = stats.get('armor', 20)
        attack_speed = stats.get('attackspeed', 0.6)
        
        # Classification logic
        
        # Marksman (ADC)
        if 'Marksman' in tags:
            # Check if on-hit or crit based
            if attack_speed > 0.65:
                return 'ADC_ONHIT'
            else:
                return 'ADC_CRIT'
        
        # Assassins
        if 'Assassin' in tags:
            # Check if AP or AD based
            spells_data = champion_data.get('spells', [])
            ap_scaling_count = 0
            ad_scaling_count = 0
            
            for spell in spells_data:
                for var in spell.get('vars', []):
                    if 'ap' in var.get('link', '').lower():
                        ap_scaling_count += 1
                    if 'ad' in var.get('link', '').lower() or 'attackdamage' in var.get('link', '').lower():
                        ad_scaling_count += 1
            
            if ap_scaling_count > ad_scaling_count:
                return 'ASSASSIN_AP'
            else:
                return 'ASSASSIN_AD'
        
        # Mages
        if 'Mage' in tags:
            # Battlemage if melee or short range
            if attack_range < 400:
                return 'MAGE_BATTLEMAGE'
            else:
                return 'MAGE_BURST'
        
        # Tanks
        if 'Tank' in tags:
            # Support tank if has support tag
            if 'Support' in tags:
                return 'TANK_SUPPORT'
            else:
                return 'TANK'
        
        # Support
        if 'Support' in tags:
            # Enchanter support (ranged, low armor)
            if attack_range > 400 and armor < 30:
                return 'SUPPORT_ENCHANTER'
            else:
                return 'TANK_SUPPORT'
        
        # Fighters
        if 'Fighter' in tags:
            # On-hit fighter if high base attack speed
            if attack_speed > 0.65:
                return 'FIGHTER_ONHIT'
            else:
                return 'FIGHTER_AD'
        
        # Skirmishers (high mobility fighters)
        if attack_range < 200 and attack_damage > 55:
            return 'SKIRMISHER'
        
        # Default fallback based on range
        if attack_range > 400:
            return 'ADC_CRIT'  # Ranged DPS
        elif hp > 600 and armor > 30:
            return 'TANK'  # Tanky
        else:
            return 'FIGHTER_AD'  # Melee DPS
    
    def get_intelligent_build(self, champion_name: str, champion_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get intelligent build for any champion based on their stats and tags
        
        Args:
            champion_name: Champion name
            champion_data: Champion data from Data Dragon
            
        Returns:
            Build dictionary with items and runes
        """
        # Classify champion
        build_category = self.classify_champion(champion_data)
        
        # Get build template
        build_template = self.role_builds.get(build_category, self.role_builds['FIGHTER_AD'])
        
        # Return build with metadata
        return {
            'items': build_template['items'].copy(),
            'runes': build_template['runes'].copy(),
            'primary_style': build_template['primary_style'],
            'sub_style': build_template['sub_style'],
            'role': build_category.replace('_', ' ').title(),
            'notes': f'Auto-detected as {build_category} based on champion stats and tags',
            'auto_generated': True
        }
    
    def get_build_with_explanation(self, champion_name: str, champion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get build with detailed explanation of why it was chosen"""
        build = self.get_intelligent_build(champion_name, champion_data)
        
        tags = champion_data.get('tags', [])
        stats = champion_data.get('stats', {})
        
        explanation = f"Build for {champion_name}:\n"
        explanation += f"  Tags: {', '.join(tags)}\n"
        explanation += f"  Range: {stats.get('attackrange', 'N/A')}\n"
        explanation += f"  HP: {stats.get('hp', 'N/A')}\n"
        explanation += f"  AD: {stats.get('attackdamage', 'N/A')}\n"
        explanation += f"  → Classified as: {build['role']}\n"
        
        build['explanation'] = explanation
        return build


# Singleton instance
intelligent_build_provider = IntelligentBuildProvider()


"""
Meta builds database for champions across patches
Includes popular items and runes per champion per patch
Each champion has its own unique meta build
"""
from typing import Dict, List, Any, Optional


class MetaBuildsDatabase:
    """Database of meta builds for champions across patches"""
    
    # Rune styles
    PRECISION = 8000
    DOMINATION = 8100
    SORCERY = 8200
    RESOLVE = 8400
    INSPIRATION = 8300
    
    # Common full rune pages (4 primary + 2 secondary + 3 stat shards = 9 total)
    PRESS_THE_ATTACK_RUNES = {
        'primary_style': PRECISION, 'sub_style': SORCERY,
        'runes': [8005, 9111, 9104, 8014, 8234, 8237, 5008, 5008, 5002]
    }
    
    LETHAL_TEMPO_RUNES = {
        'primary_style': PRECISION, 'sub_style': DOMINATION,
        'runes': [8008, 9111, 9104, 8014, 8139, 8135, 5005, 5008, 5002]
    }
    
    FLEET_FOOTWORK_RUNES = {
        'primary_style': PRECISION, 'sub_style': SORCERY,
        'runes': [8021, 9111, 9104, 8014, 8234, 8237, 5005, 5008, 5002]
    }
    
    CONQUEROR_RUNES = {
        'primary_style': PRECISION, 'sub_style': RESOLVE,
        'runes': [8010, 9111, 9104, 8014, 8473, 8242, 5008, 5008, 5002]
    }
    
    ELECTROCUTE_RUNES = {
        'primary_style': DOMINATION, 'sub_style': SORCERY,
        'runes': [8112, 8139, 8138, 8135, 8234, 8237, 5008, 5008, 5002]
    }
    
    DARK_HARVEST_RUNES = {
        'primary_style': DOMINATION, 'sub_style': PRECISION,
        'runes': [8128, 8139, 8138, 8135, 9111, 8014, 5008, 5008, 5002]
    }
    
    HAIL_OF_BLADES_RUNES = {
        'primary_style': DOMINATION, 'sub_style': PRECISION,
        'runes': [9923, 8139, 8138, 8135, 9111, 8014, 5005, 5008, 5002]
    }
    
    SUMMON_AERY_RUNES = {
        'primary_style': SORCERY, 'sub_style': INSPIRATION,
        'runes': [8214, 8226, 8210, 8237, 8347, 8410, 5008, 5008, 5002]
    }
    
    ARCANE_COMET_RUNES = {
        'primary_style': SORCERY, 'sub_style': INSPIRATION,
        'runes': [8229, 8226, 8210, 8237, 8347, 8410, 5008, 5008, 5002]
    }
    
    PHASE_RUSH_RUNES = {
        'primary_style': SORCERY, 'sub_style': RESOLVE,
        'runes': [8230, 8226, 8210, 8237, 8473, 8242, 5008, 5008, 5002]
    }
    
    GRASP_RUNES = {
        'primary_style': RESOLVE, 'sub_style': PRECISION,
        'runes': [8437, 8401, 8473, 8242, 9111, 8014, 5008, 5002, 5002]
    }
    
    AFTERSHOCK_RUNES = {
        'primary_style': RESOLVE, 'sub_style': INSPIRATION,
        'runes': [8439, 8401, 8473, 8242, 8347, 8410, 5008, 5002, 5002]
    }
    
    GLACIAL_AUGMENT_RUNES = {
        'primary_style': INSPIRATION, 'sub_style': PRECISION,
        'runes': [8351, 8306, 8345, 8347, 9111, 8014, 5008, 5008, 5002]
    }
    
    def __init__(self):
        """Initialize meta builds for all champions"""
        self.meta_builds = {
            # ADC Champions
            'Aphelios': {'role': 'ADC', 'items': [3031, 3094, 3072, 3046, 6676, 3006], 'runes': self.CONQUEROR_RUNES},
            'Ashe': {'role': 'ADC', 'items': [3031, 3094, 3046, 6676, 3072, 3006], 'runes': self.LETHAL_TEMPO_RUNES},
            'Caitlyn': {'role': 'ADC', 'items': [3031, 3094, 6676, 3046, 3072, 3006], 'runes': self.FLEET_FOOTWORK_RUNES},
            'Draven': {'role': 'ADC', 'items': [3031, 3072, 3046, 3094, 3508, 3006], 'runes': self.CONQUEROR_RUNES},
            'Ezreal': {'role': 'ADC', 'items': [3508, 3078, 3156, 3031, 3036, 3006], 'runes': self.CONQUEROR_RUNES},
            'Jhin': {'role': 'ADC', 'items': [3031, 3094, 6676, 6693, 3036, 3006], 'runes': self.FLEET_FOOTWORK_RUNES},
            'Jinx': {'role': 'ADC', 'items': [3031, 3094, 3046, 3072, 6676, 3006], 'runes': self.LETHAL_TEMPO_RUNES},
            'Kaisa': {'role': 'ADC', 'items': [3115, 3508, 3031, 3046, 3089, 3006], 'runes': self.HAIL_OF_BLADES_RUNES},
            'Kalista': {'role': 'ADC', 'items': [3153, 3085, 3046, 3091, 6676, 3006], 'runes': self.LETHAL_TEMPO_RUNES},
            'KogMaw': {'role': 'ADC', 'items': [3153, 3124, 3085, 3091, 3046, 3006], 'runes': self.LETHAL_TEMPO_RUNES},
            'Lucian': {'role': 'ADC', 'items': [3508, 3031, 3094, 3046, 6676, 3006], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'MissFortune': {'role': 'ADC', 'items': [3142, 6676, 6694, 3814, 3036, 3006], 'runes': self.DARK_HARVEST_RUNES},
            'Nilah': {'role': 'ADC', 'items': [3031, 3072, 3046, 3153, 3094, 3006], 'runes': self.CONQUEROR_RUNES},
            'Samira': {'role': 'ADC', 'items': [3031, 3072, 6676, 3046, 3508, 3006], 'runes': self.CONQUEROR_RUNES},
            'Senna': {'role': 'ADC', 'items': [3031, 3094, 6676, 3046, 3508, 3006], 'runes': self.FLEET_FOOTWORK_RUNES},
            'Sivir': {'role': 'ADC', 'items': [3031, 3508, 3046, 3094, 6676, 3006], 'runes': self.LETHAL_TEMPO_RUNES},
            'Smolder': {'role': 'ADC', 'items': [3031, 3094, 3072, 3046, 3508, 3006], 'runes': self.FLEET_FOOTWORK_RUNES},
            'Tristana': {'role': 'ADC', 'items': [3031, 3094, 6676, 3046, 3072, 3006], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'Twitch': {'role': 'ADC', 'items': [3153, 3085, 3031, 3046, 3091, 3006], 'runes': self.LETHAL_TEMPO_RUNES},
            'Varus': {'role': 'ADC', 'items': [3124, 3085, 3091, 3153, 3046, 3006], 'runes': self.LETHAL_TEMPO_RUNES},
            'Vayne': {'role': 'ADC', 'items': [3153, 3124, 3085, 3091, 3046, 3006], 'runes': self.LETHAL_TEMPO_RUNES},
            'Xayah': {'role': 'ADC', 'items': [3031, 3508, 3046, 3094, 6676, 3006], 'runes': self.LETHAL_TEMPO_RUNES},
            'Zeri': {'role': 'ADC', 'items': [3078, 3153, 3085, 3046, 3091, 3006], 'runes': self.FLEET_FOOTWORK_RUNES},
            
            # Assassins
            'Akali': {'role': 'Assassin', 'items': [4633, 3152, 3157, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Ekko': {'role': 'Assassin', 'items': [3152, 4645, 3157, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Evelynn': {'role': 'Assassin', 'items': [3152, 4645, 3135, 3157, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Fizz': {'role': 'Assassin', 'items': [3152, 3157, 6653, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Kassadin': {'role': 'Assassin', 'items': [3040, 3003, 3157, 3089, 3135, 3020], 'runes': self.FLEET_FOOTWORK_RUNES},
            'Katarina': {'role': 'Assassin', 'items': [3152, 4645, 3157, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'KhaZix': {'role': 'Assassin', 'items': [6691, 3142, 3814, 6676, 3036, 3111], 'runes': self.ELECTROCUTE_RUNES},
            'LeBlanc': {'role': 'Assassin', 'items': [6653, 4645, 3135, 3157, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Nocturne': {'role': 'Assassin', 'items': [6692, 3156, 3074, 3071, 3026, 3111], 'runes': self.LETHAL_TEMPO_RUNES},
            'Pyke': {'role': 'Assassin', 'items': [6691, 3142, 3814, 6676, 3036, 3111], 'runes': self.HAIL_OF_BLADES_RUNES},
            'Qiyana': {'role': 'Assassin', 'items': [3142, 6691, 3814, 6676, 3036, 3111], 'runes': self.ELECTROCUTE_RUNES},
            'Rengar': {'role': 'Assassin', 'items': [6691, 3142, 6676, 3814, 3036, 3111], 'runes': self.ELECTROCUTE_RUNES},
            'Shaco': {'role': 'Assassin', 'items': [6691, 3142, 6676, 3814, 3036, 3111], 'runes': self.HAIL_OF_BLADES_RUNES},
            'Talon': {'role': 'Assassin', 'items': [3142, 6691, 3814, 6676, 3036, 3111], 'runes': self.ELECTROCUTE_RUNES},
            'Zed': {'role': 'Assassin', 'items': [3142, 6691, 6676, 3814, 3036, 3111], 'runes': self.ELECTROCUTE_RUNES},
            
            # Fighters/Bruisers
            'Aatrox': {'role': 'Fighter', 'items': [6630, 3071, 3742, 3065, 3053, 3111], 'runes': self.CONQUEROR_RUNES},
            'Camille': {'role': 'Fighter', 'items': [3078, 3074, 3153, 3742, 3026, 3111], 'runes': self.CONQUEROR_RUNES},
            'Darius': {'role': 'Fighter', 'items': [6632, 3071, 3748, 6630, 3065, 3047], 'runes': self.CONQUEROR_RUNES},
            'Fiora': {'role': 'Fighter', 'items': [3078, 3074, 3153, 3742, 3026, 3111], 'runes': self.CONQUEROR_RUNES},
            'Garen': {'role': 'Fighter', 'items': [6632, 3071, 3748, 6630, 3065, 3047], 'runes': self.CONQUEROR_RUNES},
            'Gwen': {'role': 'Fighter', 'items': [3152, 3115, 3135, 3089, 3157, 3020], 'runes': self.CONQUEROR_RUNES},
            'Illaoi': {'role': 'Fighter', 'items': [6632, 3071, 3748, 6630, 3065, 3047], 'runes': self.CONQUEROR_RUNES},
            'Irelia': {'role': 'Fighter', 'items': [3153, 3078, 3156, 3748, 3026, 3111], 'runes': self.CONQUEROR_RUNES},
            'Jax': {'role': 'Fighter', 'items': [3078, 3153, 3748, 3026, 3065, 3111], 'runes': self.CONQUEROR_RUNES},
            'Jayce': {'role': 'Fighter', 'items': [3142, 3156, 3071, 3814, 3036, 3111], 'runes': self.CONQUEROR_RUNES},
            'Mordekaiser': {'role': 'Fighter', 'items': [4633, 3116, 3065, 3742, 3157, 3047], 'runes': self.CONQUEROR_RUNES},
            'Olaf': {'role': 'Fighter', 'items': [6630, 3071, 3748, 3065, 3053, 3111], 'runes': self.CONQUEROR_RUNES},
            'Pantheon': {'role': 'Fighter', 'items': [6692, 3071, 3742, 3053, 3026, 3111], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'Renekton': {'role': 'Fighter', 'items': [6630, 3071, 3748, 3065, 3053, 3047], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'Riven': {'role': 'Fighter', 'items': [6630, 3071, 3156, 3742, 3053, 3111], 'runes': self.CONQUEROR_RUNES},
            'Rumble': {'role': 'Fighter', 'items': [4633, 6653, 3135, 3157, 3089, 3020], 'runes': self.ARCANE_COMET_RUNES},
            'Sett': {'role': 'Fighter', 'items': [6632, 3748, 3071, 3065, 6630, 3047], 'runes': self.CONQUEROR_RUNES},
            'Trundle': {'role': 'Fighter', 'items': [3078, 3153, 3748, 3742, 3065, 3111], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'Tryndamere': {'role': 'Fighter', 'items': [3078, 3031, 3046, 3153, 3036, 3006], 'runes': self.LETHAL_TEMPO_RUNES},
            'Urgot': {'role': 'Fighter', 'items': [3071, 3748, 3075, 6630, 3065, 3047], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'Vi': {'role': 'Fighter', 'items': [3078, 3074, 3748, 3156, 3026, 3111], 'runes': self.HAIL_OF_BLADES_RUNES},
            'Volibear': {'role': 'Fighter', 'items': [4633, 3748, 3065, 3742, 3075, 3047], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'Warwick': {'role': 'Fighter', 'items': [3078, 3748, 3065, 3153, 3742, 3047], 'runes': self.LETHAL_TEMPO_RUNES},
            'Wukong': {'role': 'Fighter', 'items': [3078, 3071, 3748, 3742, 3026, 3111], 'runes': self.CONQUEROR_RUNES},
            'Yorick': {'role': 'Fighter', 'items': [3078, 3748, 3053, 3742, 3065, 3047], 'runes': self.CONQUEROR_RUNES},
            
            # Mages
            'Ahri': {'role': 'Mage', 'items': [6653, 4645, 3157, 3089, 3135, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Anivia': {'role': 'Mage', 'items': [3040, 3003, 3157, 6653, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Annie': {'role': 'Mage', 'items': [6653, 4645, 3157, 3089, 3135, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'AurelionSol': {'role': 'Mage', 'items': [6653, 3116, 3157, 3135, 3089, 3020], 'runes': self.PHASE_RUSH_RUNES},
            'Azir': {'role': 'Mage', 'items': [3152, 4645, 3135, 3157, 3089, 3020], 'runes': self.LETHAL_TEMPO_RUNES},
            'Brand': {'role': 'Mage', 'items': [6653, 3135, 4645, 3089, 3157, 3020], 'runes': self.DARK_HARVEST_RUNES},
            'Cassiopeia': {'role': 'Mage', 'items': [3040, 3003, 3157, 6653, 3089, 3135], 'runes': self.CONQUEROR_RUNES},
            'Hwei': {'role': 'Mage', 'items': [6653, 3089, 4645, 3135, 3157, 3020], 'runes': self.ARCANE_COMET_RUNES},
            'Karma': {'role': 'Mage', 'items': [6653, 3504, 3135, 3089, 3157, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Karthus': {'role': 'Mage', 'items': [6653, 3089, 3135, 4645, 3157, 3020], 'runes': self.DARK_HARVEST_RUNES},
            'Lissandra': {'role': 'Mage', 'items': [6653, 3157, 4645, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Lux': {'role': 'Mage', 'items': [6653, 4645, 3135, 3089, 3157, 3020], 'runes': self.ARCANE_COMET_RUNES},
            'Malzahar': {'role': 'Mage', 'items': [6653, 3089, 3135, 3157, 4645, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Neeko': {'role': 'Mage', 'items': [3152, 4645, 3157, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Orianna': {'role': 'Mage', 'items': [6653, 3157, 3089, 4645, 3135, 3020], 'runes': self.PHASE_RUSH_RUNES},
            'Ryze': {'role': 'Mage', 'items': [3040, 3003, 3157, 6653, 3089, 3020], 'runes': self.PHASE_RUSH_RUNES},
            'Syndra': {'role': 'Mage', 'items': [6653, 4645, 3135, 3089, 3157, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Taliyah': {'role': 'Mage', 'items': [6653, 4645, 3157, 3135, 3089, 3020], 'runes': self.PHASE_RUSH_RUNES},
            'Twisted Fate': {'role': 'Mage', 'items': [3152, 6653, 3157, 3089, 3135, 3020], 'runes': self.PHASE_RUSH_RUNES},
            'TwistedFate': {'role': 'Mage', 'items': [3152, 6653, 3157, 3089, 3135, 3020], 'runes': self.PHASE_RUSH_RUNES},
            'Veigar': {'role': 'Mage', 'items': [6653, 3089, 4645, 3135, 3157, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'VelKoz': {'role': 'Mage', 'items': [6653, 3135, 4645, 3089, 3157, 3020], 'runes': self.ARCANE_COMET_RUNES},
            'VelKoz': {'role': 'Mage', 'items': [6653, 3135, 4645, 3089, 3157, 3020], 'runes': self.ARCANE_COMET_RUNES},
            'Viktor': {'role': 'Mage', 'items': [6653, 3157, 3089, 4645, 3135, 3020], 'runes': self.PHASE_RUSH_RUNES},
            'Vladimir': {'role': 'Mage', 'items': [3152, 3157, 6653, 3089, 3135, 3020], 'runes': self.PHASE_RUSH_RUNES},
            'Xerath': {'role': 'Mage', 'items': [6653, 4645, 3135, 3089, 3157, 3020], 'runes': self.ARCANE_COMET_RUNES},
            'Ziggs': {'role': 'Mage', 'items': [6653, 4645, 3135, 3089, 3157, 3020], 'runes': self.ARCANE_COMET_RUNES},
            'Zoe': {'role': 'Mage', 'items': [6653, 4645, 3157, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Zyra': {'role': 'Mage', 'items': [6653, 3089, 3135, 4645, 3157, 3020], 'runes': self.ARCANE_COMET_RUNES},
            
            # Tanks
            'Alistar': {'role': 'Tank', 'items': [3190, 3109, 3068, 3075, 3065, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Amumu': {'role': 'Tank', 'items': [3068, 6653, 3075, 3143, 3065, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Blitzcrank': {'role': 'Tank', 'items': [3190, 3109, 3068, 3075, 3143, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Braum': {'role': 'Tank', 'items': [3190, 3109, 3068, 3075, 3065, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'ChoGath': {'role': 'Tank', 'items': [3068, 3075, 3742, 3065, 3143, 3047], 'runes': self.GRASP_RUNES},
            'Galio': {'role': 'Tank', 'items': [3068, 3157, 3065, 3075, 3742, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Gragas': {'role': 'Tank', 'items': [3068, 3157, 3742, 3075, 3065, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'KSante': {'role': 'Tank', 'items': [3068, 3748, 3143, 3075, 3065, 3047], 'runes': self.GRASP_RUNES},
            # K'Sante handled by KSante key above
            'Leona': {'role': 'Tank', 'items': [3190, 3109, 3068, 3075, 3065, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Malphite': {'role': 'Tank', 'items': [3068, 3075, 3143, 3742, 3065, 3047], 'runes': self.ARCANE_COMET_RUNES},
            'Maokai': {'role': 'Tank', 'items': [3068, 3075, 3065, 3143, 3742, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Nautilus': {'role': 'Tank', 'items': [3190, 3109, 3068, 3075, 3065, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Nunu': {'role': 'Tank', 'items': [3068, 3075, 3143, 3065, 3742, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Ornn': {'role': 'Tank', 'items': [3068, 3075, 3143, 3065, 3742, 3047], 'runes': self.GRASP_RUNES},
            'Poppy': {'role': 'Tank', 'items': [3068, 3748, 3075, 3143, 3065, 3047], 'runes': self.GRASP_RUNES},
            'Rammus': {'role': 'Tank', 'items': [3068, 3075, 3143, 6664, 3065, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Rell': {'role': 'Tank', 'items': [3190, 3109, 3068, 3075, 3065, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Sejuani': {'role': 'Tank', 'items': [3068, 3075, 3143, 3065, 3742, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Shen': {'role': 'Tank', 'items': [3068, 3748, 3075, 3065, 3742, 3047], 'runes': self.GRASP_RUNES},
            'Sion': {'role': 'Tank', 'items': [3068, 3075, 3143, 3065, 3742, 3047], 'runes': self.GRASP_RUNES},
            'Tahm Kench': {'role': 'Tank', 'items': [3068, 3748, 3075, 3065, 3742, 3047], 'runes': self.GRASP_RUNES},
            'TahmKench': {'role': 'Tank', 'items': [3068, 3748, 3075, 3065, 3742, 3047], 'runes': self.GRASP_RUNES},
            'Taric': {'role': 'Tank', 'items': [3190, 3109, 3068, 3075, 3065, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Thresh': {'role': 'Tank', 'items': [3190, 3109, 3068, 3075, 3065, 3047], 'runes': self.AFTERSHOCK_RUNES},
            'Zac': {'role': 'Tank', 'items': [3068, 3075, 3065, 3143, 3742, 3047], 'runes': self.AFTERSHOCK_RUNES},
            
            # Supports (Enchanters)
            'Bard': {'role': 'Support', 'items': [3504, 3107, 3152, 3050, 3157, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Janna': {'role': 'Support', 'items': [3504, 3107, 3011, 3050, 3222, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Lulu': {'role': 'Support', 'items': [3504, 3107, 3011, 3050, 3222, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Milio': {'role': 'Support', 'items': [3504, 3107, 3011, 3050, 3222, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Nami': {'role': 'Support', 'items': [3504, 3107, 3011, 3050, 3222, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Rakan': {'role': 'Support', 'items': [3504, 3107, 3050, 3222, 3011, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Renata Glasc': {'role': 'Support', 'items': [3504, 3107, 3011, 3050, 3222, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'RenataGlasc': {'role': 'Support', 'items': [3504, 3107, 3011, 3050, 3222, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Senna': {'role': 'Support', 'items': [6692, 3094, 3031, 3046, 6676, 3006], 'runes': self.FLEET_FOOTWORK_RUNES},
            'Seraphine': {'role': 'Support', 'items': [3504, 3107, 3011, 3050, 3222, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Sona': {'role': 'Support', 'items': [3504, 3107, 3011, 3050, 3222, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Soraka': {'role': 'Support', 'items': [3504, 3107, 3011, 3050, 3222, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Yuumi': {'role': 'Support', 'items': [3504, 3107, 3011, 3050, 3222, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Zilean': {'role': 'Support', 'items': [3504, 3107, 3050, 6653, 3222, 3020], 'runes': self.SUMMON_AERY_RUNES},
            
            # Skirmishers/Divers
            'Diana': {'role': 'Diver', 'items': [3152, 4645, 3157, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Elise': {'role': 'Diver', 'items': [3152, 4645, 3157, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Hecarim': {'role': 'Diver', 'items': [3078, 3071, 3748, 6630, 3065, 3111], 'runes': self.CONQUEROR_RUNES},
            'Jarvan IV': {'role': 'Diver', 'items': [6692, 3071, 3748, 3742, 3065, 3111], 'runes': self.CONQUEROR_RUNES},
            'JarvanIV': {'role': 'Diver', 'items': [6692, 3071, 3748, 3742, 3065, 3111], 'runes': self.CONQUEROR_RUNES},
            'Lee Sin': {'role': 'Diver', 'items': [6692, 3071, 3748, 3742, 3065, 3111], 'runes': self.CONQUEROR_RUNES},
            'LeeSin': {'role': 'Diver', 'items': [6692, 3071, 3748, 3742, 3065, 3111], 'runes': self.CONQUEROR_RUNES},
            'Master Yi': {'role': 'Diver', 'items': [3124, 3153, 3085, 3091, 3046, 3006], 'runes': self.LETHAL_TEMPO_RUNES},
            'MasterYi': {'role': 'Diver', 'items': [3124, 3153, 3085, 3091, 3046, 3006], 'runes': self.LETHAL_TEMPO_RUNES},
            'RekSai': {'role': 'Diver', 'items': [6692, 3071, 3748, 3053, 3026, 3111], 'runes': self.HAIL_OF_BLADES_RUNES},
            'RekSai': {'role': 'Diver', 'items': [6692, 3071, 3748, 3053, 3026, 3111], 'runes': self.HAIL_OF_BLADES_RUNES},
            'Viego': {'role': 'Diver', 'items': [3153, 3078, 3156, 3026, 3053, 3111], 'runes': self.CONQUEROR_RUNES},
            'Xin Zhao': {'role': 'Diver', 'items': [6692, 3748, 3156, 3071, 3026, 3111], 'runes': self.HAIL_OF_BLADES_RUNES},
            'XinZhao': {'role': 'Diver', 'items': [6692, 3748, 3156, 3071, 3026, 3111], 'runes': self.HAIL_OF_BLADES_RUNES},
            
            # Ranged/Marksman (Top/Mid)
            'Akshan': {'role': 'Marksman', 'items': [3031, 3046, 6676, 3094, 3072, 3006], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'Corki': {'role': 'Marksman', 'items': [3078, 3115, 3031, 3089, 3046, 3020], 'runes': self.FLEET_FOOTWORK_RUNES},
            'Graves': {'role': 'Marksman', 'items': [6692, 6676, 3156, 3814, 3036, 3111], 'runes': self.FLEET_FOOTWORK_RUNES},
            'Kindred': {'role': 'Marksman', 'items': [3153, 3078, 3046, 3094, 3091, 3006], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'Quinn': {'role': 'Marksman', 'items': [3031, 6676, 3094, 3046, 3072, 3006], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'Teemo': {'role': 'Marksman', 'items': [6653, 3152, 3135, 3089, 3157, 3020], 'runes': self.SUMMON_AERY_RUNES},
            
            # Unique/Hybrid
            'Dr. Mundo': {'role': 'Tank', 'items': [3068, 3075, 3065, 3748, 3143, 3047], 'runes': self.GRASP_RUNES},
            'DrMundo': {'role': 'Tank', 'items': [3068, 3075, 3065, 3748, 3143, 3047], 'runes': self.GRASP_RUNES},
            'Fiddlesticks': {'role': 'Mage', 'items': [3152, 3157, 6653, 3089, 3135, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Gangplank': {'role': 'Fighter', 'items': [3078, 6676, 3508, 3031, 3036, 3111], 'runes': self.FLEET_FOOTWORK_RUNES},
            'Gnar': {'role': 'Fighter', 'items': [3078, 3071, 3748, 3053, 3065, 3047], 'runes': self.FLEET_FOOTWORK_RUNES},
            'Ivern': {'role': 'Support', 'items': [3504, 3107, 3011, 3050, 3222, 3020], 'runes': self.SUMMON_AERY_RUNES},
            'Kayn': {'role': 'Assassin', 'items': [6691, 3142, 6676, 3814, 3036, 3111], 'runes': self.CONQUEROR_RUNES},
            'Kennen': {'role': 'Mage', 'items': [3152, 4645, 3157, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Kled': {'role': 'Fighter', 'items': [6630, 3071, 3748, 6632, 3065, 3111], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'Lillia': {'role': 'Mage', 'items': [6653, 3116, 3157, 3089, 3135, 3020], 'runes': self.DARK_HARVEST_RUNES},
            'Naafiri': {'role': 'Assassin', 'items': [3142, 6691, 6676, 3814, 3036, 3111], 'runes': self.ELECTROCUTE_RUNES},
            'Nasus': {'role': 'Fighter', 'items': [3078, 3065, 3748, 3053, 3742, 3047], 'runes': self.FLEET_FOOTWORK_RUNES},
            'Nidalee': {'role': 'Assassin', 'items': [3152, 6653, 3157, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Shyvana': {'role': 'Fighter', 'items': [4633, 3115, 3135, 3157, 3089, 3020], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'Singed': {'role': 'Tank', 'items': [4633, 3116, 3075, 3065, 3742, 3047], 'runes': self.CONQUEROR_RUNES},
            'Skarner': {'role': 'Fighter', 'items': [3078, 3748, 3071, 3065, 3742, 3047], 'runes': self.PHASE_RUSH_RUNES},
            'Swain': {'role': 'Mage', 'items': [6653, 3157, 3089, 3135, 4645, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Sylas': {'role': 'Assassin', 'items': [3152, 3157, 6653, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Udyr': {'role': 'Fighter', 'items': [3078, 3748, 3071, 3065, 3742, 3047], 'runes': self.PRESS_THE_ATTACK_RUNES},
            'Vex': {'role': 'Mage', 'items': [6653, 4645, 3157, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Yasuo': {'role': 'Fighter', 'items': [3031, 3046, 3153, 3026, 3072, 3006], 'runes': self.CONQUEROR_RUNES},
            'Yone': {'role': 'Fighter', 'items': [3031, 3046, 3153, 3026, 3072, 3006], 'runes': self.CONQUEROR_RUNES},
            
            # New/Newest Champions
            'Aurora': {'role': 'Mage', 'items': [6653, 4645, 3157, 3135, 3089, 3020], 'runes': self.ELECTROCUTE_RUNES},
            'Ambessa': {'role': 'Fighter', 'items': [6630, 3071, 3748, 3156, 3065, 3111], 'runes': self.CONQUEROR_RUNES},
            'Briar': {'role': 'Diver', 'items': [6692, 3748, 3074, 3065, 3071, 3111], 'runes': self.HAIL_OF_BLADES_RUNES},
            'Mel': {'role': 'Mage', 'items': [6653, 3089, 4645, 3135, 3157, 3020], 'runes': self.ARCANE_COMET_RUNES},
        }
        
    def get_meta_build(self, champion_name: str, patch: str = None, champion_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get meta build for a champion
        
        Uses intelligent fallback system:
        1. Check if champion has manual build in database
        2. If patch specified, check for patch-specific overrides
        3. If not found, use intelligent build based on champion stats/tags
        
        Args:
            champion_name: Champion name
            patch: Patch version (e.g., '14.24', '25.S1.1')
            champion_data: Champion data from Data Dragon (for intelligent classification)
            
        Returns:
            Dictionary with items and runes
        """
        # Try manual builds first
        if champion_name in self.meta_builds:
            build = self.meta_builds[champion_name].copy()
            rune_setup = build['runes']
            base_build = {
                'items': build['items'],
                'runes': rune_setup['runes'],
                'primary_style': rune_setup['primary_style'],
                'sub_style': rune_setup['sub_style'],
                'role': build['role'],
                'notes': f"{build['role']} build (manual)",
                'auto_generated': False
            }
        else:
            # Use intelligent build system
            if champion_data:
                from .intelligent_build_provider import intelligent_build_provider
                base_build = intelligent_build_provider.get_intelligent_build(champion_name, champion_data)
            else:
                # Last resort: generic AD build
                base_build = {
                    'items': [3031, 3072, 3046, 3094, 3508, 3006],
                    'runes': [8005, 9111, 9104, 8014, 8234, 8237, 5008, 5008, 5002],
                    'primary_style': 8000,
                    'sub_style': 8200,
                    'role': 'Unknown',
                    'notes': 'Generic AD build (no champion data provided)',
                    'auto_generated': True
                }
        
        # If patch specified, check for patch-specific overrides
        if patch:
            from .patch_specific_builds import patch_specific_builds
            return patch_specific_builds.get_build_for_patch(champion_name, patch, base_build)
        
        return base_build


# Singleton instance
meta_builds_db = MetaBuildsDatabase()

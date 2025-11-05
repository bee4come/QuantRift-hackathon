"""
OP.GG Leaderboard Data Batcher

This service fetches and batches champion leaderboard data from the OP.GG MCP server
using the lol_list_lane_meta_champions tool, which provides comprehensive tier information.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .opgg_mcp_service import opgg_mcp_service

class OPGGLeaderboardBatcher:
    def __init__(self):
        self.cache_file = "data/opgg_leaderboard_data.json"
        self.cache_duration = timedelta(hours=6)  # Cache for 6 hours
        
    def refresh_data(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetch fresh leaderboard data from OP.GG MCP server
        
        Args:
            force: Force refresh even if cache is valid
            
        Returns:
            Dict containing leaderboard data or None if failed
        """
        try:
            # Check if we should use cached data
            if not force and self.is_cache_valid():
                print("Using cached leaderboard data")
                return self.load_from_cache()
            
            print("Fetching fresh leaderboard data...")
            print("Fetching leaderboard data from OP.GG MCP server...")
            
            # Call the MCP tool
            result = opgg_mcp_service.get_all_positions_meta()
            
            if not result:
                print("❌ Failed to fetch leaderboard data from MCP server")
                return None
            
            # Process the data
            processed_data = self._process_leaderboard_data(result)
            
            # Save to cache
            self._save_to_cache(processed_data)
            
            print(f"Leaderboard data saved to {self.cache_file}")
            return processed_data
            
        except Exception as e:
            print(f"Error fetching leaderboard data: {e}")
            return None
    
    def _process_leaderboard_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw leaderboard data into our format
        
        Args:
            raw_data: Raw data from OP.GG MCP server
            
        Returns:
            Processed data structure
        """
        try:
            processed_positions = {}
            
            # Champion ID to name mapping
            champion_map = self._get_champion_map()
            
            for position_key, champions in raw_data.items():
                position_name = position_key.upper()
                
                processed_champions = []
                
                for champion in champions:
                    # Tier is already a letter (A, B, C, D, S) from MCP service
                    tier_letter = champion.get('tier', 'D')
                    
                    # Categorize tier: S and A = META, B/C/D = Normal
                    champion['tier_category'] = 'META' if tier_letter in ['S', 'A'] else 'Normal'
                    
                    # Add champion name if not present
                    if 'champion_name' not in champion:
                        champion_id = champion.get('champion_id')
                        champion_name = champion_map.get(champion_id)
                        champion['champion_name'] = champion_name
                    
                    # Add position
                    champion['position'] = position_name
                    
                    processed_champions.append(champion)
                
                processed_positions[position_name] = {
                    'champions': processed_champions,
                    'total_champions': len(processed_champions)
                }
            
            return {
                'positions': processed_positions,
                'metadata': {
                    'last_updated': datetime.now().isoformat(),
                    'source': 'opgg_mcp_leaderboard',
                    'total_positions': len(processed_positions)
                }
            }
            
        except Exception as e:
            print(f"Error processing leaderboard data: {e}")
            return {}
    
    def _get_champion_map(self) -> Dict[int, str]:
        """
        Get champion ID to name mapping
        This is a simplified mapping - in production you'd want to fetch this from Riot API
        """
        # This is a basic mapping - you might want to fetch this from Riot API
        champion_map = {
            1: "Annie", 2: "Olaf", 3: "Galio", 4: "TwistedFate", 5: "XinZhao",
            6: "Urgot", 7: "LeBlanc", 8: "Vladimir", 9: "FiddleSticks", 10: "Kayle",
            11: "MasterYi", 12: "Alistar", 13: "Ryze", 14: "Sion", 15: "Sivir",
            16: "Soraka", 17: "Teemo", 18: "Tristana", 19: "Warwick", 20: "Nunu",
            21: "MissFortune", 22: "Ashe", 23: "Tryndamere", 24: "Jax", 25: "Morgana",
            26: "Zilean", 27: "Singed", 28: "Evelynn", 29: "Twitch", 30: "Karthus",
            31: "Chogath", 32: "Amumu", 33: "Rammus", 34: "Anivia", 35: "Shaco",
            36: "DrMundo", 37: "Sona", 38: "Kassadin", 39: "Irelia", 40: "Janna",
            41: "Gangplank", 42: "Corki", 43: "Karma", 44: "Taric", 45: "Veigar",
            46: "Trundle", 47: "Swain", 48: "Caitlyn", 49: "Blitzcrank", 50: "Malphite",
            51: "Katarina", 52: "Nocturne", 53: "Maokai", 54: "Renekton", 55: "JarvanIV",
            56: "Elise", 57: "Orianna", 58: "Wukong", 59: "Brand", 60: "LeeSin",
            61: "Vayne", 62: "Rumble", 63: "Cassiopeia", 64: "Skarner", 65: "Heimerdinger",
            66: "Nasus", 67: "Nidalee", 68: "Udyr", 69: "Poppy", 70: "Gragas",
            71: "Pantheon", 72: "Ezreal", 73: "Mordekaiser", 74: "Yorick", 75: "Akali",
            76: "Kennen", 77: "Garen", 78: "Leona", 79: "Malzahar", 80: "Talon",
            81: "Riven", 82: "KogMaw", 83: "Shen", 84: "Lux", 85: "Xerath",
            86: "Shyvana", 87: "Ahri", 88: "Graves", 89: "Fizz", 90: "Volibear",
            91: "Rengar", 92: "Varus", 93: "Nautilus", 94: "Viktor", 95: "Sejuani",
            96: "Fiora", 97: "Ziggs", 98: "Lulu", 99: "Draven", 100: "Hecarim",
            101: "Khazix", 102: "Darius", 103: "Jayce", 104: "Lissandra", 105: "Diana",
            106: "Quinn", 107: "Syndra", 108: "AurelionSol", 109: "Kayn", 110: "Zoe",
            111: "Zyra", 112: "Kaisa", 113: "Seraphine", 114: "Gnar", 115: "Zac",
            116: "Yasuo", 117: "Velkoz", 118: "Taliyah", 119: "Camille", 120: "Akshan",
            121: "Belveth", 122: "Braum", 123: "Jhin", 124: "Kindred", 125: "Zeri",
            126: "Jinx", 127: "TahmKench", 128: "Briar", 129: "Viego", 130: "Senna",
            131: "Lucian", 132: "Zed", 133: "Kled", 134: "Ekko", 135: "Qiyana",
            136: "Vi", 137: "Aatrox", 138: "Nami", 139: "Azir", 140: "Yuumi",
            141: "Samira", 142: "Thresh", 143: "Illaoi", 144: "RekSai", 145: "Ivern",
            146: "Kalista", 147: "Bard", 148: "Rakan", 149: "Xayah", 150: "Ornn",
            151: "Sylas", 152: "Neeko", 153: "Aphelios", 154: "Rell", 155: "Pyke",
            156: "Vex", 157: "Yone", 158: "Ambessa", 159: "Sett", 160: "Lillia",
            161: "Gwen", 162: "RenataGlasc", 163: "Aurora", 164: "Nilah", 165: "Ksante",
            166: "Smolder", 167: "Milio", 168: "Hwei", 169: "Naafiri"
        }
        return champion_map
    
    def load_from_cache(self) -> Optional[Dict[str, Any]]:
        """Load data from cache file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
        return None
    
    def _save_to_cache(self, data: Dict[str, Any]) -> None:
        """Save data to cache file"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def is_cache_valid(self) -> bool:
        """Check if cached data is still valid"""
        try:
            if not os.path.exists(self.cache_file):
                return False
            
            # Check file modification time
            mod_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file))
            return datetime.now() - mod_time < self.cache_duration
        except Exception:
            return False

# Global instance
opgg_leaderboard_batcher = OPGGLeaderboardBatcher()

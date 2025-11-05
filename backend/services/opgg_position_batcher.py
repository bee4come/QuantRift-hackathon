"""
OP.GG Position Data Fetcher and Batcher
Fetches comprehensive position statistics and batches them locally for fast access
"""
import requests
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import time


class OPGGPositionDataBatcher:
    """
    Fetches and batches OP.GG position data for all champions and positions
    """
    
    def __init__(self):
        self.mcp_url = "https://mcp-api.op.gg/mcp"
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.cache_file = os.path.join(self.cache_dir, 'opgg_position_data.json')
        self.timeout = 15
        self.max_retries = 3
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def _make_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a request to the MCP server with retry logic"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.mcp_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'error' in data:
                        print(f"MCP server error: {data['error']}")
                        return None
                    return data.get('result')
                else:
                    print(f"MCP server HTTP error: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"MCP server request error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    
        return None
    
    def fetch_position_data(self, position: str) -> Optional[Dict[str, Any]]:
        """Fetch position data for a specific lane"""
        try:
            result = self._make_request("tools/call", {
                "name": "lol_list_lane_meta_champions",
                "arguments": {
                    "lane": position,
                    "lang": "en_US"
                }
            })
            
            if result and 'content' in result and result['content']:
                data = json.loads(result['content'][0]['text'])
                return data
            return None
            
        except Exception as e:
            print(f"Error fetching position data for {position}: {e}")
            return None
    
    def fetch_all_positions_data(self) -> Dict[str, Any]:
        """Fetch data for all positions"""
        positions = ['top', 'jungle', 'mid', 'adc', 'support']
        all_data = {}
        
        print("Fetching position data from OP.GG MCP server...")
        
        for position in positions:
            print(f"  Fetching {position} data...")
            data = self.fetch_position_data(position)
            if data:
                all_data[position] = data
                print(f"    ✅ {position}: {len(data.get('data', {}).get(f'position.{position}', {}).get('rows', []))} champions")
            else:
                print(f"    ❌ {position}: Failed to fetch data")
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.5)
        
        return all_data
    
    def process_position_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw position data into a more usable format"""
        processed_data = {
            'metadata': {
                'last_updated': datetime.now().isoformat(),
                'source': 'opgg_mcp',
                'total_positions': len(raw_data)
            },
            'positions': {},
            'champions': {}
        }
        
        # Champion ID to name mapping
        champion_map = self._get_champion_id_map()
        
        for position, data in raw_data.items():
            if 'data' not in data:
                continue
                
            position_key = f"position.{position}"
            if position_key not in data['data']:
                continue
            
            position_data = data['data'][position_key]
            headers = position_data.get('headers', [])
            rows = position_data.get('rows', [])
            
            processed_position = {
                'position': position.upper(),
                'champions': [],
                'total_champions': len(rows)
            }
            
            for row in rows:
                if len(row) >= len(headers):
                    champion_data = {}
                    for i, header in enumerate(headers):
                        champion_data[header] = row[i]
                    
                    # Convert tier number to letter and categorize
                    tier_num = champion_data.get('tier', 5)
                    tier_map = {0: 'S', 1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'D'}
                    tier_letter = tier_map.get(tier_num, 'D')
                    champion_data['tier'] = tier_letter
                    
                    # Categorize tier: S and A = META, B/C/D = Normal
                    champion_data['tier_category'] = 'META' if tier_letter in ['S', 'A'] else 'Normal'
                    
                    # Add champion name
                    champion_id = champion_data.get('champion_id')
                    champion_name = champion_map.get(champion_id)
                    champion_data['champion_name'] = champion_name
                    
                    # Convert rates to percentages
                    champion_data['win_rate'] = champion_data.get('win_rate', 0) * 100
                    champion_data['pick_rate'] = champion_data.get('pick_rate', 0) * 100
                    champion_data['ban_rate'] = champion_data.get('ban_rate', 0) * 100
                    
                    processed_position['champions'].append(champion_data)
                    
                    # Add to global champions data
                    if champion_name:
                        if champion_name not in processed_data['champions']:
                            processed_data['champions'][champion_name] = {
                                'champion_id': champion_id,
                                'positions': {}
                            }
                        
                        processed_data['champions'][champion_name]['positions'][position.upper()] = {
                            'tier': champion_data['tier'],
                            'win_rate': champion_data['win_rate'],
                            'pick_rate': champion_data['pick_rate'],
                            'ban_rate': champion_data['ban_rate'],
                            'rank': champion_data.get('rank', 999),
                            'kda': champion_data.get('kda', 0)
                        }
            
            processed_data['positions'][position.upper()] = processed_position
        
        return processed_data
    
    def _get_champion_id_map(self) -> Dict[int, str]:
        """Get champion ID to name mapping"""
        return {
            1: "Annie", 2: "Olaf", 3: "Galio", 4: "TwistedFate", 5: "XinZhao",
            6: "Urgot", 7: "LeBlanc", 8: "Vladimir", 9: "FiddleSticks", 10: "Kayle",
            11: "MasterYi", 12: "Alistar", 13: "Ryze", 14: "Sion", 15: "Sivir",
            16: "Soraka", 17: "Teemo", 18: "Tristana", 19: "Warwick", 20: "Nunu",
            21: "MissFortune", 22: "Ashe", 23: "Tryndamere", 24: "Jax", 25: "Morgana",
            26: "Zilean", 27: "Singed", 28: "Evelynn", 29: "Twitch", 30: "Karthus",
            31: "ChoGath", 32: "Amumu", 33: "Rammus", 34: "Anivia", 35: "Shaco",
            36: "DrMundo", 37: "Sona", 38: "Kassadin", 39: "Irelia", 40: "Janna",
            41: "Gangplank", 42: "Corki", 43: "Karma", 44: "Taric", 45: "Veigar",
            48: "Trundle", 50: "Swain", 51: "Caitlyn", 53: "Blitzcrank", 54: "Malphite",
            55: "Katarina", 56: "Nocturne", 57: "Maokai", 58: "Renekton", 59: "JarvanIV",
            60: "Elise", 61: "Orianna", 62: "Wukong", 63: "Brand", 64: "LeeSin",
            67: "Vayne", 68: "Rumble", 69: "Cassiopeia", 72: "Skarner", 74: "Heimerdinger",
            75: "Nasus", 76: "Nidalee", 77: "Udyr", 78: "Poppy", 79: "Gragas",
            80: "Pantheon", 81: "Ezreal", 82: "Mordekaiser", 83: "Yorick", 84: "Akali",
            85: "Kennen", 86: "Garen", 89: "Leona", 90: "Malzahar", 91: "Talon",
            92: "Riven", 96: "KogMaw", 98: "Shen", 99: "Lux", 101: "Xerath",
            102: "Shyvana", 103: "Ahri", 104: "Graves", 105: "Fizz", 106: "Volibear",
            107: "Rengar", 110: "Varus", 111: "Nautilus", 112: "Viktor", 113: "Sejuani",
            114: "Fiora", 115: "Ziggs", 117: "Lulu", 119: "Draven", 120: "Hecarim",
            121: "Khazix", 122: "Darius", 126: "Jayce", 127: "Lissandra", 131: "Diana",
            133: "Quinn", 134: "Syndra", 136: "AurelionSol", 141: "Kayn", 142: "Zoe",
            143: "Zyra", 147: "Seraphine", 150: "Gnar", 154: "Zac", 157: "Yasuo",
            161: "VelKoz", 163: "Taliyah", 164: "Camille", 166: "Akshan", 200: "BelVeth",
            201: "Braum", 202: "Jhin", 203: "Kindred", 222: "Jinx", 223: "TahmKench",
            234: "Viego", 235: "Senna", 236: "Lucian", 238: "Zed", 240: "Kled",
            245: "Ekko", 246: "Qiyana", 254: "Vi", 266: "Aatrox", 267: "Nami",
            268: "Azir", 350: "Yuumi", 360: "Samira", 412: "Thresh", 420: "Illaoi",
            421: "RekSai", 427: "Ivern", 429: "Kalista", 432: "Bard", 497: "Rakan",
            498: "Xayah", 516: "Ornn", 517: "Sylas", 518: "Neeko", 523: "Aphelios",
            526: "Rell", 555: "Pyke", 711: "Vex", 777: "Yone", 875: "Sett",
            876: "Lillia", 887: "Gwen", 888: "Renata", 895: "K'Sante", 897: "K'Sante",
            901: "Smolder", 902: "Milio", 910: "Hwei", 950: "Naafiri"
        }
    
    def save_to_cache(self, data: Dict[str, Any]):
        """Save processed data to cache file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Position data saved to {self.cache_file}")
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def load_from_cache(self) -> Optional[Dict[str, Any]]:
        """Load data from cache file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                return data
        except Exception as e:
            print(f"Error loading cache: {e}")
        return None
    
    def is_cache_valid(self, max_age_hours: int = 1) -> bool:
        """Check if cache is still valid"""
        try:
            if not os.path.exists(self.cache_file):
                return False
            
            data = self.load_from_cache()
            if not data or 'metadata' not in data:
                return False
            
            last_updated = datetime.fromisoformat(data['metadata']['last_updated'])
            age = datetime.now() - last_updated
            
            return age < timedelta(hours=max_age_hours)
        except Exception as e:
            print(f"Error checking cache validity: {e}")
            return False
    
    def refresh_data(self, force: bool = False) -> Dict[str, Any]:
        """Refresh position data"""
        if not force and self.is_cache_valid():
            print("Using cached position data")
            return self.load_from_cache()
        
        print("Fetching fresh position data...")
        raw_data = self.fetch_all_positions_data()
        
        if not raw_data:
            print("Failed to fetch fresh data, using cache if available")
            cached_data = self.load_from_cache()
            if cached_data:
                return cached_data
            return {}
        
        processed_data = self.process_position_data(raw_data)
        self.save_to_cache(processed_data)
        
        return processed_data
    
    def get_champion_positions(self, champion_name: str) -> Dict[str, Any]:
        """Get all positions for a specific champion"""
        data = self.load_from_cache()
        if not data or 'champions' not in data:
            return {}
        
        return data['champions'].get(champion_name, {})
    
    def get_position_leaderboard(self, position: str) -> List[Dict[str, Any]]:
        """Get leaderboard for a specific position"""
        data = self.load_from_cache()
        if not data or 'positions' not in data:
            return []
        
        position_data = data['positions'].get(position.upper(), {})
        return position_data.get('champions', [])
    
    def get_all_champions_data(self) -> Dict[str, Any]:
        """Get all champions data"""
        data = self.load_from_cache()
        if not data or 'champions' not in data:
            return {}
        
        return data['champions']


# Global instance
opgg_position_batcher = OPGGPositionDataBatcher()

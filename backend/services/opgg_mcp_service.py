"""
OP.GG MCP Service Wrapper
Ensures reliable access to OP.GG meta data through MCP server
"""
import requests
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class OPGGMCPService:
    """
    Service wrapper for OP.GG MCP server with reliability features
    """
    
    def __init__(self):
        self.mcp_url = "https://mcp-api.op.gg/mcp"
        self.timeout = 15
        self.max_retries = 3
        self.retry_delay = 1
        self.last_health_check = None
        self.health_check_interval = 300  # 5 minutes
        self.is_healthy = False
        
    def _make_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Make a request to the MCP server with retry logic
        """
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
                    time.sleep(self.retry_delay * (attempt + 1))
                    
        return None
    
    def health_check(self) -> bool:
        """
        Check if the MCP server is healthy
        """
        now = datetime.now()
        if (self.last_health_check and 
            now - self.last_health_check < timedelta(seconds=self.health_check_interval)):
            return self.is_healthy
            
        try:
            # Test with a simple tool list request
            result = self._make_request("tools/list", {})
            if result and 'tools' in result:
                self.is_healthy = True
                self.last_health_check = now
                print("OP.GG MCP server health check: OK")
                return True
        except Exception as e:
            print(f"OP.GG MCP server health check failed: {e}")
            
        self.is_healthy = False
        self.last_health_check = now
        return False
    
    def get_champion_meta_data(self, champion: str, position: str = "mid", 
                             game_mode: str = "ranked") -> Optional[Dict[str, Any]]:
        """
        Get champion meta data including tier, win rate, pick rate, ban rate
        """
        if not self.health_check():
            print("OP.GG MCP server is not healthy")
            return None
            
        result = self._make_request("tools/call", {
            "name": "lol_get_champion_analysis",
            "arguments": {
                "champion": champion,
                "game_mode": game_mode,
                "position": position,
                "lang": "en_US"
            }
        })
        
        if result and 'content' in result and result['content']:
            try:
                data = json.loads(result['content'][0]['text'])
                return data
            except json.JSONDecodeError as e:
                print(f"Failed to parse champion meta data: {e}")
                
        return None
    
    def get_lane_meta_champions(self, lane: str = "mid") -> Optional[Dict[str, Any]]:
        """
        Get meta champions for a specific lane with tier rankings
        """
        if not self.health_check():
            print("OP.GG MCP server is not healthy")
            return None
            
        result = self._make_request("tools/call", {
            "name": "lol_list_lane_meta_champions",
            "arguments": {
                "lane": lane,
                "lang": "en_US"
            }
        })
        
        if result and 'content' in result and result['content']:
            try:
                data = json.loads(result['content'][0]['text'])
                return data
            except json.JSONDecodeError as e:
                print(f"Failed to parse lane meta data: {e}")
                
        return None
    
    def get_champion_leaderboard(self, position: str = "all") -> Optional[List[Dict[str, Any]]]:
        """
        Get champion leaderboard with tier rankings
        """
        meta_data = self.get_lane_meta_champions(position)
        if not meta_data or 'data' not in meta_data:
            return None
            
        leaderboard = []
        position_key = f"position.{position.lower()}"
        
        if position_key in meta_data['data']:
            position_data = meta_data['data'][position_key]
            headers = position_data.get('headers', [])
            rows = position_data.get('rows', [])
            
            # Map headers to row data
            for row in rows:
                if len(row) >= len(headers):
                    champion_data = {}
                    for i, header in enumerate(headers):
                        champion_data[header] = row[i]
                    
                    # Convert tier number to letter
                    tier_num = champion_data.get('tier', 5)
                    tier_map = {0: 'S', 1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'D'}
                    champion_data['tier'] = tier_map.get(tier_num, 'D')
                    
                    leaderboard.append(champion_data)
                    
        return leaderboard
    
    def get_all_positions_meta(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get meta data for all positions
        """
        positions = ['top', 'jungle', 'mid', 'adc', 'support']
        all_meta = {}
        
        for position in positions:
            leaderboard = self.get_champion_leaderboard(position)
            if leaderboard:
                all_meta[position.upper()] = leaderboard
                
        return all_meta
    
    def is_server_available(self) -> bool:
        """
        Check if the MCP server is available
        """
        return self.health_check()
    
    def get_summoner_profile(self, game_name: str, tag_line: str, region: str = "na") -> Optional[Dict[str, Any]]:
        """
        Get comprehensive summoner profile from OP.GG MCP
        
        Args:
            game_name: Summoner game name
            tag_line: Summoner tag line
            region: Region code (na, euw, kr, etc.)
            
        Returns:
            Comprehensive summoner data including:
            - Basic profile (level, profile image, puuid)
            - Current rank (tier, division, LP, wins, losses)
            - LP history (rank progression over time)
            - Previous seasons (historical ranks)
            - Most played champions (detailed stats)
            - Recent champion stats (last 7 champions)
            - Ladder rank (overall ranking position)
        """
        if not self.health_check():
            print("OP.GG MCP server is not healthy")
            return None
            
        result = self._make_request("tools/call", {
            "name": "lol_get_summoner_profile",
            "arguments": {
                "game_name": game_name,
                "tag_line": tag_line,
                "region": region,
                "lang": "en_US"
            }
        })
        
        if result and 'content' in result and result['content']:
            try:
                data = json.loads(result['content'][0]['text'])
                print(f"Successfully fetched OP.GG profile for {game_name}#{tag_line}")
                return data
            except json.JSONDecodeError as e:
                print(f"Failed to parse summoner profile data: {e}")
                return None
        else:
            print(f"Failed to fetch summoner profile for {game_name}#{tag_line}")
            return None


# Global instance
opgg_mcp_service = OPGGMCPService()

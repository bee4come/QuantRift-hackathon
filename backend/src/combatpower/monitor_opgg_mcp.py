#!/usr/bin/env python3
"""
OP.GG MCP Server Monitor
Ensures the MCP server is always working and provides alerts if it fails
"""
import time
import requests
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('opgg_mcp_monitor.log'),
        logging.StreamHandler()
    ]
)

class OPGGMCPMonitor:
    def __init__(self):
        self.mcp_url = "https://mcp-api.op.gg/mcp"
        self.health_check_interval = 300  # 5 minutes
        self.alert_threshold = 3  # Alert after 3 consecutive failures
        self.consecutive_failures = 0
        self.last_alert_time = None
        self.alert_cooldown = 1800  # 30 minutes between alerts
        
    def check_mcp_health(self):
        """Check if the MCP server is healthy"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            response = requests.post(
                self.mcp_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'error' not in data and 'result' in data:
                    self.consecutive_failures = 0
                    logging.info("OP.GG MCP server is healthy")
                    return True
            
            logging.warning(f"MCP server returned status {response.status_code}")
            return False
            
        except Exception as e:
            logging.error(f"MCP server health check failed: {e}")
            return False
    
    def test_meta_data_retrieval(self):
        """Test actual meta data retrieval"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "lol_list_lane_meta_champions",
                    "arguments": {
                        "lane": "mid",
                        "lang": "en_US"
                    }
                }
            }
            
            response = requests.post(
                self.mcp_url,
                json=payload,
                timeout=15,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and 'content' in data['result']:
                    meta_data = json.loads(data['result']['content'][0]['text'])
                    if 'data' in meta_data and 'position.mid' in meta_data['data']:
                        champions_count = len(meta_data['data']['position.mid'].get('rows', []))
                        logging.info(f"Successfully retrieved meta data for {champions_count} mid lane champions")
                        return True
            
            logging.warning("Meta data retrieval test failed")
            return False
            
        except Exception as e:
            logging.error(f"Meta data retrieval test failed: {e}")
            return False
    
    def send_alert(self, message):
        """Send alert about MCP server issues"""
        now = datetime.now()
        
        # Check if we should send an alert (cooldown period)
        if (self.last_alert_time and 
            now - self.last_alert_time < self.alert_cooldown):
            return
        
        logging.error(f"ALERT: {message}")
        self.last_alert_time = now
        
        # Here you could add email notifications, Slack webhooks, etc.
        # For now, we'll just log the alert
    
    def run_monitor(self):
        """Run the monitoring loop"""
        logging.info("Starting OP.GG MCP server monitor")
        
        while True:
            try:
                # Check basic health
                is_healthy = self.check_mcp_health()
                
                if is_healthy:
                    # Test actual functionality
                    meta_working = self.test_meta_data_retrieval()
                    if not meta_working:
                        self.consecutive_failures += 1
                        if self.consecutive_failures >= self.alert_threshold:
                            self.send_alert("MCP server is responding but meta data retrieval is failing")
                else:
                    self.consecutive_failures += 1
                    if self.consecutive_failures >= self.alert_threshold:
                        self.send_alert("MCP server is not responding")
                
                # Wait before next check
                time.sleep(self.health_check_interval)
                
            except KeyboardInterrupt:
                logging.info("Monitor stopped by user")
                break
            except Exception as e:
                logging.error(f"Monitor error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    monitor = OPGGMCPMonitor()
    monitor.run_monitor()

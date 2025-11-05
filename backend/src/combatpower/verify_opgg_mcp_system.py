#!/usr/bin/env python3
"""
OP.GG MCP System Verification Script
Comprehensive test to ensure the MCP server is always working
"""
import requests
import json
import time
from datetime import datetime

def test_mcp_server_direct():
    """Test MCP server directly"""
    print("🔍 Testing OP.GG MCP server directly...")
    
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
            "https://mcp-api.op.gg/mcp",
            json=payload,
            timeout=15,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'content' in data['result']:
                meta_data = json.loads(data['result']['content'][0]['text'])
                champions_count = len(meta_data['data']['position.mid'].get('rows', []))
                print(f"✅ MCP server direct test: {champions_count} champions retrieved")
                return True
        
        print("❌ MCP server direct test failed")
        return False
        
    except Exception as e:
        print(f"❌ MCP server direct test error: {e}")
        return False

def test_backend_health():
    """Test backend health endpoint"""
    print("🔍 Testing backend health endpoint...")
    
    try:
        response = requests.get("http://localhost:5000/api/health/opgg-mcp", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('mcp_server_healthy'):
                print("✅ Backend health check: MCP server is healthy")
                return True
            else:
                print("❌ Backend health check: MCP server is unhealthy")
                return False
        
        print(f"❌ Backend health check failed: HTTP {response.status_code}")
        return False
        
    except Exception as e:
        print(f"❌ Backend health check error: {e}")
        return False

def test_leaderboard_api():
    """Test leaderboard API endpoints"""
    print("🔍 Testing leaderboard API endpoints...")
    
    endpoints = [
        ("all", "ALL"),
        ("mid", "MID"),
        ("top", "TOP"),
        ("jungle", "JUNGLE"),
        ("adc", "ADC"),
        ("support", "SUPPORT")
    ]
    
    all_passed = True
    
    for endpoint, position in endpoints:
        try:
            response = requests.get(f"http://localhost:5000/api/champions/leaderboard?position={endpoint}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'leaderboard' in data:
                    leaderboard = data['leaderboard']
                    total_entries = data.get('total_entries', 0)
                    source = leaderboard.get('source', 'unknown')
                    
                    if total_entries > 0:
                        print(f"✅ {position} leaderboard: {total_entries} champions (source: {source})")
                    else:
                        print(f"❌ {position} leaderboard: No champions found")
                        all_passed = False
                else:
                    print(f"❌ {position} leaderboard: Invalid response format")
                    all_passed = False
            else:
                print(f"❌ {position} leaderboard: HTTP {response.status_code}")
                all_passed = False
                
        except Exception as e:
            print(f"❌ {position} leaderboard error: {e}")
            all_passed = False
    
    return all_passed

def test_data_quality():
    """Test data quality and consistency"""
    print("🔍 Testing data quality...")
    
    try:
        response = requests.get("http://localhost:5000/api/champions/leaderboard?position=mid", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            leaderboard = data['leaderboard']['data']
            
            # Check for required fields
            required_fields = ['champion_name', 'tier', 'win_rate', 'pick_rate', 'ban_rate', 'rank']
            sample_champion = leaderboard[0] if leaderboard else {}
            
            missing_fields = [field for field in required_fields if field not in sample_champion]
            if missing_fields:
                print(f"❌ Data quality: Missing fields: {missing_fields}")
                return False
            
            # Check tier values
            valid_tiers = {'S', 'A', 'B', 'C', 'D'}
            invalid_tiers = [champ['tier'] for champ in leaderboard[:10] if champ['tier'] not in valid_tiers]
            if invalid_tiers:
                print(f"❌ Data quality: Invalid tier values: {invalid_tiers}")
                return False
            
            # Check win rate range
            invalid_winrates = [champ['win_rate'] for champ in leaderboard[:10] if not (0 <= champ['win_rate'] <= 100)]
            if invalid_winrates:
                print(f"❌ Data quality: Invalid win rate values: {invalid_winrates}")
                return False
            
            print("✅ Data quality: All checks passed")
            return True
        
        print("❌ Data quality: Could not retrieve data")
        return False
        
    except Exception as e:
        print(f"❌ Data quality error: {e}")
        return False

def main():
    """Run all verification tests"""
    print("🚀 OP.GG MCP System Verification")
    print("=" * 50)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("MCP Server Direct", test_mcp_server_direct),
        ("Backend Health", test_backend_health),
        ("Leaderboard API", test_leaderboard_api),
        ("Data Quality", test_data_quality)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        result = test_func()
        results.append((test_name, result))
        print()
    
    # Summary
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print()
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! OP.GG MCP system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the system.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

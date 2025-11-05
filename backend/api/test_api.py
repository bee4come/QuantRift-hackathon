"""
API Test Script for Risk Forecaster and Annual Summary Endpoints
"""

import requests
import json
from pathlib import Path
from typing import Dict, Any

# API Configuration
BASE_URL = "http://localhost:8000"
RISK_FORECASTER_ENDPOINT = f"{BASE_URL}/v1/risk-forecaster/analyze"
ANNUAL_SUMMARY_ENDPOINT = f"{BASE_URL}/v1/annual-summary"


def test_risk_forecaster():
    """Test Risk Forecaster API endpoint"""
    print("\n" + "="*80)
    print("Testing Risk Forecaster Endpoint")
    print("="*80)
    
    # Example request payload
    request_data = {
        "match_id": "test_match_001",
        "our_team": {
            "composition": [
                {"champion_id": 105, "role": "TOP", "summoner_id": "player1"},
                {"champion_id": 64, "role": "JUNGLE", "summoner_id": "player2"},
                {"champion_id": 103, "role": "MIDDLE", "summoner_id": "player3"},
                {"champion_id": 498, "role": "BOTTOM", "summoner_id": "player4"},
                {"champion_id": 432, "role": "UTILITY", "summoner_id": "player5"}
            ]
        },
        "enemy_team": {
            "composition": [
                {"champion_id": 92, "role": "TOP", "summoner_id": None},
                {"champion_id": 120, "role": "JUNGLE", "summoner_id": None},
                {"champion_id": 157, "role": "MIDDLE", "summoner_id": None},
                {"champion_id": 222, "role": "BOTTOM", "summoner_id": None},
                {"champion_id": 12, "role": "UTILITY", "summoner_id": None}
            ]
        },
        "include_visualizations": True,
        "language": "en"
    }
    
    try:
        print(f"\n📤 Sending POST request to {RISK_FORECASTER_ENDPOINT}")
        print(f"Request payload: {json.dumps(request_data, indent=2)}")
        
        response = requests.post(
            RISK_FORECASTER_ENDPOINT,
            json=request_data,
            timeout=60
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Success! API returned valid response")
            print(f"\nResponse structure:")
            print(f"  - risk_level: {data.get('risk_level')}")
            print(f"  - win_probability: {data.get('win_probability')}")
            print(f"  - power_curve points: {len(data.get('power_curve', {}).get('time_series', []))}")
            print(f"  - phase_tactics: {len(data.get('phase_tactics', []))}")
            print(f"  - key_milestones: {len(data.get('key_milestones', []))}")
            
            # Check power curve data
            power_curve = data.get('power_curve', {})
            if power_curve.get('time_series'):
                print(f"\n📈 Power Curve Sample (first 3 points):")
                for point in power_curve['time_series'][:3]:
                    print(f"  Minute {point['minute']}: Our={point['our_power']:.1f}, Enemy={point['enemy_power']:.1f}, Diff={point['power_diff']:+.1f}")
            
            # Save full response
            output_file = "/home/zty/rift_rewind/api/test_risk_forecaster_response.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n💾 Full response saved to: {output_file}")
            
            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Could not connect to API server")
        print("Make sure server is running with: uvicorn api.server:app --reload")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        return False


def test_annual_summary():
    """Test Annual Summary API endpoint"""
    print("\n" + "="*80)
    print("Testing Annual Summary Endpoint")
    print("="*80)
    
    # Test with actual summoner data (if exists)
    summoner_id = "s1ne"  # Example summoner ID
    params = {
        "region": "na1",
        "start_patch": "15.12",
        "end_patch": "15.20"
    }
    
    try:
        endpoint_url = f"{ANNUAL_SUMMARY_ENDPOINT}/{summoner_id}"
        print(f"\n📤 Sending GET request to {endpoint_url}")
        print(f"Parameters: {params}")
        
        response = requests.get(
            endpoint_url,
            params=params,
            timeout=120
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Success! API returned valid response")
            print(f"\nResponse structure:")
            print(f"  - summoner_id: {data.get('summoner_id')}")
            print(f"  - region: {data.get('region')}")
            print(f"  - season_overview.total_games: {data.get('season_overview', {}).get('total_games')}")
            print(f"  - season_overview.overall_winrate: {data.get('season_overview', {}).get('overall_winrate')}")
            print(f"  - growth_curve points: {len(data.get('growth_curve', []))}")
            print(f"  - three_phase_comparison phases: {len(data.get('three_phase_comparison', []))}")
            
            # Check growth curve data
            growth_curve = data.get('growth_curve', [])
            if growth_curve:
                print(f"\n📈 Growth Curve Sample (first 3 patches):")
                for point in growth_curve[:3]:
                    print(f"  Patch {point['patch']}: Games={point['games']}, WR={point['winrate']:.1%}")
            
            # Save full response
            output_file = f"/home/zty/rift_rewind/api/test_annual_summary_response.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n💾 Full response saved to: {output_file}")
            
            return True
        elif response.status_code == 404:
            print(f"\n⚠️  Player data not found for summoner: {summoner_id}")
            print("This is expected if player data hasn't been collected yet")
            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Could not connect to API server")
        print("Make sure server is running with: uvicorn api.server:app --reload")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        return False


def test_health_check():
    """Test health check endpoint"""
    print("\n" + "="*80)
    print("Testing Health Check Endpoint")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Health check passed: {data}")
            return True
        else:
            print(f"\n❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Health check failed: {str(e)}")
        return False


def main():
    """Run all API tests"""
    print("\n" + "="*80)
    print("🚀 Starting API Test Suite")
    print("="*80)
    
    results = {
        "health_check": test_health_check(),
        "risk_forecaster": test_risk_forecaster(),
        "annual_summary": test_annual_summary()
    }
    
    print("\n" + "="*80)
    print("📊 Test Results Summary")
    print("="*80)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check output above for details.")


if __name__ == "__main__":
    main()

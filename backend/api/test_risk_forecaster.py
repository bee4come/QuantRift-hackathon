"""
Test Risk Forecaster API endpoint only
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/v1/risk-forecaster/analyze"


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
                {"champion_id": 105, "role": "TOP"},      # Fizz
                {"champion_id": 64, "role": "JUNGLE"},    # Lee Sin
                {"champion_id": 103, "role": "MIDDLE"},   # Ahri
                {"champion_id": 498, "role": "BOTTOM"},   # Xayah
                {"champion_id": 432, "role": "UTILITY"}   # Bard
            ]
        },
        "enemy_team": {
            "composition": [
                {"champion_id": 92, "role": "TOP"},       # Riven
                {"champion_id": 120, "role": "JUNGLE"},   # Hecarim
                {"champion_id": 157, "role": "MIDDLE"},   # Yasuo
                {"champion_id": 222, "role": "BOTTOM"},   # Jinx
                {"champion_id": 12, "role": "UTILITY"}    # Alistar
            ]
        },
        "include_visualizations": True,
        "language": "en"
    }
    
    try:
        print(f"\n📤 Sending POST request to {ENDPOINT}")
        print(f"Request payload:")
        print(json.dumps(request_data, indent=2))
        
        print("\n⏳ Waiting for response (this may take 2-3 minutes due to LLM generation)...")
        
        response = requests.post(
            ENDPOINT,
            json=request_data,
            timeout=300  # 5 minute timeout
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Success! API returned valid response")
            
            # Print structure
            print(f"\n📊 Response structure:")
            print(f"  - match_id: {data.get('match_id')}")
            print(f"  - timestamp: {data.get('timestamp')}")
            print(f"  - analysis_version: {data.get('analysis_version')}")
            
            # Power curve
            power_curve = data.get('power_curve', {})
            time_series = power_curve.get('time_series', [])
            print(f"\n📈 Power Curve:")
            print(f"  - Total data points: {len(time_series)}")
            if time_series:
                print(f"  - First point: Minute {time_series[0]['minute']}, Our={time_series[0]['our_power']:.1f}, Enemy={time_series[0]['enemy_power']:.1f}")
                print(f"  - Last point: Minute {time_series[-1]['minute']}, Our={time_series[-1]['our_power']:.1f}, Enemy={time_series[-1]['enemy_power']:.1f}")
                
                if power_curve.get('crossover_point'):
                    print(f"  - Crossover at: {power_curve['crossover_point']['minute']} min")
            
            # Key milestones
            milestones = data.get('key_milestones', [])
            print(f"\n🎯 Key Milestones: {len(milestones)} identified")
            for i, milestone in enumerate(milestones[:3], 1):
                print(f"  {i}. {milestone['minute']}min - {milestone.get('title', 'N/A')} ({milestone['risk_level']})")
            
            # Phase tactics
            tactics = data.get('phase_tactics', [])
            print(f"\n⚔️  Phase Tactics: {len(tactics)} phases")
            for tactic in tactics:
                print(f"  - {tactic['phase'].upper()}: {tactic['objective']}")
            
            # Victory path
            victory_path = data.get('victory_path', {})
            print(f"\n🏆 Victory Path:")
            print(f"  - Summary: {victory_path.get('summary', 'N/A')}")
            stages = victory_path.get('stages', [])
            print(f"  - Stages: {len(stages)}")
            
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
            
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out after 5 minutes")
        print("The LLM call may be taking longer than expected")
        return False
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Could not connect to API server")
        print("Make sure server is running with: uvicorn api.server:app --reload")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_risk_forecaster()

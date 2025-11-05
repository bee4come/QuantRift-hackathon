"""
Test custom build system
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_custom_builds():
    """Test custom build API"""
    print("="*70)
    print("Testing Custom Build System")
    print("="*70)
    
    # 1. Get all champions
    print("\n1. Get all configured champions:")
    response = requests.get(f"{BASE_URL}/api/custom-build/champions")
    if response.status_code == 200:
        data = response.json()
        print(f"   Champion count: {data['total']}")
        print(f"   Champion list: {data['champions']}")
    else:
        print(f"   Error: {response.status_code}")
    
    # 2. Get Draven's build
    print("\n2. Get Draven's build:")
    response = requests.get(f"{BASE_URL}/api/custom-build/champions/Draven")
    if response.status_code == 200:
        data = response.json()
        print(f"   Items: {data['build']['items']}")
        print(f"   Runes: {data['build']['runes']}")
    else:
        print(f"   Error: {response.status_code}")
    
    # 3. Update Draven's items
    print("\n3. Update Draven's items:")
    new_items = [3031, 3072, 3046, 3085, 3006, 0]  # IE, BT, PD, Runaan's, Boots, Empty
    response = requests.put(
        f"{BASE_URL}/api/custom-build/champions/Draven/items",
        json={"items": new_items}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   Update successful: {data['items']}")
    else:
        print(f"   Error: {response.status_code}")
    
    # 4. Update Draven's runes
    print("\n4. Update Draven's runes:")
    new_runes = {
        "primary_style": 8000,  # Precision
        "sub_style": 8100,      # Domination
        "perk_ids": [8008, 9111, 9104, 8014, 8139, 8135, 5005, 5008, 5002]
    }
    response = requests.put(
        f"{BASE_URL}/api/custom-build/champions/Draven/runes",
        json={"runes": new_runes}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   Update successful: {data['runes']}")
    else:
        print(f"   Error: {response.status_code}")
    
    # 5. Test API endpoint
    print("\n5. Test API endpoint:")
    response = requests.get(f"{BASE_URL}/api/patch/champion/Draven/patch/14.20")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total power: {data['champion']['total_combat_power']}")
        print(f"   Item power: {data['champion']['item_power']}")
        print(f"   Rune power: {data['champion']['rune_power']}")
        print(f"   Custom build: {data['popular_build']['is_custom']}")
    else:
        print(f"   Error: {response.status_code}")
    
    # 6. Add new champion
    print("\n6. Add new champion Yasuo:")
    yasuo_build = {
        "items": [3031, 3072, 3046, 3085, 3006, 0],
        "runes": {
            "primary_style": 8000,
            "sub_style": 8200,
            "perk_ids": [8005, 9111, 9104, 8014, 8234, 8237, 5008, 5008, 5002]
        }
    }
    response = requests.post(
        f"{BASE_URL}/api/custom-build/champions/Yasuo",
        json=yasuo_build
    )
    if response.status_code == 200:
        data = response.json()
        print(f"   Add successful: {data['message']}")
    else:
        print(f"   Error: {response.status_code}")
    
    print("\n" + "="*70)
    print("Testing completed!")
    print("="*70)

if __name__ == '__main__':
    test_custom_builds()

"""
Test script for the multi-patch system
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .services.patch_manager import patch_manager
from .services.data_provider import data_provider
from .services.combat_power import combat_power_calculator


def test_patch_manager():
    """Test patch manager functionality"""
    print("="*60)
    print("Testing Patch Manager")
    print("="*60)
    
    # Test patch detection
    import time
    from datetime import datetime
    
    test_dates = [
        ("Sep 25, 2024", datetime(2024, 9, 25)),
        ("Oct 15, 2024", datetime(2024, 10, 15)),
        ("Dec 15, 2024", datetime(2024, 12, 15)),
        ("Jan 20, 2025", datetime(2025, 1, 20)),
    ]
    
    print("\nPatch Detection:")
    for date_str, date_obj in test_dates:
        timestamp_ms = int(date_obj.timestamp() * 1000)
        patch = patch_manager.get_patch_for_timestamp(timestamp_ms)
        ddragon = patch_manager.get_ddragon_version(patch)
        print(f"  {date_str} -> Patch {patch} (DDragon: {ddragon})")
    
    # List all patches
    print(f"\nTotal Patches: {len(patch_manager.get_all_patches())}")
    print(f"First 5 patches: {patch_manager.get_all_patches()[:5]}")
    print(f"Last 5 patches: {patch_manager.get_all_patches()[-5:]}")


def test_multi_patch_data():
    """Test fetching data for different patches"""
    print("\n" + "="*60)
    print("Testing Multi-Patch Data Fetching")
    print("="*60)
    
    patches_to_test = ["14.19", "14.22", "15.5"]
    
    for patch in patches_to_test:
        print(f"\nFetching data for Patch {patch}...")
        
        try:
            # Fetch champions
            champions = data_provider.get_champions_for_patch(patch)
            print(f"  Champions available: {len(champions)}")
            
            # Fetch Draven detail
            draven = data_provider.get_champion_detail_for_patch(patch, "Draven")
            if draven:
                print(f"  Draven found: {draven.get('name')} - {draven.get('title')}")
                stats = draven.get('stats', {})
                print(f"    Base AD: {stats.get('attackdamage', 'N/A')}")
                print(f"    Base HP: {stats.get('hp', 'N/A')}")
            
            # Fetch items
            items = data_provider.get_items_for_patch(patch)
            print(f"  Items available: {len(items)}")
            
        except Exception as e:
            print(f"  Error: {e}")


def test_combat_power_by_patch():
    """Test combat power calculations for different patches"""
    print("\n" + "="*60)
    print("Testing Combat Power Across Patches")
    print("="*60)
    
    champion = "Draven"
    level = 18
    items = [3072, 3031, 3046]  # Bloodthirster, Infinity Edge, Phantom Dancer
    patches = ["14.19", "14.22"]
    
    print(f"\nChampion: {champion} (Level {level})")
    print(f"Items: Bloodthirster, Infinity Edge, Phantom Dancer\n")
    
    for patch in patches:
        try:
            power = combat_power_calculator.calculate_total_combat_power(
                champion_name=champion,
                level=level,
                item_ids=items,
                patch=patch
            )
            
            print(f"Patch {patch}:")
            print(f"  Total Combat Power: {power:.2f}")
            
            # Get detailed breakdown
            champions = data_provider.get_champions_for_patch(patch)
            champion_detail = data_provider.get_champion_detail_for_patch(patch, champion)
            
            if champion in champions:
                stats = champions[champion]['stats']
                base_power = combat_power_calculator.calculate_base_stats_power(stats, level)
                skill_power = combat_power_calculator.calculate_skill_power(champion_detail)
                item_power = combat_power_calculator.calculate_item_power(items)
                
                print(f"    Base Stats Power: {base_power:.2f}")
                print(f"    Skill Power: {skill_power:.2f}")
                print(f"    Item Power: {item_power:.2f}")
                print(f"    Base AD: {stats.get('attackdamage', 'N/A')}")
        except Exception as e:
            print(f"Patch {patch}: Error - {e}")


def test_champion_comparison():
    """Compare multiple champions in same patch"""
    print("\n" + "="*60)
    print("Testing Champion Comparison (Patch 14.19)")
    print("="*60)
    
    patch = "14.19"
    champions_to_test = ["Draven", "Jinx", "Vayne", "KSante", "Zed"]
    
    results = []
    
    for champion in champions_to_test:
        try:
            power = combat_power_calculator.calculate_total_combat_power(
                champion_name=champion,
                level=18,
                patch=patch
            )
            results.append((champion, power))
        except Exception as e:
            print(f"Error calculating {champion}: {e}")
    
    # Sort by power
    results.sort(key=lambda x: x[1], reverse=True)
    
    print("\nChampion Power Rankings:")
    for i, (champ, power) in enumerate(results, 1):
        print(f"  {i}. {champ}: {power:.2f}")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Multi-Patch System Tests")
    print("="*60)
    
    # Run all tests
    test_patch_manager()
    test_multi_patch_data()
    test_combat_power_by_patch()
    test_champion_comparison()
    
    print("\n" + "="*60)
    print("All Tests Completed!")
    print("="*60)
    print("\nNote: Some tests may fail if internet connection is unavailable")
    print("or if Data Dragon doesn't have data for newer patches yet.")


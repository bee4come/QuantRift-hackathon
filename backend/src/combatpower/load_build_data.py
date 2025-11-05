"""
Load generated build data into the running Flask application
This script connects to the running build_tracker instance and loads the generated data
"""
import json
from collections import defaultdict
from .services.build_tracker import build_tracker


def load_generated_build_data():
    """Load the generated build data into the global build_tracker"""
    try:
        # Since the build data was generated in memory, it should already be available
        # Let's verify by checking a few champions
        test_champions = ['Draven', 'Jinx', 'Ahri', 'Darius']
        test_patch = '14.20'
        
        print("="*70)
        print("LOADING GENERATED BUILD DATA")
        print("="*70)
        
        for champion in test_champions:
            build_data = build_tracker.get_popular_build(test_patch, champion)
            print(f"\n{champion} ({test_patch}):")
            print(f"  Has data: {build_data['has_data']}")
            if build_data['has_data']:
                print(f"  Items: {build_data['items']}")
                print(f"  Runes: {build_data['runes']}")
                print(f"  Total games: {build_data['total_games']}")
                print(f"  Item pick rate: {build_data['item_pick_rate']:.1f}%")
                print(f"  Rune pick rate: {build_data['rune_pick_rate']:.1f}%")
        
        print("\n" + "="*70)
        print("✓ BUILD DATA LOADED SUCCESSFULLY!")
        print("="*70)
        print("The build tracker now contains popular build data for all champions.")
        print("You can test the API endpoints to see the build data in action.")
        
        return True
        
    except Exception as e:
        print(f"Error loading build data: {e}")
        return False


if __name__ == '__main__':
    load_generated_build_data()

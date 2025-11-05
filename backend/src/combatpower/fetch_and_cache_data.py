"""
Fetch and cache all Data Dragon data locally for all patches
Run this once to download all necessary data
"""
import os
import json
import requests
import sys
from datetime import datetime
from .services.patch_manager import patch_manager


class DataCacher:
    """Fetch and cache all patch data locally"""
    
    def __init__(self, cache_dir='data/patches'):
        self.cache_dir = cache_dir
        self.base_url = 'https://ddragon.leagueoflegends.com/cdn'
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
    def fetch_champions_for_patch(self, patch: str) -> dict:
        """Fetch champion data for a specific patch"""
        ddragon_version = patch_manager.get_ddragon_version(patch)
        url = f"{self.base_url}/{ddragon_version}/data/en_US/champion.json"
        
        print(f"  Fetching champions for {patch} ({ddragon_version})...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        return response.json()
    
    def fetch_champion_detail(self, patch: str, champion_id: str) -> dict:
        """Fetch detailed champion data"""
        ddragon_version = patch_manager.get_ddragon_version(patch)
        url = f"{self.base_url}/{ddragon_version}/data/en_US/champion/{champion_id}.json"
        
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        return response.json()
    
    def fetch_items_for_patch(self, patch: str) -> dict:
        """Fetch item data for a specific patch"""
        ddragon_version = patch_manager.get_ddragon_version(patch)
        url = f"{self.base_url}/{ddragon_version}/data/en_US/item.json"
        
        print(f"  Fetching items for {patch} ({ddragon_version})...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        return response.json()
    
    def fetch_runes_for_patch(self, patch: str) -> dict:
        """Fetch rune data for a specific patch"""
        ddragon_version = patch_manager.get_ddragon_version(patch)
        url = f"{self.base_url}/{ddragon_version}/data/en_US/runesReforged.json"
        
        print(f"  Fetching runes for {patch} ({ddragon_version})...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        return response.json()
    
    def save_patch_data(self, patch: str, champions_data: dict, items_data: dict, runes_data: dict):
        """Save patch data to local files"""
        patch_dir = os.path.join(self.cache_dir, patch)
        os.makedirs(patch_dir, exist_ok=True)
        
        # Save champions
        with open(os.path.join(patch_dir, 'champions.json'), 'w', encoding='utf-8') as f:
            json.dump(champions_data, f, indent=2)
        
        # Save items
        with open(os.path.join(patch_dir, 'items.json'), 'w', encoding='utf-8') as f:
            json.dump(items_data, f, indent=2)
        
        # Save runes
        with open(os.path.join(patch_dir, 'runes.json'), 'w', encoding='utf-8') as f:
            json.dump(runes_data, f, indent=2)
        
        print(f"  ✓ Saved data for patch {patch}")
    
    def fetch_champion_details_batch(self, patch: str, champion_ids: list):
        """Fetch detailed data for all champions in a patch"""
        patch_dir = os.path.join(self.cache_dir, patch, 'champions_detail')
        os.makedirs(patch_dir, exist_ok=True)
        
        print(f"  Fetching {len(champion_ids)} champion details for {patch}...")
        
        success_count = 0
        for i, champ_id in enumerate(champion_ids):
            try:
                detail = self.fetch_champion_detail(patch, champ_id)
                
                with open(os.path.join(patch_dir, f'{champ_id}.json'), 'w', encoding='utf-8') as f:
                    json.dump(detail, f, indent=2)
                
                success_count += 1
                
                if (i + 1) % 20 == 0:
                    print(f"    Progress: {i + 1}/{len(champion_ids)}")
                    
            except Exception as e:
                print(f"    Error fetching {champ_id}: {e}")
        
        print(f"  ✓ Saved {success_count}/{len(champion_ids)} champion details")
    
    def validate_patch_data(self, patch: str) -> bool:
        """Validate that patch data is complete and accurate"""
        patch_dir = os.path.join(self.cache_dir, patch)
        
        # Check if files exist
        champions_file = os.path.join(patch_dir, 'champions.json')
        items_file = os.path.join(patch_dir, 'items.json')
        runes_file = os.path.join(patch_dir, 'runes.json')
        
        if not all(os.path.exists(f) for f in [champions_file, items_file, runes_file]):
            return False
        
        # Load and validate
        try:
            with open(champions_file, 'r', encoding='utf-8') as f:
                champions = json.load(f)
                if 'data' not in champions or len(champions['data']) < 100:
                    print(f"  ✗ Invalid champions data for {patch}")
                    return False
            
            with open(items_file, 'r', encoding='utf-8') as f:
                items = json.load(f)
                if 'data' not in items or len(items['data']) < 100:
                    print(f"  ✗ Invalid items data for {patch}")
                    return False
            
            with open(runes_file, 'r', encoding='utf-8') as f:
                runes = json.load(f)
                if not isinstance(runes, list) or len(runes) < 5:
                    print(f"  ✗ Invalid runes data for {patch}")
                    return False
            
            print(f"  ✓ Valid: {len(champions['data'])} champions, {len(items['data'])} items, {len(runes)} rune trees")
            return True
            
        except Exception as e:
            print(f"  ✗ Validation error for {patch}: {e}")
            return False
    
    def cache_all_patches(self, patches: list = None, include_champion_details: bool = True):
        """Fetch and cache data for all patches"""
        if patches is None:
            patches = patch_manager.get_all_patches()
        
        print("="*70)
        print(f"Fetching data for {len(patches)} patches")
        print("="*70)
        
        total_success = 0
        total_failed = 0
        
        for i, patch in enumerate(patches, 1):
            print(f"\n[{i}/{len(patches)}] Processing patch {patch}")
            
            try:
                # Fetch basic data
                champions_data = self.fetch_champions_for_patch(patch)
                items_data = self.fetch_items_for_patch(patch)
                runes_data = self.fetch_runes_for_patch(patch)
                
                # Save to disk
                self.save_patch_data(patch, champions_data, items_data, runes_data)
                
                # Optionally fetch champion details
                if include_champion_details:
                    champion_ids = list(champions_data['data'].keys())
                    self.fetch_champion_details_batch(patch, champion_ids)
                
                # Validate
                if self.validate_patch_data(patch):
                    total_success += 1
                else:
                    total_failed += 1
                    
            except Exception as e:
                print(f"  ✗ Error processing {patch}: {e}")
                total_failed += 1
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Total patches: {len(patches)}")
        print(f"Successfully cached: {total_success}")
        print(f"Failed: {total_failed}")
        print(f"Data directory: {os.path.abspath(self.cache_dir)}")
        
        # Create metadata file
        metadata = {
            'cached_at': datetime.now().isoformat(),
            'total_patches': len(patches),
            'patches': patches,
            'success_count': total_success,
            'failed_count': total_failed
        }
        
        with open(os.path.join(self.cache_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\nMetadata saved to: {os.path.join(self.cache_dir, 'metadata.json')}")
        
        return total_success == len(patches)


def main():
    """Main function to cache all data"""
    print("\n" + "="*70)
    print("DATA DRAGON CACHE BUILDER")
    print("="*70)
    print("\nThis script will download all champion, item, and rune data")
    print("for all patches and store them locally for fast access.")
    print("\n" + "="*70)
    
    cacher = DataCacher()
    
    # Get all patches
    all_patches = patch_manager.get_all_patches()
    print(f"\nTotal patches to cache: {len(all_patches)}")
    print(f"Patches: {', '.join(all_patches[:5])}... {', '.join(all_patches[-3:])}")
    
    # Check for --yes flag to skip confirmation
    auto_confirm = '--yes' in sys.argv
    
    if not auto_confirm:
        # Ask for confirmation
        try:
            response = input("\nProceed with download? (yes/no): ").lower()
            if response != 'yes':
                print("Aborted.")
                return
        except EOFError:
            print("\nNo input available. Use --yes flag to run without confirmation.")
            return
    else:
        print("\nAuto-confirming download (--yes flag detected)...")
    
    # Cache all data
    success = cacher.cache_all_patches(
        patches=all_patches,
        include_champion_details=True
    )
    
    if success:
        print("\n" + "="*70)
        print("✓ ALL DATA SUCCESSFULLY CACHED!")
        print("="*70)
        print("\nYou can now run the application offline.")
        print("Data is stored in: data/patches/")
    else:
        print("\n" + "="*70)
        print("⚠ SOME PATCHES FAILED")
        print("="*70)
        print("\nPlease check the errors above and retry if needed.")


if __name__ == '__main__':
    main()


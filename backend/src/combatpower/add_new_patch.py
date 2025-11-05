"""
Add a new patch to the cached data
Run this when a new patch is officially released
"""
import os
import json
from datetime import datetime
from fetch_and_cache_data import DataCacher


def add_new_patch(patch_version: str, release_date: str, ddragon_version: str):
    """
    Add a new patch to the system
    
    Args:
        patch_version: User-facing patch name (e.g., '25.21', '25.S2.1')
        release_date: Release date in YYYY-MM-DD format
        ddragon_version: Data Dragon version (e.g., '15.21.1')
    
    Example:
        add_new_patch('25.21', '2025-10-21', '15.21.1')
    """
    print("="*70)
    print(f"Adding New Patch: {patch_version}")
    print("="*70)
    print(f"Release Date: {release_date}")
    print(f"Data Dragon Version: {ddragon_version}")
    print()
    
    # 1. Update patch_manager.py
    print("[1/3] Updating patch_manager.py...")
    update_patch_manager(patch_version, release_date, ddragon_version)
    print("  ✓ Updated")
    
    # 2. Download and cache the patch data
    print(f"\n[2/3] Downloading data for patch {patch_version}...")
    cacher = DataCacher()
    
    try:
        # Fetch data using the ddragon version
        champions_data = cacher.fetch_champions_for_patch(patch_version)
        items_data = cacher.fetch_items_for_patch(patch_version)
        runes_data = cacher.fetch_runes_for_patch(patch_version)
        
        # Save to disk
        cacher.save_patch_data(patch_version, champions_data, items_data, runes_data)
        
        # Download champion details
        champion_ids = list(champions_data['data'].keys())
        cacher.fetch_champion_details_batch(patch_version, champion_ids)
        
        # Validate
        if cacher.validate_patch_data(patch_version):
            print(f"  ✓ Successfully cached patch {patch_version}")
        else:
            print(f"  ✗ Validation failed for patch {patch_version}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error downloading patch {patch_version}: {e}")
        return False
    
    # 3. Update metadata
    print(f"\n[3/3] Updating metadata...")
    update_metadata(patch_version)
    print("  ✓ Metadata updated")
    
    print("\n" + "="*70)
    print(f"✓ Patch {patch_version} successfully added!")
    print("="*70)
    print(f"\nYou can now use patch {patch_version} in your API calls.")
    print(f"Example: GET /api/patch/champion/Draven/patch/{patch_version}")
    
    return True


def update_patch_manager(patch_version: str, release_date: str, ddragon_version: str):
    """Update the patch_manager.py file with new patch info"""
    
    # Read the current file
    patch_manager_file = 'services/patch_manager.py'
    with open(patch_manager_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse the release date
    date_obj = datetime.strptime(release_date, '%Y-%m-%d')
    date_str = f"datetime({date_obj.year}, {date_obj.month}, {date_obj.day})"
    
    # Add to PATCH_DATES
    patch_dates_insert = f"        '{patch_version}': {date_str},"
    
    # Find the last patch date line and insert after it
    lines = content.split('\n')
    new_lines = []
    inserted_date = False
    inserted_version = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Insert into PATCH_DATES (before the closing brace)
        if not inserted_date and '    }' in line and 'PATCH_DATES' in '\n'.join(lines[max(0,i-30):i]):
            new_lines.insert(-1, patch_dates_insert)
            inserted_date = True
        
        # Insert into DDRAGON_VERSIONS (before the closing brace)
        if not inserted_version and '    }' in line and 'DDRAGON_VERSIONS' in '\n'.join(lines[max(0,i-30):i]):
            new_lines.insert(-1, f"        '{patch_version}': '{ddragon_version}',")
            inserted_version = True
    
    # Write back
    with open(patch_manager_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))


def update_metadata(patch_version: str):
    """Update the metadata.json file"""
    metadata_file = 'data/patches/metadata.json'
    
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    else:
        metadata = {
            'cached_at': datetime.now().isoformat(),
            'patches': [],
            'total_patches': 0
        }
    
    # Add new patch
    if patch_version not in metadata['patches']:
        metadata['patches'].append(patch_version)
        metadata['total_patches'] = len(metadata['patches'])
        metadata['last_updated'] = datetime.now().isoformat()
        metadata['latest_patch'] = patch_version
    
    # Write back
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)


def main():
    """Interactive mode to add a new patch"""
    print("\n" + "="*70)
    print("ADD NEW PATCH TO THE SYSTEM")
    print("="*70)
    print("\nThis will:")
    print("1. Update patch_manager.py with the new patch info")
    print("2. Download and cache all data for the new patch")
    print("3. Update metadata")
    print("\n" + "="*70 + "\n")
    
    # Get patch info
    patch_version = input("Patch Version (e.g., 25.21, 25.S2.1): ").strip()
    release_date = input("Release Date (YYYY-MM-DD): ").strip()
    
    # Try to guess ddragon version
    # Pattern: 25.XX -> 15.XX.1, 25.S2.X -> 15.X.1 (season 2 starts at patch 15.X)
    suggested_ddragon = None
    if patch_version.startswith('25.'):
        parts = patch_version.replace('25.', '').replace('S1.', '').replace('S2.', '').replace('S', '')
        try:
            patch_num = int(parts)
            suggested_ddragon = f"15.{patch_num}.1"
        except:
            pass
    
    if suggested_ddragon:
        ddragon_input = input(f"Data Dragon Version (suggested: {suggested_ddragon}): ").strip()
        ddragon_version = ddragon_input if ddragon_input else suggested_ddragon
    else:
        ddragon_version = input("Data Dragon Version (e.g., 15.21.1): ").strip()
    
    # Confirm
    print("\n" + "="*70)
    print("Please confirm:")
    print(f"  Patch Version: {patch_version}")
    print(f"  Release Date: {release_date}")
    print(f"  Data Dragon: {ddragon_version}")
    print("="*70)
    
    confirm = input("\nProceed? (yes/no): ").lower()
    
    if confirm != 'yes':
        print("Aborted.")
        return
    
    # Add the patch
    success = add_new_patch(patch_version, release_date, ddragon_version)
    
    if success:
        print("\n✓ Successfully added patch!")
        print("\nNext steps:")
        print("1. Restart your app server")
        print("2. Test the new patch:")
        print(f"   python -c \"from services.patch_manager import patch_manager; print(patch_manager.get_all_patches())\"")
        print(f"3. Use in API:")
        print(f"   curl http://localhost:5000/api/patch/champion/Draven/patch/{patch_version}")
    else:
        print("\n✗ Failed to add patch. Please check the errors above.")


if __name__ == '__main__':
    main()


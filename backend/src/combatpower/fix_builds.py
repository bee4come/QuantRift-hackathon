#!/usr/bin/env python3
"""
Fix champion builds to use current patch item IDs
This script maps old item IDs to their current equivalents
"""
import json
import requests

# Item ID mappings (old -> new) based on item reworks
ITEM_MAPPINGS = {
    # Old Mythic/Legendary items -> Season 15 replacements
    3027: 3072,  # Rod of Ages -> Bloodthirster (placeholder)
    3136: 4005,  # Liandry's Anguish -> Imperial Mandate
    3151: 3165,  # Liandry's Anguish -> Morellonomicon  
    3157: 3152,  # Zhonya's Hourglass -> Hextech Rocketbelt
}

def get_current_items():
    """Get current patch item data"""
    response = requests.get('https://ddragon.leagueoflegends.com/cdn/15.20.1/data/en_US/item.json')
    items_data = response.json()['data']
    valid_ids = {int(item_id) for item_id in items_data.keys()}
    return valid_ids, items_data

def load_build_tracker_data():
    """Load the build tracker data"""
    with open('data/build_tracker_data.json', 'r') as f:
        return json.load(f)

def map_item_id(old_id, valid_ids):
    """Map an old item ID to a valid current one"""
    # If the item still exists, use it
    if old_id in valid_ids:
        return old_id
    
    # Try mapped replacement
    if old_id in ITEM_MAPPINGS:
        new_id = ITEM_MAPPINGS[old_id]
        if new_id in valid_ids:
            return new_id
    
    # Return None if no valid mapping
    return None

def fix_builds():
    """Fix all builds to use current item IDs"""
    print("Getting current patch items...")
    valid_ids, items_data = get_current_items()
    print(f"Found {len(valid_ids)} valid items in current patch")
    
    print("\nLoading build tracker data...")
    build_data = load_build_tracker_data()
    
    fixed_count = 0
    removed_count = 0
    
    # Process each patch
    for patch in build_data.keys():
        if patch.startswith('_'):
            continue
        
        print(f"\nProcessing patch {patch}...")
        
        # Process each champion
        for champ_name in build_data[patch].keys():
            champ_data = build_data[patch][champ_name]
            item_sets = champ_data.get('item_sets', {})
            
            fixed_item_sets = {}
            
            for item_set_str, games_count in item_sets.items():
                # Parse item set
                items = json.loads(item_set_str)
                
                # Map items to current IDs
                fixed_items = []
                valid_build = True
                
                for item_id in items:
                    mapped_id = map_item_id(item_id, valid_ids)
                    if mapped_id is None:
                        valid_build = False
                        break
                    fixed_items.append(mapped_id)
                
                # Only keep builds with all valid items and no duplicate boots
                if valid_build and len(fixed_items) == 6:
                    # Check for duplicate boots (items with "Boots" in name)
                    boot_count = sum(1 for item_id in fixed_items 
                                    if str(item_id) in items_data 
                                    and 'Boots' in items_data[str(item_id)]['name'])
                    
                    if boot_count <= 1:  # Max 1 pair of boots
                        fixed_set_str = json.dumps(fixed_items)
                        fixed_item_sets[fixed_set_str] = games_count
                        fixed_count += 1
                    else:
                        removed_count += 1
                else:
                    removed_count += 1
            
            # Update champion data
            build_data[patch][champ_name]['item_sets'] = fixed_item_sets
    
    # Save fixed data
    print(f"\n\nSaving fixed builds...")
    print(f"Fixed {fixed_count} builds")
    print(f"Removed {removed_count} invalid builds")
    
    with open('data/build_tracker_data_fixed.json', 'w') as f:
        json.dump(build_data, f, indent=2)
    
    print("\nFixed data saved to: data/build_tracker_data_fixed.json")
    print("To use this, rename it to build_tracker_data.json")

if __name__ == '__main__':
    fix_builds()

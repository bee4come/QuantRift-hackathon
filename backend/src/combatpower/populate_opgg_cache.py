#!/usr/bin/env python3
"""
Utility script to populate OP.GG build cache
Run this periodically (e.g., weekly) to update lane-specific builds
"""
from .services.data_dragon import data_dragon
from .services.opgg_builds import opgg_builds
import time


def main():
    print("=" * 60)
    print("OP.GG Build Cache Population Script")
    print("=" * 60)
    print("\nThis will fetch lane-specific builds from OP.GG for all champions.")
    print("This may take several minutes to complete.\n")
    
    # Get all champions
    champions = data_dragon.get_champions()
    print(f"Found {len(champions)} champions\n")
    
    # Refresh cache
    opgg_builds.refresh_all_cache(champions)
    
    print("\n" + "=" * 60)
    print("Cache population complete!")
    print("=" * 60)
    
    # Show cache stats
    cache = opgg_builds.cache
    total_entries = len([k for k in cache.keys() if not k.startswith('_')])
    print(f"\nTotal champion-lane combinations cached: {total_entries}")
    
    # Show breakdown by lane
    lanes = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT']
    for lane in lanes:
        count = len([k for k in cache.keys() if k.endswith(f'_{lane}')])
        print(f"  {lane}: {count} champions")


if __name__ == '__main__':
    main()


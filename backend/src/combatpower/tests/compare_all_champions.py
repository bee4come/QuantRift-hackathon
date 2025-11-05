"""
Compare all champion combat power across patches
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .services.patch_manager import patch_manager
from .services.data_provider import data_provider
from .services.combat_power import combat_power_calculator


def compare_champions_across_patches():
    """Compare total combat power for all champions across patches"""
    
    print("="*80)
    print("ALL CHAMPIONS COMBAT POWER COMPARISON ACROSS PATCHES")
    print("="*80)
    
    # Get all patches
    all_patches = patch_manager.get_all_patches()
    
    # Select a subset of patches to test (every 3rd patch for readability)
    test_patches = all_patches[::3][:8]  # Take every 3rd patch, max 8 patches
    
    print(f"\nTesting patches: {', '.join(test_patches)}")
    print(f"\nCalculating combat power (Level 18, with meta builds)...")
    print("-"*80)
    
    # Store results: {champion_name: {patch: power}}
    champion_powers = {}
    
    # Calculate for each patch
    for patch in test_patches:
        print(f"\nProcessing {patch}...", end=" ", flush=True)
        try:
            powers = combat_power_calculator.calculate_all_champions_base_power(
                include_builds=True,
                patch=patch
            )
            
            for champion, power in powers.items():
                if champion not in champion_powers:
                    champion_powers[champion] = {}
                champion_powers[champion][patch] = power
            
            print(f"✓ {len(powers)} champions")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    # Create header
    header = f"{'Champion':<20}"
    for patch in test_patches:
        header += f"{patch:>12}"
    header += f"{'Avg':>12}{'Change':>10}"
    print(header)
    print("-"*80)
    
    # Sort champions by average power
    champion_stats = []
    for champion, powers in champion_powers.items():
        if len(powers) >= 2:  # Only include if we have multiple patches
            # Only calculate if we have both first and last patch
            if test_patches[0] in powers and test_patches[-1] in powers:
                avg_power = sum(powers.values()) / len(powers)
                first_power = powers[test_patches[0]]
                last_power = powers[test_patches[-1]]
                change = ((last_power - first_power) / first_power * 100) if first_power > 0 else 0
                champion_stats.append((champion, powers, avg_power, change))
    
    # Sort by average power (descending)
    champion_stats.sort(key=lambda x: x[2], reverse=True)
    
    # Print top 20 champions
    print("\nTOP 20 STRONGEST CHAMPIONS (by average power):")
    print("-"*80)
    for champion, powers, avg_power, change in champion_stats[:20]:
        row = f"{champion:<20}"
        for patch in test_patches:
            power = powers.get(patch, 0)
            row += f"{power:>12.0f}"
        row += f"{avg_power:>12.0f}"
        change_str = f"{change:+.1f}%"
        row += f"{change_str:>10}"
        print(row)
    
    # Print bottom 10 champions
    print("\n" + "-"*80)
    print("BOTTOM 10 WEAKEST CHAMPIONS (by average power):")
    print("-"*80)
    for champion, powers, avg_power, change in champion_stats[-10:]:
        row = f"{champion:<20}"
        for patch in test_patches:
            power = powers.get(patch, 0)
            row += f"{power:>12.0f}"
        row += f"{avg_power:>12.0f}"
        change_str = f"{change:+.1f}%"
        row += f"{change_str:>10}"
        print(row)
    
    # Find champions with biggest changes
    print("\n" + "="*80)
    print("BIGGEST POWER CHANGES")
    print("="*80)
    
    # Sort by absolute change
    champion_stats.sort(key=lambda x: abs(x[3]), reverse=True)
    
    print("\nBIGGEST BUFFS (increased most):")
    print("-"*80)
    buffed = [x for x in champion_stats if x[3] > 0][:10]
    for champion, powers, avg_power, change in buffed:
        first = powers[test_patches[0]]
        last = powers[test_patches[-1]] if test_patches[-1] in powers else first
        print(f"{champion:<20} {first:>10.0f} → {last:>10.0f}  ({change:+.1f}%)")
    
    print("\nBIGGEST NERFS (decreased most):")
    print("-"*80)
    nerfed = [x for x in champion_stats if x[3] < 0][:10]
    for champion, powers, avg_power, change in nerfed:
        first = powers[test_patches[0]]
        last = powers[test_patches[-1]] if test_patches[-1] in powers else first
        print(f"{champion:<20} {first:>10.0f} → {last:>10.0f}  ({change:+.1f}%)")
    
    print("\n" + "="*80)
    print(f"Total champions analyzed: {len(champion_powers)}")
    print(f"Patches compared: {len(test_patches)}")
    print("="*80)


if __name__ == "__main__":
    compare_champions_across_patches()


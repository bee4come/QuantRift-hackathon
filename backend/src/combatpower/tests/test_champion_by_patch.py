"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

Test champion combat power across different patches
"""
from .services.patch_manager import patch_manager
from .services.multi_patch_data import multi_patch_data
from .services.combat_power import combat_power_calculator


def get_champion_power_by_patch(champion_name: str, patch: str):
    """Get champion combat power for a specific patch"""
    try:
        # Get champion data for this patch
        champions = multi_patch_data.get_champions_for_patch(patch)
        
        if champion_name not in champions:
            print(f"Champion {champion_name} not found in patch {patch}")
            return None
        
        champion_detail = multi_patch_data.get_champion_detail_for_patch(patch, champion_name)
        champion_stats = champions[champion_name]['stats']
        
        # Calculate combat power components
        base_power = combat_power_calculator.calculate_base_stats_power(champion_stats, 18)
        skill_power = combat_power_calculator.calculate_skill_power(champion_detail)
        total_power = base_power + skill_power
        
        return {
            'champion': champion_name,
            'patch': patch,
            'base_power': round(base_power, 2),
            'skill_power': round(skill_power, 2),
            'total_power': round(total_power, 2),
            'base_ad': champion_stats.get('attackdamage'),
            'base_hp': champion_stats.get('hp'),
            'armor': champion_stats.get('armor'),
            'mr': champion_stats.get('spellblock')
        }
    except Exception as e:
        print(f"Error: {e}")
        return None


def compare_champion_across_patches(champion_name: str, patches: list):
    """Compare a champion's power across multiple patches"""
    print("="*70)
    print(f"Champion: {champion_name} - Combat Power Across Patches")
    print("="*70)
    
    results = []
    
    for patch in patches:
        result = get_champion_power_by_patch(champion_name, patch)
        if result:
            results.append(result)
    
    if not results:
        print("No data found")
        return
    
    # Display results
    print(f"\n{'Patch':<12} {'Total Power':<15} {'Base':<12} {'Skills':<12} {'AD':<8} {'HP':<8}")
    print("-"*70)
    
    for r in results:
        print(f"{r['patch']:<12} {r['total_power']:<15} {r['base_power']:<12} "
              f"{r['skill_power']:<12} {r['base_ad']:<8} {r['base_hp']:<8}")
    
    # Show changes
    if len(results) > 1:
        print("\n" + "="*70)
        print("Power Changes:")
        print("="*70)
        for i in range(1, len(results)):
            prev = results[i-1]
            curr = results[i]
            diff = curr['total_power'] - prev['total_power']
            percent = (diff / prev['total_power'] * 100) if prev['total_power'] > 0 else 0
            
            status = "BUFF" if diff > 0 else "NERF" if diff < 0 else "UNCHANGED"
            print(f"{prev['patch']} -> {curr['patch']}: {diff:+.2f} ({percent:+.2f}%) - {status}")


if __name__ == '__main__':
    # Test different champions across patches
    
    print("\n" + "="*70)
    print("DRAVEN - Combat Power History")
    print("="*70)
    compare_champion_across_patches("Draven", ["14.19", "14.20", "14.21", "14.22", "14.23"])
    
    print("\n\n" + "="*70)
    print("KSANTE - Combat Power History")
    print("="*70)
    compare_champion_across_patches("KSante", ["14.19", "14.20", "14.21", "14.22"])
    
    print("\n\n" + "="*70)
    print("AHRI - Combat Power History")
    print("="*70)
    compare_champion_across_patches("Ahri", ["14.19", "14.22", "15.5"])
    
    print("\n\n" + "="*70)
    print("All Available Patches")
    print("="*70)
    all_patches = patch_manager.get_all_patches()
    print(f"Total: {len(all_patches)} patches")
    print(f"Patches: {', '.join(all_patches[:10])}...")


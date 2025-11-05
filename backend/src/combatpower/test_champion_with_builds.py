"""
Test champion combat power WITH meta builds across patches
"""
from .services.patch_manager import patch_manager
from .services.multi_patch_data import multi_patch_data
from .services.combat_power import combat_power_calculator
from .services.meta_builds import meta_builds_db


def get_champion_power_with_build(champion_name: str, patch: str):
    """Get champion combat power WITH meta items and runes"""
    try:
        # Get meta build
        meta_build = meta_builds_db.get_meta_build(champion_name, patch)
        
        # Calculate total power with build
        total_power = combat_power_calculator.calculate_total_combat_power(
            champion_name=champion_name,
            level=18,
            item_ids=meta_build['items'],
            rune_ids=meta_build['runes'],
            primary_style=meta_build['primary_style'],
            sub_style=meta_build['sub_style'],
            patch=patch
        )
        
        # Get component breakdown
        champions = multi_patch_data.get_champions_for_patch(patch)
        champion_detail = multi_patch_data.get_champion_detail_for_patch(patch, champion_name)
        champion_stats = champions[champion_name]['stats']
        
        base_power = combat_power_calculator.calculate_base_stats_power(champion_stats, 18)
        skill_power = combat_power_calculator.calculate_skill_power(champion_detail)
        item_power = combat_power_calculator.calculate_item_power(meta_build['items'])
        rune_power = combat_power_calculator.calculate_rune_power(
            meta_build['runes'],
            meta_build['primary_style'],
            meta_build['sub_style']
        )
        
        return {
            'champion': champion_name,
            'patch': patch,
            'total_power': round(total_power, 2),
            'base_power': round(base_power, 2),
            'skill_power': round(skill_power, 2),
            'item_power': round(item_power, 2),
            'rune_power': round(rune_power, 2),
            'role': meta_build['role'],
            'items': meta_build['items']
        }
    except Exception as e:
        print(f"Error: {e}")
        return None


def compare_with_and_without_builds(champion_name: str, patches: list):
    """Compare champion power with and without builds"""
    print("="*90)
    print(f"{champion_name} - Combat Power Comparison")
    print("="*90)
    
    print(f"\n{'Patch':<12} {'Without Build':<18} {'With Build':<18} {'Difference':<15} {'% Increase':<12}")
    print("-"*90)
    
    for patch in patches:
        # Without build
        champions = multi_patch_data.get_champions_for_patch(patch)
        champion_detail = multi_patch_data.get_champion_detail_for_patch(patch, champion_name)
        champion_stats = champions[champion_name]['stats']
        
        base_power = combat_power_calculator.calculate_base_stats_power(champion_stats, 18)
        skill_power = combat_power_calculator.calculate_skill_power(champion_detail)
        power_without = base_power + skill_power
        
        # With build
        result = get_champion_power_with_build(champion_name, patch)
        power_with = result['total_power']
        
        diff = power_with - power_without
        percent = (diff / power_without * 100) if power_without > 0 else 0
        
        print(f"{patch:<12} {power_without:<18.2f} {power_with:<18.2f} {diff:<15.2f} {percent:<12.1f}%")


def show_champion_build_details(champion_name: str, patch: str):
    """Show detailed breakdown for a champion"""
    print("\n" + "="*90)
    print(f"{champion_name} - Detailed Power Breakdown (Patch {patch})")
    print("="*90)
    
    result = get_champion_power_with_build(champion_name, patch)
    
    if not result:
        print("Error getting champion data")
        return
    
    print(f"\nRole: {result['role']}")
    print(f"\nCombat Power Components:")
    print(f"  Base Stats:  {result['base_power']:>10.2f}")
    print(f"  Skills:      {result['skill_power']:>10.2f}")
    print(f"  Items:       {result['item_power']:>10.2f}")
    print(f"  Runes:       {result['rune_power']:>10.2f}")
    print(f"  " + "-"*20)
    print(f"  TOTAL:       {result['total_power']:>10.2f}")
    
    print(f"\nMeta Build:")
    meta_build = meta_builds_db.get_meta_build(champion_name, patch)
    print(f"  Items: {meta_build['items']}")
    print(f"  Runes: Primary={meta_build['primary_style']}, Sub={meta_build['sub_style']}")
    print(f"  Notes: {meta_build['notes']}")


if __name__ == '__main__':
    print("\n" + "="*90)
    print("TESTING: Champion Combat Power WITH Meta Builds")
    print("="*90)
    
    # Test Draven with builds
    print("\n1. DRAVEN (ADC) - With vs Without Builds")
    compare_with_and_without_builds('Draven', ['14.19', '14.20', '14.21', '14.22', '14.23'])
    show_champion_build_details('Draven', '14.19')
    
    # Test K'Sante with builds
    print("\n\n2. KSANTE (Tank) - With vs Without Builds")
    compare_with_and_without_builds('KSante', ['14.19', '14.20', '14.21', '14.22'])
    show_champion_build_details('KSante', '14.20')
    
    # Test Ahri with builds
    print("\n\n3. AHRI (Mage) - With vs Without Builds")
    compare_with_and_without_builds('Ahri', ['14.19', '14.22', '25.05'])
    show_champion_build_details('Ahri', '14.22')
    
    print("\n" + "="*90)
    print("Summary:")
    print("="*90)
    print("Items and Runes add significant combat power!")
    print("Now when items/runes get buffed/nerfed, champion power will change even if")
    print("the champion itself wasn't touched.")


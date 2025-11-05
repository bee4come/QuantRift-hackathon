"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

Debug script to show how ability power is calculated
"""
from .services.data_dragon import data_dragon

def debug_draven_abilities():
    print("="*60)
    print("Draven Ability Breakdown")
    print("="*60)
    
    draven = data_dragon.get_champion_detail('Draven')
    
    # Show passive
    print("\nPASSIVE:")
    passive = draven.get('passive', {})
    print(f"  Name: {passive.get('name')}")
    print(f"  Description: {passive.get('description', '')[:100]}...")
    print(f"  Combat Power Contribution: +100 (flat bonus)")
    
    # Show each ability
    print("\nABILITIES:")
    spells = draven.get('spells', [])
    
    total_spell_power = 0.0
    
    for i, spell in enumerate(spells, 1):
        print(f"\n{['Q', 'W', 'E', 'R'][i-1]} - {spell.get('name')}:")
        print(f"  Description: {spell.get('description', '')[:80]}...")
        
        # Cooldown
        cooldown = spell.get('cooldownBurn', '0')
        print(f"  Cooldown: {cooldown}")
        
        # Damage
        damage = spell.get('effectBurn', [])
        print(f"  Effect Values: {damage[:3] if len(damage) >= 3 else damage}")
        
        # Calculate power contribution
        try:
            cd_values = [float(x) for x in cooldown.split('/')]
            cd = cd_values[-1] if cd_values else 8.0
            
            if damage and len(damage) > 0:
                dmg_str = damage[0] if isinstance(damage[0], str) else '0'
                dmg_value = float(dmg_str.replace('%', ''))
                dpm = (dmg_value / max(cd, 1)) * 60
                power = dpm * 0.1
                total_spell_power += power
                print(f"  Combat Power: {power:.2f} (from {dmg_value} dmg / {cd}s CD * 60 * 0.1)")
            else:
                print(f"  Combat Power: 0.00 (no damage data)")
        except Exception as e:
            print(f"  Combat Power: 0.00 (calculation error: {e})")
    
    print("\n" + "="*60)
    print("TOTAL ABILITY COMBAT POWER:")
    print(f"  From Spells (Q+W+E+R): {total_spell_power:.2f}")
    print(f"  From Passive: 100.00")
    print(f"  TOTAL: {total_spell_power + 100:.2f}")
    print("="*60)
    
    print("\nNOTE: This is a simplified calculation!")
    print("It doesn't account for:")
    print("  - AD/AP ratios")
    print("  - Scaling with items")
    print("  - Complex mechanics (Draven's Q axe catching)")
    print("  - Utility effects (slows, CC, etc.)")

if __name__ == '__main__':
    debug_draven_abilities()


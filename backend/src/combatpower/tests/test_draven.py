"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

Test combat power calculation for level 15 Draven with Bloodthirster
"""
from .services.data_dragon import data_dragon
from .services.combat_power import combat_power_calculator

def test_draven():
    print("="*60)
    print("Testing: Level 15 Draven with Bloodthirster")
    print("="*60)
    
    # Get champion data
    print("\n1. Fetching Draven data...")
    champions = data_dragon.get_champions()
    draven_detail = data_dragon.get_champion_detail('Draven')
    draven_stats = champions['Draven']['stats']
    
    print(f"   Champion: {draven_detail['name']} - {draven_detail['title']}")
    
    # Calculate base power at level 15 (no items)
    print("\n2. Calculating base combat power at level 15...")
    base_power = combat_power_calculator.calculate_base_stats_power(draven_stats, level=15)
    skill_power = combat_power_calculator.calculate_skill_power(draven_detail)
    
    print(f"   Base Stats Power: {base_power:.2f}")
    print(f"   Skill Power: {skill_power:.2f}")
    print(f"   Total (no items): {base_power + skill_power:.2f}")
    
    # Show level 15 stats breakdown
    print("\n3. Level 15 Stats Breakdown:")
    base_hp = float(draven_stats.get('hp', 0))
    hp_per_level = float(draven_stats.get('hpperlevel', 0))
    base_ad = float(draven_stats.get('attackdamage', 0))
    ad_per_level = float(draven_stats.get('attackdamageperlevel', 0))
    base_armor = float(draven_stats.get('armor', 0))
    armor_per_level = float(draven_stats.get('armorperlevel', 0))
    base_mr = float(draven_stats.get('spellblock', 0))
    mr_per_level = float(draven_stats.get('spellblockperlevel', 0))
    base_as = float(draven_stats.get('attackspeed', 0.625))
    as_per_level = float(draven_stats.get('attackspeedperlevel', 0))
    
    level = 15
    hp = base_hp + (hp_per_level * (level - 1))
    ad = base_ad + (ad_per_level * (level - 1))
    armor = base_armor + (armor_per_level * (level - 1))
    mr = base_mr + (mr_per_level * (level - 1))
    attack_speed = base_as * (1 + (as_per_level / 100) * (level - 1))
    
    print(f"   Health: {hp:.0f} HP")
    print(f"   Attack Damage: {ad:.1f} AD")
    print(f"   Armor: {armor:.1f}")
    print(f"   Magic Resist: {mr:.1f}")
    print(f"   Attack Speed: {attack_speed:.3f}")
    
    # Get Bloodthirster item
    print("\n4. Fetching Bloodthirster data...")
    items = data_dragon.get_items()
    
    # Find Bloodthirster (item ID 3072)
    bloodthirster_id = '3072'
    if bloodthirster_id in items:
        bt = items[bloodthirster_id]
        print(f"   Item: {bt['name']}")
        print(f"   Description: {bt.get('plaintext', 'N/A')}")
        print(f"   Stats: {bt.get('stats', {})}")
    else:
        print("   Bloodthirster not found, using ID 3072")
    
    # Calculate power with Bloodthirster
    print("\n5. Calculating combat power WITH Bloodthirster...")
    total_power_with_item = combat_power_calculator.calculate_total_combat_power(
        champion_name='Draven',
        level=15,
        item_ids=[3072]  # Bloodthirster
    )
    
    item_power = combat_power_calculator.calculate_item_power([3072])
    
    print(f"   Base + Skills: {base_power + skill_power:.2f}")
    print(f"   Item Power (Bloodthirster): {item_power:.2f}")
    print(f"   TOTAL Combat Power: {total_power_with_item:.2f}")
    
    # Show the difference
    print("\n6. Impact Analysis:")
    power_without_items = base_power + skill_power
    power_increase = total_power_with_item - power_without_items
    percent_increase = (power_increase / power_without_items * 100) if power_without_items > 0 else 0
    
    print(f"   Power without items: {power_without_items:.2f}")
    print(f"   Power with Bloodthirster: {total_power_with_item:.2f}")
    print(f"   Increase: +{power_increase:.2f} ({percent_increase:.1f}%)")
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60)
    
    return {
        'champion': 'Draven',
        'level': 15,
        'base_power': base_power,
        'skill_power': skill_power,
        'item_power': item_power,
        'total_power': total_power_with_item,
        'stats': {
            'hp': hp,
            'ad': ad,
            'armor': armor,
            'mr': mr,
            'attack_speed': attack_speed
        }
    }


if __name__ == '__main__':
    result = test_draven()
    
    print("\n" + "="*60)
    print("Summary:")
    print("="*60)
    print(f"Champion: {result['champion']}")
    print(f"Level: {result['level']}")
    print(f"Combat Power: {result['total_power']:.2f}")
    print(f"  - Base Stats: {result['base_power']:.2f}")
    print(f"  - Skills (Q/W/E/R/Passive): {result['skill_power']:.2f}")
    print(f"  - Items: {result['item_power']:.2f}")


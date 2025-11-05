"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

Show where all data comes from
"""

# Official Riot Data Dragon CDN
BASE_URL = "https://ddragon.leagueoflegends.com"

print("="*70)
print("DATA SOURCES - All from Riot's Official Data Dragon CDN")
print("="*70)

print("\n1. AVAILABLE VERSIONS (All patches):")
print(f"   {BASE_URL}/api/versions.json")
print("   → Returns: ['15.20.1', '15.19.1', '14.19.1', ...]")

print("\n2. CHAMPIONS DATA (Per patch):")
patch = "14.19.1"
print(f"   {BASE_URL}/cdn/{patch}/data/en_US/champion.json")
print("   → Returns: All champions with base stats (HP, AD, Armor, etc.)")

print("\n3. CHAMPION DETAILS (Abilities):")
print(f"   {BASE_URL}/cdn/{patch}/data/en_US/champion/Draven.json")
print("   → Returns: Draven's Q/W/E/R abilities, passive, scaling")

print("\n4. ITEMS DATA:")
print(f"   {BASE_URL}/cdn/{patch}/data/en_US/item.json")
print("   → Returns: All items with stats (IE, BT, etc.)")

print("\n5. RUNES DATA:")
print(f"   {BASE_URL}/cdn/{patch}/data/en_US/runesReforged.json")
print("   → Returns: All rune trees (Precision, Domination, etc.)")

print("\n" + "="*70)
print("Let's test these URLs...")
print("="*70)

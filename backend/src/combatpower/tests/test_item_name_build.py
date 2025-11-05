"""
Test custom build with item NAMES instead of IDs
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .services.custom_build_analyzer import custom_build_analyzer
from .services.item_search import item_search


def test_build_with_names():
    """Test using item names instead of IDs"""
    print("\n" + "="*80)
    print("CUSTOM BUILD WITH ITEM NAMES")
    print("="*80)
    
    champion = "Draven"
    
    # User enters item names
    item_names = ["IE", "Bloodthirster", "phantom dancer"]
    
    print(f"\nChampion: {champion}")
    print(f"Items (user input): {item_names}")
    
    # Convert names to IDs
    print("\nConverting names to IDs...")
    item_ids, failed = item_search.convert_names_to_ids(item_names)
    
    if failed:
        print(f"Failed to find: {failed}")
        return
    
    print(f"Item IDs: {item_ids}")
    
    # Show what items we found
    print("\nMatched items:")
    for item_id in item_ids:
        results = item_search.search_item(str(item_id), max_results=1)
        if results:
            print(f"  - {results[0]['name']} ({item_id})")
    
    # Analyze build
    print(f"\nAnalyzing build across all patches...")
    results = custom_build_analyzer.analyze_custom_build(
        champion_name=champion,
        item_ids=item_ids,
        level=18
    )
    
    # Display results
    print("\n" + custom_build_analyzer.format_results_table(results))


def test_with_typos():
    """Test with common typos"""
    print("\n" + "="*80)
    print("TEST WITH TYPOS")
    print("="*80)
    
    champion = "Jinx"
    
    # User enters with typos
    item_names = ["infinty edge", "rapidfire", "collector"]
    
    print(f"\nChampion: {champion}")
    print(f"Items (with typos): {item_names}")
    
    # Convert names to IDs
    item_ids, failed = item_search.convert_names_to_ids(item_names)
    
    print(f"\nConverted to IDs: {item_ids}")
    print(f"Failed: {failed if failed else 'None!'}")
    
    # Show matches
    print("\nMatched items:")
    for name, item_id in zip(item_names, item_ids):
        results = item_search.search_item(str(item_id), max_results=1)
        if results:
            print(f"  '{name}' → {results[0]['name']}")


def test_abbreviations():
    """Test with common abbreviations"""
    print("\n" + "="*80)
    print("TEST WITH ABBREVIATIONS")
    print("="*80)
    
    test_cases = [
        ("Draven", ["IE", "BT", "PD"]),
        ("Ahri", ["liandry", "dcap", "void"]),
        ("Ornn", ["sunfire", "thornmail", "visage"]),
    ]
    
    for champion, item_names in test_cases:
        print(f"\n{champion} with {item_names}:")
        
        item_ids, failed = item_search.convert_names_to_ids(item_names)
        
        for name, item_id in zip(item_names, item_ids):
            results = item_search.search_item(str(item_id), max_results=1)
            if results:
                print(f"  {name.upper():10} → {results[0]['name']}")


def interactive_item_picker():
    """Interactive item picker with name search"""
    print("\n" + "="*80)
    print("INTERACTIVE ITEM PICKER")
    print("="*80)
    
    print("\nPick 3 items by typing names, abbreviations, or partial names!")
    print("Examples: IE, blood, phantom, infinty edge, etc.\n")
    
    items = []
    for i in range(3):
        while True:
            query = input(f"Item {i+1}: ").strip()
            
            if not query:
                continue
            
            # Search
            results = item_search.search_item(query, max_results=3)
            
            if results:
                top_match = results[0]
                
                if len(results) == 1 or top_match['score'] > 0.9:
                    # Clear match
                    print(f"  ✓ {top_match['name']}")
                    items.append(top_match['id'])
                    break
                else:
                    # Multiple matches - ask user to choose
                    print(f"\n  Multiple matches found:")
                    for j, item in enumerate(results, 1):
                        print(f"    {j}. {item['name']} (Score: {item['score']:.2f})")
                    
                    choice = input(f"  Choose 1-{len(results)} (or retry): ").strip()
                    if choice.isdigit():
                        idx = int(choice) - 1
                        if 0 <= idx < len(results):
                            selected = results[idx]
                            print(f"  ✓ {selected['name']}")
                            items.append(selected['id'])
                            break
            else:
                print(f"  ✗ No matches for '{query}'. Try again!")
    
    print(f"\n✓ Selected items: {items}")
    
    # Now pick champion and analyze
    champion = input("\nEnter champion name: ").strip()
    
    print(f"\nAnalyzing {champion} with items {items}...")
    
    results = custom_build_analyzer.analyze_custom_build(
        champion_name=champion,
        item_ids=items,
        level=18
    )
    
    # Get item names
    item_names = []
    for item_id in items:
        search_results = item_search.search_item(str(item_id), max_results=1)
        if search_results:
            item_names.append(search_results[0]['name'])
    
    print(f"\n{champion} with {', '.join(item_names)}:")
    if 'statistics' in results:
        stats = results['statistics']
        print(f"  Average Power: {stats['avg_power']:.2f}")
        print(f"  Strongest Patch: {stats['strongest_patch']}")
        print(f"  Power Range: {stats['min_power']:.2f} - {stats['max_power']:.2f}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        interactive_item_picker()
    else:
        test_build_with_names()
        test_with_typos()
        test_abbreviations()
        
        print("\n" + "="*80)
        print("✓ All tests passed!")
        print("\nTo run interactive mode:")
        print("  python tests/test_item_name_build.py interactive")
        print("="*80)


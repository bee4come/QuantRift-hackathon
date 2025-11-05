"""
Test custom build analyzer
User picks champion and items, sees combat power across patches
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .services.custom_build_analyzer import custom_build_analyzer


def test_three_item_build():
    """Test with user picking 3 items"""
    print("\n" + "="*80)
    print("CUSTOM BUILD TEST: User Picks 3 Items")
    print("="*80)
    
    # User picks Draven
    champion = "Draven"
    
    # User picks 3 items one by one
    print(f"\nChampion selected: {champion}")
    print("User picks items:")
    
    # Item 1: Infinity Edge (3031)
    print("  1. Infinity Edge (3031)")
    
    # Item 2: Bloodthirster (3072)
    print("  2. Bloodthirster (3072)")
    
    # Item 3: Phantom Dancer (3046)
    print("  3. Phantom Dancer (3046)")
    
    items = [3031, 3072, 3046]
    
    # Analyze across all patches
    print("\nCalculating combat power across all patches...")
    results = custom_build_analyzer.analyze_custom_build(
        champion_name=champion,
        item_ids=items,
        level=18
    )
    
    # Display results
    print("\n" + custom_build_analyzer.format_results_table(results))


def test_custom_builds_comparison():
    """Test comparing different builds"""
    print("\n" + "="*80)
    print("BUILD COMPARISON TEST")
    print("="*80)
    
    champion = "Draven"
    
    # Build 1: Crit build (3 items)
    build1 = {
        'name': 'Crit Build',
        'items': [3031, 3072, 3046]  # IE, BT, PD
    }
    
    # Build 2: Lethality build (3 items)
    build2 = {
        'name': 'Lethality Build',
        'items': [3142, 6676, 3814]  # Youmuu's, Collector, Edge of Night
    }
    
    # Build 3: On-hit build (3 items)
    build3 = {
        'name': 'On-Hit Build',
        'items': [3153, 3124, 3085]  # BORK, Rageblade, Runaan's
    }
    
    print(f"\nComparing 3 builds for {champion}:")
    print(f"  1. {build1['name']}: {build1['items']}")
    print(f"  2. {build2['name']}: {build2['items']}")
    print(f"  3. {build3['name']}: {build3['items']}")
    
    comparison = custom_build_analyzer.compare_builds(
        champion_name=champion,
        build_options=[build1, build2, build3],
        level=18
    )
    
    # Display comparison
    print("\n" + "="*80)
    print("COMPARISON RESULTS")
    print("="*80)
    
    for build_name, results in comparison['builds'].items():
        if 'statistics' in results:
            stats = results['statistics']
            print(f"\n{build_name}:")
            print(f"  Average Power: {stats['avg_power']:.2f}")
            print(f"  Power Range: {stats['min_power']:.2f} - {stats['max_power']:.2f}")
            print(f"  Best Patch: {stats['strongest_patch']} ({stats['max_power']:.2f})")


def interactive_mode():
    """Interactive mode for users to pick champion and items"""
    print("\n" + "="*80)
    print("INTERACTIVE CUSTOM BUILD ANALYZER")
    print("="*80)
    
    # Pick champion
    champion = input("\nEnter champion name (e.g., Draven): ").strip()
    
    # Pick items by NAME
    print("\nEnter item names or abbreviations (one at a time):")
    print("Examples:")
    print("  - Full names: 'Infinity Edge', 'Bloodthirster'")
    print("  - Abbreviations: 'IE', 'BT', 'PD', 'RFC'")
    print("  - Partial: 'blood', 'phantom'")
    print("  - With typos: 'infinty edge' works too!")
    
    from services.item_search import item_search
    
    items = []
    for i in range(3):
        while True:
            item_input = input(f"\nItem {i+1} name/abbr: ").strip()
            
            # Search for item
            item_id = item_search.get_best_match(item_input)
            
            if item_id:
                # Get item info to show user
                results = item_search.search_item(item_input, max_results=1)
                if results:
                    item_name = results[0]['name']
                    print(f"  ✓ Found: {item_name} (ID: {item_id})")
                    items.append(item_id)
                    break
            else:
                print(f"  ✗ '{item_input}' not found. Try again or use abbreviations (IE, BT, PD)")
                suggestions = item_search.suggest_items(item_input, count=3)
                if suggestions:
                    print("  Did you mean:")
                    for s in suggestions:
                        print(f"    - {s['name']}")

    
    # Level
    level = input("\nChampion level (default 18): ").strip()
    level = int(level) if level else 18
    
    print(f"\nAnalyzing {champion} with items {items} at level {level}...")
    
    results = custom_build_analyzer.analyze_custom_build(
        champion_name=champion,
        item_ids=items,
        level=level
    )
    
    print("\n" + custom_build_analyzer.format_results_table(results))
    
    # Ask if user wants to export
    export = input("\nExport results to file? (y/n): ").strip().lower()
    if export == 'y':
        filename = f"custom_build_{champion}_{'-'.join(map(str, items))}.txt"
        with open(filename, 'w') as f:
            f.write(custom_build_analyzer.format_results_table(results))
        print(f"✅ Results exported to {filename}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        interactive_mode()
    else:
        # Run tests
        test_three_item_build()
        test_custom_builds_comparison()
        
        print("\n" + "="*80)
        print("To run interactive mode:")
        print("  python tests/test_custom_build.py interactive")
        print("="*80)


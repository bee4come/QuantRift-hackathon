"""
Test item search functionality
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .services.item_search import item_search


def test_abbreviations():
    """Test common abbreviations"""
    print("\n" + "="*80)
    print("TEST: Item Abbreviations")
    print("="*80)
    
    test_queries = [
        'IE',  # Infinity Edge
        'bt',  # Bloodthirster
        'PD',  # Phantom Dancer
        'bork',  # Blade of the Ruined King
        'rfc',  # Rapid Firecannon
    ]
    
    for query in test_queries:
        results = item_search.search_item(query)
        if results:
            item = results[0]
            print(f"\n'{query}' → {item['name']} (ID: {item['id']})")
            print(f"  Match type: {item['match_type']}")
            print(f"  Score: {item['score']:.2f}")
        else:
            print(f"\n'{query}' → No match found")


def test_partial_names():
    """Test partial name matching"""
    print("\n" + "="*80)
    print("TEST: Partial Name Matching")
    print("="*80)
    
    test_queries = [
        'blood',  # Should find Bloodthirster
        'phantom',  # Should find Phantom Dancer
        'infinity',  # Should find Infinity Edge
        'rapid',  # Should find Rapid Firecannon
    ]
    
    for query in test_queries:
        results = item_search.search_item(query, max_results=3)
        print(f"\n'{query}':")
        for item in results:
            print(f"  - {item['name']} (Score: {item['score']:.2f})")


def test_typos():
    """Test typo handling"""
    print("\n" + "="*80)
    print("TEST: Typo Handling")
    print("="*80)
    
    test_queries = [
        'infinty edge',  # Typo
        'bloodthirster',  # Common misspelling
        'rabadons',  # Missing apostrophe
        'zhonyas',  # Common variant
    ]
    
    for query in test_queries:
        results = item_search.search_item(query, max_results=1)
        if results:
            item = results[0]
            print(f"\n'{query}' → {item['name']}")
            print(f"  Score: {item['score']:.2f}")


def test_name_to_id_conversion():
    """Test converting names to IDs"""
    print("\n" + "="*80)
    print("TEST: Name to ID Conversion")
    print("="*80)
    
    item_names = [
        'IE',
        'Bloodthirster',
        'phantom dancer',
        'RFC',
        'invalid item name'  # Should fail
    ]
    
    item_ids, failed = item_search.convert_names_to_ids(item_names)
    
    print(f"\nInput: {item_names}")
    print(f"Item IDs: {item_ids}")
    print(f"Failed matches: {failed}")
    print(f"Success rate: {len(item_ids)}/{len(item_names)}")


def test_suggestions():
    """Test autocomplete suggestions"""
    print("\n" + "="*80)
    print("TEST: Autocomplete Suggestions")
    print("="*80)
    
    partial_queries = ['blo', 'inf', 'ra']
    
    for query in partial_queries:
        suggestions = item_search.suggest_items(query, count=5)
        print(f"\n'{query}' suggestions:")
        for item in suggestions:
            print(f"  - {item['name']} (Score: {item['score']:.2f})")


def test_common_abbreviations():
    """Test listing all abbreviations"""
    print("\n" + "="*80)
    print("TEST: Common Abbreviations List")
    print("="*80)
    
    abbreviations = item_search.list_common_abbreviations()
    
    print(f"\nTotal abbreviations: {len(abbreviations)}")
    print("\nSample abbreviations:")
    for abbr, name in list(abbreviations.items())[:20]:
        print(f"  {abbr:<10} → {name}")


def interactive_search():
    """Interactive search mode"""
    print("\n" + "="*80)
    print("INTERACTIVE ITEM SEARCH")
    print("="*80)
    print("\nEnter item names to search (or 'quit' to exit)")
    print("Examples: IE, blood, phantom dancer, infinty edge\n")
    
    while True:
        query = input("Search: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not query:
            continue
        
        results = item_search.search_item(query, max_results=5)
        
        if results:
            print(f"\nFound {len(results)} matches:")
            for i, item in enumerate(results, 1):
                print(f"\n{i}. {item['name']} (ID: {item['id']})")
                print(f"   Gold: {item['gold']}")
                print(f"   {item['description']}")
                print(f"   Match: {item['match_type']} (Score: {item['score']:.2f})")
        else:
            print("\nNo matches found. Try:")
            print("  - Check spelling")
            print("  - Use abbreviations (IE, BT, PD)")
            print("  - Use partial names (blood, phantom)")
        
        print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        interactive_search()
    else:
        # Run all tests
        test_abbreviations()
        test_partial_names()
        test_typos()
        test_name_to_id_conversion()
        test_suggestions()
        test_common_abbreviations()
        
        print("\n" + "="*80)
        print("All tests complete!")
        print("\nTo run interactive mode:")
        print("  python tests/test_item_search.py interactive")
        print("="*80)


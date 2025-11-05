"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

Simple test script to verify API functionality
"""
from .services.riot_api import riot_api
from .services.data_dragon import data_dragon
from .services.combat_power import combat_power_calculator
from .services.analytics import player_analytics


def test_data_dragon():
    """Test Data Dragon service"""
    print("\n=== Testing Data Dragon ===")
    
    # Test champions
    print("Fetching champions...")
    champions = data_dragon.get_champions()
    print(f"Found {len(champions)} champions")
    
    # Test champion detail
    print("\nFetching Ahri details...")
    ahri = data_dragon.get_champion_detail('Ahri')
    print(f"Ahri: {ahri['name']} - {ahri['title']}")
    print(f"Spells: {len(ahri['spells'])}")
    
    # Test items
    print("\nFetching items...")
    items = data_dragon.get_items()
    print(f"Found {len(items)} items")
    
    # Test runes
    print("\nFetching runes...")
    runes = data_dragon.get_runes()
    print(f"Found {len(runes)} rune trees")
    
    print("\nData Dragon tests passed!")


def test_combat_power():
    """Test combat power calculation"""
    print("\n=== Testing Combat Power ===")
    
    # Calculate all champions base power
    print("Calculating base combat power for all champions...")
    all_powers = combat_power_calculator.calculate_all_champions_base_power()
    
    # Sort by power
    sorted_champions = sorted(all_powers.items(), key=lambda x: x[1], reverse=True)
    
    print("\nTop 10 strongest champions (base power):")
    for i, (name, power) in enumerate(sorted_champions[:10], 1):
        print(f"{i}. {name}: {power:.2f}")
    
    print("\nBottom 10 weakest champions (base power):")
    for i, (name, power) in enumerate(sorted_champions[-10:], 1):
        print(f"{i}. {name}: {power:.2f}")
    
    avg_power = sum(all_powers.values()) / len(all_powers)
    print(f"\nAverage combat power: {avg_power:.2f}")
    
    print("\nCombat Power tests passed!")


def test_riot_api(game_name='S1NE', tag_line='NA1'):
    """Test Riot API integration"""
    print("\n=== Testing Riot API ===")
    
    try:
        # Get account
        print(f"Fetching account for {game_name}#{tag_line}...")
        account = riot_api.get_account_by_riot_id(game_name, tag_line)
        print(f"Found account: {account['gameName']}#{account['tagLine']}")
        print(f"PUUID: {account['puuid']}")
        
        # Get summoner
        print("\nFetching summoner info...")
        summoner = riot_api.get_summoner_by_puuid(account['puuid'])
        print(f"Summoner Level: {summoner['summonerLevel']}")
        
        # Get recent matches (just 5 for testing)
        print("\nFetching recent matches...")
        match_ids = riot_api.get_match_ids_by_puuid(account['puuid'], count=5)
        print(f"Found {len(match_ids)} recent matches")
        
        if match_ids:
            print("\nFetching first match details...")
            match = riot_api.get_match_by_id(match_ids[0])
            print(f"Match ID: {match['metadata']['matchId']}")
            print(f"Game Duration: {match['info']['gameDuration']} seconds")
            print(f"Game Mode: {match['info']['gameMode']}")
        
        print("\nRiot API tests passed!")
        
    except Exception as e:
        print(f"\nRiot API test failed: {e}")
        print("Make sure RIOT_API_KEY is set in .env file")


def test_analytics(game_name='S1NE', tag_line='NA1'):
    """Test analytics service"""
    print("\n=== Testing Analytics ===")
    
    try:
        # Get account
        print(f"Analyzing player {game_name}#{tag_line}...")
        account = riot_api.get_account_by_riot_id(game_name, tag_line)
        
        # Get recent matches for testing (limit to 20)
        print("Fetching match history...")
        match_ids = riot_api.get_match_ids_by_puuid(account['puuid'], count=20)
        
        matches = []
        for match_id in match_ids[:10]:  # Only process 10 for testing
            match = riot_api.get_match_by_id(match_id)
            matches.append(match)
        
        # Analyze
        print("Analyzing matches...")
        analysis = player_analytics.analyze_player_matches(matches, account['puuid'])
        
        print(f"\nTotal Games: {analysis['total_games']}")
        print(f"Win Rate: {analysis['win_rate']}%")
        print(f"Player Type: {analysis['player_type']}")
        print(f"Average KDA: {analysis['avg_kda']}")
        print(f"Average Combat Power: {analysis['avg_combat_power_per_game']:.2f}")
        
        if analysis['most_played_champions']:
            print(f"\nMost Played Champion: {analysis['most_played_champions'][0]['name']}")
            print(f"  Games: {analysis['most_played_champions'][0]['games']}")
            print(f"  Win Rate: {analysis['most_played_champions'][0]['win_rate']}%")
        
        print("\nAnalytics tests passed!")
        
    except Exception as e:
        print(f"\nAnalytics test failed: {e}")
        print("Make sure RIOT_API_KEY is set in .env file")


if __name__ == '__main__':
    print("Starting API Tests...")
    print("="*50)
    
    # Test Data Dragon (no API key needed)
    test_data_dragon()
    
    # Test Combat Power
    test_combat_power()
    
    # Test Riot API (requires API key)
    # Uncomment these if you have a valid API key configured
    # test_riot_api()
    # test_analytics()
    
    print("\n" + "="*50)
    print("All tests completed!")


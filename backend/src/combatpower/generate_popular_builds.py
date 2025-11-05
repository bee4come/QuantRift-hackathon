"""
Generate realistic popular build data for champions across patches
This script creates sample build data that mimics real League of Legends meta builds
"""
import json
import random
from typing import Dict, List, Any
from .services.patch_manager import patch_manager
from .services.meta_builds import MetaBuildsDatabase
from .services.build_tracker import BuildTracker


class PopularBuildGenerator:
    """Generates realistic popular build data for champions"""
    
    def __init__(self):
        self.meta_db = MetaBuildsDatabase()
        self.build_tracker = BuildTracker()
        
        # Load item data to get valid item IDs
        self.item_data = self._load_item_data()
        
        # Common item variations for different roles
        self.item_variations = {
            'ADC': {
                'core_items': [3031, 3094, 3046],  # IE, BT, PD
                'alternative_core': [3508, 3072, 3046],  # Essence Reaver, Bloodthirster, PD
                'situational': [3085, 3153, 6676, 3036, 3006]  # Runaan's, BotRK, RFC, LDR, Boots
            },
            'MID': {
                'core_items': [3089, 3135, 3020],  # Rabadon's, Luden's, Frost Queen
                'alternative_core': [3136, 3157, 3020],  # Rylai's, Liandry's, Frost Queen
                'situational': [3151, 3003, 3027, 3116, 3006]  # Morello, Archangel's, Rod, Rylai's, Boots
            },
            'TOP': {
                'core_items': [3072, 3074, 3075],  # Bloodthirster, Ravenous Hydra, Thornmail
                'alternative_core': [3068, 3071, 3083],  # Sunfire, Randuin's, Warmog's
                'situational': [3035, 3143, 3006, 3111, 3158]  # Phantom Dancer, Randuin's, Boots, Banshee's, Maw
            },
            'JUNGLE': {
                'core_items': [3156, 3074, 3022],  # Nashor's, Ravenous Hydra, Frost Queen
                'alternative_core': [3072, 3071, 3022],  # Bloodthirster, Randuin's, Frost Queen
                'situational': [3143, 3006, 3111, 3158, 3035]  # Randuin's, Boots, Banshee's, Maw, Phantom Dancer
            },
            'SUPPORT': {
                'core_items': [3109, 3020, 3117],  # Knight's Vow, Frost Queen, Mobility Boots
                'alternative_core': [3105, 3020, 3117],  # Aegis, Frost Queen, Mobility Boots
                'situational': [3102, 3006, 3111, 3158, 3035]  # Banshee's Veil, Boots, Banshee's, Maw, Phantom Dancer
            }
        }
    
    def _load_item_data(self) -> Dict[str, Any]:
        """Load item data from cached files"""
        try:
            # Try to load from latest patch
            patches = patch_manager.get_all_patches()
            latest_patch = patches[-1] if patches else "14.20"
            
            with open(f'data/patches/{latest_patch}/items.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load item data: {e}")
            return {}
    
    def _get_champion_role(self, champion_name: str) -> str:
        """Get champion role from meta builds"""
        if champion_name in self.meta_db.meta_builds:
            return self.meta_db.meta_builds[champion_name]['role']
        
        # Fallback role detection based on champion name patterns
        adc_champions = ['Draven', 'Jinx', 'Caitlyn', 'Ashe', 'Ezreal', 'Jhin', 'Kaisa', 'Lucian', 'MissFortune', 'Sivir', 'Tristana', 'Twitch', 'Varus', 'Vayne', 'Xayah']
        mid_champions = ['Ahri', 'Akali', 'Azir', 'Cassiopeia', 'Fizz', 'Katarina', 'LeBlanc', 'Orianna', 'Syndra', 'Talon', 'Zed', 'Zoe']
        top_champions = ['Darius', 'Garen', 'Jax', 'Malphite', 'Nasus', 'Renekton', 'Riven', 'Shen', 'Singed', 'Teemo', 'Tryndamere', 'Yorick']
        jungle_champions = ['Graves', 'JarvanIV', 'KhaZix', 'LeeSin', 'MasterYi', 'Nidalee', 'Rengar', 'Sejuani', 'Vi', 'Warwick', 'XinZhao']
        support_champions = ['Alistar', 'Blitzcrank', 'Braum', 'Janna', 'Leona', 'Lulu', 'Morgana', 'Nami', 'Pyke', 'Rakan', 'Soraka', 'Thresh', 'Yuumi']
        
        if champion_name in adc_champions:
            return 'ADC'
        elif champion_name in mid_champions:
            return 'MID'
        elif champion_name in top_champions:
            return 'TOP'
        elif champion_name in jungle_champions:
            return 'JUNGLE'
        elif champion_name in support_champions:
            return 'SUPPORT'
        else:
            return 'MID'  # Default fallback
    
    def _generate_item_build(self, champion_name: str, patch: str) -> List[int]:
        """Generate a realistic item build for a champion"""
        role = self._get_champion_role(champion_name)
        
        if role not in self.item_variations:
            role = 'MID'  # Fallback
        
        variations = self.item_variations[role]
        
        # Choose core build (70% chance for primary, 30% for alternative)
        if random.random() < 0.7:
            core_items = variations['core_items'][:]
        else:
            core_items = variations['alternative_core'][:]
        
        # Add 2-3 situational items
        situational_count = random.randint(2, 3)
        situational_items = random.sample(variations['situational'], situational_count)
        
        # Combine and ensure we have exactly 6 items (excluding boots slot)
        all_items = core_items + situational_items
        final_items = all_items[:6] if len(all_items) >= 6 else all_items + [3006] * (6 - len(all_items))
        
        # Add boots (always in slot 6)
        final_items[5] = 3006  # Boots
        
        return final_items
    
    def _generate_rune_build(self, champion_name: str, patch: str) -> tuple:
        """Generate a realistic rune build for a champion"""
        # Get meta runes if available
        if champion_name in self.meta_db.meta_builds:
            meta_runes = self.meta_db.meta_builds[champion_name]['runes']
            return (
                meta_runes['primary_style'],
                meta_runes['sub_style'],
                meta_runes['runes']
            )
        
        # Fallback to role-based runes
        role = self._get_champion_role(champion_name)
        
        if role == 'ADC':
            return (
                self.meta_db.PRECISION,
                self.meta_db.SORCERY,
                self.meta_db.LETHAL_TEMPO_RUNES['runes']
            )
        elif role == 'MID':
            return (
                self.meta_db.SORCERY,
                self.meta_db.INSPIRATION,
                self.meta_db.ARCANE_COMET_RUNES['runes']
            )
        elif role == 'TOP':
            return (
                self.meta_db.RESOLVE,
                self.meta_db.PRECISION,
                self.meta_db.GRASP_RUNES['runes']
            )
        elif role == 'JUNGLE':
            return (
                self.meta_db.DOMINATION,
                self.meta_db.PRECISION,
                self.meta_db.ELECTROCUTE_RUNES['runes']
            )
        else:  # Support
            return (
                self.meta_db.RESOLVE,
                self.meta_db.INSPIRATION,
                self.meta_db.AFTERSHOCK_RUNES['runes']
            )
    
    def generate_build_data_for_patch(self, patch: str, champions: List[str], games_per_champion: int = 50) -> None:
        """Generate build data for all champions in a specific patch"""
        print(f"Generating build data for patch {patch}...")
        
        for champion in champions:
            print(f"  Generating {games_per_champion} games for {champion}")
            
            # Generate multiple builds with some variation
            for game in range(games_per_champion):
                # Generate items and runes
                items = self._generate_item_build(champion, patch)
                primary_style, sub_style, rune_ids = self._generate_rune_build(champion, patch)
                
                # Add some random variation to make it more realistic
                if random.random() < 0.3:  # 30% chance for variation
                    # Swap one item
                    if len(items) > 1:
                        swap_idx = random.randint(0, len(items) - 2)  # Don't swap boots
                        items[swap_idx] = random.choice([3006, 3085, 3153, 6676, 3036])
                
                # Add to build tracker
                self.build_tracker.add_match(patch, champion, items, rune_ids, primary_style, sub_style)
    
    def generate_all_patches_data(self) -> None:
        """Generate build data for all patches and champions"""
        patches = patch_manager.get_all_patches()
        
        # Get champion list from latest patch
        try:
            latest_patch = patches[-1]
            with open(f'data/patches/{latest_patch}/champions.json', 'r', encoding='utf-8') as f:
                champions_data = json.load(f)
                champions = list(champions_data['data'].keys())
        except Exception as e:
            print(f"Error loading champions: {e}")
            # Fallback to common champions
            champions = ['Draven', 'Jinx', 'Caitlyn', 'Ashe', 'Ezreal', 'Ahri', 'Zed', 'Yasuo', 'Darius', 'Garen']
        
        print(f"Generating build data for {len(patches)} patches and {len(champions)} champions")
        
        for patch in patches:
            # Vary games per champion by patch (newer patches have more data)
            games_per_champion = random.randint(30, 80)
            self.generate_build_data_for_patch(patch, champions, games_per_champion)
        
        print("Build data generation complete!")
    
    def export_build_data(self, filename: str = "generated_builds.json") -> None:
        """Export generated build data to JSON file"""
        # Convert defaultdict to regular dict for JSON serialization
        export_data = {}
        for patch, patch_data in self.build_tracker.builds.items():
            export_data[patch] = {}
            for champion, champ_data in patch_data.items():
                # Convert tuple keys to string keys for JSON serialization
                item_sets = {}
                for item_tuple, count in champ_data['item_sets'].items():
                    item_sets[str(list(item_tuple))] = count
                
                rune_sets = {}
                for rune_tuple, count in champ_data['rune_sets'].items():
                    primary_style, sub_style, rune_ids = rune_tuple
                    rune_sets[f"{primary_style}_{sub_style}_{str(list(rune_ids))}"] = count
                
                export_data[patch][champion] = {
                    'item_sets': item_sets,
                    'rune_sets': rune_sets,
                    'total_games': champ_data['total_games']
                }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Build data exported to {filename}")
    
    def load_build_data(self, filename: str = "generated_builds.json") -> None:
        """Load build data from JSON file into build tracker"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for patch, patch_data in data.items():
                for champion, champ_data in patch_data.items():
                    # Restore defaultdict structure
                    self.build_tracker.builds[patch][champion] = {
                        'item_sets': defaultdict(int, champ_data['item_sets']),
                        'rune_sets': defaultdict(int, champ_data['rune_sets']),
                        'total_games': champ_data['total_games']
                    }
            
            print(f"Build data loaded from {filename}")
        except Exception as e:
            print(f"Error loading build data: {e}")


def main():
    """Main function to generate and export build data"""
    print("="*70)
    print("POPULAR BUILD DATA GENERATOR")
    print("="*70)
    
    generator = PopularBuildGenerator()
    
    # Generate build data for all patches
    generator.generate_all_patches_data()
    
    # Save the data to persistent storage
    generator.build_tracker.save_data()
    
    # Export the data
    generator.export_build_data()
    
    # Test with a few champions
    print("\n" + "="*70)
    print("TESTING GENERATED DATA")
    print("="*70)
    
    test_champions = ['Draven', 'Jinx', 'Ahri', 'Darius']
    test_patch = '14.20'
    
    for champion in test_champions:
        build_data = generator.build_tracker.get_popular_build(test_patch, champion)
        print(f"\n{champion} ({test_patch}):")
        print(f"  Has data: {build_data['has_data']}")
        if build_data['has_data']:
            print(f"  Items: {build_data['items']}")
            print(f"  Runes: {build_data['runes']}")
            print(f"  Total games: {build_data['total_games']}")
            print(f"  Item pick rate: {build_data['item_pick_rate']:.1f}%")
    
    print("\n" + "="*70)
    print("✓ BUILD DATA GENERATION COMPLETE!")
    print("="*70)
    print("The generated build data is now available in the build_tracker.")
    print("You can test it with the API endpoints.")


if __name__ == '__main__':
    main()

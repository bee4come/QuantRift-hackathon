"""
Intelligent Item Search System
Allows users to search items by:
- Full name: "Infinity Edge"
- Abbreviations: "IE", "BT", "PD"
- Partial names: "blood", "phantom"
- With typos: "infinty edge", "bloodthirster"
"""
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
from .data_provider import data_provider


class ItemSearchEngine:
    """Intelligent item search with fuzzy matching and abbreviations"""
    
    def __init__(self):
        """Initialize with common item abbreviations"""
        
        # Common abbreviations (lowercase for matching)
        self.abbreviations = {
            # ADC Items
            'ie': 3031,  # Infinity Edge
            'bt': 3072,  # Bloodthirster
            'pd': 3046,  # Phantom Dancer
            'rfc': 3094,  # Rapid Firecannon
            'er': 3508,  # Essence Reaver
            'bork': 3153,  # Blade of the Ruined King
            'botrk': 3153,  # Alternative
            'gb': 3124,  # Guinsoo's Rageblade
            'rageblade': 3124,
            'runaans': 3085,  # Runaan's Hurricane
            'hurricane': 3085,
            
            # Lethality Items
            'youmuus': 3142,  # Youmuu's Ghostblade
            'ghostblade': 3142,
            'duskblade': 6691,
            'collector': 6676,
            'edge': 3814,  # Edge of Night
            'eon': 3814,
            'ldr': 3036,  # Lord Dominik's Regards
            'dominiks': 3036,
            
            # Mage Items
            'liandrys': 6653,  # Liandry's Anguish
            'liandries': 6653,
            'liandry': 6653,
            'deathcap': 3089,  # Rabadon's Deathcap
            'rabadons': 3089,
            'rabadon': 3089,
            'dcap': 3089,
            'zhonyas': 3157,  # Zhonya's Hourglass
            'zhonya': 3157,
            'shadowflame': 4645,
            'void': 3135,  # Void Staff
            'voidstaff': 3135,
            'ludens': 3152,  # Luden's Companion
            'riftmaker': 4633,
            
            # Tank Items
            'sunfire': 3068,  # Sunfire Aegis
            'thornmail': 3075,
            'visage': 3065,  # Spirit Visage
            'randuins': 3143,  # Randuin's Omen
            'randuin': 3143,
            'titanic': 3748,  # Titanic Hydra
            'fh': 3110,  # Frozen Heart
            'frozen': 3110,
            
            # Fighter Items
            'gore': 6630,  # Goredrinker
            'goredrinker': 6630,
            'sunderer': 6632,  # Divine Sunderer
            'divine': 6632,
            'bc': 3071,  # Black Cleaver
            'cleaver': 3071,
            'trinity': 3078,  # Trinity Force
            'triforce': 3078,
            'tf': 3078,
            'ravenous': 3074,  # Ravenous Hydra
            'steraks': 3053,  # Sterak's Gage
            'sterak': 3053,
            'ga': 3026,  # Guardian Angel
            
            # Boots
            'zerkers': 3006,  # Berserker's Greaves
            'berserkers': 3006,
            'mercs': 3111,  # Mercury's Treads
            'mercury': 3111,
            'tabis': 3047,  # Plated Steelcaps
            'steelcaps': 3047,
            'ninja': 3047,  # Old name
            'sorc': 3020,  # Sorcerer's Shoes
            'sorcs': 3020,
            'sorcerer': 3020,
            'swifties': 3009,  # Boots of Swiftness
            'swiftness': 3009,
            
            # Support Items
            'ardent': 3504,  # Ardent Censer
            'censer': 3504,
            'staff': 3107,  # Staff of Flowing Water (context dependent)
            'redemption': 3107,
            'mikaels': 3222,  # Mikael's Blessing
            'mikael': 3222,
        }
        
        # Alternative spellings and common typos
        self.typo_mappings = {
            'infinty': 'infinity',
            'infintiy': 'infinity',
            'bloodthirster': 'bloodthirster',
            'bloodthirsty': 'bloodthirster',
            'firecannon': 'firecannon',
            'rapidfire': 'rapid firecannon',
            'essense': 'essence',
            'essensce': 'essence',
            'rabadons': 'rabadon',
            'rabbadon': 'rabadon',
            'zhonyas': 'zhonya',
            'zhonyah': 'zhonya',
            'randuins': 'randuin',
            'sunfre': 'sunfire',
            'youmuus': 'youmuu',
            'youmoos': 'youmuu',
        }
    
    def search_item(
        self,
        query: str,
        patch: str = '14.19',
        max_results: int = 5,
        threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Search for items by name, abbreviation, or partial match
        
        Args:
            query: Search query (e.g., "IE", "blood", "infinty edge")
            patch: Patch version to search in
            max_results: Maximum number of results to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of matching items with scores
        """
        query_lower = query.lower().strip()
        
        # Check abbreviations first (exact match)
        if query_lower in self.abbreviations:
            item_id = self.abbreviations[query_lower]
            item_info = self._get_item_info(item_id, patch)
            if item_info:
                return [{
                    'id': item_id,
                    'name': item_info['name'],
                    'description': item_info.get('plaintext', ''),
                    'gold': item_info.get('gold', {}).get('total', 0),
                    'match_type': 'abbreviation',
                    'score': 1.0
                }]
        
        # Apply typo corrections
        for typo, correction in self.typo_mappings.items():
            if typo in query_lower:
                query_lower = query_lower.replace(typo, correction)
        
        # Get all items for the patch
        items = data_provider.get_items_for_patch(patch)
        
        # Search through items
        matches = []
        for item_id, item_data in items.items():
            item_name = item_data.get('name', '').lower()
            
            # Skip special/unpurchasable items
            if not item_data.get('gold', {}).get('purchasable', True):
                continue
            
            # Calculate similarity
            score = self._calculate_similarity(query_lower, item_name)
            
            # Check if query is contained in name (partial match)
            if query_lower in item_name:
                score = max(score, 0.8)
            
            # Check if name contains query words
            query_words = query_lower.split()
            if len(query_words) > 1:
                # Multi-word query
                word_matches = sum(1 for word in query_words if word in item_name)
                word_score = word_matches / len(query_words)
                score = max(score, word_score)
            
            if score >= threshold:
                matches.append({
                    'id': int(item_id),
                    'name': item_data.get('name', ''),
                    'description': item_data.get('plaintext', ''),
                    'gold': item_data.get('gold', {}).get('total', 0),
                    'stats': item_data.get('stats', {}),
                    'tags': item_data.get('tags', []),
                    'match_type': 'fuzzy' if score < 0.9 else 'exact',
                    'score': score
                })
        
        # Sort by score (descending)
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches[:max_results]
    
    def search_items_batch(
        self,
        queries: List[str],
        patch: str = '14.19'
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for multiple items at once
        
        Args:
            queries: List of search queries
            patch: Patch version
            
        Returns:
            Dictionary mapping queries to results
        """
        results = {}
        for query in queries:
            results[query] = self.search_item(query, patch)
        return results
    
    def get_best_match(
        self,
        query: str,
        patch: str = '14.19'
    ) -> Optional[int]:
        """
        Get the single best matching item ID
        
        Args:
            query: Search query
            patch: Patch version
            
        Returns:
            Item ID or None if no good match
        """
        results = self.search_item(query, patch, max_results=1, threshold=0.6)
        if results:
            return results[0]['id']
        return None
    
    def convert_names_to_ids(
        self,
        item_names: List[str],
        patch: str = '14.19'
    ) -> Tuple[List[int], List[str]]:
        """
        Convert item names to IDs, return IDs and any failed matches
        
        Args:
            item_names: List of item names/abbreviations
            patch: Patch version
            
        Returns:
            Tuple of (item_ids, failed_matches)
        """
        item_ids = []
        failed = []
        
        for name in item_names:
            item_id = self.get_best_match(name, patch)
            if item_id:
                item_ids.append(item_id)
            else:
                failed.append(name)
        
        return item_ids, failed
    
    def _calculate_similarity(self, query: str, item_name: str) -> float:
        """Calculate similarity score between query and item name"""
        return SequenceMatcher(None, query, item_name).ratio()
    
    def _get_item_info(self, item_id: int, patch: str) -> Optional[Dict[str, Any]]:
        """Get item information"""
        try:
            items = data_provider.get_items_for_patch(patch)
            return items.get(str(item_id))
        except:
            return None
    
    def list_common_abbreviations(self) -> Dict[str, str]:
        """List all common abbreviations with their full names"""
        items = data_provider.get_champions_for_patch('14.19')
        result = {}
        
        for abbr, item_id in self.abbreviations.items():
            item_info = self._get_item_info(item_id, '14.19')
            if item_info:
                result[abbr.upper()] = item_info['name']
        
        return result
    
    def suggest_items(self, query: str, patch: str = '14.19', count: int = 10) -> List[Dict[str, Any]]:
        """
        Suggest items based on partial input (for autocomplete)
        
        Args:
            query: Partial input
            patch: Patch version
            count: Number of suggestions
            
        Returns:
            List of suggested items
        """
        if len(query) < 2:
            return []
        
        return self.search_item(query, patch, max_results=count, threshold=0.3)


# Singleton instance
item_search = ItemSearchEngine()


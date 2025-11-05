"""
Custom Build Analyzer
Allows users to test specific item combinations across all patches
"""
from typing import List, Dict, Any, Optional
from .patch_manager import patch_manager
from .combat_power import combat_power_calculator
from .data_provider import data_provider


class CustomBuildAnalyzer:
    """
    Analyze custom builds across patches
    User picks champion + items, system calculates power across all patches
    """
    
    def __init__(self):
        self.all_patches = patch_manager.get_all_patches()
    
    def analyze_custom_build(
        self,
        champion_name: str,
        item_ids: List[int],
        level: int = 18,
        rune_ids: Optional[List[int]] = None,
        primary_style: Optional[int] = None,
        sub_style: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze a custom build across all patches
        
        Args:
            champion_name: Champion name (e.g., 'Draven')
            item_ids: List of 1-6 item IDs (user can pick 3 or more)
            level: Champion level (default 18)
            rune_ids: Optional rune IDs (uses default if not provided)
            primary_style: Optional primary rune tree
            sub_style: Optional secondary rune tree
            
        Returns:
            Dictionary with combat power for each patch
        """
        results = {
            'champion': champion_name,
            'items': item_ids,
            'level': level,
            'patches': {}
        }
        
        # Default runes if not provided (generic Conqueror setup)
        if rune_ids is None:
            rune_ids = [8010, 9111, 9104, 8014, 8473, 8242, 5008, 5008, 5002]
            primary_style = 8000  # Precision
            sub_style = 8400  # Resolve
        
        # Calculate for each patch
        for patch in self.all_patches:
            try:
                power = combat_power_calculator.calculate_total_combat_power(
                    champion_name=champion_name,
                    level=level,
                    item_ids=item_ids,
                    rune_ids=rune_ids,
                    primary_style=primary_style,
                    sub_style=sub_style,
                    patch=patch
                )
                
                results['patches'][patch] = {
                    'total_power': power,
                    'patch_date': patch_manager.PATCH_DATES.get(patch).strftime('%Y-%m-%d') if patch in patch_manager.PATCH_DATES else 'Unknown'
                }
            except Exception as e:
                results['patches'][patch] = {
                    'total_power': None,
                    'error': str(e)
                }
        
        # Add statistics
        powers = [p['total_power'] for p in results['patches'].values() if p['total_power'] is not None]
        if powers:
            results['statistics'] = {
                'min_power': min(powers),
                'max_power': max(powers),
                'avg_power': sum(powers) / len(powers),
                'power_change': ((powers[-1] - powers[0]) / powers[0] * 100) if powers[0] > 0 else 0,
                'strongest_patch': max(results['patches'].items(), key=lambda x: x[1].get('total_power', 0))[0],
                'weakest_patch': min(results['patches'].items(), key=lambda x: x[1].get('total_power', float('inf')))[0]
            }
        
        return results
    
    def compare_builds(
        self,
        champion_name: str,
        build_options: List[Dict[str, Any]],
        level: int = 18
    ) -> Dict[str, Any]:
        """
        Compare multiple build options for the same champion
        
        Args:
            champion_name: Champion name
            build_options: List of builds, each with 'name', 'items', optional 'runes'
            level: Champion level
            
        Returns:
            Comparison results across patches
        """
        comparison = {
            'champion': champion_name,
            'level': level,
            'builds': {}
        }
        
        for build in build_options:
            build_name = build.get('name', 'Unnamed Build')
            item_ids = build.get('items', [])
            rune_ids = build.get('runes')
            primary_style = build.get('primary_style')
            sub_style = build.get('sub_style')
            
            results = self.analyze_custom_build(
                champion_name=champion_name,
                item_ids=item_ids,
                level=level,
                rune_ids=rune_ids,
                primary_style=primary_style,
                sub_style=sub_style
            )
            
            comparison['builds'][build_name] = results
        
        return comparison
    
    def get_item_info(self, item_id: int, patch: str = '14.19') -> Optional[Dict[str, Any]]:
        """Get item information for display"""
        try:
            items = data_provider.get_items_for_patch(patch)
            item_data = items.get(str(item_id), {})
            return {
                'id': item_id,
                'name': item_data.get('name', 'Unknown'),
                'description': item_data.get('plaintext', ''),
                'gold': item_data.get('gold', {}).get('total', 0),
                'stats': item_data.get('stats', {})
            }
        except:
            return None
    
    def format_results_table(self, results: Dict[str, Any]) -> str:
        """Format results as a readable table"""
        output = []
        output.append("="*80)
        output.append(f"CUSTOM BUILD ANALYSIS: {results['champion']}")
        output.append("="*80)
        
        # Show items
        output.append(f"\nItems: {results['items']}")
        item_names = []
        for item_id in results['items']:
            item_info = self.get_item_info(item_id)
            if item_info:
                item_names.append(item_info['name'])
        if item_names:
            output.append(f"  ({', '.join(item_names)})")
        
        output.append(f"Level: {results['level']}")
        output.append("")
        
        # Statistics
        if 'statistics' in results:
            stats = results['statistics']
            output.append("STATISTICS:")
            output.append("-"*80)
            output.append(f"  Average Power: {stats['avg_power']:.2f}")
            output.append(f"  Min Power: {stats['min_power']:.2f} (Patch {stats['weakest_patch']})")
            output.append(f"  Max Power: {stats['max_power']:.2f} (Patch {stats['strongest_patch']})")
            output.append(f"  Power Change: {stats['power_change']:+.2f}%")
            output.append("")
        
        # Patch-by-patch results
        output.append("COMBAT POWER BY PATCH:")
        output.append("-"*80)
        output.append(f"{'Patch':<12} {'Date':<12} {'Combat Power':>15} {'Change':>10}")
        output.append("-"*80)
        
        previous_power = None
        for patch, data in results['patches'].items():
            power = data.get('total_power')
            if power:
                date = data.get('patch_date', '')
                change = ""
                if previous_power:
                    change_pct = ((power - previous_power) / previous_power * 100)
                    change = f"{change_pct:+.2f}%"
                output.append(f"{patch:<12} {date:<12} {power:>15.2f} {change:>10}")
                previous_power = power
        
        output.append("="*80)
        return "\n".join(output)


# Singleton instance
custom_build_analyzer = CustomBuildAnalyzer()


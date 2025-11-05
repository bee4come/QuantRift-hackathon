#!/usr/bin/env python3
"""
Item Gold Efficiency (item_ge_t) Metric
Calculates gold efficiency ratios using DimStatWeights and DimItemPassive
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import pandas as pd

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'dimensions'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'transforms'))

from utils import format_output_precision, load_user_mode_config
from governance_framework import DataGovernanceFramework
from dim_stat_weights import DimStatWeights
from dim_item_passive import DimItemPassive

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ItemGoldEfficiencyAnalyzer:
    """Analyzes item gold efficiency using stat weights and item data"""
    
    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """Initialize analyzer with configuration and dimension tables"""
        self.config = load_user_mode_config(config_path)
        self.governance = DataGovernanceFramework()
        
        # Initialize dimension tables
        self.stat_weights = DimStatWeights()
        self.item_passive = DimItemPassive()
        
    def calculate_item_gold_efficiency(self, item_id: int, patch_version: str = "14.1") -> Optional[Dict[str, Any]]:
        """
        Calculate gold efficiency for a single item with DDragon enhancement
        Returns efficiency ratio and breakdown
        """

        # Determine appropriate patch version
        if patch_version is None:
            if self.enhanced_mode and patch_mapper:
                patch_version = patch_mapper.get_latest_patch()
            else:
                patch_version = "14.23.1"
        # Get enhanced item data
        item_data = self.item_passive.get_item_stats(item_id)
        if not item_data:
            logger.warning(f"Item {item_id} not found in dimension table")
            return None

        # Skip items with 0 cost (trinkets, consumables)
        if item_data.cost <= 0:
            return None

        # Use enhanced gold efficiency calculation if available
        if self.enhanced_mode:
            efficiency_data = self.item_passive.calculate_gold_efficiency(item_id)
            governance_tag = self._determine_governance_tag(
                efficiency_data["efficiency"] / 100,  # Convert to ratio
                len(item_data.stats) / 10,
                item_data
            )

            return {
                "item_id": item_id,
                "item_name": item_data.item_name,
                "patch_version": patch_version,
                "gold_efficiency_ratio": efficiency_data["efficiency"] / 100,
                "gold_efficiency_percent": efficiency_data["efficiency"],
                "raw_stats_value": efficiency_data["raw_stats_value"],
                "total_cost": efficiency_data["total_cost"],
                "passive_value_estimate": efficiency_data.get("passive_value_estimate", 0),
                "governance_tag": governance_tag,
                "enhanced_with_ddragon": True,
                "item_stats": item_data.stats,
                "item_tags": getattr(item_data, 'tags', []),
                "validated_with_ddragon": getattr(item_data, 'validated_with_ddragon', False)
            }
            
        # Calculate total stat gold value
        stat_gold_value = self.stat_weights.calculate_stat_gold_value(
            item_data.stats, patch_version
        )
        
        # Calculate efficiency ratio
        efficiency_ratio = stat_gold_value / item_data.cost if item_data.cost > 0 else 0.0
        
        # Determine governance tag based on stat coverage
        stat_coverage = len(item_data.stats) / 10  # Normalize by typical max stats
        governance_tag = self._determine_governance_tag(efficiency_ratio, stat_coverage, item_data)
        
        return {
            "item_id": item_id,
            "item_name": item_data.item_name,
            "item_cost": item_data.cost,
            "stat_gold_value": stat_gold_value,
            "efficiency_ratio": efficiency_ratio,
            "efficiency_percentage": efficiency_ratio * 100,
            "stat_breakdown": item_data.stats,
            "passive_effects": item_data.passive_effects,
            "stat_coverage": stat_coverage,
            "governance_tag": governance_tag,
            "patch_version": patch_version
        }
        
    def _determine_governance_tag(self, efficiency_ratio: float, stat_coverage: float, item_data) -> str:
        """Determine governance quality based on efficiency calculation reliability"""
        
        # CONFIDENT: High stat coverage, reasonable efficiency
        if stat_coverage >= 0.4 and len(item_data.stats) >= 3:
            if 0.5 <= efficiency_ratio <= 2.0:  # Reasonable efficiency range
                return "CONFIDENT"
                
        # CAUTION: Some stats missing or extreme efficiency
        if stat_coverage >= 0.2 and len(item_data.stats) >= 2:
            if efficiency_ratio > 0:
                return "CAUTION"
                
        # CONTEXT: Poor stat coverage or missing data
        return "CONTEXT"
        
    def analyze_all_items(self, patch_version: str = "14.1") -> List[Dict[str, Any]]:
        """Calculate gold efficiency for all items in dimension table"""
        results = []
        
        for item_id in self.item_passive.items.keys():
            efficiency_data = self.calculate_item_gold_efficiency(item_id, patch_version)
            if efficiency_data:  # Skip items with 0 cost
                results.append(efficiency_data)
                
        # Sort by efficiency ratio descending
        results.sort(key=lambda x: x['efficiency_ratio'], reverse=True)
        
        logger.info(f"Calculated gold efficiency for {len(results)} items")
        return results
        
    def generate_efficiency_tiers(self, efficiency_results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize items by efficiency tiers"""
        tiers = {
            "highly_efficient": [],      # >110% efficiency
            "efficient": [],             # 90-110% efficiency
            "average": [],               # 70-90% efficiency
            "inefficient": [],           # 50-70% efficiency
            "very_inefficient": []       # <50% efficiency
        }
        
        for item in efficiency_results:
            ratio = item['efficiency_ratio']
            if ratio >= 1.10:
                tiers["highly_efficient"].append(item)
            elif ratio >= 0.90:
                tiers["efficient"].append(item)
            elif ratio >= 0.70:
                tiers["average"].append(item)
            elif ratio >= 0.50:
                tiers["inefficient"].append(item)
            else:
                tiers["very_inefficient"].append(item)
                
        return tiers
        
    def export_results(self, patch_version: str = "14.1", output_dir: str = "out/quantitative/") -> Dict[str, Any]:
        """Analyze and export gold efficiency results"""
        
        # Calculate efficiency for all items
        efficiency_results = self.analyze_all_items(patch_version)
        
        # Generate efficiency tiers
        efficiency_tiers = self.generate_efficiency_tiers(efficiency_results)
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Prepare export data
        export_data = {
            "metadata": {
                "metric_type": "item_ge_t",
                "description": "Item gold efficiency calculations",
                "patch_version": patch_version,
                "record_count": len(efficiency_results),
                "generated_at": pd.Timestamp.now().isoformat(),
                "governance_enabled": True
            },
            "summary": {
                "highly_efficient_count": len(efficiency_tiers["highly_efficient"]),
                "efficient_count": len(efficiency_tiers["efficient"]),
                "average_count": len(efficiency_tiers["average"]),
                "inefficient_count": len(efficiency_tiers["inefficient"]),
                "very_inefficient_count": len(efficiency_tiers["very_inefficient"])
            },
            "governance_distribution": self._analyze_governance_distribution(efficiency_results),
            "records": efficiency_results,
            "efficiency_tiers": efficiency_tiers
        }
        
        # Save to file
        patch_suffix = f"_patch_{patch_version}" if patch_version != "14.1" else ""
        output_file = output_path / f"item_gold_efficiency{patch_suffix}.json"
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
            
        logger.info(f"Exported item gold efficiency results to {output_file}")
        
        return export_data
        
    def _analyze_governance_distribution(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze governance tag distribution"""
        distribution = {"CONFIDENT": 0, "CAUTION": 0, "CONTEXT": 0}
        
        for result in results:
            tag = result.get("governance_tag", "CONTEXT")
            if tag in distribution:
                distribution[tag] += 1
                
        return distribution
        
    def get_top_efficient_items(self, n: int = 10, patch_version: str = "14.1") -> List[Dict[str, Any]]:
        """Get top N most gold efficient items"""
        efficiency_results = self.analyze_all_items(patch_version)
        return efficiency_results[:n]
        
    def get_least_efficient_items(self, n: int = 10, patch_version: str = "14.1") -> List[Dict[str, Any]]:
        """Get N least gold efficient items"""
        efficiency_results = self.analyze_all_items(patch_version)
        return efficiency_results[-n:]


def main():
    """Demo usage of item gold efficiency analyzer"""
    analyzer = ItemGoldEfficiencyAnalyzer()
    
    print("🔍 ITEM GOLD EFFICIENCY ANALYSIS")
    print("=" * 50)
    
    # Test single item calculation
    test_items = [1055, 3031, 3078, 3364]  # Doran's Blade, IE, Trinity, Oracle Lens
    
    print("\n📊 Sample Item Efficiency Calculations:")
    for item_id in test_items:
        efficiency = analyzer.calculate_item_gold_efficiency(item_id)
        if efficiency:
            print(f"\n{efficiency['item_name']} (ID: {item_id}):")
            print(f"  Cost: {efficiency['item_cost']} gold")
            print(f"  Stat Value: {efficiency['stat_gold_value']:.0f} gold")
            print(f"  Efficiency: {efficiency['efficiency_percentage']:.1f}%")
            print(f"  Stats: {efficiency['stat_breakdown']}")
            print(f"  Governance: {efficiency['governance_tag']}")
        else:
            print(f"Item {item_id}: No efficiency data (likely 0 cost)")
            
    # Run full analysis
    print("\n📈 Running Full Gold Efficiency Analysis...")
    results = analyzer.export_results()
    
    print(f"\n✅ ANALYSIS COMPLETE:")
    print(f"  📦 Total items analyzed: {results['metadata']['record_count']}")
    print(f"  🟢 Highly efficient (>110%): {results['summary']['highly_efficient_count']}")
    print(f"  🔵 Efficient (90-110%): {results['summary']['efficient_count']}")
    print(f"  🟡 Average (70-90%): {results['summary']['average_count']}")
    print(f"  🟠 Inefficient (50-70%): {results['summary']['inefficient_count']}")
    print(f"  🔴 Very inefficient (<50%): {results['summary']['very_inefficient_count']}")
    
    # Show governance quality
    gov_dist = results['governance_distribution']
    total = sum(gov_dist.values())
    print(f"\n🏛️ DATA GOVERNANCE QUALITY:")
    for tag, count in gov_dist.items():
        percentage = count / total * 100 if total > 0 else 0
        print(f"  {tag}: {count} records ({percentage:.1f}%)")
        
    # Show most/least efficient items
    if results['records']:
        print(f"\n🏆 TOP 3 MOST EFFICIENT ITEMS:")
        for i, item in enumerate(results['records'][:3], 1):
            print(f"  {i}. {item['item_name']}: {item['efficiency_percentage']:.1f}% efficient")
            
        print(f"\n💸 TOP 3 LEAST EFFICIENT ITEMS:")
        for i, item in enumerate(results['records'][-3:], 1):
            print(f"  {i}. {item['item_name']}: {item['efficiency_percentage']:.1f}% efficient")


if __name__ == "__main__":
    main()
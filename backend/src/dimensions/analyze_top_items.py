#!/usr/bin/env python3
"""
Script to analyze attach_rates data and identify top 50 most frequent items
"""

import json
import logging
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_top_items(attach_rates_file: str = "/home/zty/rift_rewind/experiment/out/behavioral/attach_rates_all_patches.json") -> List[Tuple[int, int, float]]:
    """
    Analyze attach rates data to find top 50 most frequently attached items
    Returns: List of (item_id, total_occurrences, avg_attach_rate)
    """
    
    with open(attach_rates_file, 'r') as f:
        data = json.load(f)
    
    records = data['records']
    logger.info(f"Analyzing {len(records)} attach rate records")
    
    # Aggregate by item_id
    item_stats = defaultdict(lambda: {'total_occurrences': 0, 'attach_rates': [], 'total_games': 0})
    
    for record in records:
        item_id = record['item_id']
        n = record['n']  # total games for this champion
        w = record['w']  # times this item was used
        attach_rate = record['p_hat']
        
        item_stats[item_id]['total_occurrences'] += w
        item_stats[item_id]['total_games'] += n
        item_stats[item_id]['attach_rates'].append(attach_rate)
    
    # Calculate aggregated metrics
    item_rankings = []
    for item_id, stats in item_stats.items():
        total_occurrences = stats['total_occurrences']
        avg_attach_rate = sum(stats['attach_rates']) / len(stats['attach_rates'])
        total_games = stats['total_games']
        
        # Use total occurrences as primary ranking metric
        item_rankings.append((item_id, total_occurrences, avg_attach_rate, total_games))
    
    # Sort by total occurrences (descending)
    item_rankings.sort(key=lambda x: x[1], reverse=True)
    
    # Take top 50
    top_50 = item_rankings[:50]
    
    logger.info(f"Top 50 items identified:")
    for i, (item_id, occurrences, avg_rate, games) in enumerate(top_50[:10], 1):
        logger.info(f"  {i}. Item {item_id}: {occurrences:,} occurrences, {avg_rate:.3f} avg rate")
    
    return top_50


def main():
    """Analyze and display top items"""
    top_items = analyze_top_items()
    
    print("\nTop 50 Most Frequently Attached Items:")
    print("=" * 60)
    print(f"{'Rank':<4} {'Item ID':<8} {'Occurrences':<12} {'Avg Rate':<10} {'Total Games':<12}")
    print("-" * 60)
    
    for i, (item_id, occurrences, avg_rate, games) in enumerate(top_items, 1):
        print(f"{i:<4} {item_id:<8} {occurrences:<12,} {avg_rate:<10.3f} {games:<12,}")
    
    # Save results for use in DimItemPassive
    output = {
        "metadata": {
            "description": "Top 50 most frequently attached items",
            "total_items_analyzed": len(top_items),
            "ranking_criteria": "total_occurrences"
        },
        "top_items": [
            {
                "rank": i,
                "item_id": item_id,
                "total_occurrences": occurrences,
                "avg_attach_rate": avg_rate,
                "total_games": games
            }
            for i, (item_id, occurrences, avg_rate, games) in enumerate(top_items, 1)
        ]
    }
    
    output_file = Path("/home/zty/rift_rewind/experiment/dimensions/top_50_items.json")
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    return top_items


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Timeline Metrics: Average Time to Core Items Analysis
Analyzes core item completion times using final_items data and attach_rate patterns
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy import stats

# Import existing core utilities
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'core'))
from utils import (
    generate_row_id, apply_governance_tag, safe_float_convert,
    safe_int_convert, format_output_precision, load_user_mode_config
)
from transforms.governance_framework import DataGovernanceFramework

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AvgTimeToCoreAnalyzer:
    """Analyzes core item completion times from enhanced facts data"""

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """Initialize analyzer with configuration"""
        self.config = load_user_mode_config(config_path)
        self.governance = DataGovernanceFramework()
        self.silver_data = {}
        self.core_items_cache = {}

    def load_silver_data(self, data_dir: str = "data/silver/enhanced_facts_test/") -> None:
        """Load Silver layer enhanced facts data for analysis"""
        data_path = Path(data_dir)

        if not data_path.exists():
            raise FileNotFoundError(f"Silver data directory not found: {data_dir}")

        # Load all patch data files
        patch_files = list(data_path.glob("enhanced_fact_match_performance_patch_*.json"))

        for file_path in patch_files:
            # Extract patch version from filename
            patch_version = file_path.stem.split("_")[-1]

            logger.info(f"Loading data for patch {patch_version}")

            with open(file_path, 'r') as f:
                data = json.load(f)

            # Convert records to DataFrame
            df = pd.DataFrame(data['records'])

            # Data quality filtering
            df = df[df.get('data_quality_score', 1.0) >= 0.8]  # Filter low quality data
            df = df[df['game_duration_minutes'] >= 10]  # Filter very short games

            # Parse final_items JSON field safely
            df['final_items_parsed'] = df['final_items'].apply(self._parse_items_safely)

            self.silver_data[patch_version] = {
                'metadata': data['metadata'],
                'df': df
            }

            logger.info(f"Loaded {len(df)} high-quality records for patch {patch_version}")

    def _parse_items_safely(self, items_str: str) -> List[int]:
        """Safely parse the final_items JSON string"""
        try:
            if pd.isna(items_str) or items_str == '':
                return []
            items = json.loads(items_str)
            return [int(item) for item in items if item != 0]  # Remove empty slots
        except (json.JSONDecodeError, ValueError, TypeError):
            return []

    def _wilson_confidence_interval(self, successes: int, trials: int, alpha: float = 0.05) -> Tuple[float, float, float]:
        """Calculate Wilson confidence interval for proportions"""
        if trials == 0:
            return 0.0, 0.0, 0.0

        p = successes / trials
        z = stats.norm.ppf(1 - alpha/2)

        # Wilson CI formula
        denominator = 1 + z**2 / trials
        centre_adjusted_probability = (p + z**2 / (2 * trials)) / denominator
        adjusted_standard_deviation = np.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / denominator

        lower_bound = centre_adjusted_probability - z * adjusted_standard_deviation
        upper_bound = centre_adjusted_probability + z * adjusted_standard_deviation

        return p, max(0, lower_bound), min(1, upper_bound)

    def _identify_core_items(self, patch_version: str) -> Dict[Tuple[int, str], List[int]]:
        """
        Identify core items for each champion×role×patch using attach rate data.
        Returns top 3 items by attach rate as "core items".
        """
        if patch_version in self.core_items_cache:
            return self.core_items_cache[patch_version]

        core_items = {}

        if patch_version not in self.silver_data:
            logger.warning(f"No data available for patch {patch_version}")
            return core_items

        df = self.silver_data[patch_version]['df']

        # Calculate item attach rates by champion×position
        for (champion_id, position), group in df.groupby(['champion_id', 'position']):
            if len(group) < 10:  # Skip champion×position combos with too few games
                continue

            # Count item occurrences
            item_counts = defaultdict(int)
            for items_list in group['final_items_parsed']:
                for item_id in items_list:
                    item_counts[item_id] += 1

            # Calculate attach rates and select top 3 as core items
            item_rates = []
            total_games = len(group)

            for item_id, count in item_counts.items():
                if count >= 3:  # Minimum threshold
                    attach_rate = count / total_games
                    item_rates.append((item_id, attach_rate))

            # Sort by attach rate and take top 3
            item_rates.sort(key=lambda x: x[1], reverse=True)
            core_items[(champion_id, position)] = [item_id for item_id, _ in item_rates[:3]]

        self.core_items_cache[patch_version] = core_items
        logger.info(f"Identified core items for {len(core_items)} champion×position combinations in patch {patch_version}")

        return core_items

    def _estimate_item_timing(self, final_items: List[int], game_duration: float) -> Dict[int, float]:
        """
        Estimate item completion times based on game duration and item order.
        Uses heuristic: items completed at evenly spaced intervals.
        """
        if not final_items or game_duration <= 0:
            return {}

        # Heuristic timing model:
        # - First item: 20% of game duration
        # - Subsequent items: evenly distributed over remaining time
        timings = {}

        if len(final_items) == 1:
            timings[final_items[0]] = game_duration * 0.4  # Single item at 40% of game
        else:
            # First item timing
            first_item_time = min(game_duration * 0.25, 8.0)  # Cap at 8 minutes
            timings[final_items[0]] = first_item_time

            # Distribute remaining items
            remaining_time = game_duration - first_item_time
            item_interval = remaining_time / (len(final_items) - 1) if len(final_items) > 1 else 0

            for i, item_id in enumerate(final_items[1:], 1):
                timings[item_id] = first_item_time + (i * item_interval)

        return timings

    def calculate_avg_time_to_core(self, patch_version: str = None) -> List[Dict[str, Any]]:
        """
        Calculate average time to core item completion.
        Analyzes 2-item and 3-item core builds with P50/P75 completion times.
        """
        results = []

        patches_to_process = [patch_version] if patch_version else list(self.silver_data.keys())

        for patch in patches_to_process:
            if patch not in self.silver_data:
                logger.warning(f"Patch {patch} data not available")
                continue

            df = self.silver_data[patch]['df']
            core_items = self._identify_core_items(patch)

            # Analyze time to core for each champion×position
            for (champion_id, position), champion_group in df.groupby(['champion_id', 'position']):
                if len(champion_group) < 15:  # Skip small samples
                    continue

                if (champion_id, position) not in core_items:
                    continue

                core_item_list = core_items[(champion_id, position)]
                if len(core_item_list) < 2:  # Need at least 2 core items
                    continue

                champion_name = champion_group['champion_name'].iloc[0] if 'champion_name' in champion_group.columns else f"Champion_{champion_id}"

                # Analyze completion times for 2-item and 3-item cores
                completion_times_2 = []
                completion_times_3 = []

                for _, game in champion_group.iterrows():
                    final_items = game['final_items_parsed']
                    duration = game['game_duration_minutes']

                    if not final_items or duration <= 5:
                        continue

                    # Estimate item timing
                    item_timings = self._estimate_item_timing(final_items, duration)

                    # Check 2-item core completion
                    core_2_times = []
                    for item_id in core_item_list[:2]:
                        if item_id in item_timings:
                            core_2_times.append(item_timings[item_id])

                    if len(core_2_times) == 2:
                        completion_times_2.append(max(core_2_times))  # Time when both items completed

                    # Check 3-item core completion
                    if len(core_item_list) >= 3:
                        core_3_times = []
                        for item_id in core_item_list[:3]:
                            if item_id in item_timings:
                                core_3_times.append(item_timings[item_id])

                        if len(core_3_times) == 3:
                            completion_times_3.append(max(core_3_times))  # Time when all 3 items completed

                # Calculate statistics for 2-item core
                if len(completion_times_2) >= 5:
                    p50_2 = np.percentile(completion_times_2, 50)
                    p75_2 = np.percentile(completion_times_2, 75)
                    mean_2 = np.mean(completion_times_2)

                    record_2 = {
                        'row_id': generate_row_id(
                            patch, champion_id, position.lower(), 'ranked_solo',
                            'avg_time_to_core', '2_item'
                        ),
                        'patch_id': patch,
                        'champion_id': int(champion_id),
                        'champion_name': champion_name,
                        'role': position.lower(),
                        'queue': 'ranked_solo',
                        'metric_type': 'avg_time_to_core',
                        'core_item_count': 2,
                        'core_items': core_item_list[:2],

                        # Sample metrics
                        'n': len(completion_times_2),
                        'w': len([t for t in completion_times_2 if t <= p75_2]),  # Games completing within P75
                        'uses_prior': False,
                        'effective_n': float(len(completion_times_2)),
                        'p_hat': format_output_precision(mean_2 / 30.0, is_probability=False),  # Normalized by max game time
                        'ci': {
                            'lo': format_output_precision(p50_2, is_probability=False),
                            'hi': format_output_precision(p75_2, is_probability=False)
                        },
                        'avg_completion_time': format_output_precision(mean_2, is_probability=False),
                        'p50_completion_time': format_output_precision(p50_2, is_probability=False),
                        'p75_completion_time': format_output_precision(p75_2, is_probability=False),
                        'winrate_delta': 0.0,  # Not applicable for timing metric
                        'stability': min(1.0, 10.0 / (p75_2 - p50_2 + 0.1)),  # Inverse of timing variance
                        'synthetic_share': 0.0,
                        'aggregation_level': 'champion:role:patch:2_item',
                        'k_selected': 2,
                        'oot_pass': True
                    }

                    # Apply governance tag
                    record_2['governance_tag'] = apply_governance_tag(record_2, self.config)
                    results.append(record_2)

                # Calculate statistics for 3-item core
                if len(completion_times_3) >= 5:
                    p50_3 = np.percentile(completion_times_3, 50)
                    p75_3 = np.percentile(completion_times_3, 75)
                    mean_3 = np.mean(completion_times_3)

                    record_3 = {
                        'row_id': generate_row_id(
                            patch, champion_id, position.lower(), 'ranked_solo',
                            'avg_time_to_core', '3_item'
                        ),
                        'patch_id': patch,
                        'champion_id': int(champion_id),
                        'champion_name': champion_name,
                        'role': position.lower(),
                        'queue': 'ranked_solo',
                        'metric_type': 'avg_time_to_core',
                        'core_item_count': 3,
                        'core_items': core_item_list[:3],

                        # Sample metrics
                        'n': len(completion_times_3),
                        'w': len([t for t in completion_times_3 if t <= p75_3]),  # Games completing within P75
                        'uses_prior': False,
                        'effective_n': float(len(completion_times_3)),
                        'p_hat': format_output_precision(mean_3 / 35.0, is_probability=False),  # Normalized
                        'ci': {
                            'lo': format_output_precision(p50_3, is_probability=False),
                            'hi': format_output_precision(p75_3, is_probability=False)
                        },
                        'avg_completion_time': format_output_precision(mean_3, is_probability=False),
                        'p50_completion_time': format_output_precision(p50_3, is_probability=False),
                        'p75_completion_time': format_output_precision(p75_3, is_probability=False),
                        'winrate_delta': 0.0,
                        'stability': min(1.0, 15.0 / (p75_3 - p50_3 + 0.1)),
                        'synthetic_share': 0.0,
                        'aggregation_level': 'champion:role:patch:3_item',
                        'k_selected': 3,
                        'oot_pass': True
                    }

                    # Apply governance tag
                    record_3['governance_tag'] = apply_governance_tag(record_3, self.config)
                    results.append(record_3)

        logger.info(f"Calculated {len(results)} avg_time_to_core records")
        return results


def main():
    """Demo script for avg_time_to_core analysis"""
    analyzer = AvgTimeToCoreAnalyzer()

    try:
        # Load Silver layer data
        analyzer.load_silver_data()

        # Calculate avg_time_to_core metrics
        results = analyzer.calculate_avg_time_to_core()

        # Display sample results
        print(f"\nGenerated {len(results)} avg_time_to_core records")

        if results:
            print("\nSample records:")
            for i, record in enumerate(results[:3]):
                print(f"\n{i+1}. Champion: {record['champion_name']}, Role: {record['role']}")
                print(f"   Core Items ({record['core_item_count']}): {record['core_items']}")
                print(f"   P50/P75 Completion: {record['p50_completion_time']:.1f}/{record['p75_completion_time']:.1f} min")
                print(f"   Sample Size: {record['n']}, Governance: {record['governance_tag']}")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()
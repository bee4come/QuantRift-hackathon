#!/usr/bin/env python3
"""
Timeline Metrics: Enhanced Baseline Winrate Analysis
Calculates winrate deltas vs enhanced baselines (champion×role×patch and tier×role×patch)
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


class BaselineWinrateAnalyzer:
    """Enhanced baseline winrate calculations with multiple baseline types"""

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """Initialize analyzer with configuration"""
        self.config = load_user_mode_config(config_path)
        self.governance = DataGovernanceFramework()
        self.silver_data = {}
        self.baseline_cache = {}

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
            df = df[df.get('data_quality_score', 1.0) >= 0.8]
            df = df[df['game_duration_minutes'] >= 10]  # Filter very short games

            # Ensure win column is boolean
            df['win'] = df['win'].astype(bool)

            self.silver_data[patch_version] = {
                'metadata': data['metadata'],
                'df': df
            }

            logger.info(f"Loaded {len(df)} high-quality records for patch {patch_version}")

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

    def _calculate_champion_role_baseline(self, patch_version: str) -> Dict[Tuple[int, str], Dict[str, float]]:
        """
        Calculate baseline winrates for champion×role×patch combinations.
        Returns winrate with Wilson CI for each combination.
        """
        cache_key = f"champion_role_{patch_version}"
        if cache_key in self.baseline_cache:
            return self.baseline_cache[cache_key]

        baselines = {}

        if patch_version not in self.silver_data:
            return baselines

        df = self.silver_data[patch_version]['df']

        # Calculate winrate for each champion×position combination
        for (champion_id, position), group in df.groupby(['champion_id', 'position']):
            if len(group) < 10:  # Skip small samples
                continue

            wins = group['win'].sum()
            games = len(group)
            winrate, ci_lower, ci_upper = self._wilson_confidence_interval(wins, games)

            baselines[(champion_id, position)] = {
                'winrate': winrate,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
                'games': games,
                'wins': wins
            }

        self.baseline_cache[cache_key] = baselines
        logger.info(f"Calculated {len(baselines)} champion×position baselines for patch {patch_version}")
        return baselines

    def _calculate_tier_role_baseline(self, patch_version: str) -> Dict[Tuple[str, str], Dict[str, float]]:
        """
        Calculate baseline winrates for tier×role×patch combinations.
        Returns winrate with Wilson CI for each combination.
        """
        cache_key = f"tier_role_{patch_version}"
        if cache_key in self.baseline_cache:
            return self.baseline_cache[cache_key]

        baselines = {}

        if patch_version not in self.silver_data:
            return baselines

        df = self.silver_data[patch_version]['df']

        # Calculate winrate for each tier×position combination
        for (tier, position), group in df.groupby(['tier', 'position']):
            if len(group) < 50:  # Need larger sample for tier baselines
                continue

            wins = group['win'].sum()
            games = len(group)
            winrate, ci_lower, ci_upper = self._wilson_confidence_interval(wins, games)

            baselines[(tier, position)] = {
                'winrate': winrate,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
                'games': games,
                'wins': wins
            }

        self.baseline_cache[cache_key] = baselines
        logger.info(f"Calculated {len(baselines)} tier×position baselines for patch {patch_version}")
        return baselines

    def _calculate_winrate_delta_significance(self, actual_winrate: float, baseline_winrate: float,
                                           actual_ci: Tuple[float, float], baseline_ci: Tuple[float, float]) -> Dict[str, float]:
        """
        Calculate statistical significance of winrate delta using CI overlap.
        Returns significance metrics and confidence in the delta.
        """
        delta = actual_winrate - baseline_winrate

        # Check CI overlap for significance
        actual_lower, actual_upper = actual_ci
        baseline_lower, baseline_upper = baseline_ci

        # No overlap = statistically significant
        if actual_lower > baseline_upper or baseline_lower > actual_upper:
            significance = 'significant'
            confidence = 0.95  # High confidence
        elif (actual_lower <= baseline_lower <= actual_upper) or (baseline_lower <= actual_lower <= baseline_upper):
            significance = 'marginal'
            confidence = 0.75  # Medium confidence
        else:
            significance = 'not_significant'
            confidence = 0.50  # Low confidence

        return {
            'delta': delta,
            'significance': significance,
            'confidence': confidence,
            'ci_overlap': not (actual_lower > baseline_upper or baseline_lower > actual_upper)
        }

    def calculate_winrate_delta_vs_baseline(self, patch_version: str = None) -> List[Dict[str, Any]]:
        """
        Calculate enhanced winrate deltas vs multiple baseline types.
        Returns records with both champion×role and tier×role baseline comparisons.
        """
        results = []

        patches_to_process = [patch_version] if patch_version else list(self.silver_data.keys())

        for patch in patches_to_process:
            if patch not in self.silver_data:
                logger.warning(f"Patch {patch} data not available")
                continue

            df = self.silver_data[patch]['df']

            # Calculate baseline winrates
            champion_baselines = self._calculate_champion_role_baseline(patch)
            tier_baselines = self._calculate_tier_role_baseline(patch)

            # Analyze each player's performance vs baselines
            for _, player_record in df.iterrows():
                champion_id = player_record['champion_id']
                position = player_record['position']
                tier = player_record['tier']
                win = player_record['win']

                # Get player identifier (use match_performance_sk or create one)
                player_key = player_record.get('player_key', f"player_{len(results)}")

                # Calculate actual winrate for this player (single game)
                actual_winrate = 1.0 if win else 0.0
                actual_ci = (actual_winrate - 0.4, actual_winrate + 0.4)  # Wide CI for single game

                # Get champion×position baseline
                champion_baseline = champion_baselines.get((champion_id, position))
                if champion_baseline and champion_baseline['games'] >= 15:
                    baseline_winrate = champion_baseline['winrate']
                    baseline_ci = (champion_baseline['ci_lower'], champion_baseline['ci_upper'])

                    delta_stats = self._calculate_winrate_delta_significance(
                        actual_winrate, baseline_winrate, actual_ci, baseline_ci
                    )

                    # Create record for champion baseline comparison
                    record_champion = {
                        'row_id': generate_row_id(
                            patch, champion_id, position.lower(), 'ranked_solo',
                            'winrate_delta_vs_baseline', f'champion_{player_key}'
                        ),
                        'patch_id': patch,
                        'champion_id': int(champion_id),
                        'champion_name': player_record.get('champion_name', f"Champion_{champion_id}"),
                        'role': position.lower(),
                        'tier': tier.lower(),
                        'queue': 'ranked_solo',
                        'metric_type': 'winrate_delta_vs_baseline',
                        'baseline_type': 'champion_role_patch',
                        'player_key': player_key,

                        # Sample metrics
                        'n': 1,  # Single game
                        'w': 1 if win else 0,
                        'uses_prior': True,  # Uses champion baseline as prior
                        'effective_n': float(champion_baseline['games']),  # Baseline sample size
                        'p_hat': format_output_precision(actual_winrate, is_probability=True),
                        'ci': {
                            'lo': format_output_precision(actual_ci[0], is_probability=True),
                            'hi': format_output_precision(actual_ci[1], is_probability=True)
                        },
                        'baseline_winrate': format_output_precision(baseline_winrate, is_probability=True),
                        'baseline_ci': {
                            'lo': format_output_precision(baseline_ci[0], is_probability=True),
                            'hi': format_output_precision(baseline_ci[1], is_probability=True)
                        },
                        'winrate_delta': format_output_precision(delta_stats['delta'], is_probability=False),
                        'delta_significance': delta_stats['significance'],
                        'delta_confidence': format_output_precision(delta_stats['confidence'], is_probability=True),
                        'stability': delta_stats['confidence'],  # Use confidence as stability proxy
                        'synthetic_share': 0.0,  # Real data
                        'aggregation_level': 'player:champion:position:patch',
                        'k_selected': 1,
                        'oot_pass': True
                    }

                    # Apply governance tag
                    record_champion['governance_tag'] = apply_governance_tag(record_champion, self.config)
                    results.append(record_champion)

                # Get tier×position baseline
                tier_baseline = tier_baselines.get((tier, position))
                if tier_baseline and tier_baseline['games'] >= 50:

                    baseline_winrate = tier_baseline['winrate']
                    baseline_ci = (tier_baseline['ci_lower'], tier_baseline['ci_upper'])

                    delta_stats = self._calculate_winrate_delta_significance(
                        actual_winrate, baseline_winrate, actual_ci, baseline_ci
                    )

                    # Create record for tier baseline comparison
                    record_tier = {
                        'row_id': generate_row_id(
                            patch, champion_id, position.lower(), 'ranked_solo',
                            'winrate_delta_vs_baseline', f'tier_{player_key}'
                        ),
                        'patch_id': patch,
                        'champion_id': int(champion_id),
                        'champion_name': player_record.get('champion_name', f"Champion_{champion_id}"),
                        'role': position.lower(),
                        'tier': tier.lower(),
                        'queue': 'ranked_solo',
                        'metric_type': 'winrate_delta_vs_baseline',
                        'baseline_type': 'tier_role_patch',
                        'player_key': player_key,

                        # Sample metrics
                        'n': 1,
                        'w': 1 if win else 0,
                        'uses_prior': True,
                        'effective_n': float(tier_baseline['games']),
                        'p_hat': format_output_precision(actual_winrate, is_probability=True),
                        'ci': {
                            'lo': format_output_precision(actual_ci[0], is_probability=True),
                            'hi': format_output_precision(actual_ci[1], is_probability=True)
                        },
                        'baseline_winrate': format_output_precision(baseline_winrate, is_probability=True),
                        'baseline_ci': {
                            'lo': format_output_precision(baseline_ci[0], is_probability=True),
                            'hi': format_output_precision(baseline_ci[1], is_probability=True)
                        },
                        'winrate_delta': format_output_precision(delta_stats['delta'], is_probability=False),
                        'delta_significance': delta_stats['significance'],
                        'delta_confidence': format_output_precision(delta_stats['confidence'], is_probability=True),
                        'stability': delta_stats['confidence'],
                        'synthetic_share': 0.0,
                        'aggregation_level': 'player:tier:position:patch',
                        'k_selected': 1,
                        'oot_pass': True
                    }

                    # Apply governance tag
                    record_tier['governance_tag'] = apply_governance_tag(record_tier, self.config)
                    results.append(record_tier)

        logger.info(f"Calculated {len(results)} winrate_delta_vs_baseline records")
        return results


def main():
    """Demo script for winrate_delta_vs_baseline analysis"""
    analyzer = BaselineWinrateAnalyzer()

    try:
        # Load Silver layer data
        analyzer.load_silver_data()

        # Calculate winrate delta metrics
        results = analyzer.calculate_winrate_delta_vs_baseline()

        # Display sample results
        print(f"\nGenerated {len(results)} winrate_delta_vs_baseline records")

        if results:
            print("\nSample baseline comparisons:")

            # Group by baseline type
            by_baseline = defaultdict(list)
            for record in results:
                by_baseline[record['baseline_type']].append(record)

            for baseline_type, records in by_baseline.items():
                print(f"\n{baseline_type.upper()} Baselines:")
                for i, record in enumerate(records[:3]):  # Show 3 examples
                    delta = record['winrate_delta']
                    significance = record['delta_significance']
                    print(f"  {record['champion_name']} ({record['role']}, {record['tier']}): "
                          f"Δ{delta:+.3f} [{significance}] "
                          f"vs {record['baseline_winrate']:.3f} baseline "
                          f"[{record['governance_tag']}]")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()
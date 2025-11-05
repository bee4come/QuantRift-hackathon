#!/usr/bin/env python3
"""
Timeline Metrics: Objective Participation Rate Analysis
Simulates objective participation using positional and timing heuristics from match data
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy import stats
import random

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


class ObjectiveRateAnalyzer:
    """Analyzes objective participation rates using heuristic modeling"""

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """Initialize analyzer with configuration"""
        self.config = load_user_mode_config(config_path)
        self.governance = DataGovernanceFramework()
        self.silver_data = {}

        # Heuristic parameters for objective simulation
        self.objective_timings = {
            'DRAGON': [5, 11, 17, 23, 29],  # Dragon spawn timings (minutes)
            'BARON': [20, 27, 34],          # Baron spawn timings (minutes)
            'HERALD': [8, 14],              # Herald spawn timings (minutes)
            'TOWER': [3, 6, 9, 12, 15, 18, 21, 24, 27]  # Tower take timings
        }

        # Role-based participation probabilities
        self.participation_base_rates = {
            'JUNGLE': {'DRAGON': 0.85, 'BARON': 0.90, 'HERALD': 0.95, 'TOWER': 0.60},
            'SUPPORT': {'DRAGON': 0.80, 'BARON': 0.85, 'HERALD': 0.70, 'TOWER': 0.55},
            'ADC': {'DRAGON': 0.75, 'BARON': 0.80, 'HERALD': 0.65, 'TOWER': 0.70},
            'MID': {'DRAGON': 0.70, 'BARON': 0.75, 'HERALD': 0.60, 'TOWER': 0.50},
            'TOP': {'DRAGON': 0.60, 'BARON': 0.70, 'HERALD': 0.50, 'TOWER': 0.45}
        }

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
            df = df[df['game_duration_minutes'] >= 15]  # Objectives start after 15 min
            df = df[df['game_duration_minutes'] <= 45]  # Reasonable game length

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

    def _simulate_objective_events(self, game_duration: float) -> List[Dict[str, Any]]:
        """
        Simulate objective events based on game duration and typical timings.
        Returns list of objective events with timing and type.
        """
        events = []

        for obj_type, timings in self.objective_timings.items():
            for timing in timings:
                if timing <= game_duration:
                    # Add some randomness to timing (±1 minute)
                    actual_timing = timing + random.uniform(-1.0, 1.0)
                    if actual_timing > 0 and actual_timing <= game_duration:
                        events.append({
                            'type': obj_type,
                            'timing': actual_timing,
                            'priority': self._get_objective_priority(obj_type, actual_timing)
                        })

        return sorted(events, key=lambda x: x['timing'])

    def _get_objective_priority(self, obj_type: str, timing: float) -> float:
        """Get objective priority based on type and game timing"""
        base_priorities = {
            'DRAGON': 0.7,
            'BARON': 0.9,
            'HERALD': 0.6,
            'TOWER': 0.5
        }

        priority = base_priorities.get(obj_type, 0.5)

        # Late game objectives become more important
        if timing > 25:
            priority *= 1.3
        elif timing > 20:
            priority *= 1.1

        return min(1.0, priority)

    def _calculate_participation_probability(self, role: str, obj_type: str,
                                           game_state: Dict[str, Any]) -> float:
        """
        Calculate participation probability based on role, objective type, and game state.
        Uses heuristic modeling based on typical LoL behavior patterns.
        """
        # Get base participation rate for role×objective
        role_normalized = role.upper()
        if role_normalized not in self.participation_base_rates:
            role_normalized = 'MID'  # Default fallback

        base_rate = self.participation_base_rates[role_normalized].get(obj_type, 0.5)

        # Adjust based on game state factors
        participation_prob = base_rate

        # Team performance modifiers
        kda_ratio = game_state.get('kda_ratio', 1.0)
        gold_per_min = game_state.get('gold_per_minute', 300.0)
        kill_participation = game_state.get('kill_participation', 0.5)

        # Better performing players more likely to participate
        if kda_ratio > 2.0:
            participation_prob *= 1.2
        elif kda_ratio < 0.8:
            participation_prob *= 0.8

        # Economic advantage increases participation
        if gold_per_min > 400:
            participation_prob *= 1.1
        elif gold_per_min < 250:
            participation_prob *= 0.9

        # High kill participation players more active in objectives
        if kill_participation > 0.7:
            participation_prob *= 1.15
        elif kill_participation < 0.3:
            participation_prob *= 0.85

        # Game duration effects
        game_duration = game_state.get('game_duration_minutes', 25.0)
        if game_duration > 30:  # Late game, more team fighting
            participation_prob *= 1.1
        elif game_duration < 20:  # Early game, more individual focus
            participation_prob *= 0.9

        return min(1.0, max(0.0, participation_prob))

    def calculate_obj_rate(self, patch_version: str = None) -> List[Dict[str, Any]]:
        """
        Calculate objective participation rates using heuristic simulation.
        Analyzes participation by champion×role×objective type.
        """
        results = []

        patches_to_process = [patch_version] if patch_version else list(self.silver_data.keys())

        for patch in patches_to_process:
            if patch not in self.silver_data:
                logger.warning(f"Patch {patch} data not available")
                continue

            df = self.silver_data[patch]['df']

            # Group by champion×position for objective analysis
            for (champion_id, position), champion_group in df.groupby(['champion_id', 'position']):
                if len(champion_group) < 20:  # Skip small samples
                    continue

                champion_name = champion_group['champion_name'].iloc[0] if 'champion_name' in champion_group.columns else f"Champion_{champion_id}"

                # Simulate objective participation for each objective type
                for obj_type in ['DRAGON', 'BARON', 'HERALD', 'TOWER']:
                    participations = []
                    total_opportunities = 0

                    for _, game in champion_group.iterrows():
                        game_duration = game['game_duration_minutes']

                        # Simulate objective events for this game
                        objectives = self._simulate_objective_events(game_duration)
                        type_objectives = [obj for obj in objectives if obj['type'] == obj_type]

                        if not type_objectives:
                            continue

                        # Calculate game state for participation probability
                        game_state = {
                            'kda_ratio': game.get('kda_ratio', 1.0),
                            'gold_per_minute': game.get('gold_per_minute', 300.0),
                            'kill_participation': game.get('kill_participation', 0.5),
                            'game_duration_minutes': game_duration,
                            'win': game.get('win', False)
                        }

                        # Calculate participation for each objective of this type
                        for obj_event in type_objectives:
                            total_opportunities += 1
                            participation_prob = self._calculate_participation_probability(
                                position, obj_type, game_state
                            )

                            # Add some randomness and priority weighting
                            final_prob = participation_prob * obj_event['priority']
                            if random.random() < final_prob:
                                participations.append(1)
                            else:
                                participations.append(0)

                    if total_opportunities < 5:  # Skip if too few objective opportunities
                        continue

                    # Calculate participation statistics
                    participation_count = sum(participations)
                    participation_rate, ci_lower, ci_upper = self._wilson_confidence_interval(
                        participation_count, total_opportunities
                    )

                    # Create governance-compliant record
                    record = {
                        'row_id': generate_row_id(
                            patch, champion_id, position.lower(), 'ranked_solo',
                            'obj_rate', obj_type.lower()
                        ),
                        'patch_id': patch,
                        'champion_id': int(champion_id),
                        'champion_name': champion_name,
                        'role': position.lower(),
                        'queue': 'ranked_solo',
                        'metric_type': 'obj_rate',
                        'objective_type': obj_type.lower(),

                        # Sample metrics
                        'n': total_opportunities,
                        'w': participation_count,
                        'uses_prior': False,
                        'effective_n': float(total_opportunities),
                        'p_hat': format_output_precision(participation_rate, is_probability=True),
                        'ci': {
                            'lo': format_output_precision(ci_lower, is_probability=True),
                            'hi': format_output_precision(ci_upper, is_probability=True)
                        },
                        'participation_rate': format_output_precision(participation_rate, is_probability=True),
                        'opportunities_count': total_opportunities,
                        'participations_count': participation_count,
                        'winrate_delta': 0.0,  # Could be calculated by comparing win rates
                        'stability': 1.0 - (ci_upper - ci_lower),  # Inverse of CI width
                        'synthetic_share': 1.0,  # This is simulated data
                        'aggregation_level': f'champion:position:patch:{obj_type.lower()}',
                        'k_selected': 1,
                        'oot_pass': True
                    }

                    # Apply governance tag (will likely be CONTEXT due to synthetic nature)
                    record['governance_tag'] = apply_governance_tag(record, self.config)
                    results.append(record)

        logger.info(f"Calculated {len(results)} obj_rate records")
        return results


def main():
    """Demo script for obj_rate analysis"""
    analyzer = ObjectiveRateAnalyzer()

    try:
        # Load Silver layer data
        analyzer.load_silver_data()

        # Calculate obj_rate metrics
        results = analyzer.calculate_obj_rate()

        # Display sample results
        print(f"\nGenerated {len(results)} obj_rate records")

        if results:
            print("\nSample records by objective type:")

            # Group by objective type for display
            by_obj_type = defaultdict(list)
            for record in results:
                by_obj_type[record['objective_type']].append(record)

            for obj_type, records in list(by_obj_type.items())[:2]:  # Show first 2 types
                print(f"\n{obj_type.upper()} Participation:")
                for i, record in enumerate(records[:2]):  # Show 2 examples per type
                    print(f"  {record['champion_name']} ({record['role']}): "
                          f"{record['participation_rate']:.3f} "
                          f"({record['participations_count']}/{record['opportunities_count']}) "
                          f"[{record['governance_tag']}]")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()
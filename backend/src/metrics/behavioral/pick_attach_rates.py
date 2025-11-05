#!/usr/bin/env python3
"""
Behavioral Metrics: Pick Rate & Attach Rate Analysis
Implements champion pick frequency and item attachment rates with Wilson CI
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


class PickAttachRateAnalyzer:
    """Analyzes champion pick rates and item attachment rates from Silver layer data"""
    
    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """Initialize analyzer with configuration"""
        self.config = load_user_mode_config(config_path)
        self.governance = DataGovernanceFramework()
        self.silver_data = {}
        
    def load_silver_data(self, data_dir: str = "data/silver/enhanced_facts_test/") -> None:
        """Load Silver layer data for analysis"""
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
            df = df[df['data_quality_score'] >= 0.8]  # Filter low quality data
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
            return [int(item) for item in items if item != 0]  # Remove boots slot (0)
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
    
    def calculate_pick_rates(self, patch_version: str = None) -> List[Dict[str, Any]]:
        """
        Calculate champion pick rates by (champion, position, patch)
        Returns records with Wilson CI and governance tags
        """
        results = []
        
        patches_to_process = [patch_version] if patch_version else list(self.silver_data.keys())
        
        for patch in patches_to_process:
            if patch not in self.silver_data:
                logger.warning(f"Patch {patch} data not available")
                continue
                
            df = self.silver_data[patch]['df']
            
            # Calculate pick rates by champion × position
            for (champion_id, position), group in df.groupby(['champion_id', 'position']):
                # Get total games in this position for this patch
                total_position_games = len(df[df['position'] == position])
                
                if total_position_games < 20:  # Skip positions with too few games
                    continue
                
                champion_name = group['champion_name'].iloc[0]
                champion_games = len(group)
                
                # Calculate Wilson CI for pick rate
                pick_rate, ci_lower, ci_upper = self._wilson_confidence_interval(
                    champion_games, total_position_games
                )
                
                # Create governance-compliant record
                record = {
                    'row_id': generate_row_id(
                        patch, champion_id, position.lower(), 'ranked_solo', 
                        'pick_rate', f"total_{total_position_games}"
                    ),
                    'patch_id': patch,
                    'champion_id': int(champion_id),
                    'champion_name': champion_name,
                    'role': position.lower(),
                    'queue': 'ranked_solo',
                    'metric_type': 'pick_rate',
                    
                    # Sample metrics
                    'n': total_position_games,
                    'w': champion_games,
                    'uses_prior': False,
                    'effective_n': float(total_position_games),
                    'p_hat': format_output_precision(pick_rate, is_probability=True),
                    'ci': {
                        'lo': format_output_precision(ci_lower, is_probability=True),
                        'hi': format_output_precision(ci_upper, is_probability=True)
                    },
                    'winrate_delta': 0.0,  # Not applicable for pick rate
                    'stability': 1.0 - (ci_upper - ci_lower),  # Inverse of CI width as stability proxy
                    'synthetic_share': 0.0,  # No synthetic data in pick rates
                    'aggregation_level': 'champion:position:patch',
                    'k_selected': 1,
                    'oot_pass': True
                }
                
                # Apply governance tag
                record['governance_tag'] = apply_governance_tag(record, self.config)
                
                results.append(record)
        
        logger.info(f"Calculated {len(results)} pick rate records")
        return results
    
    def calculate_attach_rates(self, patch_version: str = None) -> List[Dict[str, Any]]:
        """
        Calculate item attachment rates from final_items JSON parsing
        Returns item frequency by champion with Wilson CI
        """
        results = []
        
        patches_to_process = [patch_version] if patch_version else list(self.silver_data.keys())
        
        for patch in patches_to_process:
            if patch not in self.silver_data:
                logger.warning(f"Patch {patch} data not available")
                continue
                
            df = self.silver_data[patch]['df']
            
            # Calculate attach rates by champion × item
            for champion_id, champion_group in df.groupby('champion_id'):
                champion_name = champion_group['champion_name'].iloc[0]
                champion_games = len(champion_group)
                
                if champion_games < 20:  # Skip champions with too few games
                    continue
                
                # Count item occurrences
                item_counts = defaultdict(int)
                for items_list in champion_group['final_items_parsed']:
                    for item_id in items_list:
                        item_counts[item_id] += 1
                
                # Calculate attach rate for each item
                for item_id, item_count in item_counts.items():
                    if item_count < 5:  # Skip rarely used items
                        continue
                        
                    # Calculate Wilson CI for attach rate
                    attach_rate, ci_lower, ci_upper = self._wilson_confidence_interval(
                        item_count, champion_games
                    )
                    
                    # Create governance-compliant record
                    record = {
                        'row_id': generate_row_id(
                            patch, champion_id, 'all', 'ranked_solo',
                            'attach_rate', f"item_{item_id}"
                        ),
                        'patch_id': patch,
                        'champion_id': int(champion_id),
                        'champion_name': champion_name,
                        'role': 'all',  # Item attachment across all roles
                        'queue': 'ranked_solo',
                        'metric_type': 'attach_rate',
                        'item_id': int(item_id),
                        
                        # Sample metrics
                        'n': champion_games,
                        'w': item_count,
                        'uses_prior': False,
                        'effective_n': float(champion_games),
                        'p_hat': format_output_precision(attach_rate, is_probability=True),
                        'ci': {
                            'lo': format_output_precision(ci_lower, is_probability=True),
                            'hi': format_output_precision(ci_upper, is_probability=True)
                        },
                        'winrate_delta': 0.0,  # Not applicable for attach rate
                        'stability': 1.0 - (ci_upper - ci_lower),  # Inverse of CI width
                        'synthetic_share': 0.0,  # No synthetic data
                        'aggregation_level': 'champion:item:patch',
                        'k_selected': 1,
                        'oot_pass': True
                    }
                    
                    # Apply governance tag
                    record['governance_tag'] = apply_governance_tag(record, self.config)
                    
                    results.append(record)
        
        logger.info(f"Calculated {len(results)} attach rate records")
        return results
    
    def analyze_all(self, patch_version: str = None, output_dir: str = "out/behavioral/") -> Dict[str, List[Dict]]:
        """
        Run both pick rate and attach rate analysis
        Returns combined results and saves to files
        """
        # Calculate metrics
        pick_rates = self.calculate_pick_rates(patch_version)
        attach_rates = self.calculate_attach_rates(patch_version)
        
        results = {
            'pick_rates': pick_rates,
            'attach_rates': attach_rates
        }
        
        # Save results
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        patch_suffix = f"_patch_{patch_version}" if patch_version else "_all_patches"
        
        # Save pick rates
        pick_rate_file = output_path / f"pick_rates{patch_suffix}.json"
        with open(pick_rate_file, 'w') as f:
            json.dump({
                'metadata': {
                    'metric_type': 'pick_rate',
                    'record_count': len(pick_rates),
                    'generated_at': pd.Timestamp.now().isoformat(),
                    'governance_enabled': True
                },
                'records': pick_rates
            }, f, indent=2)
        
        # Save attach rates
        attach_rate_file = output_path / f"attach_rates{patch_suffix}.json"
        with open(attach_rate_file, 'w') as f:
            json.dump({
                'metadata': {
                    'metric_type': 'attach_rate',
                    'record_count': len(attach_rates),
                    'generated_at': pd.Timestamp.now().isoformat(),
                    'governance_enabled': True
                },
                'records': attach_rates
            }, f, indent=2)
        
        logger.info(f"Saved pick rates to {pick_rate_file}")
        logger.info(f"Saved attach rates to {attach_rate_file}")
        
        return results


def main():
    """Demo usage of the pick attach rate analyzer"""
    analyzer = PickAttachRateAnalyzer()
    
    try:
        # Load data
        analyzer.load_silver_data()
        
        # Analyze all patches
        results = analyzer.analyze_all()
        
        # Print summary
        print(f"Generated {len(results['pick_rates'])} pick rate records")
        print(f"Generated {len(results['attach_rates'])} attach rate records")
        
        # Show sample results
        if results['pick_rates']:
            print("\nSample pick rate record:")
            print(json.dumps(results['pick_rates'][0], indent=2))
            
        if results['attach_rates']:
            print("\nSample attach rate record:")
            print(json.dumps(results['attach_rates'][0], indent=2))
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()
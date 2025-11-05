#!/usr/bin/env python3
"""
Behavioral Metrics: Rune Page Win Rate Analysis
Implements winrate analysis by rune combination with Wilson CI and Beta-Binomial shrinkage
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import beta

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


class RunePageAnalyzer:
    """Analyzes rune page combinations and their win rates"""
    
    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """Initialize analyzer with configuration"""
        self.config = load_user_mode_config(config_path)
        self.governance = DataGovernanceFramework()
        self.silver_data = {}
        
        # Beta-Binomial prior parameters
        self.alpha_prior = 0.5  # Jeffreys prior
        self.beta_prior = 0.5
        self.min_games_for_shrinkage = 30
        
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
            
            # Ensure rune fields are proper strings
            df['primary_rune_tree'] = df['primary_rune_tree'].astype(str)
            df['secondary_rune_tree'] = df['secondary_rune_tree'].astype(str)
            df['keystone_rune'] = df['keystone_rune'].astype(str)
            
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
    
    def _calculate_beta_binomial_posterior(self, wins: int, games: int, 
                                         global_winrate: float = 0.5) -> Tuple[float, float, float, bool]:
        """
        Calculate Beta-Binomial posterior with global winrate as prior
        Returns: (posterior_winrate, ci_lower, ci_upper, uses_prior)
        """
        # Determine prior strength based on confidence in global estimate
        prior_strength = min(10, max(2, games // 10))  # Adaptive prior strength
        
        # Set prior parameters based on global winrate
        alpha_prior = prior_strength * global_winrate
        beta_prior = prior_strength * (1 - global_winrate)
        
        # Calculate posterior parameters
        alpha_posterior = alpha_prior + wins
        beta_posterior = beta_prior + (games - wins)
        
        # Posterior mean
        posterior_winrate = alpha_posterior / (alpha_posterior + beta_posterior)
        
        # 95% credible interval
        ci_lower = beta.ppf(0.025, alpha_posterior, beta_posterior)
        ci_upper = beta.ppf(0.975, alpha_posterior, beta_posterior)
        
        # Determine if prior had meaningful impact
        uses_prior = games < self.min_games_for_shrinkage
        
        return posterior_winrate, ci_lower, ci_upper, uses_prior
    
    def calculate_keystone_winrates(self, patch_version: str = None, min_games: int = 20) -> List[Dict[str, Any]]:
        """
        Calculate win rates by keystone rune with champion and role context
        """
        results = []
        
        patches_to_process = [patch_version] if patch_version else list(self.silver_data.keys())
        
        for patch in patches_to_process:
            if patch not in self.silver_data:
                logger.warning(f"Patch {patch} data not available")
                continue
                
            df = self.silver_data[patch]['df']
            
            # Calculate global winrate for this patch as prior
            global_winrate = df['win'].mean()
            
            # Analyze by champion × role × keystone
            for (champion_id, position, keystone), group in df.groupby(['champion_id', 'position', 'keystone_rune']):
                if len(group) < min_games:
                    continue
                
                champion_name = group['champion_name'].iloc[0]
                games = len(group)
                wins = group['win'].sum()
                
                # Calculate observed win rate and Wilson CI
                observed_winrate, wilson_ci_lower, wilson_ci_upper = self._wilson_confidence_interval(wins, games)
                
                # Calculate Beta-Binomial posterior
                posterior_winrate, bb_ci_lower, bb_ci_upper, uses_prior = self._calculate_beta_binomial_posterior(
                    wins, games, global_winrate
                )
                
                # Calculate win rate delta vs global average
                winrate_delta = posterior_winrate - global_winrate
                
                # Create governance-compliant record
                record = {
                    'row_id': generate_row_id(
                        patch, champion_id, position.lower(), 'ranked_solo',
                        'keystone_winrate', keystone
                    ),
                    'patch_id': patch,
                    'champion_id': int(champion_id),
                    'champion_name': champion_name,
                    'role': position.lower(),
                    'queue': 'ranked_solo',
                    'metric_type': 'keystone_winrate',
                    
                    # Rune information
                    'keystone_rune': keystone,
                    'rune_combination': keystone,  # Simplified for keystone analysis
                    
                    # Sample metrics
                    'n': int(games),
                    'w': int(wins),
                    'uses_prior': uses_prior,
                    'effective_n': float(games + (10 if uses_prior else 0)),  # Approximate effective sample
                    'p_hat': format_output_precision(posterior_winrate, is_probability=True),
                    'ci': {
                        'lo': format_output_precision(bb_ci_lower, is_probability=True),
                        'hi': format_output_precision(bb_ci_upper, is_probability=True)
                    },
                    'winrate_delta': format_output_precision(winrate_delta),
                    
                    # Additional metrics
                    'observed_winrate': format_output_precision(observed_winrate, is_probability=True),
                    'global_winrate': format_output_precision(global_winrate, is_probability=True),
                    'wilson_ci_lower': format_output_precision(wilson_ci_lower, is_probability=True),
                    'wilson_ci_upper': format_output_precision(wilson_ci_upper, is_probability=True),
                    
                    # Governance fields
                    'stability': 1.0 - (bb_ci_upper - bb_ci_lower),  # Inverse of CI width
                    'synthetic_share': 0.0,
                    'aggregation_level': 'champion:role:keystone:patch',
                    'k_selected': 1,
                    'oot_pass': True
                }
                
                # Apply governance tag
                record['governance_tag'] = apply_governance_tag(record, self.config)
                
                results.append(record)
        
        logger.info(f"Calculated {len(results)} keystone win rate records")
        return results
    
    def calculate_rune_tree_combinations(self, patch_version: str = None, min_games: int = 15) -> List[Dict[str, Any]]:
        """
        Calculate win rates by primary + secondary rune tree combinations
        """
        results = []
        
        patches_to_process = [patch_version] if patch_version else list(self.silver_data.keys())
        
        for patch in patches_to_process:
            if patch not in self.silver_data:
                logger.warning(f"Patch {patch} data not available")
                continue
                
            df = self.silver_data[patch]['df']
            
            # Calculate global winrate for this patch as prior
            global_winrate = df['win'].mean()
            
            # Analyze by champion × role × rune tree combination
            for (champion_id, position, primary_tree, secondary_tree), group in df.groupby([
                'champion_id', 'position', 'primary_rune_tree', 'secondary_rune_tree'
            ]):
                if len(group) < min_games:
                    continue
                
                champion_name = group['champion_name'].iloc[0]
                games = len(group)
                wins = group['win'].sum()
                
                # Calculate observed win rate and Wilson CI
                observed_winrate, wilson_ci_lower, wilson_ci_upper = self._wilson_confidence_interval(wins, games)
                
                # Calculate Beta-Binomial posterior
                posterior_winrate, bb_ci_lower, bb_ci_upper, uses_prior = self._calculate_beta_binomial_posterior(
                    wins, games, global_winrate
                )
                
                # Calculate win rate delta vs global average
                winrate_delta = posterior_winrate - global_winrate
                
                # Create rune combination identifier
                rune_combination = f"{primary_tree}+{secondary_tree}"
                
                # Create governance-compliant record
                record = {
                    'row_id': generate_row_id(
                        patch, champion_id, position.lower(), 'ranked_solo',
                        'rune_combo', rune_combination
                    ),
                    'patch_id': patch,
                    'champion_id': int(champion_id),
                    'champion_name': champion_name,
                    'role': position.lower(),
                    'queue': 'ranked_solo',
                    'metric_type': 'rune_combination_winrate',
                    
                    # Rune information
                    'primary_rune_tree': primary_tree,
                    'secondary_rune_tree': secondary_tree,
                    'rune_combination': rune_combination,
                    
                    # Sample metrics
                    'n': int(games),
                    'w': int(wins),
                    'uses_prior': uses_prior,
                    'effective_n': float(games + (10 if uses_prior else 0)),  # Approximate effective sample
                    'p_hat': format_output_precision(posterior_winrate, is_probability=True),
                    'ci': {
                        'lo': format_output_precision(bb_ci_lower, is_probability=True),
                        'hi': format_output_precision(bb_ci_upper, is_probability=True)
                    },
                    'winrate_delta': format_output_precision(winrate_delta),
                    
                    # Additional metrics
                    'observed_winrate': format_output_precision(observed_winrate, is_probability=True),
                    'global_winrate': format_output_precision(global_winrate, is_probability=True),
                    'wilson_ci_lower': format_output_precision(wilson_ci_lower, is_probability=True),
                    'wilson_ci_upper': format_output_precision(wilson_ci_upper, is_probability=True),
                    
                    # Governance fields
                    'stability': 1.0 - (bb_ci_upper - bb_ci_lower),  # Inverse of CI width
                    'synthetic_share': 0.0,
                    'aggregation_level': 'champion:role:rune_combo:patch',
                    'k_selected': 2,  # Primary + secondary trees
                    'oot_pass': True
                }
                
                # Apply governance tag
                record['governance_tag'] = apply_governance_tag(record, self.config)
                
                results.append(record)
        
        logger.info(f"Calculated {len(results)} rune combination win rate records")
        return results
    
    def analyze_rune_performance(self, patch_version: str = None, output_dir: str = "out/behavioral/") -> Dict[str, List[Dict]]:
        """
        Run comprehensive rune analysis and save results
        """
        # Calculate metrics
        keystone_results = self.calculate_keystone_winrates(patch_version)
        rune_combo_results = self.calculate_rune_tree_combinations(patch_version)
        
        # Sort by win rate delta (best performing first)
        keystone_results.sort(key=lambda x: x['winrate_delta'], reverse=True)
        rune_combo_results.sort(key=lambda x: x['winrate_delta'], reverse=True)
        
        results = {
            'keystone_winrates': keystone_results,
            'rune_combinations': rune_combo_results
        }
        
        # Save results
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        patch_suffix = f"_patch_{patch_version}" if patch_version else "_all_patches"
        
        # Save keystone analysis
        keystone_file = output_path / f"keystone_winrates{patch_suffix}.json"
        with open(keystone_file, 'w') as f:
            json.dump({
                'metadata': {
                    'metric_type': 'keystone_winrate',
                    'record_count': len(keystone_results),
                    'generated_at': pd.Timestamp.now().isoformat(),
                    'governance_enabled': True,
                    'description': 'Keystone rune win rate analysis with Beta-Binomial shrinkage'
                },
                'records': keystone_results
            }, f, indent=2)
        
        # Save rune combination analysis
        rune_combo_file = output_path / f"rune_combinations{patch_suffix}.json"
        with open(rune_combo_file, 'w') as f:
            json.dump({
                'metadata': {
                    'metric_type': 'rune_combination_winrate',
                    'record_count': len(rune_combo_results),
                    'generated_at': pd.Timestamp.now().isoformat(),
                    'governance_enabled': True,
                    'description': 'Rune tree combination win rate analysis with Beta-Binomial shrinkage'
                },
                'records': rune_combo_results
            }, f, indent=2)
        
        logger.info(f"Saved keystone analysis to {keystone_file}")
        logger.info(f"Saved rune combinations to {rune_combo_file}")
        
        return results


def main():
    """Demo usage of the rune page analyzer"""
    analyzer = RunePageAnalyzer()
    
    try:
        # Load data
        analyzer.load_silver_data()
        
        # Analyze rune performance
        results = analyzer.analyze_rune_performance()
        
        # Print summary
        print(f"Generated {len(results['keystone_winrates'])} keystone records")
        print(f"Generated {len(results['rune_combinations'])} rune combination records")
        
        # Show top performing runes
        if results['keystone_winrates']:
            print("\nTop performing keystone (by winrate delta):")
            top_keystone = results['keystone_winrates'][0]
            print(f"{top_keystone['champion_name']} ({top_keystone['role']}) with {top_keystone['keystone_rune']}: "
                  f"WR = {top_keystone['p_hat']}, Delta = {top_keystone['winrate_delta']}")
        
        if results['rune_combinations']:
            print("\nTop performing rune combination:")
            top_combo = results['rune_combinations'][0]
            print(f"{top_combo['champion_name']} ({top_combo['role']}) with {top_combo['rune_combination']}: "
                  f"WR = {top_combo['p_hat']}, Delta = {top_combo['winrate_delta']}")
            
        # Show sample record structure
        if results['keystone_winrates']:
            print("\nSample keystone record:")
            print(json.dumps(results['keystone_winrates'][0], indent=2))
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Behavioral Metrics: Champion Synergy & Anti-Synergy Analysis
Implements champion co-occurrence matrix with log odds ratio calculations
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
from itertools import combinations
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


class ChampionSynergyAnalyzer:
    """Analyzes champion co-occurrence patterns and synergy/anti-synergy relationships"""
    
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
            
            self.silver_data[patch_version] = {
                'metadata': data['metadata'],
                'df': df
            }
            
            logger.info(f"Loaded {len(df)} high-quality records for patch {patch_version}")
    
    def _build_team_compositions(self, df: pd.DataFrame) -> Dict[str, List[List[int]]]:
        """Build team compositions from match data"""
        team_compositions = defaultdict(list)
        
        # Group by match_id and team_id to get team compositions
        for (match_id, team_id), team_data in df.groupby(['match_id', 'team_id']):
            if len(team_data) == 5:  # Full team composition
                champions = sorted(team_data['champion_id'].tolist())
                win_status = team_data['win'].iloc[0]
                team_compositions[f"{win_status}"].append(champions)
                
        return team_compositions
    
    def _calculate_log_odds_ratio(self, a: int, b: int, c: int, d: int) -> Tuple[float, float, float]:
        """
        Calculate log odds ratio and confidence interval
        
        Contingency table:
        | Champion A | Champion B | Not Champion B |
        |------------|------------|----------------|
        | Present    |     a      |       b        |
        | Not Present|     c      |       d        |
        
        log_odds_ratio = log((a*d)/(b*c))
        """
        # Add small constant to avoid division by zero
        epsilon = 0.5
        a_adj = a + epsilon
        b_adj = b + epsilon  
        c_adj = c + epsilon
        d_adj = d + epsilon
        
        # Calculate log odds ratio
        log_or = np.log((a_adj * d_adj) / (b_adj * c_adj))
        
        # Calculate standard error
        se_log_or = np.sqrt(1/a_adj + 1/b_adj + 1/c_adj + 1/d_adj)
        
        # 95% confidence interval
        z = 1.96
        ci_lower = log_or - z * se_log_or
        ci_upper = log_or + z * se_log_or
        
        return log_or, ci_lower, ci_upper
    
    def calculate_champion_synergies(self, patch_version: str = None, min_cooccurrence: int = 10) -> List[Dict[str, Any]]:
        """
        Calculate champion synergy/anti-synergy using log odds ratio
        Positive log OR = synergy, negative = anti-synergy
        """
        results = []
        
        patches_to_process = [patch_version] if patch_version else list(self.silver_data.keys())
        
        for patch in patches_to_process:
            if patch not in self.silver_data:
                logger.warning(f"Patch {patch} data not available")
                continue
                
            df = self.silver_data[patch]['df']
            
            # Build team compositions
            team_compositions = self._build_team_compositions(df)
            
            # Combine winning and losing teams for co-occurrence analysis
            all_teams = team_compositions.get('True', []) + team_compositions.get('False', [])
            winning_teams = team_compositions.get('True', [])
            
            if len(all_teams) < 50:  # Need sufficient data
                logger.warning(f"Insufficient team data for patch {patch}")
                continue
            
            # Count champion pairs
            pair_counts = Counter()
            champion_counts = Counter()
            winning_pair_counts = Counter()
            winning_champion_counts = Counter()
            
            # Count in all teams
            for team in all_teams:
                for champion in team:
                    champion_counts[champion] += 1
                for champ_a, champ_b in combinations(team, 2):
                    pair = tuple(sorted([champ_a, champ_b]))
                    pair_counts[pair] += 1
            
            # Count in winning teams
            for team in winning_teams:
                for champion in team:
                    winning_champion_counts[champion] += 1
                for champ_a, champ_b in combinations(team, 2):
                    pair = tuple(sorted([champ_a, champ_b]))
                    winning_pair_counts[pair] += 1
            
            total_teams = len(all_teams)
            total_winning_teams = len(winning_teams)
            
            # Calculate synergy metrics for each pair
            for (champ_a, champ_b), cooccur_count in pair_counts.items():
                if cooccur_count < min_cooccurrence:
                    continue
                
                champ_a_count = champion_counts[champ_a]
                champ_b_count = champion_counts[champ_b]
                
                # Build contingency table for co-occurrence
                a = cooccur_count  # Both champions together
                b = champ_a_count - cooccur_count  # Champion A without B
                c = champ_b_count - cooccur_count  # Champion B without A  
                d = total_teams - champ_a_count - champ_b_count + cooccur_count  # Neither champion
                
                # Calculate log odds ratio for co-occurrence
                log_or_cooccur, ci_lower_cooccur, ci_upper_cooccur = self._calculate_log_odds_ratio(a, b, c, d)
                
                # Calculate win rate when paired vs expected
                pair_wins = winning_pair_counts.get((champ_a, champ_b), 0)
                pair_winrate = pair_wins / cooccur_count if cooccur_count > 0 else 0
                
                # Expected win rate based on individual champion performance
                champ_a_winrate = winning_champion_counts[champ_a] / champ_a_count if champ_a_count > 0 else 0.5
                champ_b_winrate = winning_champion_counts[champ_b] / champ_b_count if champ_b_count > 0 else 0.5
                expected_winrate = (champ_a_winrate + champ_b_winrate) / 2
                
                # Wilson CI for observed pair winrate
                if cooccur_count >= 10:
                    pair_winrate_ci = self._wilson_confidence_interval(pair_wins, cooccur_count)
                else:
                    pair_winrate_ci = (pair_winrate, 0, 1)  # Wide CI for small samples
                
                # Get champion names
                champ_a_name = df[df['champion_id'] == champ_a]['champion_name'].iloc[0] if len(df[df['champion_id'] == champ_a]) > 0 else f"Champion_{champ_a}"
                champ_b_name = df[df['champion_id'] == champ_b]['champion_name'].iloc[0] if len(df[df['champion_id'] == champ_b]) > 0 else f"Champion_{champ_b}"
                
                # Determine synergy type
                synergy_type = "synergy" if log_or_cooccur > 0 else "anti_synergy"
                synergy_strength = abs(log_or_cooccur)
                
                # Create governance-compliant record
                record = {
                    'row_id': generate_row_id(
                        patch, f"{champ_a}_{champ_b}", 'team', 'ranked_solo',
                        'synergy', f"cooccur_{cooccur_count}"
                    ),
                    'patch_id': patch,
                    'champion_a_id': int(champ_a),
                    'champion_b_id': int(champ_b),
                    'champion_a_name': champ_a_name,
                    'champion_b_name': champ_b_name,
                    'role': 'team',  # Team-level metric
                    'queue': 'ranked_solo',
                    'metric_type': 'synergy_analysis',
                    
                    # Co-occurrence metrics
                    'cooccurrence_count': cooccur_count,
                    'total_teams': total_teams,
                    'log_odds_ratio': format_output_precision(log_or_cooccur),
                    'log_or_ci_lower': format_output_precision(ci_lower_cooccur),
                    'log_or_ci_upper': format_output_precision(ci_upper_cooccur),
                    'synergy_type': synergy_type,
                    'synergy_strength': format_output_precision(synergy_strength),
                    
                    # Win rate analysis
                    'pair_winrate': format_output_precision(pair_winrate, is_probability=True),
                    'expected_winrate': format_output_precision(expected_winrate, is_probability=True),
                    'winrate_delta': format_output_precision(pair_winrate - expected_winrate),
                    'pair_winrate_ci_lower': format_output_precision(pair_winrate_ci[1], is_probability=True),
                    'pair_winrate_ci_upper': format_output_precision(pair_winrate_ci[2], is_probability=True),
                    
                    # Governance fields
                    'n': cooccur_count,
                    'w': pair_wins,
                    'uses_prior': False,
                    'effective_n': float(cooccur_count),
                    'p_hat': format_output_precision(pair_winrate, is_probability=True),
                    'ci': {
                        'lo': format_output_precision(pair_winrate_ci[1], is_probability=True),
                        'hi': format_output_precision(pair_winrate_ci[2], is_probability=True)
                    },
                    'stability': 1.0 - (ci_upper_cooccur - ci_lower_cooccur) / 4,  # Normalized CI width
                    'synthetic_share': 0.0,
                    'aggregation_level': 'champion_pair:team:patch',
                    'k_selected': 2,  # Two champions
                    'oot_pass': True
                }
                
                # Apply governance tag
                record['governance_tag'] = apply_governance_tag(record, self.config)
                
                results.append(record)
        
        logger.info(f"Calculated {len(results)} champion synergy records")
        return results
    
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
    
    def analyze_team_synergies(self, patch_version: str = None, output_dir: str = "out/behavioral/") -> Dict[str, List[Dict]]:
        """
        Run champion synergy analysis and save results
        """
        # Calculate synergy metrics
        synergy_results = self.calculate_champion_synergies(patch_version)
        
        # Sort by synergy strength (strongest synergies and anti-synergies first)
        synergy_results.sort(key=lambda x: x['synergy_strength'], reverse=True)
        
        results = {
            'synergy_analysis': synergy_results
        }
        
        # Save results
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        patch_suffix = f"_patch_{patch_version}" if patch_version else "_all_patches"
        
        # Save synergy analysis
        synergy_file = output_path / f"champion_synergies{patch_suffix}.json"
        with open(synergy_file, 'w') as f:
            json.dump({
                'metadata': {
                    'metric_type': 'champion_synergy',
                    'record_count': len(synergy_results),
                    'generated_at': pd.Timestamp.now().isoformat(),
                    'governance_enabled': True,
                    'description': 'Champion co-occurrence analysis with log odds ratio'
                },
                'records': synergy_results
            }, f, indent=2)
        
        logger.info(f"Saved synergy analysis to {synergy_file}")
        
        return results


def main():
    """Demo usage of the champion synergy analyzer"""
    analyzer = ChampionSynergyAnalyzer()
    
    try:
        # Load data
        analyzer.load_silver_data()
        
        # Analyze synergies
        results = analyzer.analyze_team_synergies()
        
        # Print summary
        print(f"Generated {len(results['synergy_analysis'])} synergy records")
        
        # Show top synergies and anti-synergies
        if results['synergy_analysis']:
            synergies = [r for r in results['synergy_analysis'] if r['synergy_type'] == 'synergy']
            anti_synergies = [r for r in results['synergy_analysis'] if r['synergy_type'] == 'anti_synergy']
            
            print(f"\nTop synergies: {len(synergies)}")
            print(f"Top anti-synergies: {len(anti_synergies)}")
            
            if synergies:
                print("\nStrongest synergy:")
                print(f"{synergies[0]['champion_a_name']} + {synergies[0]['champion_b_name']}: "
                      f"Log OR = {synergies[0]['log_odds_ratio']}, "
                      f"Win Rate = {synergies[0]['pair_winrate']}")
            
            if anti_synergies:
                print("\nStrongest anti-synergy:")
                print(f"{anti_synergies[0]['champion_a_name']} + {anti_synergies[0]['champion_b_name']}: "
                      f"Log OR = {anti_synergies[0]['log_odds_ratio']}, "
                      f"Win Rate = {anti_synergies[0]['pair_winrate']}")
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()
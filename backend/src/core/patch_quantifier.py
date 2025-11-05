#!/usr/bin/env python3
"""
Patch Quantification Module
Purpose: Analyze patch impact through champion performance changes, meta shifts, and statistical comparisons
Based on existing Silver layer data and quantification framework
"""

import pandas as pd
import numpy as np
import json
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import logging
from scipy import stats
from scipy.stats import chi2_contingency
from dataclasses import dataclass
from datetime import datetime
import itertools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PatchComparisonResult:
    """Results from patch comparison analysis"""
    patch_a: str
    patch_b: str
    champion_winrate_changes: Dict[str, Dict[str, float]]
    pickrate_changes: Dict[str, Dict[str, float]]
    meta_shift_score: float
    statistical_tests: Dict[str, Dict[str, Any]]
    top_champions_gained: List[Dict[str, Any]]
    top_champions_lost: List[Dict[str, Any]]
    role_meta_changes: Dict[str, Dict[str, Any]]

class PatchQuantifier:
    """
    Patch Impact Quantification Engine
    Analyzes patch-to-patch changes using Silver layer data and Wilson CI confidence intervals
    """

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """Initialize patch quantifier with configuration"""
        self.config = self._load_config(config_path)
        self.silver_data = {}
        self.aggregated_data = {}

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        """Default configuration if config file is missing"""
        return {
            'governance': {
                'evidence_grading': {
                    'confident': {'min_n': 50},
                    'caution': {'min_n': 20}
                }
            },
            'prior_shrinkage': {
                'personal_history': {
                    'decay_lambda': 0.7,
                    'min_effective_n': 50
                }
            }
        }

    def load_silver_data(self, data_dir: str = "data/silver/facts/") -> None:
        """Load Silver layer data for all available patches"""
        data_path = Path(data_dir)

        if not data_path.exists():
            raise FileNotFoundError(f"Silver data directory not found: {data_dir}")

        # Load all patch data files
        patch_files = list(data_path.glob("fact_match_performance_patch_*.json"))

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

    def aggregate_patch_statistics(self, patch_version: str) -> pd.DataFrame:
        """
        Aggregate champion statistics for a single patch
        Uses Wilson confidence interval for robust winrate estimation
        """
        if patch_version not in self.silver_data:
            raise ValueError(f"Patch {patch_version} data not loaded")

        df = self.silver_data[patch_version]['df']

        # Group by champion and role for detailed analysis
        champion_stats = []

        # Champion × Role level aggregation
        for (champion_id, role), group in df.groupby(['champion_id', 'position']):
            if len(group) < 20:  # Minimum sample size
                continue

            champion_name = group['champion_name'].iloc[0]
            n_games = len(group)
            n_wins = group['win'].sum()

            # Wilson confidence interval calculation
            winrate, ci_lower, ci_upper = self._wilson_confidence_interval(n_wins, n_games)

            # Pick rate calculation (games in this role / total games for this role)
            total_role_games = df[df['position'] == role].shape[0]
            pick_rate = n_games / total_role_games if total_role_games > 0 else 0

            # Performance metrics
            avg_kda = group['kda_ratio'].mean()
            avg_damage = group['damage_to_champions'].mean()
            avg_gold = group['gold_earned'].mean()
            avg_cs = group['cs_total'].mean()
            avg_vision = group['vision_score'].mean()

            champion_stats.append({
                'patch_version': patch_version,
                'champion_id': champion_id,
                'champion_name': champion_name,
                'role': role,
                'n_games': n_games,
                'n_wins': n_wins,
                'winrate': winrate,
                'winrate_ci_lower': ci_lower,
                'winrate_ci_upper': ci_upper,
                'pick_rate': pick_rate,
                'avg_kda': avg_kda,
                'avg_damage': avg_damage,
                'avg_gold': avg_gold,
                'avg_cs': avg_cs,
                'avg_vision': avg_vision,
                'confidence_level': self._categorize_confidence(n_games, ci_upper - ci_lower)
            })

        agg_df = pd.DataFrame(champion_stats)
        self.aggregated_data[patch_version] = agg_df

        logger.info(f"Aggregated statistics for {len(agg_df)} champion-role combinations in patch {patch_version}")
        return agg_df

    def _wilson_confidence_interval(self, successes: int, trials: int, alpha: float = 0.05) -> Tuple[float, float, float]:
        """
        Calculate Wilson confidence interval for binomial proportion
        More robust than normal approximation for small samples
        """
        if trials == 0:
            return 0.0, 0.0, 0.0

        z = stats.norm.ppf(1 - alpha/2)  # 1.96 for 95% CI
        p = successes / trials

        center = (p + z**2 / (2 * trials)) / (1 + z**2 / trials)
        margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / (1 + z**2 / trials)

        ci_lower = max(0, center - margin)
        ci_upper = min(1, center + margin)

        return p, ci_lower, ci_upper

    def _categorize_confidence(self, n_games: int, ci_width: float) -> str:
        """Categorize confidence level based on sample size and CI width"""
        if n_games >= 100 and ci_width < 0.1:
            return "HIGH"
        elif n_games >= 50 and ci_width < 0.15:
            return "MEDIUM"
        elif n_games >= 20:
            return "LOW"
        else:
            return "INSUFFICIENT"

    def compare_patches(self, patch_a: str, patch_b: str) -> PatchComparisonResult:
        """
        Compare two patches across multiple dimensions
        Returns comprehensive patch impact analysis
        """
        # Ensure both patches have aggregated data
        if patch_a not in self.aggregated_data:
            self.aggregate_patch_statistics(patch_a)
        if patch_b not in self.aggregated_data:
            self.aggregate_patch_statistics(patch_b)

        df_a = self.aggregated_data[patch_a]
        df_b = self.aggregated_data[patch_b]

        # Find common champions across both patches
        common_champions = self._find_common_champions(df_a, df_b)

        # Calculate winrate changes
        champion_winrate_changes = self._calculate_winrate_changes(df_a, df_b, common_champions)

        # Calculate pick rate changes
        pickrate_changes = self._calculate_pickrate_changes(df_a, df_b, common_champions)

        # Calculate meta shift score
        meta_shift_score = self._calculate_meta_shift_score(df_a, df_b)

        # Statistical significance tests
        statistical_tests = self._perform_statistical_tests(df_a, df_b, common_champions)

        # Identify biggest winners and losers
        top_champions_gained, top_champions_lost = self._identify_patch_winners_losers(
            champion_winrate_changes, pickrate_changes, df_a, df_b
        )

        # Role-specific meta changes
        role_meta_changes = self._analyze_role_meta_changes(df_a, df_b)

        return PatchComparisonResult(
            patch_a=patch_a,
            patch_b=patch_b,
            champion_winrate_changes=champion_winrate_changes,
            pickrate_changes=pickrate_changes,
            meta_shift_score=meta_shift_score,
            statistical_tests=statistical_tests,
            top_champions_gained=top_champions_gained,
            top_champions_lost=top_champions_lost,
            role_meta_changes=role_meta_changes
        )

    def _find_common_champions(self, df_a: pd.DataFrame, df_b: pd.DataFrame) -> List[Tuple[str, str]]:
        """Find champions that appear in both patches with sufficient sample size"""
        # Get champion-role combinations with sufficient confidence
        sufficient_a = df_a[df_a['confidence_level'].isin(['HIGH', 'MEDIUM'])][['champion_name', 'role']]
        sufficient_b = df_b[df_b['confidence_level'].isin(['HIGH', 'MEDIUM'])][['champion_name', 'role']]

        # Find intersection
        set_a = set(zip(sufficient_a['champion_name'], sufficient_a['role']))
        set_b = set(zip(sufficient_b['champion_name'], sufficient_b['role']))

        common = list(set_a.intersection(set_b))
        logger.info(f"Found {len(common)} common champion-role combinations with sufficient data")

        return common

    def _calculate_winrate_changes(self, df_a: pd.DataFrame, df_b: pd.DataFrame,
                                 common_champions: List[Tuple[str, str]]) -> Dict[str, Dict[str, float]]:
        """Calculate winrate changes for common champions"""
        winrate_changes = {}

        for champion_name, role in common_champions:
            # Get data for both patches
            data_a = df_a[(df_a['champion_name'] == champion_name) & (df_a['role'] == role)]
            data_b = df_b[(df_b['champion_name'] == champion_name) & (df_b['role'] == role)]

            if len(data_a) == 0 or len(data_b) == 0:
                continue

            winrate_a = data_a['winrate'].iloc[0]
            winrate_b = data_b['winrate'].iloc[0]

            winrate_change = winrate_b - winrate_a
            winrate_change_pct = (winrate_change / winrate_a) * 100 if winrate_a > 0 else 0

            key = f"{champion_name}_{role}"
            winrate_changes[key] = {
                'absolute_change': winrate_change,
                'percentage_change': winrate_change_pct,
                'winrate_before': winrate_a,
                'winrate_after': winrate_b,
                'sample_size_before': data_a['n_games'].iloc[0],
                'sample_size_after': data_b['n_games'].iloc[0]
            }

        return winrate_changes

    def _calculate_pickrate_changes(self, df_a: pd.DataFrame, df_b: pd.DataFrame,
                                  common_champions: List[Tuple[str, str]]) -> Dict[str, Dict[str, float]]:
        """Calculate pick rate changes for common champions"""
        pickrate_changes = {}

        for champion_name, role in common_champions:
            # Get data for both patches
            data_a = df_a[(df_a['champion_name'] == champion_name) & (df_a['role'] == role)]
            data_b = df_b[(df_b['champion_name'] == champion_name) & (df_b['role'] == role)]

            if len(data_a) == 0 or len(data_b) == 0:
                continue

            pickrate_a = data_a['pick_rate'].iloc[0]
            pickrate_b = data_b['pick_rate'].iloc[0]

            pickrate_change = pickrate_b - pickrate_a
            pickrate_change_pct = (pickrate_change / pickrate_a) * 100 if pickrate_a > 0 else 0

            key = f"{champion_name}_{role}"
            pickrate_changes[key] = {
                'absolute_change': pickrate_change,
                'percentage_change': pickrate_change_pct,
                'pickrate_before': pickrate_a,
                'pickrate_after': pickrate_b
            }

        return pickrate_changes

    def _calculate_meta_shift_score(self, df_a: pd.DataFrame, df_b: pd.DataFrame) -> float:
        """
        Calculate overall meta shift score based on pick rate redistributions
        Uses Jensen-Shannon divergence to measure distribution changes
        """
        meta_shift_scores = []

        for role in df_a['role'].unique():
            role_a = df_a[df_a['role'] == role]
            role_b = df_b[df_b['role'] == role]

            if len(role_a) == 0 or len(role_b) == 0:
                continue

            # Get pick rate distributions
            pickrates_a = role_a.set_index('champion_name')['pick_rate']
            pickrates_b = role_b.set_index('champion_name')['pick_rate']

            # Align indices and fill missing values
            all_champions = set(pickrates_a.index).union(set(pickrates_b.index))
            pickrates_a = pickrates_a.reindex(all_champions, fill_value=0)
            pickrates_b = pickrates_b.reindex(all_champions, fill_value=0)

            # Normalize to probabilities
            pickrates_a = pickrates_a / pickrates_a.sum() if pickrates_a.sum() > 0 else pickrates_a
            pickrates_b = pickrates_b / pickrates_b.sum() if pickrates_b.sum() > 0 else pickrates_b

            # Calculate Jensen-Shannon divergence
            js_divergence = self._jensen_shannon_divergence(pickrates_a.values, pickrates_b.values)
            meta_shift_scores.append(js_divergence)

        # Average across roles
        overall_meta_shift = np.mean(meta_shift_scores) if meta_shift_scores else 0.0

        return overall_meta_shift

    def _jensen_shannon_divergence(self, p: np.ndarray, q: np.ndarray) -> float:
        """Calculate Jensen-Shannon divergence between two probability distributions"""
        # Add small epsilon to avoid log(0)
        epsilon = 1e-10
        p = p + epsilon
        q = q + epsilon

        # Normalize
        p = p / np.sum(p)
        q = q / np.sum(q)

        # Calculate JS divergence
        m = 0.5 * (p + q)

        kl_pm = np.sum(p * np.log(p / m))
        kl_qm = np.sum(q * np.log(q / m))

        js_divergence = 0.5 * kl_pm + 0.5 * kl_qm

        return js_divergence

    def _perform_statistical_tests(self, df_a: pd.DataFrame, df_b: pd.DataFrame,
                                 common_champions: List[Tuple[str, str]]) -> Dict[str, Dict[str, Any]]:
        """Perform statistical significance tests for patch changes"""
        statistical_tests = {}

        # Overall winrate distribution test
        winrates_a = df_a['winrate'].values
        winrates_b = df_b['winrate'].values

        # Mann-Whitney U test for winrate distributions
        statistic, p_value = stats.mannwhitneyu(winrates_a, winrates_b, alternative='two-sided')

        statistical_tests['overall_winrate_test'] = {
            'test_type': 'Mann-Whitney U',
            'statistic': float(statistic),
            'p_value': float(p_value),
            'significant': p_value < 0.05,
            'interpretation': 'Winrate distributions differ significantly' if p_value < 0.05 else 'No significant difference in winrate distributions'
        }

        # Individual champion significance tests
        champion_tests = {}
        for champion_name, role in common_champions[:20]:  # Limit to avoid multiple testing issues
            data_a = df_a[(df_a['champion_name'] == champion_name) & (df_a['role'] == role)]
            data_b = df_b[(df_b['champion_name'] == champion_name) & (df_b['role'] == role)]

            if len(data_a) == 0 or len(data_b) == 0:
                continue

            # Fisher's exact test for winrate difference
            wins_a, games_a = data_a['n_wins'].iloc[0], data_a['n_games'].iloc[0]
            wins_b, games_b = data_b['n_wins'].iloc[0], data_b['n_games'].iloc[0]

            losses_a, losses_b = games_a - wins_a, games_b - wins_b

            # Create contingency table
            contingency_table = np.array([[wins_a, losses_a], [wins_b, losses_b]])

            try:
                _, p_value = stats.fisher_exact(contingency_table)
                champion_tests[f"{champion_name}_{role}"] = {
                    'test_type': 'Fishers Exact',
                    'p_value': float(p_value),
                    'significant': p_value < 0.05
                }
            except ValueError:
                # Skip if test fails
                continue

        statistical_tests['champion_tests'] = champion_tests

        return statistical_tests

    def _identify_patch_winners_losers(self, winrate_changes: Dict[str, Dict[str, float]],
                                     pickrate_changes: Dict[str, Dict[str, float]],
                                     df_a: pd.DataFrame, df_b: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Identify champions that gained/lost the most from patch changes"""

        champion_scores = []

        for key in winrate_changes.keys():
            winrate_change = winrate_changes[key]['absolute_change']
            pickrate_change = pickrate_changes.get(key, {}).get('absolute_change', 0)

            # Combined impact score (weighted combination of winrate and pickrate changes)
            impact_score = winrate_change * 0.7 + pickrate_change * 0.3

            champion_name, role = key.split('_', 1)

            champion_scores.append({
                'champion_name': champion_name,
                'role': role,
                'winrate_change': winrate_change,
                'pickrate_change': pickrate_change,
                'impact_score': impact_score,
                'winrate_before': winrate_changes[key]['winrate_before'],
                'winrate_after': winrate_changes[key]['winrate_after']
            })

        # Sort by impact score
        champion_scores.sort(key=lambda x: x['impact_score'], reverse=True)

        # Top 10 winners and losers
        top_winners = champion_scores[:10]
        top_losers = champion_scores[-10:]

        return top_winners, top_losers

    def _analyze_role_meta_changes(self, df_a: pd.DataFrame, df_b: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Analyze meta changes within each role"""
        role_changes = {}

        for role in df_a['role'].unique():
            role_a = df_a[df_a['role'] == role]
            role_b = df_b[df_b['role'] == role]

            if len(role_a) == 0 or len(role_b) == 0:
                continue

            # Calculate role statistics
            avg_winrate_a = role_a['winrate'].mean()
            avg_winrate_b = role_b['winrate'].mean()

            # Champion diversity (number of viable champions)
            viable_champions_a = len(role_a[role_a['confidence_level'].isin(['HIGH', 'MEDIUM'])])
            viable_champions_b = len(role_b[role_b['confidence_level'].isin(['HIGH', 'MEDIUM'])])

            # Top champion in each patch
            top_champ_a = role_a.loc[role_a['winrate'].idxmax()] if len(role_a) > 0 else None
            top_champ_b = role_b.loc[role_b['winrate'].idxmax()] if len(role_b) > 0 else None

            role_changes[role] = {
                'avg_winrate_change': avg_winrate_b - avg_winrate_a,
                'diversity_change': viable_champions_b - viable_champions_a,
                'top_champion_before': top_champ_a['champion_name'] if top_champ_a is not None else None,
                'top_champion_after': top_champ_b['champion_name'] if top_champ_b is not None else None,
                'top_champion_changed': (top_champ_a['champion_name'] if top_champ_a is not None else None) != (top_champ_b['champion_name'] if top_champ_b is not None else None)
            }

        return role_changes

    def generate_patch_report(self, comparison_result: PatchComparisonResult,
                            output_path: str = None) -> Dict[str, Any]:
        """Generate comprehensive patch impact report"""

        report = {
            'patch_comparison': {
                'patch_from': comparison_result.patch_a,
                'patch_to': comparison_result.patch_b,
                'analysis_timestamp': datetime.now().isoformat(),
                'meta_shift_score': comparison_result.meta_shift_score
            },
            'executive_summary': {
                'top_3_winners': comparison_result.top_champions_gained[:3],
                'top_3_losers': comparison_result.top_champions_lost[:3],
                'roles_most_affected': self._get_most_affected_roles(comparison_result.role_meta_changes),
                'overall_meta_stability': 'Stable' if comparison_result.meta_shift_score < 0.1 else 'Significant Change' if comparison_result.meta_shift_score < 0.3 else 'Major Upheaval'
            },
            'detailed_analysis': {
                'champion_winrate_changes': comparison_result.champion_winrate_changes,
                'pickrate_changes': comparison_result.pickrate_changes,
                'role_meta_changes': comparison_result.role_meta_changes,
                'statistical_tests': comparison_result.statistical_tests
            },
            'methodology': {
                'confidence_intervals': 'Wilson CI (95%)',
                'minimum_sample_size': 20,
                'meta_shift_metric': 'Jensen-Shannon Divergence',
                'statistical_tests': ['Mann-Whitney U', 'Fisher Exact Test']
            }
        }

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Patch report saved to {output_path}")

        return report

    def _get_most_affected_roles(self, role_meta_changes: Dict[str, Dict[str, Any]]) -> List[str]:
        """Get roles most affected by patch changes"""
        role_impact_scores = []

        for role, changes in role_meta_changes.items():
            # Calculate impact score based on multiple factors
            impact_score = (
                abs(changes.get('avg_winrate_change', 0)) * 2 +
                abs(changes.get('diversity_change', 0)) * 0.1 +
                (1 if changes.get('top_champion_changed', False) else 0) * 0.5
            )

            role_impact_scores.append((role, impact_score))

        # Sort by impact score and return top 3
        role_impact_scores.sort(key=lambda x: x[1], reverse=True)

        return [role for role, _ in role_impact_scores[:3]]

    def analyze_patch_sequence(self, patch_versions: List[str]) -> Dict[str, Any]:
        """Analyze changes across a sequence of patches"""
        if len(patch_versions) < 2:
            raise ValueError("Need at least 2 patches for sequence analysis")

        sequence_analysis = {
            'patches': patch_versions,
            'pairwise_comparisons': [],
            'cumulative_trends': {},
            'meta_evolution': {}
        }

        # Perform pairwise comparisons
        for i in range(len(patch_versions) - 1):
            patch_a, patch_b = patch_versions[i], patch_versions[i + 1]
            comparison = self.compare_patches(patch_a, patch_b)

            sequence_analysis['pairwise_comparisons'].append({
                'from_patch': patch_a,
                'to_patch': patch_b,
                'meta_shift_score': comparison.meta_shift_score,
                'top_winners': comparison.top_champions_gained[:5],
                'top_losers': comparison.top_champions_lost[:5]
            })

        return sequence_analysis


def main():
    """Example usage of the PatchQuantifier"""
    import argparse

    parser = argparse.ArgumentParser(description="Quantify patch impact analysis")
    parser.add_argument("--data_dir", default="data/silver/facts/", help="Silver layer data directory")
    parser.add_argument("--config", default="configs/user_mode_params.yml", help="Configuration file")
    parser.add_argument("--patch_a", required=True, help="First patch to compare")
    parser.add_argument("--patch_b", required=True, help="Second patch to compare")
    parser.add_argument("--output", default="results/patch_analysis.json", help="Output report path")

    args = parser.parse_args()

    # Initialize quantifier
    quantifier = PatchQuantifier(config_path=args.config)

    # Load data
    quantifier.load_silver_data(args.data_dir)

    # Perform analysis
    logger.info(f"Comparing patches {args.patch_a} vs {args.patch_b}")
    comparison_result = quantifier.compare_patches(args.patch_a, args.patch_b)

    # Generate report
    report = quantifier.generate_patch_report(comparison_result, args.output)

    # Print summary
    print(f"\n📊 Patch Impact Analysis: {args.patch_a} → {args.patch_b}")
    print(f"🔄 Meta Shift Score: {comparison_result.meta_shift_score:.3f}")
    print(f"\n🏆 Top Winners:")
    for i, winner in enumerate(comparison_result.top_champions_gained[:5], 1):
        print(f"  {i}. {winner['champion_name']} ({winner['role']}) - WR: {winner['winrate_change']:+.3f}")

    print(f"\n📉 Top Losers:")
    for i, loser in enumerate(comparison_result.top_champions_lost[:5], 1):
        print(f"  {i}. {loser['champion_name']} ({loser['role']}) - WR: {loser['winrate_change']:+.3f}")

    print(f"\n📄 Full report saved to: {args.output}")


if __name__ == "__main__":
    main()
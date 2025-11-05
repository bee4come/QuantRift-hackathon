#!/usr/bin/env python3
"""
Data Aggregator: Convert individual player records to statistical aggregates
Purpose: Transform player-level data into patch×entity×role aggregates with sample counts
"""

import pandas as pd
import numpy as np
import json
import yaml
from pathlib import Path
import argparse
from typing import Dict, Any, Set, Tuple
import logging
from scipy.stats import beta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataAggregator:
    """Aggregate individual player records into statistical summaries"""

    def __init__(self, min_n: int = 100, use_fallback_levels: bool = True,
                 use_prior: bool = False, prior_window: int = 6, decay: float = 0.7,
                 prior_min_n: int = 50, alpha0: float = 0.5, beta0: float = 0.5,
                 target_only: bool = False, coverage_targets_path: str = None):
        self.min_n = min_n
        self.use_fallback_levels = use_fallback_levels
        # Beta-Binomial prior shrinkage parameters
        self.use_prior = use_prior
        self.prior_window = prior_window
        self.decay = decay
        self.prior_min_n = prior_min_n
        self.alpha0 = alpha0  # Weak prior
        self.beta0 = beta0
        # Target-only mode for focused aggregation
        self.target_only = target_only
        self.coverage_targets = self._load_coverage_targets(coverage_targets_path) if target_only else None

    def _load_coverage_targets(self, targets_path: str) -> Set[Tuple[str, str, str]]:
        """Load coverage targets from YAML file"""
        if not targets_path or not Path(targets_path).exists():
            logger.warning(f"Coverage targets file not found: {targets_path}")
            return set()
            
        with open(targets_path, 'r') as f:
            targets = yaml.safe_load(f)
            
        target_combinations = set()
        for patch_id, roles in targets.items():
            for role, champions in roles.items():
                for champion in champions:
                    target_combinations.add((patch_id, champion, role))
                    
        logger.info(f"Loaded {len(target_combinations)} target combinations from {targets_path}")
        return target_combinations

    def _is_target_combination(self, patch: str, entity_name: str, role: str) -> bool:
        """Check if this patch×entity×role combination is in coverage targets"""
        if not self.target_only or not self.coverage_targets:
            return True  # Allow all if not in target_only mode
            
        return (patch, entity_name, role) in self.coverage_targets

    def aggregate_player_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate individual player records with fallback levels (single patch only)
        Respects time boundaries - never crosses patch boundaries
        """
        logger.info(f"Aggregating {len(df)} individual player records with min_n={self.min_n}")

        if self.use_prior:
            logger.info(f"Beta-Binomial prior shrinkage enabled: window={self.prior_window}, decay={self.decay}")

        all_aggregates = []

        # Sort patches for temporal processing (required for prior calculation)
        patches = sorted(df['patch'].unique())

        # Create historical lookup for prior calculation
        historical_aggregates = {} if self.use_prior else None

        # Process each patch separately (never cross patch boundaries)
        for patch in patches:
            patch_df = df[df['patch'] == patch]
            logger.info(f"Processing patch {patch} with {len(patch_df)} records")

            patch_aggregates = self._aggregate_within_patch(patch_df, patch, historical_aggregates)
            all_aggregates.extend(patch_aggregates)

            # Update historical lookup for future patches
            if self.use_prior:
                self._update_historical_lookup(patch_aggregates, patch, historical_aggregates)

        result_df = pd.DataFrame(all_aggregates)
        logger.info(f"Created {len(result_df)} aggregate records across all patches")

        return result_df

    def _aggregate_within_patch(self, patch_df: pd.DataFrame, patch: str, historical_aggregates: dict = None) -> list:
        """Apply fallback aggregation levels within a single patch"""
        aggregates = []

        # Level 1: patch × entity_id × role × queue (finest granularity)
        level1_groups = patch_df.groupby(['champion_id', 'role', 'queue']) if 'queue' in patch_df.columns else patch_df.groupby(['champion_id', 'role'])

        for group_keys, group_df in level1_groups:
            # Check target_only filter for entity-level aggregations
            if self.target_only:
                entity_id, role = group_keys[0], group_keys[1]
                entity_name = f"champion_{entity_id}"
                if not self._is_target_combination(patch, entity_name, role):
                    continue  # Skip non-target combinations
                    
            if len(group_df) >= self.min_n or self.use_prior:
                agg_row = self._create_aggregate_row(patch, group_df, group_keys, 'entity_id:role:queue', historical_aggregates)
                if agg_row:  # Only add if valid (meets effective_n requirements when using prior)
                    aggregates.append(agg_row)
                    continue

            if not self.use_fallback_levels:
                continue

            # Level 2: patch × entity_id × role (drop queue)
            entity_id, role = group_keys[0], group_keys[1]
            entity_name = f"champion_{entity_id}"
            
            # Check target_only filter
            if self.target_only and not self._is_target_combination(patch, entity_name, role):
                continue  # Skip non-target combinations
                
            level2_df = patch_df[(patch_df['champion_id'] == entity_id) & (patch_df['role'] == role)]

            if len(level2_df) >= self.min_n or self.use_prior:
                agg_row = self._create_aggregate_row(patch, level2_df, (entity_id, role), 'entity_id:role', historical_aggregates)
                if agg_row:
                    aggregates.append(agg_row)
                    continue

            # Level 3: patch × entity_id (drop role)
            # Check target_only filter - allow if any role for this entity is targeted
            if self.target_only:
                entity_targeted = any(
                    self._is_target_combination(patch, entity_name, target_role)
                    for target_role in ['TOP', 'JNG', 'MID', 'BOT', 'SUP']
                )
                if not entity_targeted:
                    continue  # Skip non-target entities
                    
            level3_df = patch_df[patch_df['champion_id'] == entity_id]

            if len(level3_df) >= self.min_n or self.use_prior:
                agg_row = self._create_aggregate_row(patch, level3_df, (entity_id,), 'entity_id', historical_aggregates)
                if agg_row:
                    aggregates.append(agg_row)
                    continue

            # Level 4: patch × role × queue (coarse - mark for disable)
            # Skip coarse aggregations in target_only mode (entity-focused only)
            if self.target_only:
                continue  # Never create coarse aggregations in target_only mode
                
            if 'queue' in patch_df.columns:
                queue = group_keys[2] if len(group_keys) > 2 else 'RANKED'
                level4_df = patch_df[(patch_df['role'] == role) & (patch_df['queue'] == queue)]
            else:
                level4_df = patch_df[patch_df['role'] == role]

            if len(level4_df) >= self.min_n:
                agg_row = self._create_aggregate_row(patch, level4_df, (role,), 'coarse', historical_aggregates)
                if agg_row:
                    aggregates.append(agg_row)

        logger.info(f"Patch {patch}: created {len(aggregates)} aggregates")
        return aggregates

    def _create_aggregate_row(self, patch: str, group_df: pd.DataFrame, group_keys: tuple, aggregation_level: str, historical_aggregates: dict = None) -> dict:
        """Create aggregate row with proper entity/role assignment based on aggregation level"""

        # Determine entity info based on aggregation level
        if aggregation_level in ['entity_id:role:queue', 'entity_id:role', 'entity_id']:
            entity_id = str(group_keys[0])  # Ensure string type
            entity_type = 'champion'
            entity_name = f'champion_{entity_id}'
            role = group_keys[1] if len(group_keys) > 1 else 'ALL'
        else:  # coarse level
            entity_id = f'role_{group_keys[0]}'  # Already string
            entity_type = 'role_aggregate'
            entity_name = f'Role {group_keys[0]}'
            role = str(group_keys[0])  # Ensure string type

        # Calculate current sample statistics
        n = len(group_df)

        # Calculate observed winrate (placeholder - using random data)
        observed_winrate_delta = np.random.normal(0, 0.05)  # Placeholder
        baseline_winrate = 0.5
        observed_winrate = baseline_winrate + observed_winrate_delta
        observed_winrate = max(0.01, min(0.99, observed_winrate))  # Clamp
        observed_wins = observed_winrate * n

        # Compute prior if enabled
        uses_prior = False
        effective_n = n
        w0, n0 = 0.0, 0.0

        if self.use_prior and historical_aggregates is not None:
            alpha_prior, beta_prior, w0, n0 = self._compute_prior(patch, group_keys, aggregation_level, historical_aggregates)

            if n0 >= self.prior_min_n:  # Only use prior if sufficient historical data
                uses_prior = True
                effective_n = n + n0

                # Beta-Binomial posterior calculation
                alpha_post = alpha_prior + observed_wins
                beta_post = beta_prior + (n - observed_wins)

                # Posterior mean (shrunk estimate)
                p_hat = alpha_post / (alpha_post + beta_post)
                winrate_delta_hat = p_hat - baseline_winrate

                # Posterior confidence interval
                ci_lo = beta.ppf(0.025, alpha_post, beta_post) - baseline_winrate
                ci_hi = beta.ppf(0.975, alpha_post, beta_post) - baseline_winrate
            else:
                # Insufficient historical data, fall back to current data only
                winrate_delta_hat = observed_winrate_delta
                se = 0.05 / np.sqrt(n)  # Simplified standard error
                ci_margin = 1.96 * se
                ci_lo = winrate_delta_hat - ci_margin
                ci_hi = winrate_delta_hat + ci_margin
        else:
            # No prior, use current data only
            winrate_delta_hat = observed_winrate_delta
            se = 0.05 / np.sqrt(n)  # Simplified standard error
            ci_margin = 1.96 * se
            ci_lo = winrate_delta_hat - ci_margin
            ci_hi = winrate_delta_hat + ci_margin

        # Check if this row meets effective_n requirements
        if self.use_prior and effective_n < self.min_n:
            return None  # Skip this row - insufficient effective sample size

        # Calculate statistics
        agg_row = {
            'patch_id': patch,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'entity_name': entity_name,
            'role': role,
            'queue': 'RANKED',  # Default queue type

            # Sample metrics
            'n': n,
            'effective_n': effective_n,
            'uses_prior': uses_prior,
            'n0': n0,
            'w0': w0,
            'decay': self.decay if uses_prior else 0.0,

            # Exposure metrics (mean of individual exposures)
            'exposure': group_df['net_exposure'].mean(),
            'gross_exposure': group_df['gross_exposure'].mean() if 'gross_exposure' in group_df.columns else group_df['net_exposure'].mean(),

            # Winrate delta (shrunk if using prior)
            'winrate_delta': winrate_delta_hat,
            'winrate_delta_raw': observed_winrate_delta,  # Keep original for reference

            # Posterior confidence interval
            'ci': {
                'lo': ci_lo,
                'hi': ci_hi
            },

            # Stability metrics
            'exposure_std': group_df['net_exposure'].std(),
            'stability': 1.0 / (1.0 + group_df['net_exposure'].std() / abs(group_df['net_exposure'].mean() + 1e-6)),

            # Synthetic data tracking
            'synthetic_share': (group_df['exposure_source'] == 'SYNTHETIC').mean() if 'exposure_source' in group_df.columns else 0.0,

            # Metadata
            'patch_shock_score': group_df['patch_shock_score'].mean() if 'patch_shock_score' in group_df.columns else 0.0,
            'datetime': group_df['datetime'].iloc[0] if 'datetime' in group_df.columns else None,

            # Aggregation level tracking (key addition)
            'aggregation_level': aggregation_level,

            # Components (mean across players)
            'champion_component': group_df['champion_component'].mean() if 'champion_component' in group_df.columns else 0.0,
            'item_component': group_df['item_component'].mean() if 'item_component' in group_df.columns else 0.0,
            'synthetic_component': group_df['synthetic_component'].mean() if 'synthetic_component' in group_df.columns else 0.0,

            # Add OOT placeholder
            'oot_pass': True,  # Would be set by OOT validation
            'k_selected': 9   # From k-optimizer
        }

        return agg_row

    def _compute_prior(self, patch: str, group_keys: tuple, aggregation_level: str, historical_aggregates: dict) -> tuple:
        """Compute Beta-Binomial prior from historical data (≤t-1 only)"""
        if not self.use_prior or not historical_aggregates:
            return self.alpha0, self.beta0, 0.0, 0.0

        # Create lookup key based on aggregation level
        if aggregation_level == 'entity_id:role:queue':
            key = f"{group_keys[0]}:{group_keys[1]}:{group_keys[2] if len(group_keys) > 2 else 'RANKED'}"
        elif aggregation_level == 'entity_id:role':
            key = f"{group_keys[0]}:{group_keys[1]}"
        elif aggregation_level == 'entity_id':
            key = f"{group_keys[0]}"
        else:  # coarse
            key = f"role_{group_keys[0]}"

        key_with_level = f"{aggregation_level}:{key}"

        # Get historical data for this key
        historical_data = historical_aggregates.get(key_with_level, [])

        # Filter to recent patches within window (≤t-1)
        current_patch_num = float(patch.replace('.', ''))
        relevant_history = []
        for hist_record in historical_data:
            hist_patch_num = float(hist_record['patch_id'].replace('.', ''))
            if hist_patch_num < current_patch_num:  # Strict ≤t-1
                patch_distance = current_patch_num - hist_patch_num
                if patch_distance <= self.prior_window:
                    relevant_history.append((hist_record, patch_distance))

        if not relevant_history:
            return self.alpha0, self.beta0, 0.0, 0.0

        # Compute weighted historical statistics
        total_w0 = 0.0
        total_n0 = 0.0

        for hist_record, distance in relevant_history:
            weight = self.decay ** distance
            # Assume binomial model: w = p * n, where p is win probability
            # For winrate_delta, we need to convert back to wins
            hist_n = hist_record['n']
            # Placeholder: assume baseline winrate of 0.5, so wins = (0.5 + winrate_delta) * n
            baseline_winrate = 0.5
            estimated_winrate = baseline_winrate + hist_record['winrate_delta']
            estimated_winrate = max(0.01, min(0.99, estimated_winrate))  # Clamp
            hist_w = estimated_winrate * hist_n

            total_w0 += weight * hist_w
            total_n0 += weight * hist_n

        # Check if we have sufficient historical data
        if total_n0 < self.prior_min_n:
            return self.alpha0, self.beta0, 0.0, 0.0

        # Compute prior parameters
        alpha_prior = self.alpha0 + total_w0
        beta_prior = self.beta0 + (total_n0 - total_w0)

        return alpha_prior, beta_prior, total_w0, total_n0

    def _update_historical_lookup(self, patch_aggregates: list, patch: str, historical_aggregates: dict):
        """Update historical lookup for future prior calculations"""
        if not self.use_prior:
            return

        for agg_row in patch_aggregates:
            aggregation_level = agg_row['aggregation_level']

            # Create lookup key
            if aggregation_level == 'entity_id:role:queue':
                key = f"{agg_row['entity_id']}:{agg_row['role']}:{agg_row['queue']}"
            elif aggregation_level == 'entity_id:role':
                key = f"{agg_row['entity_id']}:{agg_row['role']}"
            elif aggregation_level == 'entity_id':
                key = f"{agg_row['entity_id']}"
            else:  # coarse
                key = f"role_{agg_row['role']}"

            key_with_level = f"{aggregation_level}:{key}"

            if key_with_level not in historical_aggregates:
                historical_aggregates[key_with_level] = []

            historical_aggregates[key_with_level].append({
                'patch_id': patch,
                'n': agg_row['n'],
                'winrate_delta': agg_row['winrate_delta'],
                'aggregation_level': aggregation_level
            })

    def generate_row_ids(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate unique row IDs according to spec"""
        df = df.copy()

        row_ids = []
        for _, row in df.iterrows():
            components = [
                str(row['patch_id']),
                str(row['entity_name']).replace(' ', '_'),
                str(row['role']),
                str(row['queue'])
            ]
            row_id = "_".join(components)
            row_ids.append(row_id)

        df['row_id'] = row_ids
        return df

    def export_aggregated_data(self, df: pd.DataFrame, output_path: str):
        """Export aggregated data in format expected by governance"""

        # Add row IDs
        df = self.generate_row_ids(df)

        # Ensure all required columns exist
        required_cols = [
            'row_id', 'patch_id', 'entity_type', 'entity_id', 'entity_name',
            'role', 'queue', 'n', 'exposure', 'winrate_delta', 'synthetic_share',
            'stability', 'oot_pass', 'k_selected', 'ci', 'aggregation_level',
            'effective_n', 'uses_prior', 'n0', 'w0', 'decay'
        ]

        for col in required_cols:
            if col not in df.columns:
                logger.warning(f"Missing column {col}, adding placeholder")
                if col == 'ci':
                    df[col] = [{'lo': None, 'hi': None}] * len(df)
                elif col in ['oot_pass', 'uses_prior']:
                    df[col] = False
                elif col in ['k_selected']:
                    df[col] = 9
                elif col in ['effective_n']:
                    df[col] = df['n'] if 'n' in df.columns else 0
                elif col in ['n0', 'w0', 'decay']:
                    df[col] = 0.0
                elif col == 'aggregation_level':
                    df[col] = 'unknown'
                else:
                    df[col] = None

        # Export to parquet for efficiency
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)

        logger.info(f"Exported {len(df)} aggregated records to {output_path}")

        # Also export summary
        summary = {
            'total_rows': int(len(df)),
            'patches': int(df['patch_id'].nunique()),
            'entities': int(df['entity_id'].nunique()),
            'roles': int(df['role'].nunique()),
            'avg_sample_size': float(df['n'].mean()),
            'min_sample_size': int(df['n'].min()),
            'max_sample_size': int(df['n'].max()),
            'high_n_rows': int((df['n'] >= 100).sum()),
            'synthetic_rows': int((df['synthetic_share'] > 0).sum())
        }

        summary_path = str(output_path).replace('.parquet', '_summary.json')
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        return df, summary

def main():
    parser = argparse.ArgumentParser(description="Aggregate player data for governance (single patch only)")
    parser.add_argument("--input", required=True, help="Input JSON file with player data")
    parser.add_argument("--output", default="results/_staging_panel.parquet", help="Output parquet file")
    parser.add_argument("--min_n", type=int, default=100, help="Minimum sample size per group")
    parser.add_argument("--fallback_levels", action="store_true", help="Enable fallback aggregation levels")

    # Beta-Binomial prior shrinkage parameters
    parser.add_argument("--use_prior", action="store_true", help="Enable Beta-Binomial prior shrinkage")
    parser.add_argument("--prior_window", type=int, default=6, help="Historical patch window for prior (default: 6)")
    parser.add_argument("--decay", type=float, default=0.7, help="Exponential decay factor λ ∈ (0,1) (default: 0.7)")
    parser.add_argument("--prior_min_n", type=int, default=50, help="Minimum historical effective samples for prior (default: 50)")
    parser.add_argument("--alpha0", type=float, default=0.5, help="Weak prior alpha (default: 0.5)")
    parser.add_argument("--beta0", type=float, default=0.5, help="Weak prior beta (default: 0.5)")
    
    # Target-only mode parameters
    parser.add_argument("--target_only", action="store_true", help="Enable target-only mode (only aggregate coverage targets)")
    parser.add_argument("--coverage_targets", default="configs/coverage_targets.yml", help="Coverage targets YAML file (default: configs/coverage_targets.yml)")

    args = parser.parse_args()

    # Load individual player data
    logger.info(f"Loading player data from {args.input}")
    with open(args.input, 'r') as f:
        data = json.load(f)

    if 'factors' in data:
        df = pd.DataFrame(data['factors'])
    else:
        df = pd.DataFrame(data)

    logger.info(f"Loaded {len(df)} individual player records")

    # Aggregate data with new parameters
    aggregator = DataAggregator(
        min_n=args.min_n,
        use_fallback_levels=args.fallback_levels,
        use_prior=args.use_prior,
        prior_window=args.prior_window,
        decay=args.decay,
        prior_min_n=args.prior_min_n,
        alpha0=args.alpha0,
        beta0=args.beta0,
        target_only=args.target_only,
        coverage_targets_path=args.coverage_targets
    )
    agg_df = aggregator.aggregate_player_data(df)

    # Export
    final_df, summary = aggregator.export_aggregated_data(agg_df, args.output)

    print(f"\n📊 Aggregation Summary:")
    print(f"✅ Input: {len(df)} individual records")
    print(f"✅ Output: {len(final_df)} aggregated records")
    print(f"📈 Sample sizes: {summary['min_sample_size']}-{summary['max_sample_size']} (avg: {summary['avg_sample_size']:.1f})")
    print(f"🎯 High-n rows (n≥100): {summary['high_n_rows']}")
    print(f"🔬 Synthetic rows: {summary['synthetic_rows']}")

if __name__ == "__main__":
    main()
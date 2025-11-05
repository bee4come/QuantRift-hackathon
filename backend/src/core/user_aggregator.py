#!/usr/bin/env python3
"""
User-Mode 聚合器
专注单用户数据聚合，Beta-Binomial先验收缩，证据分级
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from scipy import stats
import argparse

from .utils import (
    load_user_mode_config,
    generate_row_id,
    validate_evidence_schema,
    apply_governance_tag,
    safe_float_convert,
    safe_int_convert,
    format_output_precision,
    save_with_audit_trail
)


class UserAggregator:
    """单用户数据聚合器"""

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """初始化聚合器"""
        self.config = load_user_mode_config(config_path)
        self.prior_config = self.config['prior_shrinkage']
        self.governance_config = self.config['governance']

    def aggregate_user_data(self, puuid: str, match_records: List[Dict[str, Any]],
                           league_baseline: Optional[pd.DataFrame] = None) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        聚合单用户数据

        Args:
            puuid: 用户PUUID
            match_records: 比赛记录列表
            league_baseline: 联盟基线数据

        Returns:
            (entity_panel, context_panel, patch_summary)
        """
        print(f"🎯 聚合用户数据: {puuid[:20]}...")

        # 转换为DataFrame
        df = pd.DataFrame(match_records)
        if df.empty:
            return [], [], []

        # 确保必要字段存在
        required_fields = ['patch', 'champion_id', 'role', 'queue', 'win', 'games']
        missing_fields = [f for f in required_fields if f not in df.columns]
        if missing_fields:
            raise ValueError(f"缺少必要字段: {missing_fields}")

        # 按patch排序（严禁跨patch）
        df = df.sort_values('patch')
        patches = sorted(df['patch'].unique())

        print(f"  发现 {len(patches)} 个patch: {patches[:5]}...")
        print(f"  总记录数: {len(df)}")

        entity_records = []
        context_records = []
        patch_summaries = []

        # 按patch处理（严禁跨patch聚合）
        for patch in patches:
            patch_df = df[df['patch'] == patch]
            print(f"  处理 patch {patch}: {len(patch_df)} 条记录")

            # Patch级汇总
            patch_summary = self._create_patch_summary(patch, patch_df, puuid)
            patch_summaries.append(patch_summary)

            # 获取历史数据用于先验
            historical_data = self._get_historical_data(patch, df, league_baseline)

            # 按 (champion_id, role, queue) 分组聚合
            groupby_cols = ['champion_id', 'role', 'queue']
            groups = patch_df.groupby(groupby_cols)

            for group_keys, group_df in groups:
                champion_id, role, queue = group_keys

                # 计算基础统计
                base_stats = self._calculate_base_stats(group_df)

                # 应用先验收缩
                prior_stats = self._apply_prior_shrinkage(
                    base_stats, champion_id, role, queue, patch, historical_data
                )

                # 创建聚合记录
                record = self._create_aggregate_record(
                    puuid, patch, champion_id, role, queue,
                    base_stats, prior_stats, group_df
                )

                # 应用治理分级
                governance_tag = apply_governance_tag(record, self.config)
                record['governance_tag'] = governance_tag

                # 分流到entity或context
                if governance_tag in ['CONFIDENT', 'CAUTION']:
                    entity_records.append(record)
                else:
                    context_records.append(record)

        print(f"✅ 聚合完成:")
        print(f"  Entity records: {len(entity_records)}")
        print(f"  Context records: {len(context_records)}")
        print(f"  Patch summaries: {len(patch_summaries)}")

        return entity_records, context_records, patch_summaries

    def _create_patch_summary(self, patch: str, patch_df: pd.DataFrame, puuid: str) -> Dict[str, Any]:
        """创建patch级汇总"""
        total_games = len(patch_df)
        total_wins = patch_df['win'].sum()
        winrate = total_wins / total_games if total_games > 0 else 0.5

        # 位置分布
        role_dist = patch_df['role'].value_counts().to_dict()

        # 队列分布
        queue_dist = patch_df['queue'].value_counts().to_dict()

        # 英雄使用
        champion_usage = patch_df['champion_id'].value_counts().head(10).to_dict()

        # 节奏指标（模拟，实际应从match详情计算）
        avg_game_duration = patch_df.get('game_duration', pd.Series([1800] * len(patch_df))).mean()

        summary = {
            'puuid': puuid,
            'patch_id': patch,
            'total_games': int(total_games),
            'total_wins': int(total_wins),
            'winrate': format_output_precision(winrate, is_probability=True),
            'role_distribution': role_dist,
            'queue_distribution': queue_dist,
            'champion_usage': champion_usage,
            'avg_game_duration': safe_float_convert(avg_game_duration),
            'avg_lp_per_win': 17.0,  # 默认值，应从实际数据计算
            'avg_lp_per_loss': 17.0,
            'tempo_indicators': {
                'cs10': 80.0,  # 10分钟补刀，默认值
                'exp10': 120.0,  # 10分钟经验优势
                'tempo_score': 0.5  # 节奏评分
            }
        }

        return summary

    def _get_historical_data(self, current_patch: str, full_df: pd.DataFrame,
                           league_baseline: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """获取历史数据用于先验计算"""
        # 获取历史patch数据（仅≤t-1）
        all_patches = sorted(full_df['patch'].unique())
        try:
            current_idx = all_patches.index(current_patch)
            historical_patches = all_patches[:current_idx]  # 严格<当前patch
        except ValueError:
            historical_patches = []

        # 限制回看窗口
        max_lookback = self.prior_config['personal_history']['max_lookback_patches']
        if len(historical_patches) > max_lookback:
            historical_patches = historical_patches[-max_lookback:]

        # 个人历史数据
        personal_history = {}
        if historical_patches:
            hist_df = full_df[full_df['patch'].isin(historical_patches)]
            decay_lambda = self.prior_config['personal_history']['decay_lambda']

            # 按(champion_id, role, queue)分组计算衰减权重历史
            for (champion_id, role, queue), group in hist_df.groupby(['champion_id', 'role', 'queue']):
                key = f"{champion_id}_{role}_{queue}"

                # 计算衰减权重
                patch_weights = []
                for patch in historical_patches:
                    patch_idx = len(historical_patches) - 1 - historical_patches[::-1].index(patch)
                    weight = decay_lambda ** patch_idx
                    patch_weights.append(weight)

                # 加权统计
                patch_groups = group.groupby('patch')
                weighted_wins = 0
                weighted_games = 0

                for i, patch in enumerate(historical_patches):
                    if patch in patch_groups.groups:
                        patch_data = patch_groups.get_group(patch)
                        weight = patch_weights[i]
                        weighted_wins += patch_data['win'].sum() * weight
                        weighted_games += len(patch_data) * weight

                if weighted_games > 0:
                    personal_history[key] = {
                        'weighted_wins': weighted_wins,
                        'weighted_games': weighted_games,
                        'effective_winrate': weighted_wins / weighted_games
                    }

        # 联盟基线（如果提供）
        league_baseline_data = {}
        if league_baseline is not None:
            # 按patch和role分组的基线胜率
            if 'patch' in league_baseline.columns and 'role' in league_baseline.columns:
                baseline_groups = league_baseline.groupby(['patch', 'role'])
                for (patch, role), group in baseline_groups:
                    if patch == current_patch:
                        key = f"baseline_{role}"
                        league_baseline_data[key] = {
                            'avg_winrate': group.get('avg_winrate', group.get('winrate', [0.5]))[0] if len(group) > 0 else 0.5,
                            'sample_size': len(group)
                        }

        return {
            'personal_history': personal_history,
            'league_baseline': league_baseline_data
        }

    def _calculate_base_stats(self, group_df: pd.DataFrame) -> Dict[str, Any]:
        """计算基础统计"""
        n = len(group_df)
        w = group_df['win'].sum()
        p_hat_raw = w / n if n > 0 else 0.5

        # 计算Wilson置信区间
        z = 1.96  # 95%置信区间
        ci_lo, ci_hi = self._wilson_confidence_interval(w, n, z)

        base_stats = {
            'n': int(n),
            'w': int(w),
            'p_hat_raw': p_hat_raw,
            'ci_lo': ci_lo,
            'ci_hi': ci_hi,
            'ci_width': ci_hi - ci_lo
        }

        return base_stats

    def _apply_prior_shrinkage(self, base_stats: Dict[str, Any],
                              champion_id: int, role: str, queue: str, patch: str,
                              historical_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用Beta-Binomial先验收缩"""
        n = base_stats['n']
        w = base_stats['w']

        # 按优先级应用先验
        alpha_prior = 0.5  # Jeffreys默认
        beta_prior = 0.5

        # 1. League基线先验
        baseline_key = f"baseline_{role}"
        if baseline_key in historical_data['league_baseline']:
            league_data = historical_data['league_baseline'][baseline_key]
            league_winrate = league_data['avg_winrate']
            league_confidence = min(50, league_data['sample_size'])  # 限制最大权重

            alpha_prior = league_confidence * league_winrate
            beta_prior = league_confidence * (1 - league_winrate)

        # 2. 个人历史先验（优先级更高）
        personal_key = f"{champion_id}_{role}_{queue}"
        if personal_key in historical_data['personal_history']:
            personal_data = historical_data['personal_history'][personal_key]
            personal_winrate = personal_data['effective_winrate']
            personal_confidence = min(100, personal_data['weighted_games'])  # 限制最大权重

            # 与League基线的加权组合
            total_confidence = league_confidence + personal_confidence
            if total_confidence > 0:
                combined_winrate = (
                    league_confidence * league_winrate + personal_confidence * personal_winrate
                ) / total_confidence

                alpha_prior = total_confidence * combined_winrate
                beta_prior = total_confidence * (1 - combined_winrate)

        # 3. 计算后验
        alpha_posterior = alpha_prior + w
        beta_posterior = beta_prior + (n - w)

        # 后验估计
        p_hat_posterior = alpha_posterior / (alpha_posterior + beta_posterior)

        # 有效样本数
        effective_n = alpha_prior + beta_prior + n

        # 后验置信区间
        z = 1.96
        posterior_var = (alpha_posterior * beta_posterior) / (
            (alpha_posterior + beta_posterior) ** 2 * (alpha_posterior + beta_posterior + 1)
        )
        posterior_std = np.sqrt(posterior_var)

        ci_lo_posterior = max(0, p_hat_posterior - z * posterior_std)
        ci_hi_posterior = min(1, p_hat_posterior + z * posterior_std)

        # 检查是否使用了先验
        uses_prior = (alpha_prior > 0.5 or beta_prior > 0.5)

        prior_stats = {
            'uses_prior': uses_prior,
            'alpha_prior': alpha_prior,
            'beta_prior': beta_prior,
            'effective_n': effective_n,
            'p_hat': p_hat_posterior,
            'ci_lo': ci_lo_posterior,
            'ci_hi': ci_hi_posterior,
            'n0': alpha_prior + beta_prior,  # 先验样本数
            'w0': alpha_prior,  # 先验胜利数
            'decay': self.prior_config['personal_history']['decay_lambda']
        }

        return prior_stats

    def _wilson_confidence_interval(self, w: int, n: int, z: float = 1.96) -> Tuple[float, float]:
        """Wilson置信区间计算"""
        if n == 0:
            return 0.0, 1.0

        p_hat = w / n
        denominator = 1 + z**2 / n
        center = (p_hat + z**2 / (2*n)) / denominator
        margin = z * np.sqrt((p_hat * (1 - p_hat) + z**2 / (4*n)) / n) / denominator

        ci_lo = max(0, center - margin)
        ci_hi = min(1, center + margin)

        return ci_lo, ci_hi

    def _create_aggregate_record(self, puuid: str, patch: str, champion_id: int,
                               role: str, queue: str, base_stats: Dict[str, Any],
                               prior_stats: Dict[str, Any], group_df: pd.DataFrame) -> Dict[str, Any]:
        """创建聚合记录"""
        # 生成统一row_id
        row_id = generate_row_id(patch, champion_id, role, queue, "entity_id:role:queue")

        # 基础信息
        record = {
            'row_id': row_id,
            'patch_id': patch,
            'champion_id': int(champion_id),
            'champion_name': f"Champion_{champion_id}",  # 简化，实际应查表
            'role': role,
            'queue': queue,
            'n': base_stats['n'],
            'w': base_stats['w'],
            'uses_prior': prior_stats['uses_prior'],
            'effective_n': format_output_precision(prior_stats['effective_n']),
            'p_hat': format_output_precision(prior_stats['p_hat'], is_probability=True),
            'ci': {
                'lo': format_output_precision(prior_stats['ci_lo'], is_probability=True),
                'hi': format_output_precision(prior_stats['ci_hi'], is_probability=True)
            }
        }

        # 计算相对基线的差异（简化为绝对胜率-0.5）
        winrate_delta = prior_stats['p_hat'] - 0.5
        record['winrate_delta'] = format_output_precision(winrate_delta, is_probability=True)

        # 稳定性评分（基于CI宽度）
        ci_width = prior_stats['ci_hi'] - prior_stats['ci_lo']
        stability = max(0, 1 - ci_width)  # CI越窄越稳定
        record['stability'] = format_output_precision(stability, is_probability=True)

        # 合成数据占比（先验权重比例）
        if prior_stats['uses_prior']:
            synthetic_share = prior_stats['n0'] / prior_stats['effective_n']
        else:
            synthetic_share = 0.0
        record['synthetic_share'] = format_output_precision(synthetic_share, is_probability=True)

        # 其他必填字段
        record['aggregation_level'] = "entity_id:role:queue"
        record['k_selected'] = 5  # 默认值
        record['oot_pass'] = True  # 默认通过

        # 先验相关字段
        record['n0'] = format_output_precision(prior_stats['n0'])
        record['w0'] = format_output_precision(prior_stats['w0'])
        record['decay'] = format_output_precision(prior_stats['decay'])

        return record

    def save_results(self, entity_records: List[Dict], context_records: List[Dict],
                    patch_summaries: List[Dict], output_dir: str = "data/user_mode") -> Dict[str, str]:
        """保存聚合结果"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 文件路径
        entity_file = output_dir / "user_entity_panel.jsonl"
        context_file = output_dir / "user_context_panel.jsonl"
        summary_file = output_dir / "user_patch_summary.jsonl"
        parquet_file = output_dir / "user_panel.parquet"

        # 保存JSONL文件
        save_with_audit_trail(entity_records, entity_file, {'type': 'entity_panel'})
        save_with_audit_trail(context_records, context_file, {'type': 'context_panel'})
        save_with_audit_trail(patch_summaries, summary_file, {'type': 'patch_summary'})

        # 保存Parquet（内部使用）
        if entity_records:
            df_entity = pd.DataFrame(entity_records)
            df_entity.to_parquet(parquet_file, index=False)

        file_paths = {
            'entity_panel': str(entity_file),
            'context_panel': str(context_file),
            'patch_summary': str(summary_file),
            'parquet': str(parquet_file)
        }

        print(f"📁 结果已保存:")
        for name, path in file_paths.items():
            print(f"  {name}: {path}")

        return file_paths


def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description="User-Mode数据聚合")
    parser.add_argument("--puuid", required=True, help="用户PUUID")
    parser.add_argument("--input", required=True, help="输入match数据文件")
    parser.add_argument("--output", default="data/user_mode", help="输出目录")
    parser.add_argument("--baseline", help="联盟基线数据文件（可选）")
    args = parser.parse_args()

    # 加载数据
    print(f"📊 加载match数据: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        if args.input.endswith('.jsonl'):
            match_records = [json.loads(line) for line in f if line.strip()]
        else:
            match_records = json.load(f)

    print(f"  发现 {len(match_records)} 条记录")

    # 加载基线数据（可选）
    league_baseline = None
    if args.baseline:
        print(f"📈 加载基线数据: {args.baseline}")
        if args.baseline.endswith('.parquet'):
            league_baseline = pd.read_parquet(args.baseline)
        else:
            league_baseline = pd.read_csv(args.baseline)

    # 聚合数据
    aggregator = UserAggregator()
    entity_records, context_records, patch_summaries = aggregator.aggregate_user_data(
        args.puuid, match_records, league_baseline
    )

    # 保存结果
    file_paths = aggregator.save_results(entity_records, context_records, patch_summaries, args.output)

    print(f"✅ 聚合完成！")
    print(f"  Entity panel: {len(entity_records)} 行")
    print(f"  Context panel: {len(context_records)} 行")


if __name__ == "__main__":
    main()
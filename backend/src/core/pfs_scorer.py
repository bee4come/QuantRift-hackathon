#!/usr/bin/env python3
"""
PFS (Patch Fit Score) 评分模型
标准化+稳健缩尾+可解释权重
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple
import argparse

from .utils import (
    load_user_mode_config,
    standardize_pfs_inputs,
    format_output_precision,
    save_with_audit_trail
)


class PFSScorer:
    """PFS评分器"""

    def __init__(self, config_path: str = "configs/user_mode_params.yml"):
        """初始化评分器"""
        self.config = load_user_mode_config(config_path)
        self.scoring_config = self.config['pfs_scoring']
        self.weights = self.scoring_config['weights']
        self.thresholds = self.scoring_config['thresholds']
        self.robustness = self.scoring_config['robustness']

    def calculate_pfs_scores(self, records: List[Dict[str, Any]]) -> Tuple[List[Dict], Dict]:
        """
        计算PFS评分

        Args:
            records: 输入记录列表

        Returns:
            (带PFS评分的记录列表, 校准报告)
        """
        print(f"🎯 计算PFS评分，输入 {len(records)} 条记录")

        if not records:
            return [], {'calibration_stats': {}, 'threshold_stats': {}}

        # 转换为DataFrame
        df = pd.DataFrame(records)

        # 标准化输入
        df = standardize_pfs_inputs(df, self.config)

        # 计算各组件评分
        df = self._calculate_skill_score(df)
        df = self._calculate_stability_score(df)
        df = self._calculate_meta_alignment_score(df)
        df = self._calculate_volatility_penalty(df)

        # 计算最终PFS评分
        df = self._calculate_final_pfs(df)

        # 生成校准报告
        calibration_report = self._generate_calibration_report(df)

        # 添加PFS等级
        df = self._assign_pfs_levels(df)

        # 转换回记录列表
        scored_records = df.to_dict('records')

        # 清理和格式化输出
        for record in scored_records:
            # 格式化PFS相关字段
            for field in ['z_skill', 'stability_score', 'meta_alignment', 'volatility_penalty', 'pfs_score']:
                if field in record:
                    record[field] = format_output_precision(record[field])

            # 清理临时字段
            temp_fields = ['ci_width', 'z_volatility']
            for field in temp_fields:
                record.pop(field, None)

        print(f"✅ PFS评分完成")
        print(f"  平均PFS: {df['pfs_score'].mean():.3f}")
        print(f"  强推记录: {(df['pfs_level'] == 'strong_recommend').sum()}")
        print(f"  谨慎尝试: {(df['pfs_level'] == 'cautious_try').sum()}")
        print(f"  不建议: {(df['pfs_level'] == 'not_recommend').sum()}")

        return scored_records, calibration_report

    def _calculate_skill_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技能分（标准化z-score）"""
        if 'z_skill' not in df.columns:
            # 如果没有预计算的z_skill，使用简单版本
            if 'winrate_delta' in df.columns:
                df['z_skill'] = df['winrate_delta']
            else:
                df['z_skill'] = 0

        # 稳健缩尾
        lower_bound = df['z_skill'].quantile(self.robustness['winsorize_lower'])
        upper_bound = df['z_skill'].quantile(self.robustness['winsorize_upper'])
        df['z_skill'] = df['z_skill'].clip(lower=lower_bound, upper=upper_bound)

        return df

    def _calculate_stability_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算稳定性评分"""
        if 'stability' in df.columns:
            df['stability_score'] = df['stability']
        else:
            # 基于CI宽度计算稳定性
            if 'ci_width' in df.columns:
                # CI越窄越稳定，归一化到[0,1]
                max_ci_width = df['ci_width'].quantile(0.95)  # 使用95分位数避免极值
                df['stability_score'] = 1 - (df['ci_width'] / max_ci_width).clip(0, 1)
            else:
                df['stability_score'] = 0.5  # 默认中等稳定性

        return df

    def _calculate_meta_alignment_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算元适配评分（版本适配度）"""
        # 简化版本：基于patch和role的适配度
        # 实际应该结合shock_adjust等更复杂指标

        if 'patch_id' in df.columns and 'role' in df.columns:
            # 按patch和role分组，计算相对表现
            df['meta_alignment'] = 0.0

            for (patch, role), group in df.groupby(['patch_id', 'role']):
                if len(group) > 1:
                    # 组内相对表现
                    group_mean = group['winrate_delta'].mean()
                    group_std = group['winrate_delta'].std()

                    if group_std > 0:
                        # 标准化到[-1, 1]范围
                        relative_performance = (group['winrate_delta'] - group_mean) / group_std
                        relative_performance = relative_performance.clip(-1, 1)
                        df.loc[group.index, 'meta_alignment'] = relative_performance
                    else:
                        df.loc[group.index, 'meta_alignment'] = 0.0
                else:
                    # 单记录组，使用绝对表现
                    df.loc[group.index, 'meta_alignment'] = np.sign(group['winrate_delta'].iloc[0]) * 0.5
        else:
            df['meta_alignment'] = 0.0

        return df

    def _calculate_volatility_penalty(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算波动风险惩罚"""
        if 'z_volatility' in df.columns:
            # 已标准化的波动性
            df['volatility_penalty'] = df['z_volatility']
        elif 'ci_width' in df.columns:
            # 基于CI宽度
            median_ci = df['ci_width'].median()
            if median_ci > 0:
                df['volatility_penalty'] = df['ci_width'] / median_ci
            else:
                df['volatility_penalty'] = 1.0
        else:
            df['volatility_penalty'] = 1.0

        return df

    def _calculate_final_pfs(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算最终PFS评分"""
        # 使用配置中的权重
        pfs_formula = (
            self.weights['skill_score'] * df['z_skill'] +
            self.weights['stability'] * df['stability_score'] +
            self.weights['meta_alignment'] * df['meta_alignment'] +
            self.weights['volatility_penalty'] * df['volatility_penalty']  # 注意：这是负权重
        )

        df['pfs_score'] = pfs_formula

        return df

    def _assign_pfs_levels(self, df: pd.DataFrame) -> pd.DataFrame:
        """分配PFS等级"""
        conditions = [
            df['pfs_score'] >= self.thresholds['strong_recommend'],
            df['pfs_score'] >= self.thresholds['cautious_try'],
            df['pfs_score'] < self.thresholds['not_recommend']
        ]

        choices = ['strong_recommend', 'cautious_try', 'not_recommend']

        df['pfs_level'] = np.select(conditions, choices, default='not_recommend')

        return df

    def _generate_calibration_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """生成校准报告"""
        if df.empty:
            return {'calibration_stats': {}, 'threshold_stats': {}}

        # 基础统计
        calibration_stats = {
            'total_records': len(df),
            'pfs_score_mean': format_output_precision(df['pfs_score'].mean()),
            'pfs_score_std': format_output_precision(df['pfs_score'].std()),
            'pfs_score_min': format_output_precision(df['pfs_score'].min()),
            'pfs_score_max': format_output_precision(df['pfs_score'].max()),
            'pfs_score_percentiles': {
                'p25': format_output_precision(df['pfs_score'].quantile(0.25)),
                'p50': format_output_precision(df['pfs_score'].quantile(0.50)),
                'p75': format_output_precision(df['pfs_score'].quantile(0.75)),
                'p90': format_output_precision(df['pfs_score'].quantile(0.90)),
                'p95': format_output_precision(df['pfs_score'].quantile(0.95))
            }
        }

        # 阈值击穿率统计
        threshold_stats = {}
        for level_name, threshold in self.thresholds.items():
            hit_count = (df['pfs_score'] >= threshold).sum()
            hit_rate = hit_count / len(df)
            threshold_stats[level_name] = {
                'threshold': threshold,
                'hit_count': int(hit_count),
                'hit_rate': format_output_precision(hit_rate, is_probability=True)
            }

        # 按patch和role分组的校准
        groupby_calibration = {}
        if 'patch_id' in df.columns and 'role' in df.columns:
            for (patch, role), group in df.groupby(['patch_id', 'role']):
                if len(group) >= 3:  # 至少3个记录才做校准
                    group_key = f"{patch}_{role}"
                    groupby_calibration[group_key] = {
                        'count': len(group),
                        'pfs_mean': format_output_precision(group['pfs_score'].mean()),
                        'strong_recommend_rate': format_output_precision(
                            (group['pfs_level'] == 'strong_recommend').mean(), is_probability=True
                        )
                    }

        # 检查校准健康度
        strong_hit_rate = threshold_stats.get('strong_recommend', {}).get('hit_rate', 0)
        calibration_health = 'healthy'

        if strong_hit_rate < 0.20:
            calibration_health = 'too_strict'  # 阈值过严
        elif strong_hit_rate > 0.40:
            calibration_health = 'too_loose'  # 阈值过松

        calibration_report = {
            'calibration_stats': calibration_stats,
            'threshold_stats': threshold_stats,
            'groupby_calibration': groupby_calibration,
            'calibration_health': calibration_health,
            'generated_at': pd.Timestamp.now().isoformat()
        }

        return calibration_report

    def save_calibration_report(self, calibration_report: Dict[str, Any],
                               output_file: str = "data/user_mode/pfs_calibration.json") -> str:
        """保存校准报告"""
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(calibration_report, f, indent=2, ensure_ascii=False)

        print(f"📊 PFS校准报告已保存: {output_file}")
        return str(output_file)

    def get_recommendations_by_level(self, scored_records: List[Dict[str, Any]],
                                   level: str = 'strong_recommend') -> List[Dict[str, Any]]:
        """按PFS等级获取推荐"""
        return [record for record in scored_records if record.get('pfs_level') == level]


def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description="PFS评分计算")
    parser.add_argument("--input", required=True, help="输入记录文件")
    parser.add_argument("--output", default="data/user_mode", help="输出目录")
    parser.add_argument("--level", choices=['strong_recommend', 'cautious_try', 'not_recommend'],
                       help="仅输出指定等级的记录")
    args = parser.parse_args()

    # 加载数据
    print(f"📊 加载记录: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        if args.input.endswith('.jsonl'):
            records = [json.loads(line) for line in f if line.strip()]
        else:
            records = json.load(f)

    print(f"  发现 {len(records)} 条记录")

    # 计算PFS评分
    scorer = PFSScorer()
    scored_records, calibration_report = scorer.calculate_pfs_scores(records)

    # 保存结果
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存评分记录
    scored_file = output_dir / "pfs_scored_records.jsonl"
    save_with_audit_trail(scored_records, scored_file, {'type': 'pfs_scored'})

    # 保存校准报告
    calibration_file = scorer.save_calibration_report(calibration_report,
                                                     output_dir / "pfs_calibration.json")

    # 如果指定了特定等级
    if args.level:
        level_records = scorer.get_recommendations_by_level(scored_records, args.level)
        level_file = output_dir / f"pfs_{args.level}.jsonl"
        save_with_audit_trail(level_records, level_file, {'type': f'pfs_{args.level}'})
        print(f"📋 {args.level}记录: {len(level_records)} 条 → {level_file}")

    print(f"✅ PFS评分完成！")
    print(f"  评分记录: {len(scored_records)} → {scored_file}")
    print(f"  校准报告: {calibration_file}")

    # 显示校准健康度
    health = calibration_report.get('calibration_health', 'unknown')
    print(f"  校准状态: {health}")


if __name__ == "__main__":
    main()
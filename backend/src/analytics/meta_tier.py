#!/usr/bin/env python3
"""
Meta Tier Classifier
Meta层级分类模块

基于胜率和选取率对英雄进行S/A/B/C/D层级分类
"""

import duckdb
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetaTierClassifier:
    """Meta层级分类器"""

    # 默认层级阈值 (基于胜率和选取率的综合评分)
    DEFAULT_TIERS = {
        'S': 0.85,  # 顶级meta
        'A': 0.70,  # 强势
        'B': 0.50,  # 中等
        'C': 0.30,  # 偏弱
        'D': 0.0    # 弱势
    }

    def __init__(
        self,
        parquet_path: str,
        min_games: int = 50,
        tier_thresholds: Optional[Dict[str, float]] = None
    ):
        """
        初始化Meta层级分类器

        Args:
            parquet_path: Gold layer Parquet文件路径
            min_games: 最小游戏场次要求
            tier_thresholds: 自定义层级阈值（可选）
        """
        self.parquet_path = Path(parquet_path)
        self.min_games = min_games
        self.tier_thresholds = tier_thresholds or self.DEFAULT_TIERS

        if not self.parquet_path.exists():
            raise FileNotFoundError(f"Parquet文件不存在: {parquet_path}")

    def _calculate_champion_stats(self) -> List[Dict[str, Any]]:
        """
        计算每个英雄的统计数据

        Returns:
            英雄统计列表
        """
        logger.info(f"📊 正在从 {self.parquet_path} 计算英雄统计...")

        conn = duckdb.connect(":memory:")

        query = """
        SELECT
            champion_id,
            champion_name,
            COUNT(*) as total_games,
            SUM(CAST(win AS INTEGER)) as wins,
            AVG(CAST(win AS INTEGER)) as winrate,
            AVG(kda_ratio) as avg_kda,
            AVG(gold_per_minute) as avg_gold_per_min,
            AVG(damage_per_minute) as avg_damage_per_min
        FROM read_parquet(?)
        WHERE champion_id IS NOT NULL
        GROUP BY champion_id, champion_name
        HAVING COUNT(*) >= ?
        ORDER BY winrate DESC, total_games DESC
        """

        result = conn.execute(query, [str(self.parquet_path), self.min_games]).fetchall()
        conn.close()

        if not result:
            raise ValueError(f"没有找到满足最小游戏场次({self.min_games})的英雄数据")

        # 转换为字典列表
        champion_stats = []
        for row in result:
            champion_stats.append({
                'champion_id': row[0],
                'champion_name': row[1],
                'total_games': row[2],
                'wins': row[3],
                'winrate': round(row[4], 4),
                'avg_kda': round(row[5], 2),
                'avg_gold_per_min': round(row[6], 2),
                'avg_damage_per_min': round(row[7], 2)
            })

        logger.info(f"✅ 成功计算 {len(champion_stats)} 个英雄的统计数据")

        return champion_stats

    def _calculate_meta_score(self, stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        计算每个英雄的meta评分

        Meta评分 = 0.6 * 标准化胜率 + 0.4 * 标准化选取率

        Args:
            stats: 英雄统计列表

        Returns:
            添加了meta_score字段的统计列表
        """
        logger.info("🔄 正在计算meta评分...")

        # 提取胜率和选取率
        winrates = np.array([s['winrate'] for s in stats])
        pick_rates = np.array([s['total_games'] for s in stats])

        # Min-Max标准化到[0, 1]
        winrate_norm = (winrates - winrates.min()) / (winrates.max() - winrates.min() + 1e-8)
        pickrate_norm = (pick_rates - pick_rates.min()) / (pick_rates.max() - pick_rates.min() + 1e-8)

        # 计算综合meta评分 (胜率60% + 选取率40%)
        meta_scores = 0.6 * winrate_norm + 0.4 * pickrate_norm

        # 添加到统计数据
        for i, stat in enumerate(stats):
            stat['pick_rate_normalized'] = round(float(pickrate_norm[i]), 4)
            stat['meta_score'] = round(float(meta_scores[i]), 4)

        logger.info("✅ meta评分计算完成")

        return stats

    def classify(self) -> Dict[str, Any]:
        """
        对英雄进行Meta层级分类

        Returns:
            分类结果，格式：
            {
                "S": [champion_data, ...],
                "A": [...],
                "B": [...],
                "C": [...],
                "D": [...],
                "metadata": {...}
            }
        """
        # 计算统计数据
        champion_stats = self._calculate_champion_stats()

        # 计算meta评分
        champion_stats = self._calculate_meta_score(champion_stats)

        # 按meta评分排序
        champion_stats_sorted = sorted(champion_stats, key=lambda x: x['meta_score'], reverse=True)

        # 分层
        tiers = {tier: [] for tier in ['S', 'A', 'B', 'C', 'D']}

        for champion in champion_stats_sorted:
            meta_score = champion['meta_score']

            if meta_score >= self.tier_thresholds['S']:
                tier = 'S'
            elif meta_score >= self.tier_thresholds['A']:
                tier = 'A'
            elif meta_score >= self.tier_thresholds['B']:
                tier = 'B'
            elif meta_score >= self.tier_thresholds['C']:
                tier = 'C'
            else:
                tier = 'D'

            champion['tier'] = tier
            tiers[tier].append(champion)

        logger.info(f"✅ 分层完成 - S:{len(tiers['S'])} A:{len(tiers['A'])} B:{len(tiers['B'])} C:{len(tiers['C'])} D:{len(tiers['D'])}")

        return {
            **tiers,
            "metadata": {
                "total_champions": len(champion_stats),
                "min_games": self.min_games,
                "tier_thresholds": self.tier_thresholds
            }
        }

    def classify_by_role(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        按位置分别进行Meta层级分类

        Returns:
            位置→层级→英雄列表
        """
        logger.info("📊 正在按位置进行Meta分层...")

        conn = duckdb.connect(":memory:")

        query = """
        SELECT
            position,
            champion_id,
            champion_name,
            COUNT(*) as total_games,
            SUM(CAST(win AS INTEGER)) as wins,
            AVG(CAST(win AS INTEGER)) as winrate
        FROM read_parquet(?)
        WHERE champion_id IS NOT NULL AND position IS NOT NULL
        GROUP BY position, champion_id, champion_name
        HAVING COUNT(*) >= ?
        ORDER BY position, winrate DESC
        """

        result = conn.execute(query, [str(self.parquet_path), self.min_games]).fetchall()
        conn.close()

        # 按位置分组
        role_stats = {}
        for row in result:
            position = row[0]
            if position not in role_stats:
                role_stats[position] = []

            role_stats[position].append({
                'champion_id': row[1],
                'champion_name': row[2],
                'total_games': row[3],
                'wins': row[4],
                'winrate': round(row[5], 4)
            })

        # 对每个位置进行分层
        role_tiers = {}
        for position, stats in role_stats.items():
            # 计算meta评分
            stats_with_scores = self._calculate_meta_score(stats)

            # 分层
            tiers = {tier: [] for tier in ['S', 'A', 'B', 'C', 'D']}
            for champion in stats_with_scores:
                meta_score = champion['meta_score']

                if meta_score >= self.tier_thresholds['S']:
                    tier = 'S'
                elif meta_score >= self.tier_thresholds['A']:
                    tier = 'A'
                elif meta_score >= self.tier_thresholds['B']:
                    tier = 'B'
                elif meta_score >= self.tier_thresholds['C']:
                    tier = 'C'
                else:
                    tier = 'D'

                champion['tier'] = tier
                tiers[tier].append(champion)

            role_tiers[position] = tiers

        logger.info(f"✅ 完成 {len(role_tiers)} 个位置的Meta分层")

        return role_tiers

    def save(self, output_path: str, include_role_tiers: bool = True) -> None:
        """
        分类并保存Meta层级数据到JSON文件

        Args:
            output_path: 输出文件路径
            include_role_tiers: 是否包含按位置分层的结果
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 全局分层
        global_tiers = self.classify()

        # 可选：按位置分层
        if include_role_tiers:
            role_tiers = self.classify_by_role()
            output_data = {
                "global": global_tiers,
                "by_role": role_tiers
            }
        else:
            output_data = global_tiers

        # 保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Meta层级数据已保存到: {output_file}")

        # 打印摘要
        self._print_summary(global_tiers)

    def _print_summary(self, tiers: Dict[str, Any]) -> None:
        """打印Meta分层摘要"""
        print("\n" + "="*80)
        print("Meta层级分类摘要")
        print("="*80)
        print(f"总英雄数: {tiers['metadata']['total_champions']}")
        print(f"最小游戏场次: {tiers['metadata']['min_games']}")
        print()

        for tier_name in ['S', 'A', 'B', 'C', 'D']:
            champions = tiers[tier_name]
            print(f"\n{tier_name} 级 ({len(champions)} 英雄):")
            print("-"*80)

            for champion in champions[:5]:  # 只显示前5个
                print(
                    f"  {champion['champion_name']:<20} "
                    f"胜率: {champion['winrate']:.3f}  "
                    f"场次: {champion['total_games']:<6}  "
                    f"Meta评分: {champion['meta_score']:.3f}"
                )

            if len(champions) > 5:
                print(f"  ... 还有 {len(champions) - 5} 个英雄")

        print("\n" + "="*80 + "\n")

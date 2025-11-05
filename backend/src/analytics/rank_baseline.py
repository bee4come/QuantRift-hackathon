#!/usr/bin/env python3
"""
Rank Baseline Generator
生成段位基准数据模块

从Gold layer生成各段位的平均表现指标，用于同段位对比分析
"""

import duckdb
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RankBaselineGenerator:
    """段位基准数据生成器"""

    def __init__(
        self,
        parquet_path: str,
        min_sample_size: int = 20
    ):
        """
        初始化段位基准生成器

        Args:
            parquet_path: Gold layer Parquet文件路径
            min_sample_size: 最小样本量要求
        """
        self.parquet_path = Path(parquet_path)
        self.min_sample_size = min_sample_size

        if not self.parquet_path.exists():
            raise FileNotFoundError(f"Parquet文件不存在: {parquet_path}")

    def generate(self) -> Dict[str, Any]:
        """
        生成段位基准统计数据

        Returns:
            段位基准数据字典，格式：
            {
                "CHALLENGER": {
                    "avg_winrate": 0.503,
                    "avg_kda": 2.85,
                    "avg_cs_per_min": 6.2,
                    ...
                },
                ...
            }
        """
        logger.info(f"📊 正在从 {self.parquet_path} 生成段位基准数据...")

        conn = duckdb.connect(":memory:")

        query = """
        SELECT
            tier,
            COUNT(*) as sample_size,
            AVG(CAST(win AS INTEGER)) as avg_winrate,
            AVG(kda_ratio) as avg_kda,
            AVG(cs_per_minute) as avg_cs_per_min,
            AVG(gold_per_minute) as avg_gold_per_min,
            AVG(vision_score_per_minute) as avg_vision_score_per_min,
            AVG(damage_per_minute) as avg_damage_per_min,
            AVG(kills) as avg_kills,
            AVG(deaths) as avg_deaths,
            AVG(assists) as avg_assists,
            AVG(turret_kills) as avg_turret_kills,
            AVG(dragon_kills) as avg_dragon_kills,
            AVG(baron_kills) as avg_baron_kills,
            AVG(wards_placed) as avg_wards_placed,
            AVG(wards_killed) as avg_wards_killed,
            AVG(control_wards) as avg_control_wards,
            STDDEV(CAST(win AS INTEGER)) as std_winrate,
            STDDEV(kda_ratio) as std_kda,
            STDDEV(cs_per_minute) as std_cs_per_min,
            STDDEV(gold_per_minute) as std_gold_per_min
        FROM read_parquet(?)
        WHERE tier IS NOT NULL
        GROUP BY tier
        HAVING COUNT(*) >= ?
        ORDER BY
            CASE tier
                WHEN 'challenger' THEN 1
                WHEN 'grandmaster' THEN 2
                WHEN 'master' THEN 3
                WHEN 'diamond' THEN 4
                WHEN 'emerald' THEN 5
                WHEN 'platinum' THEN 6
                WHEN 'gold' THEN 7
                WHEN 'silver' THEN 8
                WHEN 'bronze' THEN 9
                WHEN 'iron' THEN 10
                ELSE 11
            END
        """

        result = conn.execute(query, [str(self.parquet_path), self.min_sample_size]).fetchall()
        columns = [desc[0] for desc in conn.description]

        conn.close()

        # 转换为字典格式
        baselines = {}
        for row in result:
            tier = row[0].upper()
            baselines[tier] = {
                columns[i]: round(row[i], 4) if isinstance(row[i], float) else row[i]
                for i in range(1, len(columns))
            }

        logger.info(f"✅ 成功生成 {len(baselines)} 个段位的基准数据")

        return baselines

    def generate_role_baselines(self) -> Dict[str, Dict[str, Any]]:
        """
        生成按位置分层的段位基准数据

        Returns:
            位置×段位的基准数据字典
        """
        logger.info("📊 正在生成位置分层的段位基准数据...")

        conn = duckdb.connect(":memory:")

        query = """
        SELECT
            tier,
            position,
            COUNT(*) as sample_size,
            AVG(CAST(win AS INTEGER)) as avg_winrate,
            AVG(kda_ratio) as avg_kda,
            AVG(cs_per_minute) as avg_cs_per_min,
            AVG(gold_per_minute) as avg_gold_per_min,
            AVG(damage_per_minute) as avg_damage_per_min
        FROM read_parquet(?)
        WHERE tier IS NOT NULL AND position IS NOT NULL
        GROUP BY tier, position
        HAVING COUNT(*) >= ?
        ORDER BY tier, position
        """

        result = conn.execute(query, [str(self.parquet_path), self.min_sample_size]).fetchall()
        columns = [desc[0] for desc in conn.description]

        conn.close()

        # 构建嵌套字典：position -> tier -> stats
        role_baselines = {}
        for row in result:
            tier = row[0].upper()
            position = row[1]

            if position not in role_baselines:
                role_baselines[position] = {}

            role_baselines[position][tier] = {
                columns[i]: round(row[i], 4) if isinstance(row[i], float) else row[i]
                for i in range(2, len(columns))
            }

        logger.info(f"✅ 成功生成 {len(role_baselines)} 个位置的分层基准数据")

        return role_baselines

    def save(self, output_path: str, include_role_baselines: bool = False) -> None:
        """
        生成并保存段位基准数据到JSON文件

        Args:
            output_path: 输出文件路径
            include_role_baselines: 是否包含位置分层的基准数据
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 生成全局基准
        baselines = self.generate()

        # 可选：生成位置分层基准
        if include_role_baselines:
            role_baselines = self.generate_role_baselines()
            output_data = {
                "global": baselines,
                "by_role": role_baselines
            }
        else:
            output_data = baselines

        # 保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 段位基准数据已保存到: {output_file}")

        # 打印摘要
        self._print_summary(baselines)

    def _print_summary(self, baselines: Dict[str, Any]) -> None:
        """打印段位基准统计摘要"""
        print("\n" + "="*80)
        print("段位基准统计摘要")
        print("="*80)
        print(f"{'段位':<15} {'样本量':<10} {'平均胜率':<12} {'平均KDA':<12} {'平均CS/min':<12}")
        print("-"*80)

        for tier, stats in baselines.items():
            print(
                f"{tier:<15} "
                f"{stats['sample_size']:<10} "
                f"{stats['avg_winrate']:<12.3f} "
                f"{stats['avg_kda']:<12.2f} "
                f"{stats['avg_cs_per_min']:<12.2f}"
            )
        print("="*80 + "\n")

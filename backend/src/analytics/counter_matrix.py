"""
CounterMatrixCalculator - Champion Counter Relationship Analysis

Calculates champion-vs-champion win rates to build a counter matrix for BP analysis.
"""

import json
import duckdb
from pathlib import Path
from typing import Dict, Any, Tuple
from collections import defaultdict


class CounterMatrixCalculator:
    """
    计算英雄克制关系矩阵

    基于Gold层数据，分析同位置英雄对抗的胜率差异，
    生成英雄克制关系矩阵用于BP决策。

    Example:
        >>> calculator = CounterMatrixCalculator(
        ...     parquet_path="data/gold/parquet/fact_match_performance.parquet"
        ... )
        >>> counter_matrix = calculator.generate()
        >>> calculator.save(output_path="data/baselines/counter_matrix.json")
    """

    def __init__(
        self,
        parquet_path: str = "data/gold/parquet/fact_match_performance.parquet",
        min_matchups: int = 20
    ):
        """
        Args:
            parquet_path: Path to Gold layer parquet file
            min_matchups: Minimum matchups required for reliable counter data
        """
        parquet_file = Path(parquet_path)
        if not parquet_file.exists():
            raise FileNotFoundError(
                f"Gold layer parquet not found: {parquet_path}\n"
                f"Please run silver_to_gold_metrics.py first"
            )

        self.parquet_path = parquet_path
        self.min_matchups = min_matchups

    def generate(self) -> Dict[str, Any]:
        """
        生成完整的英雄克制关系矩阵

        Returns:
            {
                "champions": {
                    "92": {  # Riven
                        "name": "Riven",
                        "roles": {
                            "TOP": {
                                "counters": {"122": 0.38, "86": 0.42, ...},  # Weak against
                                "strong_against": {"420": 0.65, "24": 0.61, ...}  # Strong against
                            }
                        }
                    }
                },
                "metadata": {...}
            }
        """
        print("\n" + "=" * 60)
        print("🎯 英雄克制关系矩阵生成器")
        print("=" * 60)

        print(f"\n📊 分析数据源: {self.parquet_path}")

        # Query to find all same-role matchups
        query = """
        WITH matchups AS (
            SELECT
                a.champion_id as champ_a,
                a.champion_name as name_a,
                a.position as role,
                b.champion_id as champ_b,
                b.champion_name as name_b,
                a.win as a_win,
                a.match_id
            FROM read_parquet(?) a
            JOIN read_parquet(?) b
                ON a.match_id = b.match_id
                AND a.position = b.position
                AND a.team_id != b.team_id
            WHERE a.position IS NOT NULL
                AND a.champion_id IS NOT NULL
                AND b.champion_id IS NOT NULL
        )
        SELECT
            champ_a,
            ANY_VALUE(name_a) as name_a,
            role,
            champ_b,
            ANY_VALUE(name_b) as name_b,
            COUNT(*) as matchup_count,
            SUM(CASE WHEN a_win THEN 1 ELSE 0 END) as a_wins,
            AVG(CASE WHEN a_win THEN 1.0 ELSE 0.0 END) as a_winrate
        FROM matchups
        GROUP BY champ_a, role, champ_b
        HAVING COUNT(*) >= ?
        ORDER BY champ_a, role, a_winrate DESC
        """

        print("🔍 查询同位置英雄对抗数据...")

        conn = duckdb.connect()
        result = conn.execute(
            query,
            [self.parquet_path, self.parquet_path, self.min_matchups]
        ).fetchall()

        print(f"✅ 找到 {len(result)} 条有效对抗记录")

        # Build counter matrix
        champions_data = defaultdict(lambda: {
            "name": None,
            "roles": defaultdict(lambda: {
                "counters": {},
                "strong_against": {},
                "matchup_stats": {}
            })
        })

        total_matchups = 0
        counter_threshold = 0.45  # Win rate < 45% = counter
        strong_threshold = 0.55   # Win rate > 55% = strong against

        for row in result:
            champ_a, name_a, role, champ_b, name_b, matchup_count, a_wins, a_winrate = row

            champ_a_str = str(champ_a)
            champ_b_str = str(champ_b)

            # Set champion name
            if champions_data[champ_a_str]["name"] is None:
                champions_data[champ_a_str]["name"] = name_a

            # Store matchup stats
            role_data = champions_data[champ_a_str]["roles"][role]

            # Full matchup data
            role_data["matchup_stats"][champ_b_str] = {
                "opponent_name": name_b,
                "matchup_count": int(matchup_count),
                "wins": int(a_wins),
                "winrate": round(float(a_winrate), 3)
            }

            # Identify counters (champions we struggle against)
            if a_winrate < counter_threshold:
                role_data["counters"][champ_b_str] = round(float(a_winrate), 3)

            # Identify strong matchups
            if a_winrate > strong_threshold:
                role_data["strong_against"][champ_b_str] = round(float(a_winrate), 3)

            total_matchups += 1

        # Convert defaultdict to regular dict
        champions_dict = {}
        for champ_id, champ_data in champions_data.items():
            champions_dict[champ_id] = {
                "name": champ_data["name"],
                "roles": {}
            }
            for role, role_data in champ_data["roles"].items():
                champions_dict[champ_id]["roles"][role] = dict(role_data)

        print(f"\n📈 统计信息:")
        print(f"   分析英雄数: {len(champions_dict)}")
        print(f"   总对抗记录: {total_matchups}")
        print(f"   最小对局数: {self.min_matchups}")

        return {
            "champions": champions_dict,
            "metadata": {
                "total_champions": len(champions_dict),
                "total_matchups": total_matchups,
                "min_matchups_threshold": self.min_matchups,
                "counter_threshold": counter_threshold,
                "strong_threshold": strong_threshold,
                "data_source": str(self.parquet_path)
            }
        }

    def save(self, output_path: str = "data/baselines/counter_matrix.json") -> None:
        """
        保存克制关系矩阵到JSON文件

        Args:
            output_path: Output file path
        """
        counter_matrix = self.generate()

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(counter_matrix, f, indent=2, ensure_ascii=False)

        print(f"\n💾 克制关系矩阵已保存: {output_path}")
        print(f"   文件大小: {output_file.stat().st_size / 1024:.1f} KB")


def load_counter_matrix(baselines_path: str = "data/baselines/counter_matrix.json") -> Dict[str, Any]:
    """
    加载克制关系矩阵（支持自动生成）

    Args:
        baselines_path: Path to counter_matrix.json

    Returns:
        Counter matrix data with auto-generation if missing
    """
    baseline_file = Path(baselines_path)

    # Auto-generate if missing
    if not baseline_file.exists():
        print(f"⚠️  克制关系矩阵不存在，正在自动生成...")

        gold_parquet = Path("data/gold/parquet/fact_match_performance.parquet")
        if not gold_parquet.exists():
            raise FileNotFoundError(f"❌ Gold layer数据不存在: {gold_parquet}")

        calculator = CounterMatrixCalculator(parquet_path=str(gold_parquet), min_matchups=20)
        calculator.save(output_path=baselines_path)
        print(f"✅ 克制关系矩阵已生成: {baselines_path}")

    with open(baseline_file, 'r', encoding='utf-8') as f:
        return json.load(f)

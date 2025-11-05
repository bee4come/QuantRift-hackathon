"""PeerComparisonAgent - Peer Comparison Tools"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from src.core.statistical_utils import wilson_confidence_interval
from src.analytics import RankBaselineGenerator


def load_player_data(packs_dir: str, all_packs_data: Optional[list] = None) -> Dict[str, Any]:
    """
    加载玩家数据

    Args:
        packs_dir: Pack文件目录
        all_packs_data: 预加载的所有pack数据（可选，来自AgentContext缓存）

    Returns:
        玩家数据统计
    """
    # 如果提供了缓存数据，直接使用
    if all_packs_data is not None:
        packs = all_packs_data
    else:
        # 否则从文件系统读取
        packs_dir = Path(packs_dir)
        pack_files = sorted(packs_dir.glob("pack_*.json"))
        packs = []
        for pack_file in pack_files:
            with open(pack_file, 'r') as f:
                packs.append(json.load(f))

    # 处理pack数据
    total_games = total_wins = 0
    for pack in packs:
        for cr in pack.get("by_cr", []):
            total_games += cr["games"]
            total_wins += cr["wins"]

    wr = total_wins / total_games if total_games > 0 else 0
    return {
        "total_games": total_games,
        "winrate": round(wr, 3)
    }


def load_rank_baseline(rank: str) -> Optional[Dict[str, Any]]:
    """
    加载段位基准数据（自动生成如果不存在）

    数据来源优先级：
    1. 已有缓存文件: data/baselines/rank_baselines.json
    2. 自动生成: 从Gold layer实时计算
    """
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent.parent.parent
    baseline_file = project_root / "data/baselines/rank_baselines.json"
    gold_parquet = project_root / "data/gold/parquet/fact_match_performance.parquet"

    # 检查是否已有baseline文件
    if not baseline_file.exists():
        print(f"⚠️  段位基准数据不存在，正在从Gold layer自动生成...")

        # 检查Gold layer数据是否存在
        if not gold_parquet.exists():
            print(f"❌ Gold layer数据不存在: {gold_parquet}")
            print("   请先运行数据pipeline生成Gold layer数据")
            return None

        try:
            # 自动生成baseline数据
            generator = RankBaselineGenerator(
                parquet_path=str(gold_parquet),
                min_sample_size=20
            )
            generator.save(
                output_path=str(baseline_file),
                include_role_baselines=False
            )
            print(f"✅ 段位基准数据已生成: {baseline_file}")
        except Exception as e:
            print(f"❌ 生成段位基准数据失败: {e}")
            return None

    # 读取baseline数据
    with open(baseline_file, 'r', encoding='utf-8') as f:
        baseline_data = json.load(f)

    # 返回指定段位的基准
    if rank.upper() not in baseline_data:
        print(f"⚠️  段位 {rank.upper()} 在基准数据中不存在")
        return None

    return baseline_data[rank.upper()]


def compare_to_baseline(player_data: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    """对比玩家数据与基准"""
    wr_diff = player_data["winrate"] - baseline["avg_winrate"]

    assessment = "above_average" if wr_diff > 0.02 else ("below_average" if wr_diff < -0.02 else "average")

    return {
        "player": player_data,
        "baseline": baseline,
        "winrate_diff": round(wr_diff, 3),
        "assessment": assessment
    }


def format_analysis_for_prompt(comparison: Dict[str, Any], rank: str) -> str:
    """格式化对比数据"""
    player = comparison["player"]
    baseline = comparison["baseline"]

    return f"""# 同段位对比分析数据

**段位**: {rank}
**样本量**: {baseline.get('sample_size', 'N/A')}

## 玩家表现
- 总场次: {player['total_games']}
- 胜率: {player['winrate']:.1%}

## 段位基准（Gold Layer数据）
- 平均胜率: {baseline['avg_winrate']:.1%}
- 平均KDA: {baseline.get('avg_kda', 0):.2f}
- 平均CS/min: {baseline.get('avg_cs_per_minute', 0):.2f}
- 平均金币/min: {baseline.get('avg_gold_per_minute', 0):.1f}

## 对比结果
- 胜率差值: {comparison['winrate_diff']:+.1%}
- 评估: {comparison['assessment']}
"""

"""FriendComparisonAgent - Friend Comparison Tools (Enhanced with Quantitative Metrics)"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict
from src.core.statistical_utils import wilson_confidence_interval


def load_player_data(packs_dir: str, all_packs_data: Optional[list] = None) -> Dict[str, Any]:
    """
    加载玩家数据并提取完整的量化指标

    Args:
        packs_dir: Pack文件目录
        all_packs_data: 预加载的所有pack数据（可选）

    Returns:
        包含完整量化指标的玩家数据
    """
    # 加载pack数据
    if all_packs_data is not None:
        packs = all_packs_data
    else:
        packs_dir = Path(packs_dir)
        pack_files = sorted(packs_dir.glob("pack_*.json"))
        packs = []
        for pack_file in pack_files:
            with open(pack_file, 'r') as f:
                packs.append(json.load(f))

    # 初始化聚合数据
    total_games = total_wins = 0
    total_kda_adj = total_obj_rate = total_cp_25 = 0
    champion_pool = defaultdict(lambda: {'games': 0, 'wins': 0, 'kda': 0, 'cp': 0, 'obj': 0})
    role_distribution = defaultdict(lambda: {'games': 0, 'wins': 0})
    governance_counts = defaultdict(int)

    # 聚合所有pack数据
    for pack in packs:
        for cr in pack.get("by_cr", []):
            games = cr["games"]
            wins = cr["wins"]

            # 总体统计
            total_games += games
            total_wins += wins

            # 量化指标累加（加权平均）
            total_kda_adj += cr.get("kda_adj", 0) * games
            total_obj_rate += cr.get("obj_rate", 0) * games
            total_cp_25 += cr.get("cp_25", 0) * games

            # 英雄池统计
            champ_id = cr["champ_id"]
            champion_pool[champ_id]['games'] += games
            champion_pool[champ_id]['wins'] += wins
            champion_pool[champ_id]['kda'] += cr.get("kda_adj", 0) * games
            champion_pool[champ_id]['cp'] += cr.get("cp_25", 0) * games
            champion_pool[champ_id]['obj'] += cr.get("obj_rate", 0) * games

            # 位置分布统计
            role = cr["role"]
            role_distribution[role]['games'] += games
            role_distribution[role]['wins'] += wins

    # Re-calculate Governance based on aggregated champion games (not per-patch)
    # This ensures accurate governance distribution across all patches combined
    for champ_id, champ_data in champion_pool.items():
        champ_games = champ_data['games']
        if champ_games >= 100:
            governance = "CONFIDENT"
        elif champ_games >= 30:
            governance = "CAUTION"
        else:
            governance = "CONTEXT"
        governance_counts[governance] += champ_games

    # 计算加权平均值
    avg_kda_adj = total_kda_adj / total_games if total_games > 0 else 0
    avg_obj_rate = total_obj_rate / total_games if total_games > 0 else 0
    avg_cp_25 = total_cp_25 / total_games if total_games > 0 else 0
    winrate = total_wins / total_games if total_games > 0 else 0

    # 计算英雄池深度
    top_champions = sorted(
        [(champ, data) for champ, data in champion_pool.items()],
        key=lambda x: x[1]['games'],
        reverse=True
    )[:5]  # Top 5 champions

    champion_pool_data = []
    for champ_id, data in top_champions:
        champ_games = data['games']
        champion_pool_data.append({
            'champ_id': champ_id,
            'games': champ_games,
            'winrate': data['wins'] / champ_games if champ_games > 0 else 0,
            'kda_adj': data['kda'] / champ_games if champ_games > 0 else 0,
            'combat_power': data['cp'] / champ_games if champ_games > 0 else 0,
            'obj_rate': data['obj'] / champ_games if champ_games > 0 else 0
        })

    # 计算位置分布
    role_data = []
    for role, data in sorted(role_distribution.items(), key=lambda x: x[1]['games'], reverse=True):
        role_games = data['games']
        role_data.append({
            'role': role,
            'games': role_games,
            'percentage': role_games / total_games if total_games > 0 else 0,
            'winrate': data['wins'] / role_games if role_games > 0 else 0
        })

    # 计算数据质量评分
    confident_pct = governance_counts.get('CONFIDENT', 0) / total_games if total_games > 0 else 0
    caution_pct = governance_counts.get('CAUTION', 0) / total_games if total_games > 0 else 0
    context_pct = governance_counts.get('CONTEXT', 0) / total_games if total_games > 0 else 0

    return {
        # 基础统计
        "total_games": total_games,
        "winrate": round(winrate, 3),

        # 量化核心指标
        "avg_kda_adj": round(avg_kda_adj, 2),
        "avg_combat_power": round(avg_cp_25, 1),
        "avg_obj_rate": round(avg_obj_rate, 2),

        # 英雄池
        "champion_pool": champion_pool_data,
        "champion_diversity": len(champion_pool),

        # 位置分布
        "role_distribution": role_data,
        "primary_role": role_data[0]['role'] if role_data else None,

        # 数据质量
        "data_quality": {
            "confident": round(confident_pct, 2),
            "caution": round(caution_pct, 2),
            "context": round(context_pct, 2)
        }
    }


def compare_two_players(player1_data: Dict[str, Any], player2_data: Dict[str, Any],
                        player1_name: str, player2_name: str) -> Dict[str, Any]:
    """
    Deep comparison of two players using full quantitative metrics
    """
    # Basic comparison
    wr_diff = player1_data["winrate"] - player2_data["winrate"]
    kda_diff = player1_data["avg_kda_adj"] - player2_data["avg_kda_adj"]
    cp_diff = player1_data["avg_combat_power"] - player2_data["avg_combat_power"]
    obj_diff = player1_data["avg_obj_rate"] - player2_data["avg_obj_rate"]

    # Overall evaluation
    if abs(wr_diff) < 0.02:
        wr_assessment = "Evenly matched"
    elif wr_diff > 0:
        wr_assessment = f"{player1_name} leads in win rate"
    else:
        wr_assessment = f"{player2_name} leads in win rate"

    # KDA evaluation
    if abs(kda_diff) < 0.3:
        kda_assessment = "Similar kill efficiency"
    elif kda_diff > 0:
        kda_assessment = f"{player1_name} has higher kill efficiency"
    else:
        kda_assessment = f"{player2_name} has higher kill efficiency"

    # Combat Power evaluation
    if abs(cp_diff) < 500:
        cp_assessment = "Similar combat power"
    elif cp_diff > 0:
        cp_assessment = f"{player1_name} has stronger combat power"
    else:
        cp_assessment = f"{player2_name} has stronger combat power"

    # Objective Rate evaluation
    if abs(obj_diff) < 0.3:
        obj_assessment = "Similar objective control"
    elif obj_diff > 0:
        obj_assessment = f"{player1_name} has better objective control"
    else:
        obj_assessment = f"{player2_name} has better objective control"

    # Champion pool comparison
    champ_diversity_diff = player1_data["champion_diversity"] - player2_data["champion_diversity"]
    if abs(champ_diversity_diff) < 3:
        champ_assessment = "Similar champion pool depth"
    elif champ_diversity_diff > 0:
        champ_assessment = f"{player1_name} has broader champion pool"
    else:
        champ_assessment = f"{player2_name} has broader champion pool"

    return {
        "player1": {
            "name": player1_name,
            "total_games": player1_data["total_games"],
            "winrate": player1_data["winrate"],
            "avg_kda_adj": player1_data["avg_kda_adj"],
            "avg_combat_power": player1_data["avg_combat_power"],
            "avg_obj_rate": player1_data["avg_obj_rate"],
            "champion_pool": player1_data["champion_pool"],
            "champion_diversity": player1_data["champion_diversity"],
            "role_distribution": player1_data["role_distribution"],
            "primary_role": player1_data["primary_role"],
            "data_quality": player1_data["data_quality"]
        },
        "player2": {
            "name": player2_name,
            "total_games": player2_data["total_games"],
            "winrate": player2_data["winrate"],
            "avg_kda_adj": player2_data["avg_kda_adj"],
            "avg_combat_power": player2_data["avg_combat_power"],
            "avg_obj_rate": player2_data["avg_obj_rate"],
            "champion_pool": player2_data["champion_pool"],
            "champion_diversity": player2_data["champion_diversity"],
            "role_distribution": player2_data["role_distribution"],
            "primary_role": player2_data["primary_role"],
            "data_quality": player2_data["data_quality"]
        },
        "comparison": {
            "winrate_diff": round(wr_diff, 3),
            "kda_diff": round(kda_diff, 2),
            "combat_power_diff": round(cp_diff, 1),
            "obj_rate_diff": round(obj_diff, 2),
            "champion_diversity_diff": champ_diversity_diff
        },
        "assessment": {
            "winrate": wr_assessment,
            "kda": kda_assessment,
            "combat_power": cp_assessment,
            "objective_control": obj_assessment,
            "champion_pool": champ_assessment
        }
    }


def format_comparison_for_prompt(comparison: Dict[str, Any], player1_name: str, player2_name: str) -> str:
    """Format friend comparison data with quantitative metrics for prompt"""
    p1 = comparison["player1"]
    p2 = comparison["player2"]
    diff = comparison["comparison"]
    assess = comparison["assessment"]

    # Format champion pool
    def format_champion_pool(champ_list):
        lines = []
        for i, champ in enumerate(champ_list[:3], 1):
            lines.append(
                f"  {i}. Champion ID {champ['champ_id']}: "
                f"{champ['games']} games, "
                f"Win rate {champ['winrate']:.1%}, "
                f"KDA {champ['kda_adj']:.2f}, "
                f"Combat power {champ['combat_power']:.0f}, "
                f"Obj rate {champ['obj_rate']:.2f}"
            )
        return "\n".join(lines)

    # Format role distribution
    def format_role_dist(role_list):
        lines = []
        for role in role_list[:3]:
            lines.append(
                f"  - {role['role']}: {role['percentage']:.1%} ({role['games']} games), "
                f"Win rate {role['winrate']:.1%}"
            )
        return "\n".join(lines)

    return f"""# Friend Comparison Analysis Data (Quantitative Metrics)

## {player1_name} Data Summary
### Basic Statistics
- Total games: {p1['total_games']}
- Win rate: {p1['winrate']:.1%}
- Data quality: CONFIDENT {p1['data_quality']['confident']:.0%} | CAUTION {p1['data_quality']['caution']:.0%} | CONTEXT {p1['data_quality']['context']:.0%}

### Core Quantitative Metrics
- Average KDA: {p1['avg_kda_adj']:.2f}
- 25-minute combat power: {p1['avg_combat_power']:.0f}
- Objective control rate: {p1['avg_obj_rate']:.2f}

### Champion Pool (Top 3)
{format_champion_pool(p1['champion_pool'])}
- Champion pool depth: {p1['champion_diversity']} unique champions

### Position Distribution (Top 3)
{format_role_dist(p1['role_distribution'])}
- Primary position: {p1['primary_role']}

---

## {player2_name} Data Summary
### Basic Statistics
- Total games: {p2['total_games']}
- Win rate: {p2['winrate']:.1%}
- Data quality: CONFIDENT {p2['data_quality']['confident']:.0%} | CAUTION {p2['data_quality']['caution']:.0%} | CONTEXT {p2['data_quality']['context']:.0%}

### Core Quantitative Metrics
- Average KDA: {p2['avg_kda_adj']:.2f}
- 25-minute combat power: {p2['avg_combat_power']:.0f}
- Objective control rate: {p2['avg_obj_rate']:.2f}

### Champion Pool (Top 3)
{format_champion_pool(p2['champion_pool'])}
- Champion pool depth: {p2['champion_diversity']} unique champions

### Position Distribution (Top 3)
{format_role_dist(p2['role_distribution'])}
- Primary position: {p2['primary_role']}

---

## Quantitative Comparison Results
### Metric Differences
- Win rate difference: {diff['winrate_diff']:+.1%}
- KDA difference: {diff['kda_diff']:+.2f}
- Combat power difference: {diff['combat_power_diff']:+.0f}
- Objective rate difference: {diff['obj_rate_diff']:+.2f}
- Champion pool depth difference: {diff['champion_diversity_diff']:+d}

### Overall Assessment
- Win rate: {assess['winrate']}
- Kill efficiency: {assess['kda']}
- Combat power: {assess['combat_power']}
- Objective control: {assess['objective_control']}
- Champion pool: {assess['champion_pool']}
"""

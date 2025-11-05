"""
BuildSimulatorAgent - Data Processing Tools

Core functions for build comparison and simulation.
"""

from typing import Dict, Any, List
from src.analytics import MatchSimilarityFinder
from src.utils.id_mappings import get_champion_name, get_item_name


def compare_build_options(
    champion_id: int,
    role: str,
    build_a: List[int],
    build_b: List[int],
    game_duration_min: int = None,
    game_duration_max: int = None,
    parquet_path: str = "data/gold/parquet/fact_match_performance.parquet",
    min_samples: int = 10
) -> Dict[str, Any]:
    """
    对比两种出装方案的历史表现

    Args:
        champion_id: Champion ID
        role: Role (TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY)
        build_a: First build (list of item IDs)
        build_b: Second build (list of item IDs)
        game_duration_min: Minimum game duration filter (optional)
        game_duration_max: Maximum game duration filter (optional)
        parquet_path: Path to Gold layer data
        min_samples: Minimum samples required for valid comparison

    Returns:
        Complete build comparison with statistics and metadata
    """
    # Create finder
    finder = MatchSimilarityFinder(parquet_path=parquet_path)

    # Compare builds
    comparison = finder.compare_builds(
        champion_id=champion_id,
        role=role,
        build_a=build_a,
        build_b=build_b,
        game_duration_min=game_duration_min,
        game_duration_max=game_duration_max,
        min_samples=min_samples
    )

    return {
        "champion_id": champion_id,
        "role": role,
        "build_a": build_a,
        "build_b": build_b,
        "game_duration_filter": {
            "min": game_duration_min,
            "max": game_duration_max
        },
        "comparison": comparison
    }


def format_build_comparison_for_prompt(comparison_data: Dict[str, Any]) -> str:
    """
    格式化出装对比数据为LLM友好的文本

    Args:
        comparison_data: Complete build comparison data

    Returns:
        Formatted text for LLM prompt
    """
    lines = []

    lines.append("# 出装方案对比数据\n")

    # Basic info
    champ_id = comparison_data['champion_id']
    champ_name = get_champion_name(champ_id)
    lines.append(f"**英雄**: {champ_name} (ID: {champ_id})")
    lines.append(f"**位置**: {comparison_data['role']}")

    # Game duration filter
    duration_filter = comparison_data['game_duration_filter']
    if duration_filter['min'] or duration_filter['max']:
        min_str = f"{duration_filter['min']}分钟" if duration_filter['min'] else "不限"
        max_str = f"{duration_filter['max']}分钟" if duration_filter['max'] else "不限"
        lines.append(f"**对局时长范围**: {min_str} - {max_str}")

    lines.append("")

    # Build A
    lines.append("## 出装方案A\n")
    build_a_names = [f"{get_item_name(item_id)} ({item_id})" for item_id in comparison_data['build_a']]
    lines.append(f"**装备列表**: {', '.join(build_a_names)}")

    comparison = comparison_data['comparison']
    stats_a = comparison['build_a_stats']

    lines.append(f"\n**样本量**: {stats_a['sample_size']}")
    if stats_a['win_rate'] is not None:
        lines.append(f"**胜率**: {stats_a['win_rate']:.1%}")
        lines.append(f"**平均DPM**: {stats_a['avg_damage_per_minute']}")
        lines.append(f"**平均GPM**: {stats_a['avg_gold_per_minute']}")
        lines.append(f"**平均参团率**: {stats_a['avg_kill_participation']:.1%}")
        lines.append(f"**平均KDA**: {stats_a['avg_kda']}")

    lines.append("")

    # Build B
    lines.append("## 出装方案B\n")
    build_b_names = [f"{get_item_name(item_id)} ({item_id})" for item_id in comparison_data['build_b']]
    lines.append(f"**装备列表**: {', '.join(build_b_names)}")

    stats_b = comparison['build_b_stats']

    lines.append(f"\n**样本量**: {stats_b['sample_size']}")
    if stats_b['win_rate'] is not None:
        lines.append(f"**胜率**: {stats_b['win_rate']:.1%}")
        lines.append(f"**平均DPM**: {stats_b['avg_damage_per_minute']}")
        lines.append(f"**平均GPM**: {stats_b['avg_gold_per_minute']}")
        lines.append(f"**平均参团率**: {stats_b['avg_kill_participation']:.1%}")
        lines.append(f"**平均KDA**: {stats_b['avg_kda']}")

    lines.append("")

    # Comparison results
    lines.append("## 对比结果\n")

    if comparison['comparison']['valid_comparison']:
        comp_result = comparison['comparison']

        lines.append(f"**对比有效性**: ✅ 有效")
        lines.append(f"**置信度**: {comp_result['confidence']}")
        lines.append(f"**推荐方案**: {comp_result['winner']}")

        lines.append("\n**性能差异**:\n")

        diffs = comp_result['differences']

        for metric, diff_data in diffs.items():
            metric_name = {
                'win_rate': '胜率',
                'avg_damage_per_minute': '伤害/分钟',
                'avg_gold_per_minute': '金币/分钟',
                'avg_kill_participation': '参团率',
                'avg_kda': 'KDA'
            }.get(metric, metric)

            abs_diff = diff_data['absolute_diff']
            pct_diff = diff_data['percentage_diff']

            lines.append(f"- **{metric_name}**: {abs_diff:+.2f} ({pct_diff:+.1f}%)")

    else:
        lines.append(f"**对比有效性**: ❌ 无效")
        lines.append(f"**原因**: {comparison['comparison']['reason']}")
        lines.append(f"**出装A样本**: {comparison['comparison']['build_a_samples']}")
        lines.append(f"**出装B样本**: {comparison['comparison']['build_b_samples']}")

    return "\n".join(lines)

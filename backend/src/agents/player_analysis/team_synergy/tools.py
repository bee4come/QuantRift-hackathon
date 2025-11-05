"""
TeamSynergyAgent - Data Processing Tools

Core functions for teammate analysis and synergy evaluation.
"""

from typing import Dict, Any, List
from src.analytics import FrequentTeammateDetector


def analyze_team_synergy(
    player_keys: List[str],
    parquet_path: str = "data/gold/parquet/fact_match_performance.parquet",
    min_games_together: int = 3
) -> Dict[str, Any]:
    """
    分析团队配合默契度

    Args:
        player_keys: List of player keys (2-5 players)
        parquet_path: Path to Gold layer data
        min_games_together: Minimum games together for analysis

    Returns:
        Complete team synergy analysis
    """
    # Create detector
    detector = FrequentTeammateDetector(
        parquet_path=parquet_path,
        min_games_together=min_games_together
    )

    # Generate team report
    report = detector.generate_team_report(player_keys)

    return report


def find_player_teammates(
    player_key: str,
    parquet_path: str = "data/gold/parquet/fact_match_performance.parquet",
    min_games: int = 5,
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """
    查找玩家的常用队友

    Args:
        player_key: Target player key
        parquet_path: Path to Gold layer data
        min_games: Minimum games together
        top_n: Number of top teammates to return

    Returns:
        List of frequent teammates with statistics
    """
    # Create detector
    detector = FrequentTeammateDetector(
        parquet_path=parquet_path,
        min_games_together=min_games
    )

    # Find teammates
    teammates = detector.find_frequent_teammates(player_key, min_games=min_games)

    # Return top N
    return teammates[:top_n]


def format_synergy_analysis_for_prompt(synergy_data: Dict[str, Any]) -> str:
    """
    格式化团队配合分析数据为LLM友好的文本

    Args:
        synergy_data: Team synergy analysis data

    Returns:
        Formatted text for LLM prompt
    """
    lines = []

    lines.append("# 团队默契度分析数据\n")

    # Team summary
    lines.append("## 团队概况\n")
    lines.append(f"**团队规模**: {synergy_data['team_size']}人")
    lines.append(f"**配对数量**: {synergy_data['pairs_analyzed']}对")
    lines.append(f"**总共同对局**: {synergy_data['total_games']}场")
    lines.append(f"**平均默契分数**: {synergy_data['avg_synergy_score']}/100")
    lines.append(f"**平均配合胜率**: {synergy_data['avg_win_rate']:.1%}\n")

    # Synergy level assessment
    avg_score = synergy_data['avg_synergy_score']
    if avg_score >= 70:
        synergy_level = "🔥 优秀 - 团队配合非常默契"
    elif avg_score >= 55:
        synergy_level = "✅ 良好 - 团队配合较为默契"
    elif avg_score >= 40:
        synergy_level = "⚖️ 一般 - 团队配合有待提高"
    else:
        synergy_level = "⚠️ 较差 - 团队配合需要磨合"

    lines.append(f"**默契度等级**: {synergy_level}\n")

    # Pair details
    if synergy_data['pair_details']:
        lines.append("## 配对详情\n")
        lines.append("| 队友1 | 队友2 | 共同场次 | 胜率 | 默契分数 | 主要组合 |")
        lines.append("|-------|-------|----------|------|----------|----------|")

        for pair in sorted(synergy_data['pair_details'], key=lambda x: x['synergy']['synergy_score'], reverse=True):
            s = pair['synergy']
            player1_name = s.get('player1_name', 'Unknown')[:10]
            player2_name = s.get('player2_name', 'Unknown')[:10]
            games = s['games_together']
            winrate = s['win_rate']
            score = s['synergy_score']
            combo = s.get('most_common_combo', 'N/A')

            lines.append(f"| {player1_name} | {player2_name} | {games} | {winrate:.1%} | {score}/100 | {combo} |")

        lines.append("")

    # Top performers
    if synergy_data['pair_details']:
        pairs_sorted = sorted(synergy_data['pair_details'], key=lambda x: x['synergy']['synergy_score'], reverse=True)

        if pairs_sorted:
            lines.append("## 最佳配对\n")
            best_pair = pairs_sorted[0]['synergy']
            lines.append(f"**队友组合**: {best_pair['player1_name']} + {best_pair['player2_name']}")
            lines.append(f"**共同对局**: {best_pair['games_together']}场")
            lines.append(f"**配合胜率**: {best_pair['win_rate']:.1%}")
            lines.append(f"**默契分数**: {best_pair['synergy_score']}/100")
            lines.append(f"**主要组合**: {best_pair.get('most_common_combo', 'N/A')}")
            lines.append(f"**场均击杀**: {best_pair['avg_combined_kills']:.1f}")
            lines.append(f"**场均助攻**: {best_pair['avg_combined_assists']:.1f}\n")

        if len(pairs_sorted) > 1:
            lines.append("## 需要改进的配对\n")
            worst_pair = pairs_sorted[-1]['synergy']
            lines.append(f"**队友组合**: {worst_pair['player1_name']} + {worst_pair['player2_name']}")
            lines.append(f"**共同对局**: {worst_pair['games_together']}场")
            lines.append(f"**配合胜率**: {worst_pair['win_rate']:.1%}")
            lines.append(f"**默契分数**: {worst_pair['synergy_score']}/100")
            lines.append(f"**主要组合**: {worst_pair.get('most_common_combo', 'N/A')}\n")

    return "\n".join(lines)

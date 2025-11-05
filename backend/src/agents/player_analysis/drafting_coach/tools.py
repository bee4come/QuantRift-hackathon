"""
DraftingCoachAgent - Data Processing Tools

Core functions for BP analysis and recommendations.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from src.analytics import CompositionAnalyzer, load_counter_matrix
from src.agents.player_analysis.risk_forecaster.tools import load_power_curves
from src.utils.id_mappings import get_champion_name


def load_bp_data(
    power_curves_path: str = "data/baselines/power_curves.json",
    counter_matrix_path: str = "data/baselines/counter_matrix.json"
) -> tuple:
    """
    加载BP分析所需的基线数据

    Args:
        power_curves_path: Path to power_curves.json
        counter_matrix_path: Path to counter_matrix.json

    Returns:
        (power_curves_data, counter_matrix_data)
    """
    power_curves_data = load_power_curves(power_curves_path)
    counter_matrix_data = load_counter_matrix(counter_matrix_path)

    return power_curves_data, counter_matrix_data


def analyze_bp_state(
    our_composition: List[Dict[str, Any]],
    enemy_composition: List[Dict[str, Any]],
    power_curves_path: str = "data/baselines/power_curves.json",
    counter_matrix_path: str = "data/baselines/counter_matrix.json"
) -> Dict[str, Any]:
    """
    分析当前BP状态

    Args:
        our_composition: Our team composition (can be partial)
        enemy_composition: Enemy team composition (can be partial)
        power_curves_path: Path to power curves data
        counter_matrix_path: Path to counter matrix data

    Returns:
        Complete BP state analysis
    """
    # Load baseline data
    power_curves_data, counter_matrix_data = load_bp_data(
        power_curves_path, counter_matrix_path
    )

    # Create analyzer
    analyzer = CompositionAnalyzer(power_curves_data, counter_matrix_data)

    # Analyze compositions
    if our_composition:
        our_analysis = analyzer.analyze_composition(our_composition)
    else:
        our_analysis = None

    if enemy_composition:
        enemy_analysis = analyzer.analyze_composition(enemy_composition)
    else:
        enemy_analysis = None

    # Analyze matchup if both compositions exist
    if our_composition and enemy_composition:
        matchup_analysis = analyzer.analyze_matchup(our_composition, enemy_composition)
    else:
        matchup_analysis = None

    return {
        "our_composition": our_composition,
        "enemy_composition": enemy_composition,
        "our_analysis": our_analysis,
        "enemy_analysis": enemy_analysis,
        "matchup_analysis": matchup_analysis,
        "power_curves": power_curves_data,
        "counter_matrix": counter_matrix_data
    }


def generate_pick_recommendations(
    bp_state: Dict[str, Any],
    missing_roles: List[str],
    top_n: int = 5
) -> List[Dict[str, Any]]:
    """
    生成英雄选择建议

    Args:
        bp_state: BP state from analyze_bp_state()
        missing_roles: Roles that still need to be filled
        top_n: Number of recommendations per role

    Returns:
        List of champion recommendations with priorities
    """
    recommendations = []

    our_comp = bp_state["our_composition"]
    enemy_comp = bp_state["enemy_composition"]
    counter_matrix = bp_state["counter_matrix"]["champions"]
    power_curves = bp_state["power_curves"]["champions"]

    for role in missing_roles:
        role_recs = []

        # Find champions for this role
        for champ_id, champ_data in counter_matrix.items():
            if role not in champ_data["roles"]:
                continue

            # Calculate score based on counter matchups
            score = 0.5  # Base score
            counters_count = 0

            # Check matchups against enemy champions in same role
            role_data = champ_data["roles"][role]
            matchup_stats = role_data.get("matchup_stats", {})

            for enemy_member in enemy_comp:
                enemy_champ_id = str(enemy_member["champion_id"])
                enemy_role = enemy_member["role"]

                if enemy_role == role and enemy_champ_id in matchup_stats:
                    # Found a matchup
                    winrate = matchup_stats[enemy_champ_id]["winrate"]
                    score = winrate  # Use actual winrate as score
                    counters_count += 1
                    break

            # Get scaling information
            scaling_bonus = 0
            if champ_id in power_curves:
                champ_power_data = power_curves[champ_id]
                if role in champ_power_data["roles"]:
                    peak_time = champ_power_data["roles"][role].get("peak_time", 20)
                    # Prefer mid-game champions (balanced scaling)
                    if 15 <= peak_time <= 25:
                        scaling_bonus = 0.05

            final_score = score + scaling_bonus

            role_recs.append({
                "champion_id": champ_id,
                "champion_name": champ_data["name"],
                "role": role,
                "score": round(final_score, 3),
                "has_matchup_data": counters_count > 0
            })

        # Sort by score and take top N
        role_recs.sort(key=lambda x: x["score"], reverse=True)
        recommendations.extend(role_recs[:top_n])

    return recommendations


def generate_ban_recommendations(
    bp_state: Dict[str, Any],
    top_n: int = 5
) -> List[Dict[str, Any]]:
    """
    生成禁用建议

    Args:
        bp_state: BP state from analyze_bp_state()
        top_n: Number of ban recommendations

    Returns:
        List of champion ban recommendations
    """
    ban_recommendations = []

    our_comp = bp_state["our_composition"]
    counter_matrix = bp_state["counter_matrix"]["champions"]

    # Find champions that counter our composition
    for our_member in our_comp:
        our_champ_id = str(our_member["champion_id"])
        our_role = our_member["role"]

        if our_champ_id not in counter_matrix:
            continue

        our_champ_data = counter_matrix[our_champ_id]
        if our_role not in our_champ_data["roles"]:
            continue

        # Get counters (champions we struggle against)
        counters = our_champ_data["roles"][our_role].get("counters", {})

        for counter_champ_id, winrate in counters.items():
            # Lower winrate means stronger counter
            threat_score = 0.5 - winrate  # e.g., 0.35 winrate = 0.15 threat

            if counter_champ_id in counter_matrix:
                counter_name = counter_matrix[counter_champ_id]["name"]
            else:
                counter_name = f"Champion {counter_champ_id}"

            ban_recommendations.append({
                "champion_id": counter_champ_id,
                "champion_name": counter_name,
                "counters_our_champion": our_champ_id,
                "our_winrate_against": winrate,
                "threat_score": round(threat_score, 3),
                "role": our_role
            })

    # Sort by threat score and take top N
    ban_recommendations.sort(key=lambda x: x["threat_score"], reverse=True)

    # Deduplicate by champion_id
    seen = set()
    unique_bans = []
    for ban in ban_recommendations:
        if ban["champion_id"] not in seen:
            seen.add(ban["champion_id"])
            unique_bans.append(ban)
            if len(unique_bans) >= top_n:
                break

    return unique_bans


def format_bp_analysis_for_prompt(bp_state: Dict[str, Any]) -> str:
    """
    格式化BP分析数据为LLM友好的文本

    Args:
        bp_state: Complete BP state analysis

    Returns:
        Formatted text for LLM prompt
    """
    lines = []

    lines.append("# BP状态分析数据\n")

    # Our composition
    lines.append("## 我方阵容\n")
    if bp_state["our_composition"]:
        for member in bp_state["our_composition"]:
            champ_id = member["champion_id"]
            role = member["role"]
            champ_name = get_champion_name(champ_id)
            lines.append(f"- **{role}**: {champ_name} (ID: {champ_id})")

        if bp_state["our_analysis"]:
            analysis = bp_state["our_analysis"]
            lines.append(f"\n**角色覆盖**: {', '.join(analysis['role_coverage']['covered'])}")
            lines.append(f"**缺失角色**: {', '.join(analysis['role_coverage']['missing']) or '无'}")
            lines.append(f"**缩放模式**: {analysis['scaling_pattern']['description']}")
            lines.append(f"**平衡分数**: {analysis['balance_score']}/1.0")
            lines.append(f"**优势**: {', '.join(analysis['strengths'])}")
            lines.append(f"**劣势**: {', '.join(analysis['weaknesses'])}")
    else:
        lines.append("- 暂无已选英雄")

    lines.append("")

    # Enemy composition
    lines.append("## 敌方阵容\n")
    if bp_state["enemy_composition"]:
        for member in bp_state["enemy_composition"]:
            champ_id = member["champion_id"]
            role = member["role"]
            champ_name = get_champion_name(champ_id)
            lines.append(f"- **{role}**: {champ_name} (ID: {champ_id})")

        if bp_state["enemy_analysis"]:
            analysis = bp_state["enemy_analysis"]
            lines.append(f"\n**角色覆盖**: {', '.join(analysis['role_coverage']['covered'])}")
            lines.append(f"**缺失角色**: {', '.join(analysis['role_coverage']['missing']) or '无'}")
            lines.append(f"**缩放模式**: {analysis['scaling_pattern']['description']}")
            lines.append(f"**平衡分数**: {analysis['balance_score']}/1.0")
    else:
        lines.append("- 暂无已选英雄")

    lines.append("")

    # Matchup analysis
    if bp_state["matchup_analysis"]:
        lines.append("## 分路对抗分析\n")
        matchup = bp_state["matchup_analysis"]

        if "lane_matchups" in matchup and matchup["lane_matchups"]:
            lines.append("| 分路 | 优势 | 评估 |")
            lines.append("|------|------|------|")

            for lane in matchup["lane_matchups"]:
                role = lane["role"]
                advantage = lane["advantage"]
                assessment = lane["assessment"]
                assessment_cn = {
                    "strong_advantage": "强势",
                    "slight_advantage": "小优",
                    "even": "均势",
                    "slight_disadvantage": "小劣",
                    "strong_disadvantage": "劣势"
                }.get(assessment, assessment)

                lines.append(f"| {role} | {advantage:+.3f} | {assessment_cn} |")

        lines.append(f"\n**整体阵容优势**: {matchup['overall_advantage']:+.2f}")

    return "\n".join(lines)

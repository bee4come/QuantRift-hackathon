"""
Multi-Version Analysis Prompts
"""

from typing import Dict, Any, List
from src.utils.id_mappings import get_champion_name


def build_multi_version_prompt(analysis: Dict[str, Any]) -> str:
    """
    Build multi-version analysis prompt

    Args:
        analysis: Comprehensive analysis data package

    Returns:
        str: Complete prompt
    """
    summary = analysis["summary"]
    trends = analysis["trends"]
    transitions = analysis["transitions"]
    insights = analysis["insights"]

    # Build core champion trend data
    core_heroes_text = _build_core_heroes_text(trends)

    # Build transition point data
    transitions_text = _build_transitions_text(transitions)

    # Build patch statistics table
    patch_stats_table = _format_patch_stats(trends)

    prompt = f"""You are a senior League of Legends data analyst and coach. Based on the player's {summary['total_games']} match data during {summary['patch_range']}, generate a professional cross-patch adaptation analysis report.

## Data Overview

**Patch Range**: {summary['patch_range']} ({summary['total_patches']} patches)
**Total Matches**: {summary['total_games']} games
**Average per Patch**: {summary['avg_games_per_patch']} games
**Champion Pool Breadth**: {summary['unique_champion_roles']} champion-role combinations

**Key Metrics**:
- Most Active Patch: {insights['most_active_patch']} ({trends['total_games_by_patch'][insights['most_active_patch']]} games)
- Most Stable Patch: {insights['most_stable_patch']} (stability {trends['performance_stability'][insights['most_stable_patch']]['consistency_score']:.2%})
- Largest Pool: {insights['largest_pool']} ({trends['champion_pool_size'][insights['largest_pool']]} champions)

## Core Champion Cross-Patch Performance
{core_heroes_text}

## Key Patch Transition Points
{transitions_text}

## Patch Activity and Stability

{patch_stats_table}

---

**Please generate a professional report containing the following content**:

1. **Executive Summary** - Within 300 words, summarize the player's overall adaptation capability across {summary['total_patches']} patches
2. **Patch Adaptation Assessment** - Analyze player's performance in patch transitions (excellent/good/needs improvement)
3. **Core Champion Pool Analysis** - Identify stable champions, rising champions, declining champions
4. **Key Transition Point Interpretation** - Explain significant patch transition points and their impact
5. **Champion Pool Planning Recommendations** - Based on trends, provide specific champion selection and abandonment recommendations
6. **Gameplay Habit Insights** - From game volume and champion selection, understand player style
7. **Future Patch Recommendations** - Provide champion pool and build direction for patch 15.20+

Requirements:
- Data-driven, all conclusions must be based on provided data
- Highlight key points, avoid narrative listing
- Specific and actionable, avoid generalities
- Use professional terminology while remaining understandable
- Markdown format, use tables and lists to enhance readability
"""

    return prompt


def _build_core_heroes_text(trends: Dict[str, Any]) -> str:
    """Build core champion text"""
    core_heroes_text = ""

    for cr_key, data in list(trends["winrate_trends"].items())[:10]:  # Limit to top 10
        champ_id = data["champion_id"]
        role = data["role"]
        patches_data = data["patches"]

        # Calculate winrate trend
        winrates = [p["winrate"] for p in patches_data.values()]
        if len(winrates) >= 2:
            trend_direction = "Rising" if winrates[-1] > winrates[0] else "Declining"
            change = (winrates[-1] - winrates[0]) * 100

            champ_name = get_champion_name(champ_id)
            core_heroes_text += f"\n- **{champ_name} (ID: {champ_id}, {role})**:\n"
            core_heroes_text += f"  - Patches played: {len(patches_data)}\n"
            core_heroes_text += f"  - Total games: {sum(p['games'] for p in patches_data.values())}\n"
            core_heroes_text += f"  - Winrate trend: {trend_direction} ({change:+.1f}%)\n"
            core_heroes_text += f"  - Patch details: "
            for patch in sorted(patches_data.keys()):
                p_data = patches_data[patch]
                core_heroes_text += f"{patch}({p_data['games']}games,{p_data['winrate']:.1%}) "
            core_heroes_text += "\n"

    return core_heroes_text


def _build_transitions_text(transitions: List[Dict[str, Any]]) -> str:
    """Build transition point text"""
    transitions_text = ""

    for t in transitions:
        if t["is_significant"]:
            transitions_text += f"\n- **{t['from_patch']} → {t['to_patch']}**: "
            transitions_text += f"Game volume {t['games_change_pct']:+.0f}%, "
            transitions_text += f"Champion pool {t['pool_change_pct']:+.0f}%, "
            transitions_text += f"Stability {t['stability_change']:+.2f}"

    return transitions_text


def _format_patch_stats(trends: Dict[str, Any]) -> str:
    """Format patch statistics data as table"""
    lines = [
        "| Patch | Games | Champion Pool | Avg Winrate | Stability |",
        "|-------|-------|---------------|-------------|-----------|"
    ]

    for patch in sorted(trends["patches"]):
        games = trends["total_games_by_patch"][patch]
        pool_size = trends["champion_pool_size"][patch]

        if patch in trends["performance_stability"]:
            avg_wr = trends["performance_stability"][patch]["avg_winrate"]
            stability = trends["performance_stability"][patch]["consistency_score"]
            lines.append(f"| {patch} | {games} | {pool_size} | {avg_wr:.1%} | {stability:.2%} |")
        else:
            lines.append(f"| {patch} | {games} | {pool_size} | - | - |")

    return "\n".join(lines)

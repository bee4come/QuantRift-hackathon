"""
RoleSpecializationAgent - Data Processing Tools

Analyzes player specialization and mastery of a specific role.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from datetime import datetime

from src.core.statistical_utils import wilson_ci_tuple as wilson_confidence_interval
from src.utils.id_mappings import get_champion_name


def load_role_data(packs_dir: str, role: str, all_packs_data: List[Dict] = None) -> Dict[str, Any]:
    """
    从所有pack文件中提取指定位置的数据

    Args:
        packs_dir: Pack文件目录
        role: 位置 (TOP/JUNGLE/MIDDLE/BOTTOM/SUPPORT)
        all_packs_data: 预加载的所有pack数据（可选，来自AgentContext缓存）

    Returns:
        按patch组织的位置数据
    """
    role_data = {}

    # 如果提供了缓存数据，直接使用
    if all_packs_data is not None:
        packs = all_packs_data
    else:
        # 否则从文件系统读取
        packs_dir = Path(packs_dir)
        pack_files = sorted(packs_dir.glob("pack_*.json"))
        packs = []
        for pack_file in pack_files:
            with open(pack_file, 'r', encoding='utf-8') as f:
                packs.append(json.load(f))

    # 处理pack数据
    for pack in packs:

        patch = pack["patch"]
        generated_at = pack.get("generation_timestamp", "")

        # 提取该位置的所有英雄数据
        role_champions = []
        for cr in pack.get("by_cr", []):
            if cr["role"] == role:
                role_champions.append(cr)

        if role_champions:
            role_data[patch] = {
                "patch": patch,
                "generated_at": generated_at,
                "champions": role_champions,
                "total_games": sum(c["games"] for c in role_champions),
                "total_wins": sum(c["wins"] for c in role_champions)
            }

    return role_data


def analyze_champion_pool(role_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析英雄池的广度和深度

    Args:
        role_data: 位置数据（按patch组织）

    Returns:
        英雄池分析结果
    """
    # 聚合每个英雄的数据
    champion_stats = defaultdict(lambda: {
        "games": 0,
        "wins": 0,
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "patches": set()
    })

    for patch, data in role_data.items():
        for champ_data in data["champions"]:
            champ_id = champ_data["champ_id"]
            champion_stats[champ_id]["games"] += champ_data["games"]
            champion_stats[champ_id]["wins"] += champ_data["wins"]
            champion_stats[champ_id]["kills"] += champ_data.get("total_kills", 0)
            champion_stats[champ_id]["deaths"] += champ_data.get("total_deaths", 0)
            champion_stats[champ_id]["assists"] += champ_data.get("total_assists", 0)
            champion_stats[champ_id]["patches"].add(patch)

    # 分类英雄
    core_champions = []  # 30+场
    secondary_champions = []  # 10-29场
    experimental_champions = []  # <10场

    for champ_id, stats in champion_stats.items():
        games = stats["games"]
        wins = stats["wins"]
        winrate = wins / games if games > 0 else 0
        ci_lower, ci_upper = wilson_confidence_interval(wins, games)

        deaths = stats["deaths"]
        kda = (stats["kills"] + stats["assists"]) / deaths if deaths > 0 else 0

        champion_info = {
            "champion_id": champ_id,
            "champion_name": get_champion_name(champ_id),
            "games": games,
            "wins": wins,
            "winrate": round(winrate, 3),
            "ci_lower": round(ci_lower, 3),
            "ci_upper": round(ci_upper, 3),
            "avg_kda": round(kda, 2),
            "patches_played": len(stats["patches"])
        }

        if games >= 30:
            core_champions.append(champion_info)
        elif games >= 10:
            secondary_champions.append(champion_info)
        else:
            experimental_champions.append(champion_info)

    # 按游戏数排序
    core_champions.sort(key=lambda x: x["games"], reverse=True)
    secondary_champions.sort(key=lambda x: x["games"], reverse=True)
    experimental_champions.sort(key=lambda x: x["games"], reverse=True)

    # 计算多样性分数（Shannon熵的归一化版本）
    total_games = sum(c["games"] for c in champion_stats.values())
    if total_games > 0:
        entropy = 0
        for stats in champion_stats.values():
            p = stats["games"] / total_games
            if p > 0:
                entropy -= p * (p ** 0.5)  # 简化版熵计算
        diversity_score = min(entropy, 1.0)
    else:
        diversity_score = 0

    return {
        "breadth": {
            "total_champions": len(champion_stats),
            "core_champions": len(core_champions),
            "secondary_champions": len(secondary_champions),
            "experimental_champions": len(experimental_champions)
        },
        "depth": {
            "core": core_champions,
            "secondary": secondary_champions,
            "experimental": experimental_champions
        },
        "diversity_score": round(diversity_score, 3)
    }


def analyze_role_performance(role_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析位置整体表现

    Args:
        role_data: 位置数据（按patch组织）

    Returns:
        位置表现分析结果
    """
    total_games = sum(d["total_games"] for d in role_data.values())
    total_wins = sum(d["total_wins"] for d in role_data.values())

    if total_games == 0:
        return {}

    overall_winrate = total_wins / total_games
    ci_lower, ci_upper = wilson_confidence_interval(total_wins, total_games)

    # 按patch分析表现
    patches_performance = []
    for patch in sorted(role_data.keys()):
        data = role_data[patch]
        games = data["total_games"]
        wins = data["total_wins"]

        if games > 0:
            winrate = wins / games
            p_ci_lower, p_ci_upper = wilson_confidence_interval(wins, games)

            patches_performance.append({
                "patch": patch,
                "games": games,
                "wins": wins,
                "winrate": round(winrate, 3),
                "ci_lower": round(p_ci_lower, 3),
                "ci_upper": round(p_ci_upper, 3)
            })

    # 计算趋势
    trend = "insufficient_data"
    if len(patches_performance) >= 3:
        early_patches = patches_performance[:len(patches_performance)//2]
        late_patches = patches_performance[len(patches_performance)//2:]

        early_avg = sum(p["winrate"] for p in early_patches) / len(early_patches)
        late_avg = sum(p["winrate"] for p in late_patches) / len(late_patches)

        if late_avg > early_avg + 0.05:
            trend = "improving"
        elif late_avg < early_avg - 0.05:
            trend = "declining"
        else:
            trend = "stable"

    return {
        "total_games": total_games,
        "total_wins": total_wins,
        "overall_winrate": round(overall_winrate, 3),
        "ci_lower": round(ci_lower, 3),
        "ci_upper": round(ci_upper, 3),
        "version_coverage": len(role_data),
        "patches_performance": patches_performance,
        "performance_trend": trend
    }


def calculate_role_mastery_score(
    total_games: int,
    overall_winrate: float,
    ci_width: float,
    champion_pool: Dict[str, Any],
    version_coverage: int
) -> Tuple[str, int]:
    """
    计算位置掌握度评分

    评分组成：
    1. Volume Score (0-25): 游戏量
    2. Performance Score (0-40): 胜率表现
    3. Champion Pool Score (0-20): 英雄池
    4. Consistency Score (0-15): 稳定性

    Args:
        total_games: 总游戏数
        overall_winrate: 整体胜率
        ci_width: CI区间宽度
        champion_pool: 英雄池分析结果
        version_coverage: 版本覆盖数

    Returns:
        (评级, 分数)
    """
    score = 0

    # 1. Volume Score (0-25)
    if total_games >= 100:
        score += 25
    elif total_games >= 75:
        score += 20
    elif total_games >= 50:
        score += 18
    elif total_games >= 30:
        score += 15
    else:
        score += 10

    # 2. Performance Score (0-40)
    if overall_winrate >= 0.60:
        score += 40
    elif overall_winrate >= 0.55:
        score += 35
    elif overall_winrate >= 0.52:
        score += 30
    elif overall_winrate >= 0.50:
        score += 25
    elif overall_winrate >= 0.48:
        score += 20
    else:
        score += 15

    # 3. Champion Pool Score (0-20)
    breadth = champion_pool["breadth"]
    depth = champion_pool["depth"]

    # 广度分数 (0-7)
    total_champs = breadth["total_champions"]
    if total_champs >= 10:
        score += 7
    elif total_champs >= 7:
        score += 5
    elif total_champs >= 5:
        score += 3
    else:
        score += 1

    # 深度分数 (0-10)
    core_count = breadth["core_champions"]
    if core_count >= 5:
        score += 10
    elif core_count >= 3:
        score += 7
    elif core_count >= 2:
        score += 5
    elif core_count >= 1:
        score += 3

    # 多样性分数 (0-3)
    diversity = champion_pool["diversity_score"]
    score += int(diversity * 3)

    # 4. Consistency Score (0-15)
    if ci_width < 0.10:
        score += 15
    elif ci_width < 0.15:
        score += 12
    elif ci_width < 0.20:
        score += 9
    elif ci_width < 0.25:
        score += 6
    else:
        score += 3

    # 评级映射
    if score >= 90:
        grade = "S"
    elif score >= 80:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 50:
        grade = "D"
    else:
        grade = "F"

    return grade, score


def generate_comprehensive_role_analysis(
    role: str,
    packs_dir: str,
    all_packs_data: List[Dict] = None
) -> Dict[str, Any]:
    """
    生成全面的位置专精分析

    Args:
        role: 位置
        packs_dir: Pack文件目录
        all_packs_data: 预加载的所有pack数据（可选，来自AgentContext缓存）

    Returns:
        完整的分析数据
    """
    # 1. 加载位置数据（优先使用缓存）
    role_data = load_role_data(packs_dir, role, all_packs_data)

    if not role_data:
        raise ValueError(f"No data found for role {role}")

    # 2. 分析整体表现
    performance = analyze_role_performance(role_data)

    # 3. 分析英雄池
    champion_pool = analyze_champion_pool(role_data)

    # 4. 计算掌握度评分
    ci_width = performance["ci_upper"] - performance["ci_lower"]
    mastery_grade, mastery_score = calculate_role_mastery_score(
        total_games=performance["total_games"],
        overall_winrate=performance["overall_winrate"],
        ci_width=ci_width,
        champion_pool=champion_pool,
        version_coverage=performance["version_coverage"]
    )

    # 5. 组装完整分析
    analysis = {
        "role": role,
        "summary": {
            "total_games": performance["total_games"],
            "overall_winrate": performance["overall_winrate"],
            "ci_lower": performance["ci_lower"],
            "ci_upper": performance["ci_upper"],
            "version_coverage": performance["version_coverage"],
            "role_mastery_score": mastery_grade,
            "proficiency_score": mastery_score
        },
        "champion_pool": champion_pool,
        "performance": performance,
        "metadata": {
            "analysis_timestamp": datetime.now().isoformat(),
            "patches_analyzed": sorted(role_data.keys())
        }
    }

    return analysis


def format_analysis_for_prompt(analysis: Dict[str, Any]) -> str:
    """
    格式化分析数据为LLM友好的文本

    Args:
        analysis: 分析数据

    Returns:
        格式化的文本
    """
    lines = []

    # 总体概览
    role = analysis["role"]
    summary = analysis["summary"]
    lines.append(f"# 位置专精分析数据 - {role}\n")
    lines.append(f"**掌握度评分**: {summary['role_mastery_score']} ({summary['proficiency_score']}分)")
    lines.append(f"**总场次**: {summary['total_games']}")
    lines.append(f"**整体胜率**: {summary['overall_winrate']:.1%} (95% CI: {summary['ci_lower']:.1%} - {summary['ci_upper']:.1%})")
    lines.append(f"**版本覆盖**: {summary['version_coverage']}个版本")
    lines.append("")

    # 英雄池分析
    pool = analysis["champion_pool"]
    breadth = pool["breadth"]
    lines.append("## 英雄池分析")
    lines.append(f"**总英雄数**: {breadth['total_champions']}")
    lines.append(f"**核心英雄**: {breadth['core_champions']}个 (30+场)")
    lines.append(f"**次要英雄**: {breadth['secondary_champions']}个 (10-29场)")
    lines.append(f"**实验英雄**: {breadth['experimental_champions']}个 (<10场)")
    lines.append(f"**多样性评分**: {pool['diversity_score']:.3f}")
    lines.append("")

    # 核心英雄详情
    if pool["depth"]["core"]:
        lines.append("### 核心英雄详情 (30+场)")
        for champ in pool["depth"]["core"]:
            lines.append(f"- **{champ['champion_name']} (ID: {champ['champion_id']})**: {champ['games']}场, "
                        f"{champ['winrate']:.1%}胜率 (CI: {champ['ci_lower']:.1%}-{champ['ci_upper']:.1%}), "
                        f"KDA {champ['avg_kda']:.2f}, {champ['patches_played']}个版本")
        lines.append("")

    # 次要英雄
    if pool["depth"]["secondary"]:
        lines.append("### 次要英雄 (10-29场)")
        for champ in pool["depth"]["secondary"]:
            lines.append(f"- **{champ['champion_name']} (ID: {champ['champion_id']})**: {champ['games']}场, {champ['winrate']:.1%}胜率")
        lines.append("")

    # 版本表现
    perf = analysis["performance"]
    lines.append("## 版本表现趋势")
    lines.append(f"**表现趋势**: {perf['performance_trend']}")
    lines.append("")
    for patch_data in perf["patches_performance"]:
        lines.append(f"- **{patch_data['patch']}**: {patch_data['winrate']:.1%} ({patch_data['wins']}胜/{patch_data['games']}场)")

    return "\n".join(lines)

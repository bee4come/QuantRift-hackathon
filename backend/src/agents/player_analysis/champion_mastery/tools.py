"""
ChampionMasteryAgent - Data Processing Tools

Analyzes player mastery of a single champion across all available match history.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from datetime import datetime

from src.core.statistical_utils import wilson_ci_tuple as wilson_confidence_interval
from src.utils.id_mappings import get_champion_name


def load_champion_data(packs_dir: str, champion_id: int, all_packs_data: List[Dict] = None, time_range: str = None) -> Dict[str, Any]:
    """
    从所有pack文件中提取指定英雄的数据

    Args:
        packs_dir: Pack文件目录
        champion_id: 英雄ID
        all_packs_data: 预加载的所有pack数据（可选，来自AgentContext缓存）
        time_range: Time range filter
            - "2024-01-01": Load data from 2024-01-01 to today
            - "past-365": Load data from past 365 days
            - None: Load all available data

    Returns:
        按patch组织的英雄数据，包含timeline信息
    """
    from datetime import datetime, timedelta
    
    champion_data = {}

    # Calculate time filter if needed
    cutoff_timestamp = None
    if time_range == "2024-01-01":
        cutoff_timestamp = datetime(2024, 1, 1).timestamp()
    elif time_range == "past-365":
        cutoff_timestamp = (datetime.now() - timedelta(days=365)).timestamp()

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
                pack_data = json.load(f)
                
                # Apply time range filter if specified
                if cutoff_timestamp and "generation_timestamp" in pack_data:
                    pack_timestamp = pack_data["generation_timestamp"]
                    # If timestamp is string, convert to timestamp
                    if isinstance(pack_timestamp, str):
                        pack_timestamp = datetime.fromisoformat(pack_timestamp.replace('Z', '+00:00')).timestamp()
                    
                    # Skip if before cutoff
                    if pack_timestamp < cutoff_timestamp:
                        continue
                
                packs.append(pack_data)

    # 处理pack数据
    for pack in packs:

        patch = pack["patch"]
        generated_at = pack.get("generation_timestamp", "")

        # 提取该英雄的所有角色数据
        champion_roles = []
        for cr in pack.get("by_cr", []):
            if cr["champ_id"] == champion_id:
                champion_roles.append(cr)

        if champion_roles:
            champion_data[patch] = {
                "patch": patch,
                "generated_at": generated_at,
                "roles": champion_roles,
                "total_games": sum(r["games"] for r in champion_roles),
                "total_wins": sum(r["wins"] for r in champion_roles)
            }

    return champion_data


def analyze_learning_curve(champion_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析学习曲线：按时间顺序分段分析表现

    将游戏按时间顺序分为三个阶段：
    - Early (1-30场): 初期学习
    - Mid (31-100场): 技能发展
    - Late (101+场): 掌握阶段

    Args:
        champion_data: 英雄数据（按patch组织）

    Returns:
        学习曲线分析结果
    """
    # 按时间排序所有游戏
    all_games = []
    for patch, data in sorted(champion_data.items()):
        for role_data in data["roles"]:
            all_games.append({
                "patch": patch,
                "role": role_data["role"],
                "games": role_data["games"],
                "wins": role_data["wins"],
                "total_kills": role_data.get("total_kills", 0),
                "total_deaths": role_data.get("total_deaths", 0),
                "total_assists": role_data.get("total_assists", 0),
                "generated_at": data["generated_at"]
            })

    # 按generated_at排序（时间顺序）
    all_games.sort(key=lambda x: x["generated_at"])

    # 累计游戏数
    cumulative_games = 0
    phases = {
        "early": {"games": [], "total_games": 0, "total_wins": 0, "kills": 0, "deaths": 0, "assists": 0},
        "mid": {"games": [], "total_games": 0, "total_wins": 0, "kills": 0, "deaths": 0, "assists": 0},
        "late": {"games": [], "total_games": 0, "total_wins": 0, "kills": 0, "deaths": 0, "assists": 0}
    }

    for game in all_games:
        game_count = game["games"]

        # 确定每场游戏属于哪个阶段
        for i in range(game_count):
            cumulative_games += 1

            if cumulative_games <= 30:
                phase = "early"
            elif cumulative_games <= 100:
                phase = "mid"
            else:
                phase = "late"

            # 平均分配wins/kills/deaths/assists
            phases[phase]["total_games"] += 1
            phases[phase]["total_wins"] += game["wins"] / game_count
            phases[phase]["kills"] += game["total_kills"] / game_count
            phases[phase]["deaths"] += game["total_deaths"] / game_count
            phases[phase]["assists"] += game["total_assists"] / game_count
            phases[phase]["games"].append({
                "patch": game["patch"],
                "role": game["role"]
            })

    # 计算每个阶段的统计数据
    learning_curve = {}
    for phase_name, phase_data in phases.items():
        if phase_data["total_games"] > 0:
            wins = int(phase_data["total_wins"])
            games = phase_data["total_games"]

            winrate = wins / games if games > 0 else 0
            ci_lower, ci_upper = wilson_confidence_interval(wins, games)

            deaths = phase_data["deaths"]
            kda = (phase_data["kills"] + phase_data["assists"]) / deaths if deaths > 0 else 0

            learning_curve[phase_name] = {
                "games": int(games),
                "wins": wins,
                "winrate": round(winrate, 3),
                "ci_lower": round(ci_lower, 3),
                "ci_upper": round(ci_upper, 3),
                "avg_kda": round(kda, 2),
                "total_kills": int(phase_data["kills"]),
                "total_deaths": int(phase_data["deaths"]),
                "total_assists": int(phase_data["assists"])
            }

    # 计算趋势
    trend = "insufficient_data"
    if "early" in learning_curve and "late" in learning_curve:
        early_wr = learning_curve["early"]["winrate"]
        late_wr = learning_curve["late"]["winrate"]

        if late_wr > early_wr + 0.05:
            trend = "improving"
        elif late_wr < early_wr - 0.05:
            trend = "declining"
        else:
            trend = "stable"

    return {
        "phases": learning_curve,
        "trend": trend,
        "total_games_analyzed": cumulative_games
    }


def analyze_position_specialization(champion_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析位置专精：对比不同位置的表现

    Args:
        champion_data: 英雄数据（按patch组织）

    Returns:
        位置专精分析结果
    """
    # 聚合每个位置的数据
    role_stats = defaultdict(lambda: {
        "games": 0,
        "wins": 0,
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "patches": set()
    })

    for patch, data in champion_data.items():
        for role_data in data["roles"]:
            role = role_data["role"]
            role_stats[role]["games"] += role_data["games"]
            role_stats[role]["wins"] += role_data["wins"]
            role_stats[role]["kills"] += role_data.get("total_kills", 0)
            role_stats[role]["deaths"] += role_data.get("total_deaths", 0)
            role_stats[role]["assists"] += role_data.get("total_assists", 0)
            role_stats[role]["patches"].add(patch)

    # 计算每个位置的统计指标
    position_analysis = {}
    for role, stats in role_stats.items():
        games = stats["games"]
        wins = stats["wins"]

        if games > 0:
            winrate = wins / games
            ci_lower, ci_upper = wilson_confidence_interval(wins, games)

            deaths = stats["deaths"]
            kda = (stats["kills"] + stats["assists"]) / deaths if deaths > 0 else 0

            # 评分逻辑
            score = 0
            # 游戏量 (0-30分)
            if games >= 50:
                score += 30
            elif games >= 20:
                score += 20
            elif games >= 10:
                score += 10

            # 胜率 (0-50分)
            if winrate >= 0.60:
                score += 50
            elif winrate >= 0.55:
                score += 40
            elif winrate >= 0.50:
                score += 30
            elif winrate >= 0.45:
                score += 20
            else:
                score += 10

            # CI宽度（一致性） (0-20分)
            ci_width = ci_upper - ci_lower
            if ci_width < 0.10:
                score += 20
            elif ci_width < 0.15:
                score += 15
            elif ci_width < 0.20:
                score += 10
            else:
                score += 5

            # 评级映射
            if score >= 85:
                rank = "S"
            elif score >= 75:
                rank = "A"
            elif score >= 65:
                rank = "B"
            elif score >= 55:
                rank = "C"
            else:
                rank = "D"

            position_analysis[role] = {
                "games": games,
                "wins": wins,
                "winrate": round(winrate, 3),
                "ci_lower": round(ci_lower, 3),
                "ci_upper": round(ci_upper, 3),
                "avg_kda": round(kda, 2),
                "patches_played": len(stats["patches"]),
                "rank": rank,
                "score": score
            }

    # 找出最佳位置
    best_role = None
    best_score = 0
    for role, stats in position_analysis.items():
        if stats["score"] > best_score:
            best_score = stats["score"]
            best_role = role

    return {
        "roles": position_analysis,
        "best_role": best_role,
        "total_roles_played": len(position_analysis)
    }


def analyze_version_adaptation(champion_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析版本适应性：跨版本的表现稳定性

    Args:
        champion_data: 英雄数据（按patch组织）

    Returns:
        版本适应性分析结果
    """
    patches_performance = []

    for patch in sorted(champion_data.keys()):
        data = champion_data[patch]
        total_games = data["total_games"]
        total_wins = data["total_wins"]

        if total_games > 0:
            winrate = total_wins / total_games
            ci_lower, ci_upper = wilson_confidence_interval(total_wins, total_games)

            patches_performance.append({
                "patch": patch,
                "games": total_games,
                "wins": total_wins,
                "winrate": round(winrate, 3),
                "ci_lower": round(ci_lower, 3),
                "ci_upper": round(ci_upper, 3),
                "ci_width": round(ci_upper - ci_lower, 3)
            })

    # 计算趋势
    trend = "insufficient_data"
    if len(patches_performance) >= 3:
        early_patches = patches_performance[:len(patches_performance)//2]
        late_patches = patches_performance[len(patches_performance)//2:]

        early_avg_wr = sum(p["winrate"] for p in early_patches) / len(early_patches)
        late_avg_wr = sum(p["winrate"] for p in late_patches) / len(late_patches)

        if late_avg_wr > early_avg_wr + 0.05:
            trend = "improving"
        elif late_avg_wr < early_avg_wr - 0.05:
            trend = "declining"
        else:
            trend = "stable"

    # 计算稳定性（CI宽度的标准差）
    if len(patches_performance) > 1:
        ci_widths = [p["ci_width"] for p in patches_performance]
        avg_ci_width = sum(ci_widths) / len(ci_widths)
        variance = sum((w - avg_ci_width) ** 2 for w in ci_widths) / len(ci_widths)
        stability = 1 / (1 + variance)  # 越稳定，值越接近1
    else:
        stability = 0.5

    return {
        "patches": patches_performance,
        "version_coverage": len(patches_performance),
        "performance_trend": trend,
        "stability_score": round(stability, 3)
    }


def calculate_mastery_score(
    total_games: int,
    overall_winrate: float,
    ci_width: float,
    version_coverage: int,
    position_analysis: Dict[str, Any]
) -> Tuple[str, int]:
    """
    计算英雄掌握度评分

    评分组成：
    1. Volume Score (0-30): 游戏量
    2. Performance Score (0-40): 胜率表现
    3. Consistency Score (0-15): 稳定性（CI宽度）
    4. Adaptation Score (0-15): 版本适应（版本覆盖度）

    Args:
        total_games: 总游戏数
        overall_winrate: 整体胜率
        ci_width: CI区间宽度
        version_coverage: 版本覆盖数
        position_analysis: 位置分析结果

    Returns:
        (评级, 分数)
    """
    score = 0

    # 1. Volume Score (0-30)
    if total_games >= 100:
        score += 30
    elif total_games >= 50:
        score += 25
    elif total_games >= 30:
        score += 20
    elif total_games >= 20:
        score += 15
    else:
        score += 10

    # 2. Performance Score (0-40)
    # 基础胜率分
    base_wr_score = 0
    if overall_winrate >= 0.60:
        base_wr_score = 40
    elif overall_winrate >= 0.55:
        base_wr_score = 35
    elif overall_winrate >= 0.52:
        base_wr_score = 30
    elif overall_winrate >= 0.50:
        base_wr_score = 25
    elif overall_winrate >= 0.48:
        base_wr_score = 20
    else:
        base_wr_score = 15

    score += base_wr_score

    # 3. Consistency Score (0-15)
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

    # 4. Adaptation Score (0-15)
    # 版本覆盖度
    version_score = min(version_coverage * 1.5, 10)
    score += int(version_score)

    # 位置专精度（有高分位置加分）
    best_role_rank = position_analysis.get("best_role")
    if best_role_rank:
        best_role_stats = position_analysis["roles"].get(best_role_rank, {})
        if best_role_stats.get("rank") in ["S", "A"]:
            score += 5
        elif best_role_stats.get("rank") == "B":
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


def generate_comprehensive_mastery_analysis(
    champion_id: int,
    packs_dir: str,
    all_packs_data: List[Dict] = None,
    time_range: str = None
) -> Dict[str, Any]:
    """
    生成全面的英雄掌握度分析

    Args:
        champion_id: 英雄ID
        packs_dir: Pack文件目录
        all_packs_data: 预加载的所有pack数据（可选，来自AgentContext缓存）
        time_range: Time range filter

    Returns:
        完整的分析数据
    """
    # 1. 加载英雄数据（优先使用缓存）
    champion_data = load_champion_data(packs_dir, champion_id, all_packs_data, time_range=time_range)

    if not champion_data:
        raise ValueError(f"No data found for champion_id {champion_id}")

    # 2. 计算整体统计
    total_games = sum(d["total_games"] for d in champion_data.values())
    total_wins = sum(d["total_wins"] for d in champion_data.values())
    overall_winrate = total_wins / total_games if total_games > 0 else 0
    ci_lower, ci_upper = wilson_confidence_interval(total_wins, total_games)
    ci_width = ci_upper - ci_lower

    # 3. 学习曲线分析
    learning_curve = analyze_learning_curve(champion_data)

    # 4. 位置专精分析
    position_analysis = analyze_position_specialization(champion_data)

    # 5. 版本适应性分析
    version_adaptation = analyze_version_adaptation(champion_data)

    # 6. 计算掌握度评分
    mastery_grade, mastery_score = calculate_mastery_score(
        total_games=total_games,
        overall_winrate=overall_winrate,
        ci_width=ci_width,
        version_coverage=version_adaptation["version_coverage"],
        position_analysis=position_analysis
    )

    # 7. 组装完整分析
    analysis = {
        "champion_id": champion_id,
        "summary": {
            "total_games": total_games,
            "total_wins": total_wins,
            "overall_winrate": round(overall_winrate, 3),
            "ci_lower": round(ci_lower, 3),
            "ci_upper": round(ci_upper, 3),
            "ci_width": round(ci_width, 3),
            "version_coverage": version_adaptation["version_coverage"],
            "mastery_grade": mastery_grade,
            "mastery_score": mastery_score
        },
        "learning_curve": learning_curve,
        "position_analysis": position_analysis,
        "version_adaptation": version_adaptation,
        "metadata": {
            "analysis_timestamp": datetime.now().isoformat(),
            "patches_analyzed": sorted(champion_data.keys())
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
    summary = analysis["summary"]
    champ_id = analysis['champion_id']
    champ_name = get_champion_name(champ_id)
    lines.append("# 英雄掌握度分析数据\n")
    lines.append(f"**英雄**: {champ_name} (ID: {champ_id})")
    lines.append(f"**掌握度评分**: {summary['mastery_grade']} ({summary['mastery_score']}分)")
    lines.append(f"**总场次**: {summary['total_games']}")
    lines.append(f"**总胜场**: {summary['total_wins']}")
    lines.append(f"**整体胜率**: {summary['overall_winrate']:.1%} (95% CI: {summary['ci_lower']:.1%} - {summary['ci_upper']:.1%})")
    lines.append(f"**版本覆盖**: {summary['version_coverage']}个版本")
    lines.append("")

    # 学习曲线
    lc = analysis["learning_curve"]
    lines.append("## 学习曲线分析")
    lines.append(f"**整体趋势**: {lc['trend']}")
    lines.append(f"**分析总场次**: {lc['total_games_analyzed']}")
    lines.append("")

    for phase_name, phase_data in lc["phases"].items():
        phase_label = {"early": "早期阶段", "mid": "中期阶段", "late": "后期阶段"}[phase_name]
        lines.append(f"### {phase_label} (前 {phase_data['games']} 场)")
        lines.append(f"- 胜率: {phase_data['winrate']:.1%} ({phase_data['wins']}胜 / {phase_data['games']}场)")
        lines.append(f"- 置信区间: {phase_data['ci_lower']:.1%} - {phase_data['ci_upper']:.1%}")
        lines.append(f"- 平均KDA: {phase_data['avg_kda']:.2f}")
        lines.append(f"- 总击杀/死亡/助攻: {phase_data['total_kills']}/{phase_data['total_deaths']}/{phase_data['total_assists']}")
        lines.append("")

    # 位置专精
    pos = analysis["position_analysis"]
    lines.append("## 位置专精分析")
    lines.append(f"**最佳位置**: {pos['best_role']}")
    lines.append(f"**使用位置数**: {pos['total_roles_played']}")
    lines.append("")

    for role, role_data in sorted(pos["roles"].items(), key=lambda x: x[1]["score"], reverse=True):
        lines.append(f"### {role} (评级: {role_data['rank']})")
        lines.append(f"- 场次: {role_data['games']}")
        lines.append(f"- 胜率: {role_data['winrate']:.1%} ({role_data['wins']}胜)")
        lines.append(f"- 置信区间: {role_data['ci_lower']:.1%} - {role_data['ci_upper']:.1%}")
        lines.append(f"- 平均KDA: {role_data['avg_kda']:.2f}")
        lines.append(f"- 版本覆盖: {role_data['patches_played']}个版本")
        lines.append(f"- 综合评分: {role_data['score']}分")
        lines.append("")

    # 版本适应性
    va = analysis["version_adaptation"]
    lines.append("## 版本适应性分析")
    lines.append(f"**版本覆盖**: {va['version_coverage']}个版本")
    lines.append(f"**表现趋势**: {va['performance_trend']}")
    lines.append(f"**稳定性评分**: {va['stability_score']:.3f}")
    lines.append("")

    lines.append("### 各版本表现")
    for patch_data in va["patches"]:
        lines.append(f"- **{patch_data['patch']}**: {patch_data['winrate']:.1%} ({patch_data['wins']}胜/{patch_data['games']}场), "
                    f"CI: {patch_data['ci_lower']:.1%}-{patch_data['ci_upper']:.1%}")

    return "\n".join(lines)

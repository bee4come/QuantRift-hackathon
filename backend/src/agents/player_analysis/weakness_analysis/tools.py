"""WeaknessAnalysisAgent - Weakness Diagnosis Tools"""

import json
from pathlib import Path
from typing import Dict, Any, List
from src.core.statistical_utils import wilson_confidence_interval


def load_recent_data(packs_dir: str, recent_count: int = 5) -> Dict[str, Any]:
    """加载最近N个版本数据"""
    packs_dir = Path(packs_dir)
    pack_files = sorted(packs_dir.glob("pack_*.json"))[-recent_count:]

    packs = {}
    for pack_file in pack_files:
        with open(pack_file, 'r') as f:
            pack = json.load(f)
            packs[pack["patch"]] = pack
    return packs


def identify_weaknesses(recent_data: Dict[str, Any]) -> Dict[str, Any]:
    """识别主要弱点并生成完整统计数据"""
    # 聚合数据
    low_winrate_champions = []
    all_champion_stats = []
    role_performance = {}

    total_games = 0
    total_wins = 0
    unique_champions = set()
    unique_roles = set()

    # 遍历所有数据，收集统计信息
    for patch, pack in recent_data.items():
        for cr in pack.get("by_cr", []):
            wr = cr["wins"] / cr["games"] if cr["games"] > 0 else 0
            champ_id = cr["champ_id"]
            role = cr["role"]
            games = cr["games"]
            wins = cr["wins"]

            # 收集整体统计
            total_games += games
            total_wins += wins
            unique_champions.add(champ_id)
            unique_roles.add(role)

            # 收集所有英雄表现
            all_champion_stats.append({
                "champ_id": champ_id,
                "role": role,
                "games": games,
                "winrate": round(wr, 3),
                "patch": patch
            })

            # 识别低胜率英雄
            if games >= 5 and wr < 0.45:  # 至少5场且胜率<45%
                low_winrate_champions.append({
                    "champ_id": champ_id,
                    "role": role,
                    "games": games,
                    "winrate": round(wr, 3),
                    "patch": patch
                })

            # 按角色聚合
            if role not in role_performance:
                role_performance[role] = {"games": 0, "wins": 0}
            role_performance[role]["games"] += games
            role_performance[role]["wins"] += wins

    # 处理位置表现
    all_role_stats = []
    weak_roles = []
    for role, stats in role_performance.items():
        wr = stats["wins"] / stats["games"] if stats["games"] > 0 else 0
        role_stat = {
            "role": role,
            "games": stats["games"],
            "winrate": round(wr, 3)
        }
        all_role_stats.append(role_stat)

        if stats["games"] >= 10 and wr < 0.48:
            weak_roles.append(role_stat)

    # 按胜率排序
    all_champion_stats.sort(key=lambda x: x["winrate"], reverse=True)
    all_role_stats.sort(key=lambda x: x["winrate"], reverse=True)

    weaknesses = {
        "overall_stats": {
            "total_games": total_games,
            "overall_winrate": total_wins / total_games if total_games > 0 else 0,
            "unique_champions": len(unique_champions),
            "unique_roles": len(unique_roles)
        },
        "all_champion_stats": all_champion_stats,
        "all_role_stats": all_role_stats,
        "low_winrate_champions": sorted(low_winrate_champions, key=lambda x: x["winrate"])[:5],
        "weak_roles": sorted(weak_roles, key=lambda x: x["winrate"]),
        "total_patches_analyzed": len(recent_data)
    }

    return weaknesses


def format_analysis_for_prompt(weaknesses: Dict[str, Any]) -> str:
    """格式化弱点分析数据"""
    lines = [f"# 弱点诊断数据\n"]
    lines.append(f"**分析版本数**: {weaknesses['total_patches_analyzed']}\n")

    # 添加整体统计信息（即使没有明显弱点，也要提供完整数据）
    if 'overall_stats' in weaknesses and weaknesses['overall_stats']:
        stats = weaknesses['overall_stats']
        lines.append("## 整体表现")
        lines.append(f"- **总游戏数**: {stats.get('total_games', 0)}场")
        lines.append(f"- **整体胜率**: {stats.get('overall_winrate', 0):.1%}")
        lines.append(f"- **使用英雄数**: {stats.get('unique_champions', 0)}个")
        lines.append(f"- **涉及位置数**: {stats.get('unique_roles', 0)}个")
        lines.append("")

    # 添加所有英雄表现（不仅仅是低胜率）
    if 'all_champion_stats' in weaknesses and weaknesses['all_champion_stats']:
        lines.append("## 英雄表现统计")
        for champ_stat in weaknesses['all_champion_stats'][:10]:  # 前10个英雄
            lines.append(f"- **英雄ID {champ_stat['champ_id']}** ({champ_stat['role']}): "
                        f"{champ_stat['winrate']:.1%}胜率, {champ_stat['games']}场")
        lines.append("")

    # 添加低胜率英雄（如果有）
    if weaknesses["low_winrate_champions"]:
        lines.append("## 低胜率英雄")
        for champ in weaknesses["low_winrate_champions"]:
            lines.append(f"- **英雄ID {champ['champ_id']}** ({champ['role']}): {champ['winrate']:.1%}胜率, {champ['games']}场")
        lines.append("")
    else:
        lines.append("## 低胜率英雄")
        lines.append("- **无明显低胜率英雄** (所有英雄胜率均≥45%)")
        lines.append("")

    # 添加位置表现
    if 'all_role_stats' in weaknesses and weaknesses['all_role_stats']:
        lines.append("## 位置表现统计")
        for role_stat in weaknesses['all_role_stats']:
            lines.append(f"- **{role_stat['role']}**: {role_stat['winrate']:.1%}胜率, {role_stat['games']}场")
        lines.append("")

    # 添加薄弱位置（如果有）
    if weaknesses["weak_roles"]:
        lines.append("## 薄弱位置")
        for role in weaknesses["weak_roles"]:
            lines.append(f"- **{role['role']}**: {role['winrate']:.1%}胜率, {role['games']}场")
        lines.append("")
    else:
        lines.append("## 薄弱位置")
        lines.append("- **无明显薄弱位置** (所有位置胜率均≥48%)")
        lines.append("")

    return "\n".join(lines)

"""WeaknessAnalysisAgent - Weakness Diagnosis Tools"""

import json
from pathlib import Path
from typing import Dict, Any, List
from src.core.statistical_utils import wilson_confidence_interval


def load_recent_data(packs_dir: str, recent_count: int = 5, time_range: str = None, queue_id: int = None) -> Dict[str, Any]:
    """
    加载最近N个版本数据
    
    Args:
        packs_dir: Pack文件目录
        recent_count: 最近N个版本
        time_range: Time range filter (optional)
        queue_id: Queue ID filter (optional)
    """
    from datetime import datetime, timedelta
    from pathlib import Path
    
    packs_dir = Path(packs_dir)
    
    # Calculate time filter if needed
    cutoff_timestamp = None
    cutoff_end_timestamp = None
    
    if time_range == "2024-01-01":
        cutoff_timestamp = datetime(2024, 1, 9).timestamp()
        cutoff_end_timestamp = datetime(2025, 1, 6, 23, 59, 59, 999000).timestamp()
    elif time_range == "past-365":
        cutoff_timestamp = (datetime.now() - timedelta(days=365)).timestamp()
    
    # Build file pattern based on queue_id
    if queue_id is not None:
        pack_pattern = f"pack_*_{queue_id}.json"
    else:
        pack_pattern = "pack_*.json"
    
    all_pack_files = sorted(packs_dir.glob(pack_pattern))
    
    # Apply time filter if specified
    if cutoff_timestamp:
        filtered_pack_files = []
        for pack_file in all_pack_files:
            with open(pack_file, 'r') as f:
                pack_data = json.load(f)
            
            # Verify queue_id matches if specified
            if queue_id is not None:
                pack_queue_id = pack_data.get('queue_id', 420)
                if pack_queue_id != queue_id:
                    continue
            
            # Check match dates
            pack_earliest = pack_data.get("earliest_match_date")
            pack_latest = pack_data.get("latest_match_date")
            has_match_in_range = False
            
            if pack_earliest or pack_latest:
                if pack_earliest:
                    try:
                        earliest_dt = datetime.fromisoformat(pack_earliest.replace('Z', '+00:00'))
                        if earliest_dt.tzinfo:
                            earliest_dt = earliest_dt.replace(tzinfo=None)
                        earliest_ts = earliest_dt.timestamp()
                    except:
                        earliest_ts = None
                else:
                    earliest_ts = None
                    
                if pack_latest:
                    try:
                        latest_dt = datetime.fromisoformat(pack_latest.replace('Z', '+00:00'))
                        if latest_dt.tzinfo:
                            latest_dt = latest_dt.replace(tzinfo=None)
                        latest_ts = latest_dt.timestamp()
                    except:
                        latest_ts = None
                else:
                    latest_ts = None
                
                if earliest_ts and latest_ts:
                    if cutoff_end_timestamp:
                        if earliest_ts <= cutoff_end_timestamp and latest_ts >= cutoff_timestamp:
                            has_match_in_range = True
                    else:
                        if latest_ts >= cutoff_timestamp:
                            has_match_in_range = True
                elif latest_ts:
                    if cutoff_end_timestamp:
                        if latest_ts <= cutoff_end_timestamp and latest_ts >= cutoff_timestamp:
                            has_match_in_range = True
                    else:
                        if latest_ts >= cutoff_timestamp:
                            has_match_in_range = True
            else:
                # Fallback to generation_timestamp
                if "generation_timestamp" in pack_data:
                    pack_timestamp = pack_data["generation_timestamp"]
                    if isinstance(pack_timestamp, str):
                        pack_timestamp = datetime.fromisoformat(pack_timestamp.replace('Z', '+00:00')).timestamp()
                    if cutoff_end_timestamp:
                        if cutoff_timestamp <= pack_timestamp <= cutoff_end_timestamp:
                            has_match_in_range = True
                    else:
                        if pack_timestamp >= cutoff_timestamp:
                            has_match_in_range = True
            
            if has_match_in_range:
                filtered_pack_files.append(pack_file)
        
        pack_files = filtered_pack_files[-recent_count:] if len(filtered_pack_files) >= recent_count else filtered_pack_files
    else:
        pack_files = all_pack_files[-recent_count:]

    packs = {}
    for pack_file in pack_files:
        with open(pack_file, 'r') as f:
            pack = json.load(f)
            # Extract patch version from filename if queue_id is in filename
            if queue_id is not None:
                filename = pack_file.stem
                if "_" in filename:
                    patch = filename.rsplit("_", 1)[0].replace("pack_", "")
                else:
                    patch = pack.get("patch", "unknown")
            else:
                patch = pack.get("patch", "unknown")
            packs[patch] = pack
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

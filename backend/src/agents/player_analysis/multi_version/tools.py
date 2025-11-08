"""
Multi-Version Analysis Tools
数据构建和分析工具（从原 MultiVersionAnalyzer 迁移）
"""

import json
from pathlib import Path
from typing import Dict, List, Any


def version_sort_key(patch: str) -> tuple:
    """
    版本号排序键函数，支持自然排序

    例如: "15.1" -> (15, 1), "15.10" -> (15, 10)
    这样可以正确排序: 15.1 < 15.2 < ... < 15.9 < 15.10

    Args:
        patch: 版本号字符串，如 "15.1", "15.10"

    Returns:
        tuple: (major, minor) 用于排序
    """
    try:
        parts = patch.split('.')
        return (int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        # 如果解析失败，返回一个默认值
        return (0, 0)


def load_all_packs(packs_dir: str, time_range: str = None, queue_id: int = None) -> Dict[str, Any]:
    """
    Load all Player-Pack files

    Args:
        packs_dir: Player-Pack directory path
        time_range: Time range filter
            - "2024-01-01": Load data from Past Season 2024 (2024-01-09 to 2025-01-06, patches 14.1 to 14.25)
            - "past-365": Load data from past 365 days
            - None: Load all available data
        queue_id: Queue ID filter
            - 420: Ranked Solo/Duo
            - 440: Ranked Flex
            - 400: Normal
            - None: Load all queue types

    Returns:
        dict: {patch: pack_data}
    """
    from datetime import datetime, timedelta
    
    packs_path = Path(packs_dir)
    all_packs = {}

    # Calculate time filter if needed
    cutoff_timestamp = None
    cutoff_end_timestamp = None  # For date range filtering
    
    if time_range == "2024-01-01":
        # Past Season 2024: patch 14.1 (2024-01-09) to patch 14.25 (2025-01-06)
        cutoff_timestamp = datetime(2024, 1, 9).timestamp()
        cutoff_end_timestamp = datetime(2025, 1, 6, 23, 59, 59, 999000).timestamp()
    elif time_range == "past-365":
        cutoff_timestamp = (datetime.now() - timedelta(days=365)).timestamp()

    # Build file pattern based on queue_id
    if queue_id is not None:
        pack_pattern = f"pack_*_{queue_id}.json"
    else:
        pack_pattern = "pack_*.json"

    pack_files = sorted(packs_path.glob(pack_pattern))
    for pack_file in pack_files:
        # Extract patch version from filename
        filename = pack_file.stem
        if filename.startswith("pack_"):
            patch = filename.replace("pack_", "")
            # Remove queue_id suffix if present
            if "_" in patch:
                patch = patch.rsplit("_", 1)[0]
        else:
            continue
            
        with open(pack_file, 'r', encoding='utf-8') as f:
            pack_data = json.load(f)
            
            # Verify queue_id matches if specified
            if queue_id is not None:
                pack_queue_id = pack_data.get('queue_id', 420)
                if pack_queue_id != queue_id:
                    continue
            
            # Apply time range filter based on match dates, not generation timestamp
            if cutoff_timestamp:
                # Check match dates first (more accurate)
                pack_earliest = pack_data.get("earliest_match_date")
                pack_latest = pack_data.get("latest_match_date")
                
                has_match_in_range = False
                
                if pack_earliest or pack_latest:
                    # Parse dates
                    earliest_dt = None
                    latest_dt = None
                    
                    if pack_earliest:
                        try:
                            if isinstance(pack_earliest, str):
                                date_str = pack_earliest.replace('Z', '+00:00')
                                if '+' not in date_str and 'T' in date_str:
                                    date_str = date_str + '+00:00'
                                earliest_dt = datetime.fromisoformat(date_str)
                            else:
                                earliest_dt = pack_earliest
                            if earliest_dt.tzinfo:
                                earliest_dt = earliest_dt.replace(tzinfo=None)
                        except:
                            pass
                    
                    if pack_latest:
                        try:
                            if isinstance(pack_latest, str):
                                date_str = pack_latest.replace('Z', '+00:00')
                                if '+' not in date_str and 'T' in date_str:
                                    date_str = date_str + '+00:00'
                                latest_dt = datetime.fromisoformat(date_str)
                            else:
                                latest_dt = pack_latest
                            if latest_dt.tzinfo:
                                latest_dt = latest_dt.replace(tzinfo=None)
                        except:
                            pass
                    
                    # Check if date range overlaps with the filter range
                    if earliest_dt and latest_dt:
                        earliest_ts = earliest_dt.timestamp()
                        latest_ts = latest_dt.timestamp()
                        
                        if cutoff_end_timestamp:
                            # Date range filter: check if pack date range overlaps with filter range
                            if earliest_ts <= cutoff_end_timestamp and latest_ts >= cutoff_timestamp:
                                has_match_in_range = True
                        else:
                            # Single cutoff: check if pack has matches after cutoff
                            if latest_ts >= cutoff_timestamp:
                                has_match_in_range = True
                    elif earliest_dt:
                        earliest_ts = earliest_dt.timestamp()
                        if cutoff_end_timestamp:
                            if earliest_ts <= cutoff_end_timestamp and earliest_ts >= cutoff_timestamp:
                                has_match_in_range = True
                        else:
                            if earliest_ts >= cutoff_timestamp:
                                has_match_in_range = True
                    elif latest_dt:
                        latest_ts = latest_dt.timestamp()
                        if cutoff_end_timestamp:
                            if latest_ts <= cutoff_end_timestamp and latest_ts >= cutoff_timestamp:
                                has_match_in_range = True
                        else:
                            if latest_ts >= cutoff_timestamp:
                                has_match_in_range = True
                else:
                    # Fallback to generation_timestamp if match dates not available
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
                
                # Skip if no matches in the time range
                if not has_match_in_range:
                    continue
            
            all_packs[patch] = pack_data

    return all_packs


def analyze_trends(all_packs: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析跨版本趋势

    Args:
        all_packs: 所有版本的 pack 数据

    Returns:
        dict: 趋势分析结果
    """
    trends = {
        "patches": list(all_packs.keys()),
        "total_games_by_patch": {},
        "champion_pool_size": {},
        "top_champions": {},
        "winrate_trends": {},
        "performance_stability": {},
    }

    # 1. 基础统计
    for patch, pack in all_packs.items():
        trends["total_games_by_patch"][patch] = pack["total_games"]
        trends["champion_pool_size"][patch] = len(pack["by_cr"])

    # 2. 核心英雄识别
    champion_stats = {}  # {(champ_id, role): {patch: stats}}

    for patch, pack in all_packs.items():
        for cr in pack["by_cr"]:
            key = (cr["champ_id"], cr["role"])
            if key not in champion_stats:
                champion_stats[key] = {}

            champion_stats[key][patch] = {
                "games": cr["games"],
                "wins": cr["wins"],
                "p_hat": cr["p_hat"],
                "kda_adj": cr["kda_adj"],
                "cp_25": cr["cp_25"],
                "build_core": cr["build_core"]
            }

    # 3. 筛选核心英雄(至少在3个版本出现或总场次>=10)
    core_champions = {}
    for cr_key, stats_by_patch in champion_stats.items():
        total_games = sum(s["games"] for s in stats_by_patch.values())
        patch_count = len(stats_by_patch)

        if total_games >= 10 or patch_count >= 3:
            core_champions[cr_key] = stats_by_patch

    # 4. 分析核心英雄胜率趋势
    for cr_key, stats_by_patch in core_champions.items():
        champ_id, role = cr_key
        key_str = f"{champ_id}_{role}"

        trends["winrate_trends"][key_str] = {
            "champion_id": champ_id,
            "role": role,
            "patches": {}
        }

        for patch in sorted(stats_by_patch.keys(), key=version_sort_key):
            trends["winrate_trends"][key_str]["patches"][patch] = {
                "games": stats_by_patch[patch]["games"],
                "winrate": stats_by_patch[patch]["p_hat"],
                "kda": stats_by_patch[patch]["kda_adj"]
            }

    # 5. 计算版本间稳定性(胜率方差)
    for patch in trends["patches"]:
        winrates = [cr["p_hat"] for cr in all_packs[patch]["by_cr"] if cr["games"] >= 3]
        if winrates:
            avg_wr = sum(winrates) / len(winrates)
            variance = sum((wr - avg_wr) ** 2 for wr in winrates) / len(winrates)
            trends["performance_stability"][patch] = {
                "avg_winrate": round(avg_wr, 4),
                "variance": round(variance, 4),
                "consistency_score": round(1 - variance, 4)  # 越高越稳定
            }

    return trends


def identify_key_transitions(trends: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    识别关键转折点(版本间显著变化)

    Args:
        trends: 趋势分析结果

    Returns:
        list: 转折点列表
    """
    transitions = []
    patches = sorted(trends["patches"], key=version_sort_key)

    for i in range(len(patches) - 1):
        prev_patch = patches[i]
        curr_patch = patches[i + 1]

        prev_games = trends["total_games_by_patch"][prev_patch]
        curr_games = trends["total_games_by_patch"][curr_patch]

        # 计算游戏量变化
        games_change = ((curr_games - prev_games) / max(prev_games, 1)) * 100

        # 计算英雄池变化
        prev_pool = trends["champion_pool_size"][prev_patch]
        curr_pool = trends["champion_pool_size"][curr_patch]
        pool_change = ((curr_pool - prev_pool) / max(prev_pool, 1)) * 100

        # 计算稳定性变化
        prev_stability = trends["performance_stability"].get(prev_patch, {}).get("consistency_score", 0)
        curr_stability = trends["performance_stability"].get(curr_patch, {}).get("consistency_score", 0)
        stability_change = curr_stability - prev_stability

        # 标记显著转折点
        is_significant = abs(games_change) > 30 or abs(stability_change) > 0.1

        transition = {
            "from_patch": prev_patch,
            "to_patch": curr_patch,
            "games_change_pct": round(games_change, 2),
            "pool_change_pct": round(pool_change, 2),
            "stability_change": round(stability_change, 4),
            "is_significant": is_significant
        }

        transitions.append(transition)

    return transitions


def generate_comprehensive_analysis(
    trends: Dict[str, Any],
    transitions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    生成综合分析数据包

    Args:
        trends: 趋势分析
        transitions: 转折点分析

    Returns:
        dict: 综合分析数据包
    """
    analysis = {
        "summary": {
            "total_patches": len(trends["patches"]),
            "patch_range": f"{min(trends['patches'])} - {max(trends['patches'])}",
            "total_games": sum(trends["total_games_by_patch"].values()),
            "avg_games_per_patch": round(
                sum(trends["total_games_by_patch"].values()) / len(trends["patches"]), 1
            ),
            "unique_champion_roles": len(trends["winrate_trends"])
        },
        "trends": trends,
        "transitions": transitions,
        "insights": {
            "most_active_patch": max(
                trends["total_games_by_patch"],
                key=trends["total_games_by_patch"].get
            ),
            "most_stable_patch": max(
                trends["performance_stability"],
                key=lambda p: trends["performance_stability"][p]["consistency_score"]
            ),
            "largest_pool": max(
                trends["champion_pool_size"],
                key=trends["champion_pool_size"].get
            )
        }
    }

    return analysis

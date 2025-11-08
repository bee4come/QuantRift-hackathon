"""
Annual Summary Tools - Data Processing Tools for Annual Analysis

Provides all data processing functions required for annual analysis
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
import sys

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import from multi_version for reuse
from src.agents.player_analysis.multi_version.tools import (
    analyze_trends,
    identify_key_transitions
)

# Import ID mappings
from src.utils.id_mappings import get_champion_name


def load_all_annual_packs(packs_dir: str, time_range: str = None, queue_id: int = None) -> Dict[str, Any]:
    """
    Load all Player-Pack files for the entire season

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
        {
            "15.1": {pack_data},
            "15.2": {pack_data},
            ...
        }
    """
    packs_path = Path(packs_dir)
    all_packs = {}

    # Calculate time filter if needed
    cutoff_timestamp = None
    cutoff_end_timestamp = None  # For date range filtering
    
    if time_range == "2024-01-01":
        # Past Season 2024: patch 14.1 (2024-01-09) to patch 14.25 (2025-01-06)
        cutoff_timestamp = datetime(2024, 1, 9).timestamp()
        cutoff_end_timestamp = datetime(2025, 1, 6, 23, 59, 59, 999000).timestamp()
        print(f"📅 [Annual Summary] Filtering for Season 2024: {datetime(2024, 1, 9)} to {datetime(2025, 1, 6)}")
    elif time_range == "past-365":
        cutoff_timestamp = (datetime.now() - timedelta(days=365)).timestamp()
        print(f"📅 [Annual Summary] Filtering for Past 365 Days: from {datetime.fromtimestamp(cutoff_timestamp)} to now")
    elif time_range is None:
        print(f"📅 [Annual Summary] No time filter - loading all available data")

    # Build file pattern based on queue_id
    if queue_id is not None:
        # Load specific queue_id packs: pack_{patch}_{queue_id}.json
        pack_pattern = f"pack_*_{queue_id}.json"
    else:
        # Load all packs (legacy format: pack_{patch}.json or new format: pack_{patch}_{queue_id}.json)
        pack_pattern = "pack_*.json"

    for pack_file in sorted(packs_path.glob(pack_pattern)):
        # Extract patch version from filename
        # pack_15.18_420.json → 15.18 (new format)
        # pack_15.18.json → 15.18 (legacy format)
        filename = pack_file.stem
        if filename.startswith("pack_"):
            patch_version = filename.replace("pack_", "")
            # Remove queue_id suffix if present (e.g., "15.18_420" → "15.18")
            if "_" in patch_version:
                patch_version = patch_version.rsplit("_", 1)[0]
        else:
            continue

        with open(pack_file, 'r', encoding='utf-8') as f:
            pack_data = json.load(f)
            
            # Verify queue_id matches if specified
            if queue_id is not None:
                pack_queue_id = pack_data.get('queue_id', 420)  # Default to Solo/Duo for legacy packs
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
                                earliest_dt = datetime.fromisoformat(pack_earliest.replace('Z', '+00:00'))
                            else:
                                earliest_dt = pack_earliest
                            if earliest_dt.tzinfo:
                                earliest_dt = earliest_dt.replace(tzinfo=None)
                        except:
                            pass
                    
                    if pack_latest:
                        try:
                            if isinstance(pack_latest, str):
                                latest_dt = datetime.fromisoformat(pack_latest.replace('Z', '+00:00'))
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
                            # Pack overlaps if: pack_earliest <= filter_end AND pack_latest >= filter_start
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

            all_packs[patch_version] = pack_data

    print(f"✅ [Annual Summary] Loaded {len(all_packs)} patches after filtering (time_range: {time_range}, queue_id: {queue_id})")
    return all_packs


def segment_by_time(all_packs: Dict[str, Any], segment_type: str = "monthly") -> Dict[str, Any]:
    """
    Aggregate data by time segments

    Args:
        all_packs: All Player-Pack data
        segment_type: "monthly", "quarterly", or "tri-period"

    Returns:
        {
            "2024-01": {aggregated_data},  # monthly
            "Q1": {aggregated_data},        # quarterly
            "early": {aggregated_data}      # tri-period
        }
    """
    if segment_type == "monthly":
        return _segment_by_month(all_packs)
    elif segment_type == "quarterly":
        return _segment_by_quarter(all_packs)
    elif segment_type == "tri-period":
        return _segment_by_tri_period(all_packs)
    else:
        raise ValueError(f"Unknown segment_type: {segment_type}")


def _segment_by_month(all_packs: Dict[str, Any]) -> Dict[str, Any]:
    """按月聚合数据"""
    monthly_segments = defaultdict(lambda: {
        "patches": [],
        "total_games": 0,
        "total_wins": 0,
        "champion_roles": defaultdict(lambda: {"games": 0, "wins": 0})
    })

    for patch, pack_data in all_packs.items():
        # Extract month from patch timestamp (假设patch有generation_timestamp字段)
        # 如果没有时间戳，使用patch版本号推算（简化处理）
        if "generation_timestamp" in pack_data:
            month_key = pack_data["generation_timestamp"][:7]  # "2024-01"
        else:
            # 简化：使用patch的第一个数字作为月份（仅用于演示）
            major, minor = patch.split('.')
            month_key = f"2024-{int(minor):02d}"  # 15.1 → 2024-01

        segment = monthly_segments[month_key]
        segment["patches"].append(patch)

        # 聚合每个champion-role的数据
        for cr in pack_data.get("by_cr", []):
            key = f"{cr['champ_id']}_{cr['role']}"  # JSON-safe string key
            segment["champion_roles"][key]["games"] += cr["games"]
            segment["champion_roles"][key]["wins"] += cr["wins"]
            segment["total_games"] += cr["games"]
            segment["total_wins"] += cr["wins"]

    # 计算胜率
    for month, segment in monthly_segments.items():
        if segment["total_games"] > 0:
            segment["winrate"] = segment["total_wins"] / segment["total_games"]
        else:
            segment["winrate"] = 0.0

    return dict(monthly_segments)


def _segment_by_quarter(all_packs: Dict[str, Any]) -> Dict[str, Any]:
    """按季度聚合数据"""
    # 先按月聚合
    monthly = _segment_by_month(all_packs)

    quarterly_segments = {
        "Q1": defaultdict(int),
        "Q2": defaultdict(int),
        "Q3": defaultdict(int),
        "Q4": defaultdict(int)
    }

    # 月份到季度的映射
    month_to_quarter = {
        "01": "Q1", "02": "Q1", "03": "Q1",
        "04": "Q2", "05": "Q2", "06": "Q2",
        "07": "Q3", "08": "Q3", "09": "Q3",
        "10": "Q4", "11": "Q4", "12": "Q4"
    }

    for month_key, month_data in monthly.items():
        # Extract month number from "2024-01"
        month_num = month_key.split('-')[1]
        quarter = month_to_quarter.get(month_num, "Q1")

        quarterly_segments[quarter]["total_games"] += month_data["total_games"]
        quarterly_segments[quarter]["total_wins"] += month_data["total_wins"]

    # 计算季度胜率
    for quarter, data in quarterly_segments.items():
        if data["total_games"] > 0:
            data["winrate"] = data["total_wins"] / data["total_games"]
        else:
            data["winrate"] = 0.0

    return dict(quarterly_segments)


def _segment_by_tri_period(all_packs: Dict[str, Any]) -> Dict[str, Any]:
    """按三期（早期/中期/晚期）聚合数据"""
    sorted_patches = sorted(all_packs.keys())
    total_patches = len(sorted_patches)

    # 分为三等份
    early_end = total_patches // 3
    mid_end = 2 * total_patches // 3

    periods = {
        "early": sorted_patches[:early_end],
        "mid": sorted_patches[early_end:mid_end],
        "late": sorted_patches[mid_end:]
    }

    period_segments = {}

    for period_name, patches in periods.items():
        total_games = 0
        total_wins = 0

        for patch in patches:
            pack_data = all_packs[patch]
            for cr in pack_data.get("by_cr", []):
                total_games += cr["games"]
                total_wins += cr["wins"]

        period_segments[period_name] = {
            "patches": patches,
            "total_games": total_games,
            "total_wins": total_wins,
            "winrate": total_wins / total_games if total_games > 0 else 0.0
        }

    return period_segments


def extract_annual_highlights(all_packs: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取年度统计亮点

    Returns:
        {
            "total_games": int,
            "total_wins": int,
            "overall_winrate": float,
            "unique_champions": int,
            "unique_roles": set,
            "patches_covered": int,
            "best_champion_role": {...},
            "most_played_champion": {...},
            "best_month": {...},
            "best_quarter": {...}
        }
    """
    # 全局统计
    total_games = 0
    total_wins = 0
    unique_champions = set()
    unique_roles = set()

    # Champion-role聚合
    champion_role_stats = defaultdict(lambda: {"games": 0, "wins": 0})

    for patch, pack_data in all_packs.items():
        for cr in pack_data.get("by_cr", []):
            champ_id = cr["champ_id"]
            role = cr["role"]
            games = cr["games"]
            wins = cr["wins"]

            total_games += games
            total_wins += wins
            unique_champions.add(champ_id)
            unique_roles.add(role)

            key = (champ_id, role)
            champion_role_stats[key]["games"] += games
            champion_role_stats[key]["wins"] += wins

    # 计算每个champion-role的胜率
    for key, stats in champion_role_stats.items():
        if stats["games"] > 0:
            stats["winrate"] = stats["wins"] / stats["games"]
        else:
            stats["winrate"] = 0.0

    # 找到最佳champion-role（胜率最高且至少30场）
    qualified_crs = [(key, stats) for key, stats in champion_role_stats.items()
                     if stats["games"] >= 30]

    if qualified_crs:
        best_cr_key, best_cr_stats = max(qualified_crs, key=lambda x: x[1]["winrate"])
        best_champion_role = {
            "champion_id": best_cr_key[0],
            "role": best_cr_key[1],
            "games": best_cr_stats["games"],
            "wins": best_cr_stats["wins"],
            "winrate": best_cr_stats["winrate"]
        }
    else:
        best_champion_role = None

    # 找到游戏最多的英雄
    champion_total_games = defaultdict(int)
    for (champ_id, role), stats in champion_role_stats.items():
        champion_total_games[champ_id] += stats["games"]

    if champion_total_games:
        most_played_champ_id = max(champion_total_games.keys(),
                                   key=lambda c: champion_total_games[c])
        most_played_champion = {
            "champion_id": most_played_champ_id,
            "total_games": champion_total_games[most_played_champ_id]
        }
    else:
        most_played_champion = None

    # 找到最佳月份和季度
    monthly = segment_by_time(all_packs, "monthly")
    quarterly = segment_by_time(all_packs, "quarterly")

    if monthly:
        best_month_key = max(monthly.keys(), key=lambda m: monthly[m]["winrate"])
        best_month = {
            "month": best_month_key,
            "winrate": monthly[best_month_key]["winrate"],
            "games": monthly[best_month_key]["total_games"]
        }
    else:
        best_month = None

    if quarterly:
        best_quarter_key = max(quarterly.keys(), key=lambda q: quarterly[q]["winrate"])
        best_quarter = {
            "quarter": best_quarter_key,
            "winrate": quarterly[best_quarter_key]["winrate"],
            "games": quarterly[best_quarter_key]["total_games"]
        }
    else:
        best_quarter = None

    return {
        "total_games": total_games,
        "total_wins": total_wins,
        "overall_winrate": total_wins / total_games if total_games > 0 else 0.0,
        "unique_champions": len(unique_champions),
        "unique_roles": len(unique_roles),
        "patches_covered": len(all_packs),
        "best_champion_role": best_champion_role,
        "most_played_champion": most_played_champion,
        "best_month": best_month,
        "best_quarter": best_quarter
    }


def analyze_champion_pool_evolution(all_packs: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析英雄池演进

    Returns:
        {
            "monthly_breadth": [...],  # 每月unique champions数量
            "core_champions": [...],   # 长期核心英雄（至少出现在50%版本中）
            "experimental_champions": [...],  # 短期尝试（<10%版本）
            "role_preferences": {...}  # 位置偏好变化
        }
    """
    # 按月统计英雄池广度
    monthly = segment_by_time(all_packs, "monthly")
    monthly_breadth = []

    for month in sorted(monthly.keys()):
        month_data = monthly[month]
        unique_champs = set()

        for key in month_data["champion_roles"].keys():
            champ_id = key.split('_')[0]  # Extract champion_id from "123_TOP"
            unique_champs.add(int(champ_id))

        monthly_breadth.append({
            "month": month,
            "unique_champions": len(unique_champs)
        })

    # 统计每个英雄出现在多少个版本中
    champion_patch_count = defaultdict(set)

    for patch, pack_data in all_packs.items():
        for cr in pack_data.get("by_cr", []):
            champion_patch_count[cr["champ_id"]].add(patch)

    total_patches = len(all_packs)

    # 核心英雄：出现在 >= 50% 版本中
    core_champions = []
    for champ_id, patches in champion_patch_count.items():
        if len(patches) >= total_patches * 0.5:
            core_champions.append({
                "champion_id": champ_id,
                "champion_name": get_champion_name(champ_id),
                "patch_count": len(patches),
                "coverage": len(patches) / total_patches
            })

    # 实验性英雄：出现在 < 10% 版本中
    experimental_champions = []
    for champ_id, patches in champion_patch_count.items():
        if len(patches) < total_patches * 0.1:
            experimental_champions.append({
                "champion_id": champ_id,
                "champion_name": get_champion_name(champ_id),
                "patch_count": len(patches),
                "coverage": len(patches) / total_patches
            })

    # 位置偏好变化（按月统计）
    role_preferences = {}
    for month in sorted(monthly.keys()):
        month_data = monthly[month]
        role_games = defaultdict(int)

        for key, stats in month_data["champion_roles"].items():
            role = key.split('_')[1]  # Extract role from "123_TOP"
            role_games[role] += stats["games"]

        role_preferences[month] = dict(role_games)

    return {
        "monthly_breadth": monthly_breadth,
        "core_champions": sorted(core_champions, key=lambda x: x["coverage"], reverse=True),
        "experimental_champions": sorted(experimental_champions, key=lambda x: x["patch_count"]),
        "role_preferences": role_preferences
    }


def generate_comprehensive_annual_analysis(all_packs: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成完整的年度分析数据包

    Returns:
        {
            "metadata": {...},
            "summary": {...},
            "time_segments": {...},
            "annual_highlights": {...},
            "version_adaptation": {...},
            "champion_pool_evolution": {...}
        }
    """
    # 时间分段
    monthly = segment_by_time(all_packs, "monthly")
    quarterly = segment_by_time(all_packs, "quarterly")
    tri_period = segment_by_time(all_packs, "tri-period")

    # 年度亮点
    highlights = extract_annual_highlights(all_packs)

    # 版本适应（复用MultiVersionAgent逻辑）
    trends = analyze_trends(all_packs)
    transitions = identify_key_transitions(trends)

    # 英雄池演进
    champion_pool = analyze_champion_pool_evolution(all_packs)

    # NEW: Growth metrics (kda_adj, obj_rate, time_to_core)
    growth_metrics = calculate_growth_metrics(all_packs)

    # NEW: Adaptation score (0-100)
    adaptation_score = calculate_adaptation_score(all_packs, trends)

    # NEW: Consistency profile (variance + governance quality)
    consistency = calculate_consistency_profile(all_packs)

    # 元数据
    sorted_patches = sorted(all_packs.keys())
    metadata = {
        "analysis_type": "annual_summary",
        "generated_at": datetime.now().isoformat(),
        "total_patches": len(all_packs),
        "patch_range": [sorted_patches[0], sorted_patches[-1]],
        "analysis_version": "2.0"  # Updated version
    }

    return {
        "metadata": metadata,
        "summary": {
            "total_games": highlights["total_games"],
            "total_wins": highlights["total_wins"],
            "overall_winrate": highlights["overall_winrate"],
            "unique_champions": highlights["unique_champions"],
            "unique_roles": highlights["unique_roles"],
            "patches_covered": highlights["patches_covered"]
        },
        "time_segments": {
            "monthly": monthly,
            "quarterly": quarterly,
            "tri_period": tri_period
        },
        "annual_highlights": highlights,
        "version_adaptation": {
            "trends": trends,
            "key_transitions": transitions,
            "adaptation_score": adaptation_score  # NEW
        },
        "champion_pool_evolution": champion_pool,
        "growth_metrics": growth_metrics,        # NEW
        "consistency_profile": consistency       # NEW
    }


def format_analysis_for_prompt(analysis: Dict[str, Any]) -> str:
    """
    将分析数据格式化为适合LLM的文本

    Args:
        analysis: generate_comprehensive_annual_analysis返回的数据

    Returns:
        格式化的文本字符串
    """
    summary = analysis["summary"]
    highlights = analysis["annual_highlights"]
    tri_period = analysis["time_segments"]["tri_period"]
    champion_pool = analysis["champion_pool_evolution"]

    formatted_text = f"""
## 赛季统计摘要
- 总游戏数: {summary['total_games']}
- 总胜场: {summary['total_wins']}
- 整体胜率: {summary['overall_winrate']:.1%}
- 覆盖版本: {summary['patches_covered']}个版本
- 使用英雄: {summary['unique_champions']}个英雄
- 涉及位置: {summary['unique_roles']}个位置

## 时间分段表现
### 早期 ({len(tri_period['early']['patches'])}个版本)
- 游戏数: {tri_period['early']['total_games']}
- 胜率: {tri_period['early']['winrate']:.1%}

### 中期 ({len(tri_period['mid']['patches'])}个版本)
- 游戏数: {tri_period['mid']['total_games']}
- 胜率: {tri_period['mid']['winrate']:.1%}

### 晚期 ({len(tri_period['late']['patches'])}个版本)
- 游戏数: {tri_period['late']['total_games']}
- 胜率: {tri_period['late']['winrate']:.1%}

## 年度亮点
"""

    if highlights["best_champion_role"]:
        bcr = highlights["best_champion_role"]
        champ_name = get_champion_name(bcr['champion_id'])
        formatted_text += f"""
### 最佳英雄-位置组合
- 英雄: {champ_name} (ID: {bcr['champion_id']})
- 位置: {bcr['role']}
- 场次: {bcr['games']}
- 胜率: {bcr['winrate']:.1%}
"""

    if highlights["most_played_champion"]:
        mpc = highlights["most_played_champion"]
        champ_name = get_champion_name(mpc['champion_id'])
        formatted_text += f"""
### 最多场次英雄
- 英雄: {champ_name} (ID: {mpc['champion_id']})
- 总场次: {mpc['total_games']}
"""

    if highlights["best_quarter"]:
        bq = highlights["best_quarter"]
        formatted_text += f"""
### 最佳季度
- 季度: {bq['quarter']}
- 胜率: {bq['winrate']:.1%}
- 场次: {bq['games']}
"""

    formatted_text += f"""
## 英雄池演进
- 核心英雄数量: {len(champion_pool['core_champions'])}
- 实验性英雄数量: {len(champion_pool['experimental_champions'])}
- 月度英雄池广度范围: {min(m['unique_champions'] for m in champion_pool['monthly_breadth'])} - {max(m['unique_champions'] for m in champion_pool['monthly_breadth'])}
"""

    return formatted_text.strip()


def generate_fun_tags(analysis: Dict[str, Any]) -> List[str]:
    """
    根据年度数据生成趣味化标签

    Args:
        analysis: generate_comprehensive_annual_analysis返回的数据

    Returns:
        趣味标签列表，例如: ["🎮 峡谷劳模", "👑 大神玩家", "❤️ 亚索专精"]
    """
    tags = []
    summary = analysis["summary"]
    highlights = analysis["annual_highlights"]

    # 1. 场次标签
    total_games = summary['total_games']
    if total_games >= 500:
        tags.append("🎮 峡谷劳模")
    elif total_games >= 300:
        tags.append("🎮 资深召唤师")
    elif total_games >= 100:
        tags.append("🎮 活跃玩家")
    else:
        tags.append("🎮 休闲玩家")

    # 2. 胜率标签
    overall_winrate = summary['overall_winrate']
    if overall_winrate >= 0.60:
        tags.append("👑 大神玩家")
    elif overall_winrate >= 0.55:
        tags.append("⭐ 高手玩家")
    elif overall_winrate >= 0.50:
        tags.append("✨ 稳定输出")
    elif overall_winrate >= 0.45:
        tags.append("💪 努力成长中")
    else:
        tags.append("❤️ 送温暖大使")

    # 3. 英雄专精标签
    if highlights["most_played_champion"]:
        mpc = highlights["most_played_champion"]
        champ_name = get_champion_name(mpc['champion_id'])
        if mpc['total_games'] >= 50:
            tags.append(f"❤️ {champ_name}专精")

    # 4. 最佳表现标签
    if highlights["best_champion_role"]:
        bcr = highlights["best_champion_role"]
        if bcr['winrate'] >= 0.65:
            champ_name = get_champion_name(bcr['champion_id'])
            tags.append(f"🏆 {champ_name}之神")

    # 5. 英雄池标签
    unique_champions = summary['unique_champions']
    if unique_champions >= 20:
        tags.append("🎯 全能型选手")
    elif unique_champions >= 10:
        tags.append("🎯 多面手")
    elif unique_champions <= 5:
        tags.append("🎯 专精型选手")

    # 6. 进步标签 (根据三期对比)
    tri_period = analysis["time_segments"]["tri_period"]
    if tri_period:
        early_wr = tri_period.get("early", {}).get("winrate", 0)
        late_wr = tri_period.get("late", {}).get("winrate", 0)

        if late_wr > early_wr + 0.05:
            tags.append("📈 进步之星")
        elif late_wr > early_wr:
            tags.append("📈 稳步提升")

    return tags


def generate_share_text(analysis: Dict[str, Any], style: str = "twitter") -> str:
    """
    生成社交分享文案

    Args:
        analysis: generate_comprehensive_annual_analysis返回的数据
        style: "twitter", "casual", "formal"

    Returns:
        分享文案字符串
    """
    summary = analysis["summary"]
    highlights = analysis["annual_highlights"]
    metadata = analysis["metadata"]

    # 生成标签
    fun_tags = generate_fun_tags(analysis)
    primary_tag = fun_tags[0] if fun_tags else "🎮 召唤师"

    # 获取最常玩英雄
    most_played_champ = ""
    if highlights["most_played_champion"]:
        champ_name = get_champion_name(highlights["most_played_champion"]['champion_id'])
        most_played_champ = champ_name

    # 计算进步
    tri_period = analysis["time_segments"]["tri_period"]
    early_wr = tri_period.get("early", {}).get("winrate", 0)
    late_wr = tri_period.get("late", {}).get("winrate", 0)
    improvement = late_wr - early_wr

    patch_range = metadata["patch_range"]

    if style == "twitter":
        # Twitter风格：简短、有趣、带emoji
        if improvement > 0.05:
            text = f"🎮 #RiftRewind {patch_range[0]}-{patch_range[1]} 赛季总结\n\n"
            text += f"{primary_tag}，{summary['total_games']}场排位，"
            text += f"胜率从{early_wr:.1%}提升到{late_wr:.1%}！📈\n\n"
            if most_played_champ:
                text += f"最爱英雄：{most_played_champ} ❤️\n"
            text += f"你的年度表现如何？来查看你的 #RiftRewind 吧！"
        else:
            text = f"🎮 #RiftRewind {patch_range[0]}-{patch_range[1]} 赛季总结\n\n"
            text += f"{primary_tag}，{summary['total_games']}场排位，"
            text += f"整体胜率{summary['overall_winrate']:.1%}！\n\n"
            if most_played_champ:
                text += f"最爱英雄：{most_played_champ} ❤️\n"
            text += f"来看看你的年度数据！#RiftRewind"

    elif style == "casual":
        # 轻松风格：朋友间分享
        text = f"刚看了我的{patch_range[0]}-{patch_range[1]}赛季数据，"
        text += f"打了{summary['total_games']}场，胜率{summary['overall_winrate']:.1%}！"

        if improvement > 0.05:
            text += f"从赛季初{early_wr:.1%}进步到{late_wr:.1%}，还不错哈哈😄"
        elif improvement < -0.05:
            text += f"虽然状态有点下滑，但坚持打完了整个赛季💪"
        else:
            text += f"表现还算稳定！"

        if most_played_champ:
            text += f"\n最喜欢的英雄是{most_played_champ}，你呢？"

    elif style == "formal":
        # 正式风格：详细数据报告
        text = f"【{patch_range[0]}-{patch_range[1]}赛季数据报告】\n\n"
        text += f"总场次：{summary['total_games']}场\n"
        text += f"总胜场：{summary['total_wins']}场\n"
        text += f"整体胜率：{summary['overall_winrate']:.1%}\n"
        text += f"使用英雄：{summary['unique_champions']}个\n"
        text += f"覆盖版本：{summary['patches_covered']}个版本\n\n"

        if improvement > 0:
            text += f"赛季成长：胜率提升{improvement:.1%}\n"

        if highlights["best_champion_role"]:
            bcr = highlights["best_champion_role"]
            champ_name = get_champion_name(bcr['champion_id'])
            text += f"最佳表现：{champ_name}（{bcr['role']}），{bcr['games']}场，胜率{bcr['winrate']:.1%}"

    return text


def format_annual_card_data(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    格式化年度总结卡片数据，供前端生成图片使用

    Args:
        analysis: generate_comprehensive_annual_analysis返回的数据

    Returns:
        前端卡片所需的数据格式
    """
    summary = analysis["summary"]
    highlights = analysis["annual_highlights"]
    metadata = analysis["metadata"]

    # 生成趣味标签
    fun_tags = generate_fun_tags(analysis)

    # 获取核心英雄
    core_champions = analysis["champion_pool_evolution"]["core_champions"][:3]
    core_champions_display = []
    for c in core_champions:
        core_champions_display.append({
            "name": get_champion_name(c['champion_id']),
            "games": c['patch_count'],
            "coverage": round(c['coverage'] * 100, 1)
        })

    # 最常玩英雄
    most_played = None
    if highlights["most_played_champion"]:
        mpc = highlights["most_played_champion"]
        most_played = {
            "name": get_champion_name(mpc['champion_id']),
            "games": mpc['total_games']
        }

    # 最佳表现
    best_performance = None
    if highlights["best_champion_role"]:
        bcr = highlights["best_champion_role"]
        best_performance = {
            "champion": get_champion_name(bcr['champion_id']),
            "role": bcr['role'],
            "games": bcr['games'],
            "winrate": round(bcr['winrate'] * 100, 1)
        }

    # 计算进步
    tri_period = analysis["time_segments"]["tri_period"]
    progress = {
        "early_winrate": round(tri_period.get("early", {}).get("winrate", 0) * 100, 1),
        "late_winrate": round(tri_period.get("late", {}).get("winrate", 0) * 100, 1),
        "improvement": round((tri_period.get("late", {}).get("winrate", 0) -
                             tri_period.get("early", {}).get("winrate", 0)) * 100, 1)
    }

    patch_range = metadata["patch_range"]

    return {
        "season": f"{patch_range[0]} - {patch_range[1]}",
        "fun_tags": fun_tags,
        "stats": {
            "total_games": summary['total_games'],
            "total_wins": summary['total_wins'],
            "overall_winrate": round(summary['overall_winrate'] * 100, 1),
            "unique_champions": summary['unique_champions'],
            "patches_covered": summary['patches_covered']
        },
        "most_played": most_played,
        "best_performance": best_performance,
        "core_champions": core_champions_display,
        "progress": progress,
        "share_texts": {
            "twitter": generate_share_text(analysis, "twitter"),
            "casual": generate_share_text(analysis, "casual"),
            "formal": generate_share_text(analysis, "formal")
        }
    }


def calculate_growth_metrics(all_packs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate player growth metrics (kda_adj, obj_rate, avg_time_to_core)
    Compares early season vs late season performance

    Args:
        all_packs: All Player-Pack data

    Returns:
        {
            "kda_adj": {"early": 2.1, "late": 2.8, "growth": 0.33},
            "obj_rate": {"early": 0.8, "late": 1.4, "growth": 0.75},
            "time_to_core": {"early": 32.0, "late": 27.0, "improvement": -0.16}
        }
    """
    # Split into early/late periods
    sorted_patches = sorted(all_packs.keys())
    split_point = len(sorted_patches) // 2

    early_patches = sorted_patches[:split_point]
    late_patches = sorted_patches[split_point:]

    # Aggregate metrics for early period
    early_kda = []
    early_obj = []
    early_time = []

    for patch in early_patches:
        pack = all_packs[patch]
        for cr in pack.get("by_cr", []):
            if cr.get("kda_adj"):
                early_kda.append(cr["kda_adj"])
            if cr.get("obj_rate"):
                early_obj.append(cr["obj_rate"])
            if cr.get("avg_time_to_core"):
                early_time.append(cr["avg_time_to_core"])

    # Aggregate metrics for late period
    late_kda = []
    late_obj = []
    late_time = []

    for patch in late_patches:
        pack = all_packs[patch]
        for cr in pack.get("by_cr", []):
            if cr.get("kda_adj"):
                late_kda.append(cr["kda_adj"])
            if cr.get("obj_rate"):
                late_obj.append(cr["obj_rate"])
            if cr.get("avg_time_to_core"):
                late_time.append(cr["avg_time_to_core"])

    # Calculate averages
    early_kda_avg = sum(early_kda) / len(early_kda) if early_kda else 0
    late_kda_avg = sum(late_kda) / len(late_kda) if late_kda else 0
    kda_growth = (late_kda_avg - early_kda_avg) / early_kda_avg if early_kda_avg > 0 else 0

    early_obj_avg = sum(early_obj) / len(early_obj) if early_obj else 0
    late_obj_avg = sum(late_obj) / len(late_obj) if late_obj else 0
    obj_growth = (late_obj_avg - early_obj_avg) / early_obj_avg if early_obj_avg > 0 else 0

    early_time_avg = sum(early_time) / len(early_time) if early_time else 0
    late_time_avg = sum(late_time) / len(late_time) if late_time else 0
    time_improvement = (late_time_avg - early_time_avg) / early_time_avg if early_time_avg > 0 else 0

    return {
        "kda_adj": {
            "early": round(early_kda_avg, 2),
            "late": round(late_kda_avg, 2),
            "growth": round(kda_growth, 3),
            "trend": "improving" if kda_growth > 0.05 else "stable" if kda_growth > -0.05 else "declining"
        },
        "obj_rate": {
            "early": round(early_obj_avg, 2),
            "late": round(late_obj_avg, 2),
            "growth": round(obj_growth, 3),
            "trend": "improving" if obj_growth > 0.1 else "stable" if obj_growth > -0.1 else "declining"
        },
        "time_to_core": {
            "early": round(early_time_avg, 1),
            "late": round(late_time_avg, 1),
            "improvement": round(time_improvement, 3),
            "trend": "improving" if time_improvement < -0.05 else "stable" if time_improvement < 0.05 else "declining"
        }
    }


def calculate_adaptation_score(all_packs: Dict[str, Any], trends: Dict) -> Dict[str, Any]:
    """
    Calculate meta adaptation score (0-100)

    Scoring algorithm:
    - Trend stability (30%): Low patch-to-patch winrate variance
    - Data quality (25%): High CONFIDENT governance tag ratio
    - Build evolution (25%): Build adaptation frequency
    - Champion flexibility (20%): Champion pool diversity

    Args:
        all_packs: All Player-Pack data
        trends: Trend analysis from multi_version agent

    Returns:
        {
            "score": 85,
            "grade": "A-",
            "strengths": ["Quick build adaptation", "Consistent performance"],
            "improvements": ["Limited champion diversity"]
        }
    """
    # 1. Calculate trend stability (30%)
    monthly = segment_by_time(all_packs, "monthly")
    monthly_winrates = [m["winrate"] for m in monthly.values() if m["total_games"] >= 5]

    if len(monthly_winrates) >= 2:
        variance = sum((wr - sum(monthly_winrates)/len(monthly_winrates))**2 for wr in monthly_winrates) / len(monthly_winrates)
        # Lower variance = better (max 30 points)
        stability_score = max(0, 30 - variance * 100)
    else:
        stability_score = 15  # Neutral score

    # 2. Calculate data quality (25%)
    total_games = 0
    confident_games = 0

    for pack in all_packs.values():
        for cr in pack.get("by_cr", []):
            games = cr.get("games", 0)
            total_games += games
            if cr.get("governance_tag") == "CONFIDENT":
                confident_games += games

    quality_ratio = confident_games / total_games if total_games > 0 else 0
    quality_score = quality_ratio * 25

    # 3. Calculate build evolution (25%)
    build_changes = 0
    prev_builds = {}

    for patch in sorted(all_packs.keys()):
        pack = all_packs[patch]
        for cr in pack.get("by_cr", []):
            champ_role_key = f"{cr['champ_id']}_{cr['role']}"
            current_build = tuple(cr.get("build_core", []))

            if champ_role_key in prev_builds:
                if prev_builds[champ_role_key] != current_build:
                    build_changes += 1

            prev_builds[champ_role_key] = current_build

    # More build changes = better adaptation (normalize to 25 points)
    build_score = min(25, build_changes * 2)

    # 4. Calculate champion flexibility (20%)
    unique_champs = set()
    for pack in all_packs.values():
        for cr in pack.get("by_cr", []):
            unique_champs.add(cr["champ_id"])

    # More champions = more flexible (normalize to 20 points)
    flexibility_score = min(20, len(unique_champs) * 1.5)

    # Total score
    total_score = int(stability_score + quality_score + build_score + flexibility_score)

    # Determine letter grade
    if total_score >= 90:
        grade = "A+"
    elif total_score >= 85:
        grade = "A"
    elif total_score >= 80:
        grade = "A-"
    elif total_score >= 75:
        grade = "B+"
    elif total_score >= 70:
        grade = "B"
    elif total_score >= 65:
        grade = "B-"
    elif total_score >= 60:
        grade = "C+"
    else:
        grade = "C"

    # Identify strengths and improvements
    strengths = []
    improvements = []

    if stability_score >= 20:
        strengths.append("Consistent cross-patch performance")
    elif stability_score < 15:
        improvements.append("High performance variance between patches")

    if quality_score >= 18:
        strengths.append("High data reliability (>70% CONFIDENT)")
    elif quality_score < 12:
        improvements.append("Limited sample sizes for confident analysis")

    if build_score >= 18:
        strengths.append("Quick to adapt builds")
    elif build_score < 12:
        improvements.append("Slow to adjust item builds")

    if flexibility_score >= 15:
        strengths.append("Diverse champion pool")
    elif flexibility_score < 10:
        improvements.append("Limited champion pool diversity")

    return {
        "score": total_score,
        "grade": grade,
        "component_scores": {
            "stability": round(stability_score, 1),
            "quality": round(quality_score, 1),
            "build_evolution": round(build_score, 1),
            "flexibility": round(flexibility_score, 1)
        },
        "strengths": strengths,
        "improvements": improvements
    }


def calculate_consistency_profile(all_packs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate consistency profile: monthly variance + governance quality

    Args:
        all_packs: All Player-Pack data

    Returns:
        {
            "monthly_variance": 0.123,
            "variance_grade": "B+",
            "governance_distribution": {
                "CONFIDENT": {"count": 57, "percentage": 45},
                "CAUTION": {"count": 41, "percentage": 32},
                "CONTEXT": {"count": 29, "percentage": 23}
            },
            "stability_trend": {
                "early_variance": 0.18,
                "late_variance": 0.08,
                "improving": true
            }
        }
    """
    # Calculate monthly variance
    monthly = segment_by_time(all_packs, "monthly")
    monthly_winrates = [m["winrate"] for m in monthly.values() if m["total_games"] >= 5]

    if len(monthly_winrates) >= 2:
        avg_wr = sum(monthly_winrates) / len(monthly_winrates)
        variance = sum((wr - avg_wr)**2 for wr in monthly_winrates) / len(monthly_winrates)
        monthly_variance = variance ** 0.5  # Standard deviation
    else:
        monthly_variance = 0

    # Variance grading
    if monthly_variance < 0.08:
        variance_grade = "A"
    elif monthly_variance < 0.12:
        variance_grade = "B+"
    elif monthly_variance < 0.15:
        variance_grade = "B"
    elif monthly_variance < 0.20:
        variance_grade = "C+"
    else:
        variance_grade = "C"

    # Calculate governance distribution
    governance_counts = {"CONFIDENT": 0, "CAUTION": 0, "CONTEXT": 0}
    total_games = 0

    for pack in all_packs.values():
        for cr in pack.get("by_cr", []):
            tag = cr.get("governance_tag", "CONTEXT")
            games = cr.get("games", 0)
            governance_counts[tag] += games
            total_games += games

    governance_distribution = {}
    for tag, count in governance_counts.items():
        percentage = (count / total_games * 100) if total_games > 0 else 0
        governance_distribution[tag] = {
            "count": count,
            "percentage": round(percentage, 1)
        }

    # Calculate stability trend (early vs late variance)
    sorted_patches = sorted(all_packs.keys())
    split_point = len(sorted_patches) // 2

    early_patches = sorted_patches[:split_point]
    late_patches = sorted_patches[split_point:]

    # Early period variance
    early_monthly = {}
    for patch in early_patches:
        month_key = all_packs[patch].get("generation_timestamp", "")[:7]
        if month_key not in early_monthly:
            early_monthly[month_key] = {"wins": 0, "games": 0}

        for cr in all_packs[patch].get("by_cr", []):
            early_monthly[month_key]["games"] += cr["games"]
            early_monthly[month_key]["wins"] += cr["wins"]

    early_winrates = [m["wins"]/m["games"] for m in early_monthly.values() if m["games"] >= 5]
    early_variance = 0
    if len(early_winrates) >= 2:
        early_avg = sum(early_winrates) / len(early_winrates)
        early_variance = (sum((wr - early_avg)**2 for wr in early_winrates) / len(early_winrates)) ** 0.5

    # Late period variance
    late_monthly = {}
    for patch in late_patches:
        month_key = all_packs[patch].get("generation_timestamp", "")[:7]
        if month_key not in late_monthly:
            late_monthly[month_key] = {"wins": 0, "games": 0}

        for cr in all_packs[patch].get("by_cr", []):
            late_monthly[month_key]["games"] += cr["games"]
            late_monthly[month_key]["wins"] += cr["wins"]

    late_winrates = [m["wins"]/m["games"] for m in late_monthly.values() if m["games"] >= 5]
    late_variance = 0
    if len(late_winrates) >= 2:
        late_avg = sum(late_winrates) / len(late_winrates)
        late_variance = (sum((wr - late_avg)**2 for wr in late_winrates) / len(late_winrates)) ** 0.5

    return {
        "monthly_variance": round(monthly_variance, 3),
        "variance_grade": variance_grade,
        "governance_distribution": governance_distribution,
        "stability_trend": {
            "early_variance": round(early_variance, 3),
            "late_variance": round(late_variance, 3),
            "improving": late_variance < early_variance
        }
    }

"""
Build Simulator - Player Build Analysis

Analyze player's build choices vs meta optimal builds.
"""

from typing import Dict, Any, List, Tuple, Optional
import os
import json


def extract_player_top_champions(packs_dir: str, top_n: int = 3, time_range: str = None, queue_id: int = None) -> List[Dict[str, Any]]:
    """
    从player-pack中提取玩家最常用的champion+role组合

    Args:
        packs_dir: Pack文件目录
        top_n: 返回前N个最常用的champion
        time_range: Time range filter (optional)
        queue_id: Queue ID filter (optional)
    
    Returns:
        List of {champ_id, role, games, wins, build_core, p_hat}
    """
    from datetime import datetime, timedelta
    from pathlib import Path
    
    all_champions = []
    
    # Calculate time filter if needed
    cutoff_timestamp = None
    cutoff_end_timestamp = None
    
    if time_range == "2024-01-01":
        cutoff_timestamp = datetime(2024, 1, 9).timestamp()
        cutoff_end_timestamp = datetime(2025, 1, 6, 23, 59, 59, 999000).timestamp()
    elif time_range == "past-365":
        cutoff_timestamp = (datetime.now() - timedelta(days=365)).timestamp()
    
    # Build file pattern based on queue_id
    packs_path = Path(packs_dir)
    if queue_id is not None:
        pack_pattern = f"pack_*_{queue_id}.json"
    else:
        pack_pattern = "pack_*.json"
    
    pack_files = sorted(packs_path.glob(pack_pattern))

    # 读取所有patch的pack文件
    for pack_file in pack_files:
        if not pack_file.name.startswith("pack_") or not pack_file.name.endswith(".json"):
            continue

        with open(pack_file, 'r') as f:
            pack_data = json.load(f)
        
        # Verify queue_id matches if specified
        if queue_id is not None:
            pack_queue_id = pack_data.get('queue_id', 420)
            if pack_queue_id != queue_id:
                continue
        
        # Apply time range filter
        if cutoff_timestamp:
            has_match_in_range = False
            pack_earliest = pack_data.get("earliest_match_date")
            pack_latest = pack_data.get("latest_match_date")
            
            if pack_earliest or pack_latest:
                if pack_earliest:
                    earliest_dt = datetime.fromisoformat(pack_earliest.replace('Z', '+00:00'))
                    earliest_ts = earliest_dt.timestamp()
                if pack_latest:
                    latest_dt = datetime.fromisoformat(pack_latest.replace('Z', '+00:00'))
                    latest_ts = latest_dt.timestamp()
                
                if cutoff_end_timestamp:
                    if earliest_ts <= cutoff_end_timestamp and latest_ts >= cutoff_timestamp:
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
            
            if not has_match_in_range:
                continue

        # 提取by_cr数据
        for cr in pack_data.get("by_cr", []):
            all_champions.append({
                "champ_id": cr["champ_id"],
                "role": cr["role"],
                "games": cr["games"],
                "wins": cr["wins"],
                "build_core": cr.get("build_core", []),
                "p_hat": cr.get("p_hat", 0.0),
                "kda_adj": cr.get("kda_adj", 0.0),
                "cp_25": cr.get("cp_25", 0.0)
            })

    # 合并相同champion+role的数据
    merged = {}
    for champ_data in all_champions:
        key = (champ_data["champ_id"], champ_data["role"])
        if key not in merged:
            merged[key] = {
                "champ_id": champ_data["champ_id"],
                "role": champ_data["role"],
                "games": 0,
                "wins": 0,
                "build_cores": [],  # 收集所有build_core
                "kda_values": [],
                "cp_values": []
            }
        merged[key]["games"] += champ_data["games"]
        merged[key]["wins"] += champ_data["wins"]
        if champ_data["build_core"]:
            merged[key]["build_cores"].append(champ_data["build_core"])
        merged[key]["kda_values"].append(champ_data["kda_adj"])
        merged[key]["cp_values"].append(champ_data["cp_25"])

    # 转换为列表并计算平均值
    result = []
    for key, data in merged.items():
        # 找出最常用的build_core
        if data["build_cores"]:
            # 简单选择第一个（可以改进为选择最常见的）
            most_common_build = data["build_cores"][0]
        else:
            most_common_build = []

        result.append({
            "champ_id": data["champ_id"],
            "role": data["role"],
            "games": data["games"],
            "wins": data["wins"],
            "win_rate": data["wins"] / data["games"] if data["games"] > 0 else 0,
            "build_core": most_common_build,
            "avg_kda": sum(data["kda_values"]) / len(data["kda_values"]) if data["kda_values"] else 0,
            "avg_cp": sum(data["cp_values"]) / len(data["cp_values"]) if data["cp_values"] else 0
        })

    # 按场次排序，返回top N
    result.sort(key=lambda x: x["games"], reverse=True)
    return result[:top_n]


def get_meta_optimal_builds(
    champion_id: int,
    role: str,
    parquet_path: str = "/home/zty/rift_rewind/backend/data/gold/parquet/fact_match_performance.parquet",
    top_n: int = 2
) -> List[List[int]]:
    """
    从Gold layer查询该champion+role的高胜率出装

    Returns:
        List of build arrays (each build is a list of item IDs)
    """
    try:
        import duckdb
        import json

        # Gold layer使用position列（不是role），final_items是数组
        # 映射role到position
        role_to_position = {
            "TOP": "TOP",
            "JUNGLE": "JUNGLE",
            "MIDDLE": "MIDDLE",
            "BOTTOM": "BOTTOM",
            "UTILITY": "UTILITY"
        }
        position = role_to_position.get(role, role)

        # 查询高胜率出装
        query = f"""
        SELECT
            final_items,
            COUNT(*) as games,
            AVG(CAST(win AS FLOAT)) as win_rate
        FROM read_parquet('{parquet_path}')
        WHERE champion_id = {champion_id}
          AND position = '{position}'
          AND final_items IS NOT NULL
        GROUP BY final_items
        HAVING COUNT(*) >= 5
        ORDER BY win_rate DESC, games DESC
        LIMIT {top_n * 3}
        """

        conn = duckdb.connect(':memory:')
        result = conn.execute(query).fetchall()
        conn.close()

        # 排除饰品ID
        trinket_ids = {3340, 3363, 3364, 2055, 2056, 2057, 2050, 2051, 2052}

        builds = []
        for row in result:
            if len(builds) >= top_n:
                break

            # 解析final_items数组
            items_str = row[0]
            try:
                # DuckDB返回的是字符串形式的数组，如 "[3108, 6672, 3124]"
                items_list = json.loads(items_str.replace("'", '"'))

                # 过滤掉饰品
                core_items = [item_id for item_id in items_list if item_id not in trinket_ids and item_id > 1000]

                # 只取前6件核心装备
                if len(core_items) >= 3:  # 至少3件核心装备
                    builds.append(core_items[:6])
            except:
                continue

        return builds
    except Exception as e:
        print(f"Error querying meta builds: {e}")
        import traceback
        traceback.print_exc()
        return []


def generate_player_build_analysis(packs_dir: str, time_range: str = None, queue_id: int = None) -> Dict[str, Any]:
    """
    生成玩家出装分析数据

    Args:
        packs_dir: Pack文件目录
        time_range: Time range filter (optional)
        queue_id: Queue ID filter (optional)

    Returns:
        {
            "champion": {...},
            "player_build": [...],
            "meta_builds": [[...], [...]],
            "analysis_ready": bool
        }
    """
    # 1. 提取玩家最常用的champion
    top_champions = extract_player_top_champions(packs_dir, top_n=1, time_range=time_range, queue_id=queue_id)

    if not top_champions:
        return {
            "error": "No champion data found in player pack",
            "analysis_ready": False
        }

    top_champ = top_champions[0]

    # 2. 查询meta最优出装
    meta_builds = get_meta_optimal_builds(
        champion_id=top_champ["champ_id"],
        role=top_champ["role"],
        top_n=2
    )

    if not meta_builds:
        return {
            "error": f"No meta builds found for champion {top_champ['champ_id']} in role {top_champ['role']}",
            "analysis_ready": False
        }

    return {
        "champion": {
            "id": top_champ["champ_id"],
            "role": top_champ["role"],
            "player_games": top_champ["games"],
            "player_wins": top_champ["wins"],
            "player_win_rate": top_champ["win_rate"],
            "player_avg_kda": top_champ["avg_kda"],
            "player_avg_cp": top_champ["avg_cp"]
        },
        "player_build": top_champ["build_core"],
        "meta_builds": meta_builds,
        "analysis_ready": True
    }


def format_player_build_analysis_for_prompt(analysis: Dict[str, Any]) -> str:
    """
    格式化玩家出装分析数据为LLM友好的文本
    """
    if not analysis.get("analysis_ready"):
        return f"分析失败: {analysis.get('error', 'Unknown error')}"

    from src.utils.id_mappings import get_champion_name, get_item_name

    lines = []

    lines.append("# 玩家出装分析\n")

    champ_data = analysis["champion"]
    champ_name = get_champion_name(champ_data["id"])

    lines.append(f"**英雄**: {champ_name} (ID: {champ_data['id']})")
    lines.append(f"**位置**: {champ_data['role']}")
    lines.append(f"**玩家场次**: {champ_data['player_games']}")
    lines.append(f"**玩家胜率**: {champ_data['player_win_rate']:.1%}")
    lines.append(f"**玩家平均KDA**: {champ_data['player_avg_kda']:.2f}")
    lines.append(f"**玩家平均战斗力**: {champ_data['player_avg_cp']:.0f}")
    lines.append("")

    # 玩家出装
    lines.append("## 玩家常用出装（核心3件）\n")
    player_build_names = [get_item_name(item_id) for item_id in analysis["player_build"]]
    lines.append(f"**装备**: {' → '.join(player_build_names)}")
    lines.append(f"**装备ID**: {analysis['player_build']}")
    lines.append("")

    # Meta最优出装
    lines.append("## Meta高胜率出装方案\n")
    for i, meta_build in enumerate(analysis["meta_builds"], 1):
        meta_build_names = [get_item_name(item_id) for item_id in meta_build]
        lines.append(f"### 方案{i}")
        lines.append(f"**装备**: {' → '.join(meta_build_names)}")
        lines.append(f"**装备ID**: {meta_build}")
        lines.append("")

    lines.append("## 分析要求\n")
    lines.append("请对比玩家出装与Meta高胜率出装，分析：")
    lines.append("1. 玩家出装的优劣势")
    lines.append("2. Meta出装的特点和优势")
    lines.append("3. 具体的出装优化建议")
    lines.append("4. 不同局势下的出装选择策略")

    return "\n".join(lines)

"""PeerComparisonAgent - Peer Comparison Tools"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from src.core.statistical_utils import wilson_confidence_interval
from src.analytics import RankBaselineGenerator


def load_player_data(packs_dir: str, all_packs_data: Optional[list] = None, time_range: str = None, queue_id: int = None) -> Dict[str, Any]:
    """
    加载玩家数据

    Args:
        packs_dir: Pack文件目录
        all_packs_data: 预加载的所有pack数据（可选，来自AgentContext缓存）
        time_range: Time range filter (optional)
        queue_id: Queue ID filter (optional)

    Returns:
        玩家数据统计
    """
    from datetime import datetime, timedelta
    
    # 如果提供了缓存数据，直接使用（但需要过滤）
    if all_packs_data is not None:
        packs = all_packs_data
    else:
        # 否则从文件系统读取
        packs_dir = Path(packs_dir)
        
        # Build file pattern based on queue_id
        if queue_id is not None:
            pack_pattern = f"pack_*_{queue_id}.json"
        else:
            pack_pattern = "pack_*.json"
        
        pack_files = sorted(packs_dir.glob(pack_pattern))
        packs = []
        for pack_file in pack_files:
            with open(pack_file, 'r') as f:
                pack_data = json.load(f)
                
                # Verify queue_id matches if specified
                if queue_id is not None:
                    pack_queue_id = pack_data.get('queue_id', 420)
                    if pack_queue_id != queue_id:
                        continue
                
                # Apply time range filter
                if time_range:
                    cutoff_timestamp = None
                    cutoff_end_timestamp = None
                    
                    if time_range == "2024-01-01":
                        cutoff_timestamp = datetime(2024, 1, 9).timestamp()
                        cutoff_end_timestamp = datetime(2025, 1, 6, 23, 59, 59, 999000).timestamp()
                    elif time_range == "past-365":
                        cutoff_timestamp = (datetime.now() - timedelta(days=365)).timestamp()
                    
                    if cutoff_timestamp:
                        has_match_in_range = False
                        pack_earliest = pack_data.get("earliest_match_date")
                        pack_latest = pack_data.get("latest_match_date")
                        
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
                        
                        if not has_match_in_range:
                            continue
                
                packs.append(pack_data)
    
    # 如果提供了缓存数据但需要过滤，在这里过滤
    if all_packs_data is not None and (time_range or queue_id):
        filtered_packs = []
        for pack in packs:
            # Verify queue_id matches if specified
            if queue_id is not None:
                pack_queue_id = pack.get('queue_id', 420)
                if pack_queue_id != queue_id:
                    continue
            
            # Apply time range filter
            if time_range:
                cutoff_timestamp = None
                cutoff_end_timestamp = None
                
                if time_range == "2024-01-01":
                    cutoff_timestamp = datetime(2024, 1, 9).timestamp()
                    cutoff_end_timestamp = datetime(2025, 1, 6, 23, 59, 59, 999000).timestamp()
                elif time_range == "past-365":
                    cutoff_timestamp = (datetime.now() - timedelta(days=365)).timestamp()
                
                if cutoff_timestamp:
                    has_match_in_range = False
                    pack_earliest = pack.get("earliest_match_date")
                    pack_latest = pack.get("latest_match_date")
                    
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
                        if "generation_timestamp" in pack:
                            pack_timestamp = pack["generation_timestamp"]
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
            
            filtered_packs.append(pack)
        packs = filtered_packs

    # 处理pack数据
    total_games = total_wins = 0
    for pack in packs:
        for cr in pack.get("by_cr", []):
            total_games += cr["games"]
            total_wins += cr["wins"]

    wr = total_wins / total_games if total_games > 0 else 0
    return {
        "total_games": total_games,
        "winrate": round(wr, 3)
    }


def load_rank_baseline(rank: str) -> Optional[Dict[str, Any]]:
    """
    加载段位基准数据（自动生成如果不存在）

    数据来源优先级：
    1. 已有缓存文件: data/baselines/rank_baselines.json
    2. 自动生成: 从Gold layer实时计算
    """
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent.parent.parent
    baseline_file = project_root / "data/baselines/rank_baselines.json"
    gold_parquet = project_root / "data/gold/parquet/fact_match_performance.parquet"

    # 检查是否已有baseline文件
    if not baseline_file.exists():
        print(f"⚠️  段位基准数据不存在，正在从Gold layer自动生成...")

        # 检查Gold layer数据是否存在
        if not gold_parquet.exists():
            print(f"❌ Gold layer数据不存在: {gold_parquet}")
            print("   请先运行数据pipeline生成Gold layer数据")
            return None

        try:
            # 自动生成baseline数据
            generator = RankBaselineGenerator(
                parquet_path=str(gold_parquet),
                min_sample_size=20
            )
            generator.save(
                output_path=str(baseline_file),
                include_role_baselines=False
            )
            print(f"✅ 段位基准数据已生成: {baseline_file}")
        except Exception as e:
            print(f"❌ 生成段位基准数据失败: {e}")
            return None

    # 读取baseline数据
    with open(baseline_file, 'r', encoding='utf-8') as f:
        baseline_data = json.load(f)

    # 返回指定段位的基准
    if rank.upper() not in baseline_data:
        print(f"⚠️  段位 {rank.upper()} 在基准数据中不存在")
        return None

    return baseline_data[rank.upper()]


def compare_to_baseline(player_data: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    """对比玩家数据与基准"""
    wr_diff = player_data["winrate"] - baseline["avg_winrate"]

    assessment = "above_average" if wr_diff > 0.02 else ("below_average" if wr_diff < -0.02 else "average")

    return {
        "player": player_data,
        "baseline": baseline,
        "winrate_diff": round(wr_diff, 3),
        "assessment": assessment
    }


def format_analysis_for_prompt(comparison: Dict[str, Any], rank: str) -> str:
    """格式化对比数据"""
    player = comparison["player"]
    baseline = comparison["baseline"]

    return f"""# 同段位对比分析数据

**段位**: {rank}
**样本量**: {baseline.get('sample_size', 'N/A')}

## 玩家表现
- 总场次: {player['total_games']}
- 胜率: {player['winrate']:.1%}

## 段位基准（Gold Layer数据）
- 平均胜率: {baseline['avg_winrate']:.1%}
- 平均KDA: {baseline.get('avg_kda', 0):.2f}
- 平均CS/min: {baseline.get('avg_cs_per_minute', 0):.2f}
- 平均金币/min: {baseline.get('avg_gold_per_minute', 0):.1f}

## 对比结果
- 胜率差值: {comparison['winrate_diff']:+.1%}
- 评估: {comparison['assessment']}
"""

"""ProgressTrackerAgent - Progress Tracking Tools"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta
from src.core.statistical_utils import wilson_ci_tuple as wilson_confidence_interval


def load_recent_packs(packs_dir: str, window_size: int = 10, time_range: str = None) -> Dict[str, Any]:
    """
    Load recent N patch versions of Player-Packs

    Args:
        packs_dir: Player-Pack directory path
        window_size: Number of recent patches to load
        time_range: Time range filter
            - "2024-01-01": Load data from Past Season 2024 (2024-01-09 to 2025-01-06, patches 14.1 to 14.25)
            - "past-365": Load data from past 365 days
            - None: Load recent window_size patches

    Returns:
        Dict of packs keyed by patch version
    """
    packs_dir = Path(packs_dir)

    # Calculate time filter if needed
    cutoff_timestamp = None
    cutoff_end_timestamp = None  # For date range filtering
    
    if time_range == "2024-01-01":
        # Past Season 2024: patch 14.1 (2024-01-09) to patch 14.25 (2025-01-06)
        cutoff_timestamp = datetime(2024, 1, 9).timestamp()
        cutoff_end_timestamp = datetime(2025, 1, 6, 23, 59, 59, 999000).timestamp()
    elif time_range == "past-365":
        cutoff_timestamp = (datetime.now() - timedelta(days=365)).timestamp()

    # Get all pack files
    all_pack_files = sorted(packs_dir.glob("pack_*.json"))

    # Apply time filter if specified
    if cutoff_timestamp:
        filtered_pack_files = []
        for pack_file in all_pack_files:
            with open(pack_file, 'r') as f:
                pack_data = json.load(f)
                
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
                
                if has_match_in_range:
                    filtered_pack_files.append(pack_file)

        pack_files = filtered_pack_files
    else:
        # Use most recent window_size packs
        pack_files = all_pack_files[-window_size:]

    packs = {}
    for pack_file in pack_files:
        with open(pack_file, 'r') as f:
            pack = json.load(f)
            packs[pack["patch"]] = pack
    return packs


def analyze_progress(recent_packs: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze progress trends (first half vs second half comparison)"""
    patches = sorted(recent_packs.keys())
    mid = len(patches) // 2

    early_patches = patches[:mid]
    late_patches = patches[mid:]

    def aggregate_stats(patch_list):
        total_games = total_wins = 0
        for patch in patch_list:
            pack = recent_packs[patch]
            for cr in pack.get("by_cr", []):
                total_games += cr["games"]
                total_wins += cr["wins"]
        wr = total_wins / total_games if total_games > 0 else 0
        ci_lo, ci_hi = wilson_confidence_interval(total_wins, total_games)
        return {"games": total_games, "wins": total_wins, "winrate": wr, "ci_lo": ci_lo, "ci_hi": ci_hi}

    early = aggregate_stats(early_patches)
    late = aggregate_stats(late_patches)

    improvement = late["winrate"] - early["winrate"]
    trend = "improving" if improvement > 0.03 else ("declining" if improvement < -0.03 else "stable")

    return {
        "early_half": early,
        "late_half": late,
        "improvement": round(improvement, 3),
        "trend": trend,
        "total_patches": len(patches),
        "patches_analyzed": {"early": early_patches, "late": late_patches}
    }


def format_analysis_for_prompt(analysis: Dict[str, Any]) -> str:
    """Format analysis data for LLM prompt"""
    early = analysis["early_half"]
    late = analysis["late_half"]

    return f"""# Progress Tracking Analysis Data

**Total Patches**: {analysis['total_patches']}
**Overall Trend**: {analysis['trend']}
**Improvement Magnitude**: {analysis['improvement']:+.1%}

## Early Phase (First {len(analysis['patches_analyzed']['early'])} patches)
- Games Played: {early['games']}
- Win Rate: {early['winrate']:.1%} (CI: {early['ci_lo']:.1%} - {early['ci_hi']:.1%})

## Late Phase (Last {len(analysis['patches_analyzed']['late'])} patches)
- Games Played: {late['games']}
- Win Rate: {late['winrate']:.1%} (CI: {late['ci_lo']:.1%} - {late['ci_hi']:.1%})

**Comparison**: Win rate change from early to late: {analysis['improvement']:+.1%}
"""

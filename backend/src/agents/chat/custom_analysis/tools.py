"""
Custom Analysis Tools - Data Processing for Non-Standard Queries

Leverages quantitative metrics from Player Pack data:
- kda_adj: KDA adjusted
- cp_25: Combat Power at level 25
- obj_rate: Objective participation rate
- avg_time_to_core: Time to complete core build
- effective_n: Effective sample size
- governance_tag: Data quality (CONFIDENT/CAUTION/CONTEXT)
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from dataclasses import dataclass
import sys

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.utils.id_mappings import get_champion_name


@dataclass
class GroupFilter:
    """Filter criteria for data groups"""
    name: str
    time_filter: Optional[Dict[str, Any]] = None  # {"days_ago": 30, "days_until": 0}
    champion_filter: Optional[List[int]] = None   # [145, 202, 222]
    role_filter: Optional[List[str]] = None       # ["ADC", "SUPPORT"]
    governance_filter: Optional[List[str]] = None # ["CONFIDENT", "CAUTION"]
    min_games: int = 5                            # Minimum games threshold


@dataclass
class QuantitativeMetrics:
    """Quantitative metrics for a data group"""
    games: int
    wins: int
    winrate: float

    # Combat metrics
    kda_adj: float
    cp_25: float

    # Objective metrics
    obj_rate: float

    # Economy metrics
    avg_time_to_core: float

    # Data quality
    effective_n: float
    confident_pct: float  # % of games with CONFIDENT tag

    # Champion diversity
    unique_champions: int
    top_champions: List[Tuple[str, int]]  # [(name, games), ...]


def load_all_packs(packs_dir: str) -> List[Dict[str, Any]]:
    """
    Load all Player Pack files

    Args:
        packs_dir: Player pack directory path

    Returns:
        List of pack dictionaries
    """
    packs_path = Path(packs_dir)
    if not packs_path.exists():
        return []

    all_packs = []
    for pack_file in sorted(packs_path.glob("pack_*.json")):
        try:
            with open(pack_file, 'r', encoding='utf-8') as f:
                pack_data = json.load(f)
                all_packs.append(pack_data)
        except Exception as e:
            print(f"⚠️ Failed to load {pack_file}: {e}")

    return all_packs


def filter_packs_by_group(
    all_packs: List[Dict[str, Any]],
    group_filter: GroupFilter
) -> List[Dict[str, Any]]:
    """
    Filter packs based on group filter criteria

    Supports:
    - Time filtering (days_ago, days_until)
    - Champion filtering
    - Role filtering
    - Governance quality filtering
    - Minimum games threshold

    Args:
        all_packs: All player pack data
        group_filter: Filter criteria

    Returns:
        Filtered list of packs
    """
    filtered = []

    # Calculate time cutoffs if time_filter specified
    cutoff_start = None
    cutoff_end = None

    if group_filter.time_filter:
        days_ago = group_filter.time_filter.get("days_ago")
        days_until = group_filter.time_filter.get("days_until", 0)

        if days_ago is not None:
            cutoff_start = (datetime.now() - timedelta(days=days_ago)).timestamp()
            cutoff_end = (datetime.now() - timedelta(days=days_until)).timestamp()

    for pack in all_packs:
        # Time filter - check match dates
        if cutoff_start and cutoff_end:
            pack_earliest = pack.get("earliest_match_date")
            pack_latest = pack.get("latest_match_date")

            has_match_in_range = False

            if pack_earliest and pack_latest:
                try:
                    if isinstance(pack_earliest, str):
                        earliest_dt = datetime.fromisoformat(pack_earliest.replace('Z', '+00:00'))
                        earliest_dt = earliest_dt.replace(tzinfo=None)
                        earliest_ts = earliest_dt.timestamp()
                    else:
                        earliest_ts = pack_earliest

                    if isinstance(pack_latest, str):
                        latest_dt = datetime.fromisoformat(pack_latest.replace('Z', '+00:00'))
                        latest_dt = latest_dt.replace(tzinfo=None)
                        latest_ts = latest_dt.timestamp()
                    else:
                        latest_ts = pack_latest

                    # Check if date range overlaps with filter range
                    if earliest_ts <= cutoff_end and latest_ts >= cutoff_start:
                        has_match_in_range = True
                except:
                    pass

            if not has_match_in_range:
                continue

        # Create filtered pack with matching by_cr entries
        filtered_by_cr = []

        for cr in pack.get("by_cr", []):
            # Champion filter
            if group_filter.champion_filter:
                if cr["champ_id"] not in group_filter.champion_filter:
                    continue

            # Role filter
            if group_filter.role_filter:
                if cr["role"] not in group_filter.role_filter:
                    continue

            # Governance filter
            if group_filter.governance_filter:
                if cr.get("governance_tag") not in group_filter.governance_filter:
                    continue

            # Min games threshold
            if cr.get("games", 0) < group_filter.min_games:
                continue

            filtered_by_cr.append(cr)

        # Only include pack if it has matching by_cr entries
        if filtered_by_cr:
            pack_copy = pack.copy()
            pack_copy["by_cr"] = filtered_by_cr
            filtered.append(pack_copy)

    return filtered


def calculate_metrics_from_packs(
    packs: List[Dict[str, Any]],
    group_name: str
) -> QuantitativeMetrics:
    """
    Calculate quantitative metrics from filtered packs

    Leverages all available quantitative metrics:
    - kda_adj: Adjusted KDA
    - cp_25: Combat Power at level 25
    - obj_rate: Objective participation rate
    - avg_time_to_core: Time to complete core build
    - effective_n: Effective sample size
    - governance_tag: Data quality

    Args:
        packs: Filtered pack data
        group_name: Group name for logging

    Returns:
        QuantitativeMetrics object
    """
    if not packs:
        return QuantitativeMetrics(
            games=0, wins=0, winrate=0.0,
            kda_adj=0.0, cp_25=0.0, obj_rate=0.0,
            avg_time_to_core=0.0, effective_n=0.0,
            confident_pct=0.0, unique_champions=0,
            top_champions=[]
        )

    total_games = 0
    total_wins = 0

    # Weighted sums (weighted by games)
    weighted_kda = 0.0
    weighted_cp = 0.0
    weighted_obj = 0.0
    weighted_time = 0.0
    weighted_en = 0.0

    # Data quality tracking
    confident_games = 0

    # Champion tracking
    champion_games = defaultdict(int)

    for pack in packs:
        for cr in pack.get("by_cr", []):
            games = cr.get("games", 0)
            wins = cr.get("wins", 0)

            total_games += games
            total_wins += wins

            # Weight by games
            weighted_kda += cr.get("kda_adj", 0) * games
            weighted_cp += cr.get("cp_25", 0) * games
            weighted_obj += cr.get("obj_rate", 0) * games
            weighted_time += cr.get("avg_time_to_core", 0) * games
            weighted_en += cr.get("effective_n", 0) * games

            # Data quality
            if cr.get("governance_tag") == "CONFIDENT":
                confident_games += games

            # Champion diversity
            champ_id = cr.get("champ_id")
            if champ_id:
                champion_games[champ_id] += games

    # Calculate averages
    winrate = (total_wins / total_games) if total_games > 0 else 0.0
    avg_kda = (weighted_kda / total_games) if total_games > 0 else 0.0
    avg_cp = (weighted_cp / total_games) if total_games > 0 else 0.0
    avg_obj = (weighted_obj / total_games) if total_games > 0 else 0.0
    avg_time = (weighted_time / total_games) if total_games > 0 else 0.0
    avg_en = (weighted_en / total_games) if total_games > 0 else 0.0
    confident_pct = (confident_games / total_games) if total_games > 0 else 0.0

    # Top champions
    top_champions = sorted(
        [(get_champion_name(cid), games) for cid, games in champion_games.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]

    return QuantitativeMetrics(
        games=total_games,
        wins=total_wins,
        winrate=winrate,
        kda_adj=avg_kda,
        cp_25=avg_cp,
        obj_rate=avg_obj,
        avg_time_to_core=avg_time,
        effective_n=avg_en,
        confident_pct=confident_pct,
        unique_champions=len(champion_games),
        top_champions=top_champions
    )


def compare_two_groups(
    group1_metrics: QuantitativeMetrics,
    group2_metrics: QuantitativeMetrics,
    group1_name: str,
    group2_name: str
) -> Dict[str, Any]:
    """
    Compare two groups quantitatively

    Returns delta and percentage change for all metrics

    Args:
        group1_metrics: Metrics for first group
        group2_metrics: Metrics for second group
        group1_name: Name of first group
        group2_name: Name of second group

    Returns:
        Comparison dict with deltas and trends
    """
    def calc_delta(val1: float, val2: float) -> Tuple[float, float, str]:
        """Calculate delta, percentage change, and trend"""
        delta = val2 - val1
        pct = (delta / val1 * 100) if val1 != 0 else 0.0

        if abs(pct) < 2:
            trend = "stable"
        elif pct > 0:
            trend = "improving"
        else:
            trend = "declining"

        return delta, pct, trend

    # Winrate comparison
    wr_delta, wr_pct, wr_trend = calc_delta(
        group1_metrics.winrate * 100,
        group2_metrics.winrate * 100
    )

    # KDA comparison
    kda_delta, kda_pct, kda_trend = calc_delta(
        group1_metrics.kda_adj,
        group2_metrics.kda_adj
    )

    # Combat Power comparison
    cp_delta, cp_pct, cp_trend = calc_delta(
        group1_metrics.cp_25,
        group2_metrics.cp_25
    )

    # Objective rate comparison
    obj_delta, obj_pct, obj_trend = calc_delta(
        group1_metrics.obj_rate,
        group2_metrics.obj_rate
    )

    # Time to core comparison (lower is better)
    time_delta, time_pct, _ = calc_delta(
        group1_metrics.avg_time_to_core,
        group2_metrics.avg_time_to_core
    )
    time_trend = "improving" if time_delta < -0.5 else "stable" if abs(time_delta) < 0.5 else "declining"

    return {
        "group1_name": group1_name,
        "group2_name": group2_name,
        "sample_sizes": {
            "group1_games": group1_metrics.games,
            "group2_games": group2_metrics.games
        },
        "winrate": {
            "group1": round(group1_metrics.winrate * 100, 1),
            "group2": round(group2_metrics.winrate * 100, 1),
            "delta": round(wr_delta, 1),
            "pct_change": round(wr_pct, 1),
            "trend": wr_trend
        },
        "kda_adj": {
            "group1": round(group1_metrics.kda_adj, 2),
            "group2": round(group2_metrics.kda_adj, 2),
            "delta": round(kda_delta, 2),
            "pct_change": round(kda_pct, 1),
            "trend": kda_trend
        },
        "combat_power": {
            "group1": round(group1_metrics.cp_25, 0),
            "group2": round(group2_metrics.cp_25, 0),
            "delta": round(cp_delta, 0),
            "pct_change": round(cp_pct, 1),
            "trend": cp_trend
        },
        "objective_rate": {
            "group1": round(group1_metrics.obj_rate, 2),
            "group2": round(group2_metrics.obj_rate, 2),
            "delta": round(obj_delta, 2),
            "pct_change": round(obj_pct, 1),
            "trend": obj_trend
        },
        "time_to_core": {
            "group1": round(group1_metrics.avg_time_to_core, 1),
            "group2": round(group2_metrics.avg_time_to_core, 1),
            "delta": round(time_delta, 1),
            "pct_change": round(time_pct, 1),
            "trend": time_trend
        },
        "data_quality": {
            "group1_confident_pct": round(group1_metrics.confident_pct * 100, 1),
            "group2_confident_pct": round(group2_metrics.confident_pct * 100, 1)
        },
        "champion_diversity": {
            "group1_unique": group1_metrics.unique_champions,
            "group2_unique": group2_metrics.unique_champions,
            "group1_top_champions": group1_metrics.top_champions[:3],
            "group2_top_champions": group2_metrics.top_champions[:3]
        }
    }


def format_comparison_for_prompt(
    comparison: Dict[str, Any],
    query: str
) -> str:
    """
    Format comparison data for LLM prompt

    Args:
        comparison: Comparison dict from compare_two_groups()
        query: Original user query

    Returns:
        Formatted text string
    """
    g1 = comparison["group1_name"]
    g2 = comparison["group2_name"]

    text = f"""# Custom Analysis Request

**User Query**: {query}

## Data Groups Comparison

**{g1}**: {comparison['sample_sizes']['group1_games']} games
**{g2}**: {comparison['sample_sizes']['group2_games']} games

## Quantitative Metrics Comparison

### 1. Win Rate
- {g1}: {comparison['winrate']['group1']}%
- {g2}: {comparison['winrate']['group2']}%
- **Change**: {comparison['winrate']['delta']:+.1f}% ({comparison['winrate']['pct_change']:+.1f}%)
- **Trend**: {comparison['winrate']['trend']}

### 2. KDA (Adjusted)
- {g1}: {comparison['kda_adj']['group1']:.2f}
- {g2}: {comparison['kda_adj']['group2']:.2f}
- **Change**: {comparison['kda_adj']['delta']:+.2f} ({comparison['kda_adj']['pct_change']:+.1f}%)
- **Trend**: {comparison['kda_adj']['trend']}

### 3. Combat Power (Level 25)
- {g1}: {comparison['combat_power']['group1']:.0f}
- {g2}: {comparison['combat_power']['group2']:.0f}
- **Change**: {comparison['combat_power']['delta']:+.0f} ({comparison['combat_power']['pct_change']:+.1f}%)
- **Trend**: {comparison['combat_power']['trend']}

### 4. Objective Participation Rate
- {g1}: {comparison['objective_rate']['group1']:.2f}
- {g2}: {comparison['objective_rate']['group2']:.2f}
- **Change**: {comparison['objective_rate']['delta']:+.2f} ({comparison['objective_rate']['pct_change']:+.1f}%)
- **Trend**: {comparison['objective_rate']['trend']}

### 5. Time to Core Build
- {g1}: {comparison['time_to_core']['group1']:.1f} min
- {g2}: {comparison['time_to_core']['group2']:.1f} min
- **Change**: {comparison['time_to_core']['delta']:+.1f} min ({comparison['time_to_core']['pct_change']:+.1f}%)
- **Trend**: {comparison['time_to_core']['trend']} (lower is better)

### 6. Data Quality
- {g1} CONFIDENT data: {comparison['data_quality']['group1_confident_pct']:.1f}%
- {g2} CONFIDENT data: {comparison['data_quality']['group2_confident_pct']:.1f}%

### 7. Champion Diversity
- {g1}: {comparison['champion_diversity']['group1_unique']} unique champions
  Top 3: {', '.join([f"{name} ({games})" for name, games in comparison['champion_diversity']['group1_top_champions']])}

- {g2}: {comparison['champion_diversity']['group2_unique']} unique champions
  Top 3: {', '.join([f"{name} ({games})" for name, games in comparison['champion_diversity']['group2_top_champions']])}
"""

    return text

"""
MatchSimilarityFinder - Similar Match Detection

Finds similar historical matches based on champion, role, and game context.
Used for build simulation and performance comparison.
"""

import duckdb
from pathlib import Path
from typing import Dict, Any, List, Optional


class MatchSimilarityFinder:
    """
    相似对局查找器

    基于Gold层数据，查找与指定条件相似的历史对局，
    用于出装模拟和性能对比。

    Example:
        >>> finder = MatchSimilarityFinder(
        ...     parquet_path="data/gold/parquet/fact_match_performance.parquet"
        ... )
        >>> similar_matches = finder.find_similar(
        ...     champion_id=92,
        ...     role="TOP",
        ...     game_duration_min=20,
        ...     game_duration_max=30,
        ...     limit=50
        ... )
    """

    def __init__(
        self,
        parquet_path: str = "data/gold/parquet/fact_match_performance.parquet"
    ):
        """
        Args:
            parquet_path: Path to Gold layer parquet file
        """
        parquet_file = Path(parquet_path)
        if not parquet_file.exists():
            raise FileNotFoundError(
                f"Gold layer parquet not found: {parquet_path}\n"
                f"Please run silver_to_gold_metrics.py first"
            )

        self.parquet_path = parquet_path

    def find_similar(
        self,
        champion_id: int,
        role: str,
        game_duration_min: Optional[int] = None,
        game_duration_max: Optional[int] = None,
        opponent_champion_id: Optional[int] = None,
        win: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查找相似对局

        Args:
            champion_id: Champion ID to match
            role: Role to match (TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY)
            game_duration_min: Minimum game duration in minutes (optional)
            game_duration_max: Maximum game duration in minutes (optional)
            opponent_champion_id: Opponent champion ID in same role (optional)
            win: Filter by win/loss (optional)
            limit: Maximum number of matches to return

        Returns:
            List of similar match records with performance metrics
        """
        # Build query conditions
        conditions = [
            f"champion_id = {champion_id}",
            f"position = '{role}'"
        ]

        if game_duration_min is not None:
            conditions.append(f"game_duration_minutes >= {game_duration_min}")

        if game_duration_max is not None:
            conditions.append(f"game_duration_minutes <= {game_duration_max}")

        if win is not None:
            win_value = 'TRUE' if win else 'FALSE'
            conditions.append(f"win = {win_value}")

        where_clause = " AND ".join(conditions)

        # Build query
        query = f"""
        SELECT
            match_id,
            champion_id,
            champion_name,
            position,
            win,
            game_duration_minutes,
            kills,
            deaths,
            assists,
            damage_to_champions,
            damage_per_minute,
            gold_earned,
            gold_per_minute,
            cs_total,
            cs_per_minute,
            kill_participation,
            vision_score,
            vision_score_per_minute,
            final_items
        FROM read_parquet(?)
        WHERE {where_clause}
        LIMIT ?
        """

        conn = duckdb.connect()
        result = conn.execute(query, [self.parquet_path, limit]).fetchall()

        # Convert to dictionaries
        column_names = [
            "match_id", "champion_id", "champion_name", "position", "win",
            "game_duration_minutes", "kills", "deaths", "assists",
            "damage_to_champions", "damage_per_minute",
            "gold_earned", "gold_per_minute", "cs_total",
            "cs_per_minute", "kill_participation", "vision_score",
            "vision_score_per_minute", "final_items"
        ]

        matches = []
        for row in result:
            match_dict = dict(zip(column_names, row))

            # Parse final_items (stored as string like "3071,3142,3053,0,0,0,0")
            final_items_str = match_dict.get("final_items", "")
            if final_items_str:
                try:
                    match_dict["items"] = [
                        int(item_id)
                        for item_id in final_items_str.split(",")
                        if item_id and int(item_id) > 0
                    ]
                except (ValueError, AttributeError):
                    match_dict["items"] = []
            else:
                match_dict["items"] = []

            # Remove final_items string column
            match_dict.pop("final_items", None)

            matches.append(match_dict)

        return matches

    def compare_builds(
        self,
        champion_id: int,
        role: str,
        build_a: List[int],
        build_b: List[int],
        game_duration_min: Optional[int] = None,
        game_duration_max: Optional[int] = None,
        min_samples: int = 10
    ) -> Dict[str, Any]:
        """
        对比两种出装方案的历史表现

        Args:
            champion_id: Champion ID
            role: Role
            build_a: First build (list of item IDs)
            build_b: Second build (list of item IDs)
            game_duration_min: Minimum game duration filter (optional)
            game_duration_max: Maximum game duration filter (optional)
            min_samples: Minimum samples required for valid comparison

        Returns:
            {
                "build_a_stats": {...},
                "build_b_stats": {...},
                "comparison": {...}
            }
        """
        # Find matches for each build
        all_matches = self.find_similar(
            champion_id=champion_id,
            role=role,
            game_duration_min=game_duration_min,
            game_duration_max=game_duration_max,
            limit=1000
        )

        # Filter by builds
        build_a_matches = []
        build_b_matches = []

        for match in all_matches:
            match_items = set(match["items"])

            # Check if build A items are in this match
            if set(build_a).issubset(match_items):
                build_a_matches.append(match)

            # Check if build B items are in this match
            if set(build_b).issubset(match_items):
                build_b_matches.append(match)

        # Calculate statistics for each build
        build_a_stats = self._calculate_build_stats(build_a_matches, "Build A")
        build_b_stats = self._calculate_build_stats(build_b_matches, "Build B")

        # Compare
        comparison = self._compare_stats(build_a_stats, build_b_stats, min_samples)

        return {
            "build_a_stats": build_a_stats,
            "build_b_stats": build_b_stats,
            "comparison": comparison
        }

    def _calculate_build_stats(
        self,
        matches: List[Dict[str, Any]],
        build_name: str
    ) -> Dict[str, Any]:
        """计算出装方案的统计数据"""
        if not matches:
            return {
                "build_name": build_name,
                "sample_size": 0,
                "win_rate": None,
                "avg_damage_per_minute": None,
                "avg_gold_per_minute": None,
                "avg_kill_participation": None,
                "avg_kda": None
            }

        wins = sum(1 for m in matches if m["win"])
        win_rate = wins / len(matches)

        avg_dpm = sum(m["damage_per_minute"] for m in matches) / len(matches)
        avg_gpm = sum(m["gold_per_minute"] for m in matches) / len(matches)
        avg_kp = sum(m["kill_participation"] for m in matches) / len(matches)

        total_kda = 0
        for m in matches:
            kills = m["kills"]
            deaths = m["deaths"] if m["deaths"] > 0 else 1
            assists = m["assists"]
            kda = (kills + assists) / deaths
            total_kda += kda
        avg_kda = total_kda / len(matches)

        return {
            "build_name": build_name,
            "sample_size": len(matches),
            "win_rate": round(win_rate, 3),
            "avg_damage_per_minute": round(avg_dpm, 1),
            "avg_gold_per_minute": round(avg_gpm, 1),
            "avg_kill_participation": round(avg_kp, 3),
            "avg_kda": round(avg_kda, 2)
        }

    def _compare_stats(
        self,
        stats_a: Dict[str, Any],
        stats_b: Dict[str, Any],
        min_samples: int
    ) -> Dict[str, Any]:
        """对比两种出装的统计数据"""
        # Check sample size validity
        if stats_a["sample_size"] < min_samples or stats_b["sample_size"] < min_samples:
            return {
                "valid_comparison": False,
                "reason": f"Insufficient samples (need at least {min_samples} each)",
                "build_a_samples": stats_a["sample_size"],
                "build_b_samples": stats_b["sample_size"]
            }

        # Calculate differences
        metrics = ["win_rate", "avg_damage_per_minute", "avg_gold_per_minute",
                   "avg_kill_participation", "avg_kda"]

        differences = {}
        for metric in metrics:
            if stats_a[metric] is not None and stats_b[metric] is not None:
                diff = stats_a[metric] - stats_b[metric]
                diff_pct = (diff / stats_b[metric] * 100) if stats_b[metric] != 0 else 0
                differences[metric] = {
                    "absolute_diff": round(diff, 3),
                    "percentage_diff": round(diff_pct, 1)
                }

        # Determine winner
        if differences["win_rate"]["absolute_diff"] > 0.05:  # 5% win rate difference
            winner = "build_a"
        elif differences["win_rate"]["absolute_diff"] < -0.05:
            winner = "build_b"
        else:
            winner = "similar"

        return {
            "valid_comparison": True,
            "build_a_samples": stats_a["sample_size"],
            "build_b_samples": stats_b["sample_size"],
            "differences": differences,
            "winner": winner,
            "confidence": "high" if min(stats_a["sample_size"], stats_b["sample_size"]) >= 30 else "moderate"
        }

"""
FrequentTeammateDetector - Teammate Relationship Analysis

Detects frequently played together teammates and analyzes their synergy.
"""

import duckdb
from pathlib import Path
from typing import Dict, Any, List, Optional
import json


class FrequentTeammateDetector:
    """
    检测经常一起玩的队友和他们的默契度

    分析玩家之间的配合关系，包括：
    - 共同对局次数
    - 配合胜率
    - 角色组合分析
    - 配合时长统计

    Example:
        >>> detector = FrequentTeammateDetector(parquet_path="data/gold/parquet/fact_match_performance.parquet")
        >>> teammates = detector.find_frequent_teammates(player_puuid="player123", min_games=5)
        >>> synergy = detector.analyze_synergy(teammates)
        >>> detector.save(output_path="data/baselines/teammate_synergy.json")
    """

    def __init__(
        self,
        parquet_path: str = "data/gold/parquet/fact_match_performance.parquet",
        min_games_together: int = 5
    ):
        """
        Args:
            parquet_path: Path to Gold layer parquet data
            min_games_together: Minimum games together to be considered frequent teammate
        """
        self.parquet_path = Path(parquet_path)
        if not self.parquet_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

        self.min_games_together = min_games_together
        self.teammates_data = None

    def find_frequent_teammates(
        self,
        player_key: str,
        min_games: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        查找经常一起玩的队友

        Args:
            player_key: Target player key
            min_games: Minimum games together (overrides class default)

        Returns:
            List of teammate records with statistics
        """
        min_games = min_games or self.min_games_together

        query = """
        WITH player_matches AS (
            SELECT DISTINCT
                match_id,
                team_id,
                player_key
            FROM read_parquet(?)
            WHERE player_key = ?
        ),
        teammate_pairs AS (
            SELECT
                pm.player_key as player_key,
                fp.player_key as teammate_key,
                'Player_' || fp.player_key as teammate_name,
                fp.match_id,
                fp.team_id,
                fp.position as role,
                fp.champion_id,
                fp.champion_name,
                fp.win,
                fp.game_duration_minutes,
                fp.kills,
                fp.deaths,
                fp.assists,
                fp.damage_to_champions,
                fp.gold_earned
            FROM player_matches pm
            JOIN read_parquet(?) fp
                ON pm.match_id = fp.match_id
                AND pm.team_id = fp.team_id
                AND pm.player_key != fp.player_key
        ),
        teammate_stats AS (
            SELECT
                teammate_key,
                ANY_VALUE(teammate_name) as teammate_name,
                COUNT(DISTINCT match_id) as games_together,
                SUM(CASE WHEN win THEN 1 ELSE 0 END) as wins_together,
                AVG(CASE WHEN win THEN 1.0 ELSE 0.0 END) as win_rate_together,
                AVG(game_duration_minutes) as avg_game_duration,

                -- Role distribution
                COUNT(DISTINCT role) as roles_played,
                MODE() WITHIN GROUP (ORDER BY role) as most_common_role,

                -- Performance metrics
                AVG(kills) as avg_kills,
                AVG(deaths) as avg_deaths,
                AVG(assists) as avg_assists,
                AVG(damage_to_champions) as avg_damage,
                AVG(gold_earned) as avg_gold,

                -- Champion pool
                COUNT(DISTINCT champion_id) as unique_champions,
                MODE() WITHIN GROUP (ORDER BY champion_name) as most_played_champion
            FROM teammate_pairs
            GROUP BY teammate_key
            HAVING COUNT(DISTINCT match_id) >= ?
        )
        SELECT *
        FROM teammate_stats
        ORDER BY games_together DESC, win_rate_together DESC
        """

        conn = duckdb.connect(database=':memory:')
        try:
            result = conn.execute(
                query,
                [str(self.parquet_path), player_key, str(self.parquet_path), min_games]
            ).fetchall()

            columns = [
                'teammate_key', 'teammate_name', 'games_together', 'wins_together',
                'win_rate_together', 'avg_game_duration', 'roles_played', 'most_common_role',
                'avg_kills', 'avg_deaths', 'avg_assists', 'avg_damage', 'avg_gold',
                'unique_champions', 'most_played_champion'
            ]

            teammates = []
            for row in result:
                teammate = dict(zip(columns, row))

                # Calculate KDA
                if teammate['avg_deaths'] > 0:
                    teammate['avg_kda'] = (teammate['avg_kills'] + teammate['avg_assists']) / teammate['avg_deaths']
                else:
                    teammate['avg_kda'] = teammate['avg_kills'] + teammate['avg_assists']

                teammates.append(teammate)

            return teammates

        finally:
            conn.close()

    def analyze_synergy(
        self,
        player_key1: str,
        player_key2: str
    ) -> Dict[str, Any]:
        """
        分析两个玩家之间的配合默契度

        Args:
            player_key1: First player key
            player_key2: Second player key

        Returns:
            Detailed synergy analysis
        """
        query = """
        WITH player_matches AS (
            SELECT DISTINCT
                match_id,
                team_id
            FROM read_parquet(?)
            WHERE player_key = ?
        ),
        teammate_matches AS (
            SELECT
                pm.match_id,
                p1.player_key as player1_key,
                'Player_' || p1.player_key as player1_name,
                p1.position as player1_role,
                p1.champion_name as player1_champion,
                p1.kills as p1_kills,
                p1.deaths as p1_deaths,
                p1.assists as p1_assists,
                p1.damage_to_champions as p1_damage,

                p2.player_key as player2_key,
                'Player_' || p2.player_key as player2_name,
                p2.position as player2_role,
                p2.champion_name as player2_champion,
                p2.kills as p2_kills,
                p2.deaths as p2_deaths,
                p2.assists as p2_assists,
                p2.damage_to_champions as p2_damage,

                p1.win,
                p1.game_duration_minutes
            FROM player_matches pm
            JOIN read_parquet(?) p1
                ON pm.match_id = p1.match_id
                AND pm.team_id = p1.team_id
                AND p1.player_key = ?
            JOIN read_parquet(?) p2
                ON pm.match_id = p2.match_id
                AND pm.team_id = p2.team_id
                AND p2.player_key = ?
        ),
        synergy_stats AS (
            SELECT
                COUNT(*) as games_together,
                SUM(CASE WHEN win THEN 1 ELSE 0 END) as wins,
                AVG(CASE WHEN win THEN 1.0 ELSE 0.0 END) as win_rate,
                AVG(game_duration_minutes) as avg_duration,

                -- Role combinations
                COUNT(DISTINCT player1_role || '-' || player2_role) as role_combos,
                MODE() WITHIN GROUP (ORDER BY player1_role || '-' || player2_role) as most_common_combo,

                -- Combined performance
                AVG(p1_kills + p2_kills) as avg_combined_kills,
                AVG(p1_deaths + p2_deaths) as avg_combined_deaths,
                AVG(p1_assists + p2_assists) as avg_combined_assists,
                AVG(p1_damage + p2_damage) as avg_combined_damage,

                -- Individual stats
                ANY_VALUE(player1_name) as player1_name,
                ANY_VALUE(player2_name) as player2_name,
                AVG(p1_kills) as p1_avg_kills,
                AVG(p1_deaths) as p1_avg_deaths,
                AVG(p1_assists) as p1_avg_assists,
                AVG(p2_kills) as p2_avg_kills,
                AVG(p2_deaths) as p2_avg_deaths,
                AVG(p2_assists) as p2_avg_assists
            FROM teammate_matches
        )
        SELECT *
        FROM synergy_stats
        """

        conn = duckdb.connect(database=':memory:')
        try:
            result = conn.execute(
                query,
                [
                    str(self.parquet_path), player_key1,
                    str(self.parquet_path), player_key1,
                    str(self.parquet_path), player_key2
                ]
            ).fetchone()

            if not result or result[0] == 0:
                return {
                    "games_together": 0,
                    "synergy_score": 0,
                    "message": "No games found together"
                }

            columns = [
                'games_together', 'wins', 'win_rate', 'avg_duration',
                'role_combos', 'most_common_combo',
                'avg_combined_kills', 'avg_combined_deaths', 'avg_combined_assists', 'avg_combined_damage',
                'player1_name', 'player2_name',
                'p1_avg_kills', 'p1_avg_deaths', 'p1_avg_assists',
                'p2_avg_kills', 'p2_avg_deaths', 'p2_avg_assists'
            ]

            synergy = dict(zip(columns, result))

            # Calculate synergy score (0-100)
            # Components:
            # - Win rate: 40 points
            # - Combined KDA: 30 points
            # - Games together: 20 points (capped at 50 games)
            # - Role diversity: 10 points

            win_rate_score = synergy['win_rate'] * 40

            combined_kda = (synergy['avg_combined_kills'] + synergy['avg_combined_assists']) / max(synergy['avg_combined_deaths'], 1)
            kda_score = min(combined_kda / 10.0, 1.0) * 30  # Normalize to 0-30

            games_score = min(synergy['games_together'] / 50.0, 1.0) * 20

            role_diversity_score = min(synergy['role_combos'] / 5.0, 1.0) * 10

            synergy_score = win_rate_score + kda_score + games_score + role_diversity_score

            synergy['synergy_score'] = round(synergy_score, 1)

            # Calculate individual KDAs
            if synergy['p1_avg_deaths'] > 0:
                synergy['p1_kda'] = (synergy['p1_avg_kills'] + synergy['p1_avg_assists']) / synergy['p1_avg_deaths']
            else:
                synergy['p1_kda'] = synergy['p1_avg_kills'] + synergy['p1_avg_assists']

            if synergy['p2_avg_deaths'] > 0:
                synergy['p2_kda'] = (synergy['p2_avg_kills'] + synergy['p2_avg_assists']) / synergy['p2_avg_deaths']
            else:
                synergy['p2_kda'] = synergy['p2_avg_kills'] + synergy['p2_avg_assists']

            return synergy

        finally:
            conn.close()

    def generate_team_report(
        self,
        player_keys: List[str]
    ) -> Dict[str, Any]:
        """
        生成团队配合报告

        Args:
            player_keys: List of player keys (2-5 players)

        Returns:
            Team synergy report with pairwise analysis
        """
        if len(player_keys) < 2:
            raise ValueError("Need at least 2 players for team report")
        if len(player_keys) > 5:
            raise ValueError("Maximum 5 players allowed")

        # Analyze all pairs
        pairs = []
        for i in range(len(player_keys)):
            for j in range(i + 1, len(player_keys)):
                synergy = self.analyze_synergy(player_keys[i], player_keys[j])
                if synergy['games_together'] > 0:
                    pairs.append({
                        'player1_key': player_keys[i],
                        'player2_key': player_keys[j],
                        'synergy': synergy
                    })

        # Calculate overall team synergy
        if pairs:
            avg_synergy_score = sum(p['synergy']['synergy_score'] for p in pairs) / len(pairs)
            avg_win_rate = sum(p['synergy']['win_rate'] for p in pairs) / len(pairs)
            total_games = sum(p['synergy']['games_together'] for p in pairs)
        else:
            avg_synergy_score = 0
            avg_win_rate = 0
            total_games = 0

        return {
            'team_size': len(player_keys),
            'pairs_analyzed': len(pairs),
            'total_games': total_games,
            'avg_synergy_score': round(avg_synergy_score, 1),
            'avg_win_rate': round(avg_win_rate, 3),
            'pair_details': pairs,
            'metadata': {
                'min_games_together': self.min_games_together,
                'parquet_path': str(self.parquet_path)
            }
        }

    def save(self, output_path: str) -> None:
        """
        保存teammates数据到JSON文件

        Args:
            output_path: Output file path
        """
        if self.teammates_data is None:
            raise ValueError("No teammates data to save. Run find_frequent_teammates() first.")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.teammates_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Teammates data saved to {output_path}")

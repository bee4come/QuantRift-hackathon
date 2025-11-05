"""
Power Curve Generator - Agent 1 (Risk Forecaster) Data Module

Generates champion power curves across different game time segments.
Used to predict team strength at various game phases.

Key Metrics:
- Early Power (0-15min): Based on early game statistics
- Mid Power (15-25min): Peak performance window
- Late Power (25min+): Scaling potential

Data Source: Gold layer (fact_match_performance.parquet)
"""

import duckdb
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class PowerCurveGenerator:
    """
    Generate champion power curves from Gold layer data

    Power is calculated based on:
    - Damage per minute (40% weight)
    - Gold efficiency (30% weight)
    - Kill participation (20% weight)
    - Vision control (10% weight)
    """

    def __init__(
        self,
        parquet_path: str,
        min_games_per_segment: int = 20
    ):
        """
        Args:
            parquet_path: Path to fact_match_performance.parquet
            min_games_per_segment: Minimum games required per time segment
        """
        self.parquet_path = parquet_path
        self.min_games = min_games_per_segment

        # Validate data exists
        if not Path(parquet_path).exists():
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

    def generate(self) -> Dict[str, Any]:
        """
        Generate power curves for all champion-role combinations

        Returns:
            {
                "champions": {
                    "92": {  # Champion ID
                        "name": "Riven",
                        "roles": {
                            "TOP": {
                                "power_curve": {
                                    0: 45.2,   # 0-5min average power
                                    5: 48.7,   # 5-10min
                                    10: 55.3,  # 10-15min
                                    15: 62.1,  # 15-20min
                                    20: 65.8,  # 20-25min
                                    25: 68.2,  # 25-30min
                                    30: 70.5,  # 30min+
                                },
                                "early_power": 49.7,  # 0-15min average
                                "mid_power": 63.9,    # 15-25min average
                                "late_power": 69.4,   # 25min+ average
                                "peak_time": 30,      # Strongest at 30min
                                "sample_sizes": {
                                    "0-15": 150,
                                    "15-25": 120,
                                    "25+": 80
                                }
                            }
                        }
                    }
                },
                "metadata": {
                    "generated_at": "2025-10-10T...",
                    "total_champions": 171,
                    "total_matches": 10423,
                    "min_games_threshold": 20
                }
            }
        """
        logger.info(f"📊 正在从 {self.parquet_path} 生成战力曲线...")

        conn = duckdb.connect()

        # Query: Calculate power scores by champion, role, and time segment
        query = """
        WITH time_segmented AS (
            SELECT
                champion_id,
                champion_name,
                position as role,
                CASE
                    WHEN game_duration_minutes <= 15 THEN 'early'
                    WHEN game_duration_minutes <= 25 THEN 'mid'
                    ELSE 'late'
                END as time_segment,
                -- Power components (normalized 0-100 scale)
                damage_per_minute,
                gold_per_minute,
                kill_participation,
                vision_score_per_minute,
                win,
                game_duration_minutes
            FROM read_parquet(?)
            WHERE position IS NOT NULL
              AND champion_id IS NOT NULL
        ),
        global_stats AS (
            -- Get global percentiles for normalization
            SELECT
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY damage_per_minute) as dpm_p95,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY gold_per_minute) as gpm_p95
            FROM time_segmented
        ),
        champion_role_stats AS (
            SELECT
                champion_id,
                ANY_VALUE(champion_name) as champion_name,
                role,
                time_segment,
                COUNT(*) as games,

                -- Normalize metrics to 0-100 scale (relative to dataset)
                AVG(damage_per_minute) as avg_dpm,
                AVG(gold_per_minute) as avg_gpm,
                AVG(kill_participation) as avg_kp,
                AVG(vision_score_per_minute) as avg_vspm,
                AVG(CAST(win AS INTEGER)) as winrate
            FROM time_segmented
            GROUP BY champion_id, role, time_segment
            HAVING COUNT(*) >= ?
        )
        SELECT
            c.champion_id,
            c.champion_name,
            c.role,
            c.time_segment,
            c.games,
            c.avg_dpm,
            c.avg_gpm,
            c.avg_kp,
            c.avg_vspm,
            c.winrate,
            -- Calculate power score (0-100)
            (
                (LEAST(c.avg_dpm / NULLIF(g.dpm_p95, 0), 1.0) * 40) +  -- 40% weight
                (LEAST(c.avg_gpm / NULLIF(g.gpm_p95, 0), 1.0) * 30) +  -- 30% weight
                (c.avg_kp * 20) +                                       -- 20% weight (already 0-1)
                (LEAST(c.avg_vspm / 1.5, 1.0) * 10)                    -- 10% weight (1.5 = good vision)
            ) as power_score
        FROM champion_role_stats c
        CROSS JOIN global_stats g
        ORDER BY c.champion_id, c.role, c.time_segment
        """

        results = conn.execute(query, [self.parquet_path, self.min_games]).fetchall()

        if not results:
            logger.warning("⚠️  未找到符合条件的数据")
            return {"champions": {}, "metadata": {}}

        # Organize results
        champions = {}
        total_matches = 0

        for row in results:
            champ_id = str(row[0])
            champ_name = row[1]
            role = row[2]
            time_segment = row[3]
            games = row[4]
            power_score = row[10]  # Last column

            total_matches += games

            # Initialize champion
            if champ_id not in champions:
                champions[champ_id] = {
                    "name": champ_name,
                    "roles": {}
                }

            # Initialize role
            if role not in champions[champ_id]["roles"]:
                champions[champ_id]["roles"][role] = {
                    "power_by_segment": {},
                    "sample_sizes": {}
                }

            # Store segment power
            champions[champ_id]["roles"][role]["power_by_segment"][time_segment] = round(power_score, 1)
            champions[champ_id]["roles"][role]["sample_sizes"][time_segment] = games

        # Generate power curves (interpolate between segments)
        for champ_id, champ_data in champions.items():
            for role, role_data in champ_data["roles"].items():
                segments = role_data["power_by_segment"]

                # Create detailed power curve (every 5 minutes)
                power_curve = {}

                # Get segment powers
                early_power = segments.get('early', 50.0)
                mid_power = segments.get('mid', 50.0)
                late_power = segments.get('late', 50.0)

                # Interpolate
                power_curve[0] = early_power * 0.85    # 0-5min (weaker)
                power_curve[5] = early_power * 0.92    # 5-10min
                power_curve[10] = early_power           # 10-15min
                power_curve[15] = (early_power * 0.3 + mid_power * 0.7)  # Transition
                power_curve[20] = mid_power             # 20-25min
                power_curve[25] = (mid_power * 0.6 + late_power * 0.4)  # Transition
                power_curve[30] = late_power            # 30min+
                power_curve[35] = late_power * 1.02     # Late game scaling
                power_curve[40] = late_power * 1.05     # Very late

                # Store results
                role_data["power_curve"] = {k: round(v, 1) for k, v in power_curve.items()}
                role_data["early_power"] = round(early_power, 1)
                role_data["mid_power"] = round(mid_power, 1)
                role_data["late_power"] = round(late_power, 1)

                # Find peak time
                peak_time = max(power_curve.items(), key=lambda x: x[1])[0]
                role_data["peak_time"] = peak_time

                # Clean up temporary data
                del role_data["power_by_segment"]

        logger.info(f"✅ 成功生成 {len(champions)} 个英雄的战力曲线")

        return {
            "champions": champions,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_champions": len(champions),
                "total_matches": total_matches,
                "min_games_threshold": self.min_games,
                "data_source": self.parquet_path
            }
        }

    def save(self, output_path: str) -> None:
        """
        Generate and save power curves to JSON file

        Args:
            output_path: Path to output JSON file
        """
        data = self.generate()

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 战力曲线数据已保存到: {output_path}")

    def get_champion_power(
        self,
        champion_id: int,
        role: str,
        game_time: int
    ) -> float:
        """
        Get champion power at specific game time

        Args:
            champion_id: Champion ID
            role: Position (TOP/JUNGLE/MIDDLE/BOTTOM/SUPPORT)
            game_time: Game time in minutes

        Returns:
            Power score (0-100)
        """
        data = self.generate()

        champ_id_str = str(champion_id)
        if champ_id_str not in data["champions"]:
            logger.warning(f"⚠️  Champion {champion_id} not found")
            return 50.0  # Default

        champ_data = data["champions"][champ_id_str]
        if role not in champ_data["roles"]:
            logger.warning(f"⚠️  Role {role} not found for champion {champion_id}")
            return 50.0  # Default

        power_curve = champ_data["roles"][role]["power_curve"]

        # Find nearest time point
        time_points = sorted(power_curve.keys())
        if game_time <= time_points[0]:
            return power_curve[time_points[0]]
        if game_time >= time_points[-1]:
            return power_curve[time_points[-1]]

        # Linear interpolation
        for i in range(len(time_points) - 1):
            t1, t2 = time_points[i], time_points[i + 1]
            if t1 <= game_time <= t2:
                p1, p2 = power_curve[t1], power_curve[t2]
                # Interpolate
                ratio = (game_time - t1) / (t2 - t1)
                return p1 + (p2 - p1) * ratio

        return 50.0  # Fallback


if __name__ == "__main__":
    """Quick test"""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(name)s:%(message)s'
    )

    # Test with actual data
    parquet_path = "data/gold/parquet/fact_match_performance.parquet"

    if not Path(parquet_path).exists():
        print(f"❌ Parquet file not found: {parquet_path}")
        sys.exit(1)

    print("=" * 80)
    print("Power Curve Generator - Validation Test")
    print("=" * 80)

    generator = PowerCurveGenerator(parquet_path, min_games_per_segment=20)
    data = generator.generate()

    print(f"\n总英雄数: {data['metadata']['total_champions']}")
    print(f"总对局数: {data['metadata']['total_matches']}")
    print(f"最小游戏阈值: {data['metadata']['min_games_threshold']}")

    # Show example
    if data["champions"]:
        example_id = list(data["champions"].keys())[0]
        example = data["champions"][example_id]
        print(f"\n示例 - {example['name']} (ID: {example_id}):")

        for role, role_data in example["roles"].items():
            print(f"\n  位置: {role}")
            print(f"    早期战力 (0-15分): {role_data['early_power']}")
            print(f"    中期战力 (15-25分): {role_data['mid_power']}")
            print(f"    后期战力 (25分+): {role_data['late_power']}")
            print(f"    战力高峰: {role_data['peak_time']}分钟")
            print(f"    样本量: {role_data['sample_sizes']}")

    print("\n" + "=" * 80)
    print("✅ 验证测试完成")
    print("=" * 80)

"""
Laning Phase Deep Analyzer (Phase 1.4)

Analyzes detailed performance during 0-15 minute laning phase, provides actionable improvement recommendations.
"""
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import numpy as np


class LaningPhaseAnalyzer:
    """
    Laning Phase Deep Analyzer

    Analysis Dimensions:
    1. CS curve: CS efficiency per minute
    2. Experience gap: XP lead/deficit trend
    3. Kill timing: Laning kills and deaths timing
    4. Item timing: First core item completion time
    5. Lane swap timing: Lane swap decisions and effects
    """

    def __init__(self):
        self.laning_phase_end = 15  # Laning phase defined as first 15 minutes
        self.cs_per_min_ideal = 10  # Ideal CS/min

    def analyze_match(self, timeline_data: Dict[str, Any], participant_id: int) -> Dict[str, Any]:
        """
        Analyze laning phase performance for a single match

        Args:
            timeline_data: Timeline data (Bronze layer raw data)
            participant_id: Participant ID (1-10)

        Returns:
            Laning phase analysis result dict
        """
        frames = timeline_data.get("info", {}).get("frames", [])

        if not frames:
            return {"error": "No timeline frames available"}

        # Extract laning phase frames (0-15 minutes)
        laning_frames = [
            frame for frame in frames
            if frame.get("timestamp", 0) <= self.laning_phase_end * 60 * 1000
        ]

        if not laning_frames:
            return {"error": "No laning phase frames found"}

        # Analyze各个dimensions
        cs_analysis = self._analyze_cs_curve(laning_frames, participant_id)
        xp_analysis = self._analyze_xp_trend(laning_frames, participant_id)
        kills_analysis = self._analyze_kill_timing(frames, participant_id)
        item_analysis = self._analyze_item_timing(frames, participant_id)

        return {
            "participant_id": participant_id,
            "phase_duration_minutes": self.laning_phase_end,
            "cs_efficiency": cs_analysis,
            "xp_differential": xp_analysis,
            "kill_timing": kills_analysis,
            "item_completion": item_analysis,
            "overall_score": self._calculate_laning_score(
                cs_analysis, xp_analysis, kills_analysis
            ),
            "recommendations": self._generate_recommendations(
                cs_analysis, xp_analysis, kills_analysis
            )
        }

    def _analyze_cs_curve(
        self,
        frames: List[Dict[str, Any]],
        participant_id: int
    ) -> Dict[str, Any]:
        """
        Analyze CS curve

        Returns:
            {
                "cs_per_minute": [10, 9, 11, ...],  # CS count per minute
                "total_cs_15min": 150,
                "efficiency": 0.75,  # Compared to ideal value
                "weak_minutes": [3, 5],  # Minutes with low CS efficiency
                "cs_lead": 12  # CS differential vs opponent
            }
        """
        cs_curve = []
        timestamps = []

        for frame in frames:
            participant_frame = frame.get("participantFrames", {}).get(str(participant_id), {})
            if not participant_frame:
                continue

            cs = participant_frame.get("minionsKilled", 0) + participant_frame.get("jungleMinionsKilled", 0)
            timestamp_min = frame.get("timestamp", 0) / (60 * 1000)  # Convert to minutes

            cs_curve.append(cs)
            timestamps.append(timestamp_min)

        if not cs_curve:
            return {"error": "No CS data available"}

        # Calculate CS growth per minute
        cs_per_minute = []
        for i in range(1, len(cs_curve)):
            cs_diff = cs_curve[i] - cs_curve[i-1]
            time_diff = timestamps[i] - timestamps[i-1]
            if time_diff > 0:
                cs_per_min = cs_diff / time_diff
                cs_per_minute.append(cs_per_min)

        # Find periods with low CS efficiency (below 80% of ideal)
        weak_minutes = []
        for i, cs_rate in enumerate(cs_per_minute):
            if cs_rate < self.cs_per_min_ideal * 0.8:
                weak_minutes.append(i + 1)  # +1 because starting from minute 2

        # Overall efficiency
        total_cs = cs_curve[-1] if cs_curve else 0
        ideal_cs = self.cs_per_min_ideal * timestamps[-1] if timestamps else 1
        efficiency = total_cs / ideal_cs if ideal_cs > 0 else 0

        return {
            "cs_per_minute": cs_per_minute,
            "total_cs_15min": int(total_cs),
            "efficiency": round(efficiency, 3),
            "weak_minutes": weak_minutes,
            "average_cs_per_min": round(np.mean(cs_per_minute), 2) if cs_per_minute else 0,
            "ideal_cs_15min": int(ideal_cs)
        }

    def _analyze_xp_trend(
        self,
        frames: List[Dict[str, Any]],
        participant_id: int
    ) -> Dict[str, Any]:
        """
        Analyze experience gap trend

        Returns:
            {
                "xp_curve": [280, 450, 680, ...],
                "level_curve": [1, 2, 3, ...],
                "xp_lead_avg": 150,  # Average XP lead (negative = behind)
                "level_lead_15min": 1,  # Level differential at 15 minutes
                "behind_periods": [(3, 7)]  # Periods behind (in minutes)
            }
        """
        xp_curve = []
        level_curve = []
        timestamps = []

        for frame in frames:
            participant_frame = frame.get("participantFrames", {}).get(str(participant_id), {})
            if not participant_frame:
                continue

            xp = participant_frame.get("xp", 0)
            level = participant_frame.get("level", 1)
            timestamp_min = frame.get("timestamp", 0) / (60 * 1000)

            xp_curve.append(xp)
            level_curve.append(level)
            timestamps.append(timestamp_min)

        if not xp_curve:
            return {"error": "No XP data available"}

        # Calculate gap with team average XP (needs teammate data, simplified here)
        # Should actually compare with lane opponent's XP

        return {
            "xp_curve": xp_curve,
            "level_curve": level_curve,
            "level_15min": level_curve[-1] if level_curve else 1,
            "xp_15min": int(xp_curve[-1]) if xp_curve else 0,
            "level_progression_minutes": [i for i, _ in enumerate(level_curve, 1)]
        }

    def _analyze_kill_timing(
        self,
        frames: List[Dict[str, Any]],
        participant_id: int
    ) -> Dict[str, Any]:
        """
        Analyze laning kill timing

        Returns:
            {
                "kills": [
                    {"timestamp": "05:23", "victim_id": 6, "gold_reward": 300},
                    ...
                ],
                "deaths": [
                    {"timestamp": "08:45", "killer_id": 1, "gold_lost": 300},
                    ...
                ],
                "first_blood": True,
                "kill_death_ratio_laning": 2.0
            }
        """
        kills = []
        deaths = []
        first_blood = False

        for frame in frames:
            # Only analyze first 15 minutes
            timestamp_ms = frame.get("timestamp", 0)
            if timestamp_ms > self.laning_phase_end * 60 * 1000:
                break

            events = frame.get("events", [])
            for event in events:
                if event.get("type") == "CHAMPION_KILL":
                    killer_id = event.get("killerId", 0)
                    victim_id = event.get("victimId", 0)

                    # Convert timestamp to readable format
                    minutes = timestamp_ms // (60 * 1000)
                    seconds = (timestamp_ms % (60 * 1000)) // 1000
                    time_str = f"{int(minutes):02d}:{int(seconds):02d}"

                    if killer_id == participant_id:
                        # Our kill
                        kills.append({
                            "timestamp": time_str,
                            "timestamp_ms": int(timestamp_ms),
                            "victim_id": victim_id,
                            "gold_reward": event.get("bounty", 300)
                        })

                        # Check if first blood
                        if "CHAMPION_KILL" in [e.get("type") for e in events[:events.index(event)]]:
                            pass  # Not first blood
                        else:
                            first_blood = True

                    elif victim_id == participant_id:
                        # Our death
                        deaths.append({
                            "timestamp": time_str,
                            "timestamp_ms": int(timestamp_ms),
                            "killer_id": killer_id,
                            "gold_lost": 300
                        })

        kd_ratio = len(kills) / len(deaths) if deaths else (len(kills) if kills else 0)

        return {
            "kills": kills,
            "deaths": deaths,
            "kill_count": len(kills),
            "death_count": len(deaths),
            "first_blood": first_blood,
            "kd_ratio_laning": round(kd_ratio, 2)
        }

    def _analyze_item_timing(
        self,
        frames: List[Dict[str, Any]],
        participant_id: int
    ) -> Dict[str, Any]:
        """
        Analyze item timing

        Returns:
            {
                "first_item_completed": "09:23",
                "first_item_id": 3078,  # Trinity Force
                "item_purchase_timeline": [
                    {"timestamp": "03:45", "item_id": 1001, "gold_spent": 300},
                    ...
                ]
            }
        """
        item_purchases = []
        first_completed_item = None
        first_completed_time = None

        # Core item ID list (simplified, should be more comprehensive)
        core_items = {
            3078, 3031, 3089, 6672, 6653, 6655,  # Common core items
            3074, 3153, 3087, 3004, 3026, 3072
        }

        for frame in frames:
            timestamp_ms = frame.get("timestamp", 0)
            events = frame.get("events", [])

            for event in events:
                if event.get("type") == "ITEM_PURCHASED":
                    if event.get("participantId") == participant_id - 1:  # API participantId starts from 0
                        item_id = event.get("itemId", 0)

                        minutes = timestamp_ms // (60 * 1000)
                        seconds = (timestamp_ms % (60 * 1000)) // 1000
                        time_str = f"{int(minutes):02d}:{int(seconds):02d}"

                        item_purchases.append({
                            "timestamp": time_str,
                            "timestamp_ms": int(timestamp_ms),
                            "item_id": item_id
                        })

                        # Check if core item
                        if item_id in core_items and not first_completed_item:
                            first_completed_item = item_id
                            first_completed_time = time_str

        return {
            "first_item_completed": first_completed_time or "Not completed",
            "first_item_id": first_completed_item,
            "item_purchase_timeline": item_purchases[:10],  # Return only first 10 purchases
            "total_purchases": len(item_purchases)
        }

    def _calculate_laning_score(
        self,
        cs_analysis: Dict[str, Any],
        xp_analysis: Dict[str, Any],
        kills_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive laning phase score (S/A/B/C/D)
        """
        # CS efficiency score (0-40 points)
        cs_score = min(40, cs_analysis.get("efficiency", 0) * 40)

        # Level score (0-20 points)
        level_15 = xp_analysis.get("level_15min", 1)
        level_score = min(20, (level_15 / 9) * 20)  # Level 9 is perfect score

        # KD score (0-40 points)
        kd_ratio = kills_analysis.get("kd_ratio_laning", 0)
        kd_score = min(40, kd_ratio * 15)

        total_score = cs_score + level_score + kd_score

        # Grade classification
        if total_score >= 85:
            grade = "S"
        elif total_score >= 70:
            grade = "A"
        elif total_score >= 55:
            grade = "B"
        elif total_score >= 40:
            grade = "C"
        else:
            grade = "D"

        return {
            "total_score": round(total_score, 1),
            "grade": grade,
            "breakdown": {
                "cs_score": round(cs_score, 1),
                "level_score": round(level_score, 1),
                "kd_score": round(kd_score, 1)
            }
        }

    def _generate_recommendations(
        self,
        cs_analysis: Dict[str, Any],
        xp_analysis: Dict[str, Any],
        kills_analysis: Dict[str, Any]
    ) -> List[str]:
        """
        Generate actionable laning phase improvement recommendations
        """
        recommendations = []

        # CS efficiency recommendations
        efficiency = cs_analysis.get("efficiency", 0)
        if efficiency < 0.7:
            weak_mins = cs_analysis.get("weak_minutes", [])
            if weak_mins:
                recommendations.append(
                    f"⚠️  Low CS efficiency ({efficiency:.1%}): Focus on improving last-hitting in minutes {', '.join(map(str, weak_mins[:3]))}"
                )
        elif efficiency < 0.85:
            recommendations.append(
                f"💡 Moderate CS efficiency ({efficiency:.1%}): Practice tool can help improve last-hitting mechanics"
            )

        # Death recommendations
        deaths = kills_analysis.get("deaths", [])
        if deaths:
            if len(deaths) >= 3:
                recommendations.append(
                    f"🚨 Too many laning deaths ({len(deaths)} times): Prioritize safety, avoid aggressive trading"
                )
            elif len(deaths) == 1:
                death_time = deaths[0].get("timestamp", "")
                recommendations.append(
                    f"⚠️  Solo killed at {death_time}: Review decision-making and vision setup at that moment"
                )

        # Level recommendations
        level_15 = xp_analysis.get("level_15min", 1)
        if level_15 < 7:
            recommendations.append(
                f"📉 Low level at 15 min (level {level_15}): Pay attention to positioning in shared XP zone, avoid missing wave experience"
            )

        # Kill recommendations
        if kills_analysis.get("kill_count", 0) == 0 and kills_analysis.get("death_count", 0) == 0:
            recommendations.append(
                "🔄 No kills or deaths in laning: Stable farming, but look for more pressure opportunities"
            )

        if not recommendations:
            recommendations.append(
                "✅ Excellent laning phase performance! Continue maintaining stable farming and lane pressure"
            )

        return recommendations


def main():
    """Test laning phase analyzer"""
    analyzer = LaningPhaseAnalyzer()

    # Load test data
    test_file = Path("data/bronze/timelines/challenger/na1/2025/09/28/NA1_5377928933_timeline.json")

    if not test_file.exists():
        print(f"❌ Test file does not exist: {test_file}")
        return

    with open(test_file) as f:
        timeline_data = json.load(f)

    # Extract raw_data
    raw_data = timeline_data.get("raw_data", timeline_data)

    # Analyze laning phase for participant 1
    result = analyzer.analyze_match(raw_data, participant_id=1)

    print("=" * 80)
    print("🔍 Laning Phase Deep Analysis Results")
    print("=" * 80)

    print(f"\n📊 Overall Score: {result['overall_score']['grade']} ({result['overall_score']['total_score']} points)")
    print(f"   - CS efficiency score: {result['overall_score']['breakdown']['cs_score']}")
    print(f"   - Level score: {result['overall_score']['breakdown']['level_score']}")
    print(f"   - KD score: {result['overall_score']['breakdown']['kd_score']}")

    print(f"\n📈 CS Efficiency:")
    cs = result['cs_efficiency']
    print(f"   - 15-min CS: {cs['total_cs_15min']} / {cs['ideal_cs_15min']} (ideal)")
    print(f"   - Overall efficiency: {cs['efficiency']:.1%}")
    print(f"   - Average CS/min: {cs['average_cs_per_min']}")
    if cs.get('weak_minutes'):
        print(f"   - Weak periods: Minutes {', '.join(map(str, cs['weak_minutes']))}")

    print(f"\n📚 Level Progress:")
    xp = result['xp_differential']
    print(f"   - Level at 15 min: {xp['level_15min']}")
    print(f"   - XP at 15 min: {xp['xp_15min']}")

    print(f"\n⚔️  Laning Kills:")
    kills = result['kill_timing']
    print(f"   - Kills: {kills['kill_count']}")
    print(f"   - Deaths: {kills['death_count']}")
    print(f"   - KD ratio: {kills['kd_ratio_laning']}")
    if kills.get('first_blood'):
        print(f"   - 🎯 Got first blood!")

    print(f"\n🛡️  Item Timing:")
    items = result['item_completion']
    print(f"   - First core item: {items['first_item_completed']}")
    print(f"   - Total purchases: {items['total_purchases']}")

    print(f"\n💡 Improvement Recommendations:")
    for rec in result['recommendations']:
        print(f"   {rec}")


if __name__ == "__main__":
    main()

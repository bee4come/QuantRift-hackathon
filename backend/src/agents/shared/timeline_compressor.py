"""
Timeline Compressor for Token-Efficient LLM Prompts

Compresses raw Bronze timeline data (500KB+, ~1000 lines) into compact format (~500 tokens)
by extracting only essential metrics for analysis.

Similar to enhanced_fact_transform.py compression approach:
- Extract key milestones instead of per-frame details
- Aggregate statistics (CS at 5/10/15min, not every frame)
- Focus on actionable insights (kill events, objective timing)
"""

from typing import Dict, List, Any, Optional


class TimelineCompressor:
    """
    Compresses timeline data for token-efficient LLM analysis

    Compression Strategy:
    1. CS progression: Extract at 5/10/15 min milestones (not every frame)
    2. Kill events: Only timestamp + participants (not full frame context)
    3. Gold/XP curves: 3-point summary (early/mid/late) instead of 15+ points
    4. Level progression: Milestone levels (6/11/16) not every level-up
    5. Objective timing: Only baron/dragon timestamps

    Target: 500KB raw → 100-200 lines (~500 tokens)
    """

    def __init__(self):
        self.milestone_minutes = [5, 10, 15]  # Key laning phase milestones
        self.milestone_levels = [6, 11, 16]   # Key power spikes

    def compress_timeline(
        self,
        timeline_data: Dict[str, Any],
        participant_id: int
    ) -> Dict[str, Any]:
        """
        Compress timeline data for a specific participant

        Args:
            timeline_data: Raw Bronze timeline JSON (with info.frames[])
            participant_id: Target participant (1-10)

        Returns:
            Compressed timeline dict with only essential metrics
        """
        frames = timeline_data.get("info", {}).get("frames", [])

        if not frames:
            return {"error": "No timeline frames found"}

        # Extract compressed metrics
        compressed = {
            "participant_id": participant_id,
            "cs_milestones": self._extract_cs_milestones(frames, participant_id),
            "gold_progression": self._extract_gold_progression(frames, participant_id),
            "xp_progression": self._extract_xp_progression(frames, participant_id),
            "level_milestones": self._extract_level_milestones(frames, participant_id),
            "kill_events": self._extract_kill_events(frames, participant_id),
            "objective_events": self._extract_objective_events(frames),
            "item_purchases": self._extract_item_purchases(frames, participant_id),
            "summary_stats": self._generate_summary_stats(frames, participant_id)
        }

        return compressed

    def _extract_cs_milestones(
        self,
        frames: List[Dict],
        participant_id: int
    ) -> Dict[str, int]:
        """
        Extract CS at key milestones (5/10/15 min) instead of every frame

        Compression: 15 frames → 3 data points
        """
        cs_milestones = {}

        for minute in self.milestone_minutes:
            target_timestamp = minute * 60 * 1000

            # Find closest frame
            closest_frame = None
            min_diff = float('inf')

            for frame in frames:
                timestamp = frame.get("timestamp", 0)
                diff = abs(timestamp - target_timestamp)
                if diff < min_diff:
                    min_diff = diff
                    closest_frame = frame

            if closest_frame:
                participant_frame = closest_frame.get("participantFrames", {}).get(str(participant_id), {})
                minions_killed = participant_frame.get("minionsKilled", 0)
                jungle_killed = participant_frame.get("jungleMinionsKilled", 0)
                cs_milestones[f"{minute}min"] = minions_killed + jungle_killed

        return cs_milestones

    def _extract_gold_progression(
        self,
        frames: List[Dict],
        participant_id: int
    ) -> Dict[str, int]:
        """
        Extract gold at key milestones (early/mid/late)

        Compression: 15 frames → 3 data points
        """
        gold_progression = {}

        for minute in self.milestone_minutes:
            target_timestamp = minute * 60 * 1000

            # Find closest frame
            for frame in frames:
                if abs(frame.get("timestamp", 0) - target_timestamp) < 30000:  # Within 30s
                    participant_frame = frame.get("participantFrames", {}).get(str(participant_id), {})
                    total_gold = participant_frame.get("totalGold", 0)
                    gold_progression[f"{minute}min"] = total_gold
                    break

        return gold_progression

    def _extract_xp_progression(
        self,
        frames: List[Dict],
        participant_id: int
    ) -> Dict[str, int]:
        """
        Extract XP at key milestones

        Compression: 15 frames → 3 data points
        """
        xp_progression = {}

        for minute in self.milestone_minutes:
            target_timestamp = minute * 60 * 1000

            for frame in frames:
                if abs(frame.get("timestamp", 0) - target_timestamp) < 30000:
                    participant_frame = frame.get("participantFrames", {}).get(str(participant_id), {})
                    xp = participant_frame.get("xp", 0)
                    xp_progression[f"{minute}min"] = xp
                    break

        return xp_progression

    def _extract_level_milestones(
        self,
        frames: List[Dict],
        participant_id: int
    ) -> Dict[str, str]:
        """
        Extract timing when hitting key levels (6/11/16)

        Compression: All level-ups → 3 milestone timestamps
        """
        level_milestones = {}
        last_level = 0

        for frame in frames:
            participant_frame = frame.get("participantFrames", {}).get(str(participant_id), {})
            current_level = participant_frame.get("level", 0)

            if current_level > last_level and current_level in self.milestone_levels:
                timestamp = frame.get("timestamp", 0)
                minutes = timestamp // 60000
                seconds = (timestamp % 60000) // 1000
                level_milestones[f"level_{current_level}"] = f"{minutes:02d}:{seconds:02d}"

            last_level = current_level

        return level_milestones

    def _extract_kill_events(
        self,
        frames: List[Dict],
        participant_id: int
    ) -> List[Dict[str, Any]]:
        """
        Extract kill/death events with minimal context

        Compression: Full event objects → timestamp + participants only
        """
        kill_events = []

        for frame in frames:
            # Only check laning phase (0-15 min)
            if frame.get("timestamp", 0) > 15 * 60 * 1000:
                break

            events = frame.get("events", [])
            for event in events:
                event_type = event.get("type")

                # Kill events
                if event_type == "CHAMPION_KILL":
                    killer_id = event.get("killerId")
                    victim_id = event.get("victimId")

                    # Only record if participant is involved
                    if killer_id == participant_id or victim_id == participant_id:
                        timestamp = event.get("timestamp", 0)
                        minutes = timestamp // 60000
                        seconds = (timestamp % 60000) // 1000

                        kill_events.append({
                            "time": f"{minutes:02d}:{seconds:02d}",
                            "type": "kill" if killer_id == participant_id else "death",
                            "opponent": victim_id if killer_id == participant_id else killer_id
                        })

        return kill_events

    def _extract_objective_events(
        self,
        frames: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Extract major objective events (Baron/Dragon/Tower)

        Compression: All events → only major objectives
        """
        objective_events = []

        for frame in frames:
            # Only check laning phase
            if frame.get("timestamp", 0) > 15 * 60 * 1000:
                break

            events = frame.get("events", [])
            for event in events:
                event_type = event.get("type")

                # Major objectives
                if event_type in ["ELITE_MONSTER_KILL", "BUILDING_KILL"]:
                    timestamp = event.get("timestamp", 0)
                    minutes = timestamp // 60000
                    seconds = (timestamp % 60000) // 1000

                    obj_type = event.get("monsterType") or event.get("buildingType", "UNKNOWN")

                    objective_events.append({
                        "time": f"{minutes:02d}:{seconds:02d}",
                        "type": obj_type,
                        "team": event.get("teamId", 0)
                    })

        return objective_events

    def _extract_item_purchases(
        self,
        frames: List[Dict],
        participant_id: int
    ) -> List[Dict[str, Any]]:
        """
        Extract major item purchases (>1000 gold items)

        Compression: All purchases → only major items
        """
        item_purchases = []

        for frame in frames:
            # Only check laning phase
            if frame.get("timestamp", 0) > 15 * 60 * 1000:
                break

            events = frame.get("events", [])
            for event in events:
                if event.get("type") == "ITEM_PURCHASED":
                    if event.get("participantId") == participant_id:
                        # Only track major items (>1000 gold typically)
                        item_id = event.get("itemId", 0)

                        # Simple heuristic: items with IDs > 3000 are usually major items
                        if item_id > 3000:
                            timestamp = event.get("timestamp", 0)
                            minutes = timestamp // 60000
                            seconds = (timestamp % 60000) // 1000

                            item_purchases.append({
                                "time": f"{minutes:02d}:{seconds:02d}",
                                "item_id": item_id
                            })

        return item_purchases

    def _generate_summary_stats(
        self,
        frames: List[Dict],
        participant_id: int
    ) -> Dict[str, Any]:
        """
        Generate high-level summary statistics for laning phase

        Compression: Aggregate view instead of frame-by-frame details
        """
        laning_frames = [f for f in frames if f.get("timestamp", 0) <= 15 * 60 * 1000]

        if not laning_frames:
            return {}

        # Get first and last laning frame
        first_frame = laning_frames[0]
        last_frame = laning_frames[-1]

        first_pf = first_frame.get("participantFrames", {}).get(str(participant_id), {})
        last_pf = last_frame.get("participantFrames", {}).get(str(participant_id), {})

        # Calculate deltas
        gold_earned = last_pf.get("totalGold", 0) - first_pf.get("totalGold", 0)
        xp_earned = last_pf.get("xp", 0) - first_pf.get("xp", 0)
        cs_earned = (last_pf.get("minionsKilled", 0) + last_pf.get("jungleMinionsKilled", 0)) - \
                    (first_pf.get("minionsKilled", 0) + first_pf.get("jungleMinionsKilled", 0))

        final_level = last_pf.get("level", 0)

        return {
            "total_gold_earned": gold_earned,
            "total_xp_earned": xp_earned,
            "total_cs_earned": cs_earned,
            "final_level": final_level,
            "avg_gold_per_min": round(gold_earned / 15, 1),
            "avg_cs_per_min": round(cs_earned / 15, 1)
        }

    def format_for_llm(self, compressed_data: Dict[str, Any]) -> str:
        """
        Format compressed timeline data into human-readable text for LLM

        Args:
            compressed_data: Output from compress_timeline()

        Returns:
            Formatted string (~500 tokens) for LLM prompt
        """
        if "error" in compressed_data:
            return f"Timeline Error: {compressed_data['error']}"

        lines = []
        lines.append(f"=== Timeline Analysis (Participant {compressed_data['participant_id']}) ===\n")

        # CS Milestones
        lines.append("📈 CS Progression:")
        cs_milestones = compressed_data.get("cs_milestones", {})
        for milestone, cs in sorted(cs_milestones.items()):
            lines.append(f"  {milestone}: {cs} CS")

        # Gold Progression
        lines.append("\n💰 Gold Progression:")
        gold_progression = compressed_data.get("gold_progression", {})
        for milestone, gold in sorted(gold_progression.items()):
            lines.append(f"  {milestone}: {gold}g")

        # Level Milestones
        lines.append("\n⬆️  Level Milestones:")
        level_milestones = compressed_data.get("level_milestones", {})
        for level, time in sorted(level_milestones.items()):
            lines.append(f"  {level}: {time}")

        # Kill Events
        kill_events = compressed_data.get("kill_events", [])
        if kill_events:
            lines.append("\n⚔️  Combat Events:")
            for event in kill_events:
                lines.append(f"  {event['time']}: {event['type']} (vs P{event['opponent']})")

        # Objective Events
        objective_events = compressed_data.get("objective_events", [])
        if objective_events:
            lines.append("\n🐉 Objectives:")
            for obj in objective_events:
                lines.append(f"  {obj['time']}: {obj['type']} (Team {obj['team']})")

        # Summary Stats
        lines.append("\n📊 Laning Phase Summary:")
        summary = compressed_data.get("summary_stats", {})
        lines.append(f"  Total Gold: {summary.get('total_gold_earned', 0)}g ({summary.get('avg_gold_per_min', 0)}g/min)")
        lines.append(f"  Total CS: {summary.get('total_cs_earned', 0)} ({summary.get('avg_cs_per_min', 0)} cs/min)")
        lines.append(f"  Final Level: {summary.get('final_level', 0)}")

        return "\n".join(lines)


def demo():
    """Demo timeline compression with sample data"""
    import json
    from pathlib import Path

    # Find a sample timeline file
    timeline_dir = Path("data/bronze/timelines")
    timeline_files = list(timeline_dir.glob("**/*.json"))

    if not timeline_files:
        print("❌ No timeline files found in data/bronze/timelines/")
        return

    # Load first timeline
    with open(timeline_files[0], 'r') as f:
        timeline_data = json.load(f)

    raw_data = timeline_data.get("raw_data", timeline_data)

    # Test compression
    compressor = TimelineCompressor()

    print("=" * 80)
    print("Timeline Compression Demo")
    print("=" * 80)

    # Original size
    raw_json = json.dumps(raw_data, indent=2)
    original_size = len(raw_json)
    print(f"\n📦 Original timeline size: {original_size:,} characters (~{original_size // 4} tokens)")

    # Compress for participant 1
    compressed = compressor.compress_timeline(raw_data, participant_id=1)
    compressed_json = json.dumps(compressed, indent=2)
    compressed_size = len(compressed_json)
    print(f"✅ Compressed size: {compressed_size:,} characters (~{compressed_size // 4} tokens)")

    compression_ratio = ((original_size - compressed_size) / original_size) * 100
    print(f"🎯 Compression: {compression_ratio:.1f}% reduction")

    # Format for LLM
    llm_text = compressor.format_for_llm(compressed)
    llm_size = len(llm_text)
    print(f"📝 LLM-formatted size: {llm_size:,} characters (~{llm_size // 4} tokens)")

    print("\n" + "=" * 80)
    print("LLM-Formatted Output Preview:")
    print("=" * 80)
    print(llm_text)


if __name__ == "__main__":
    demo()

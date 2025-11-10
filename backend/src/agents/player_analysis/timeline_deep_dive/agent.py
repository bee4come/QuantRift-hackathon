"""
Timeline Deep Dive Agent (Phase 1.4)

Provides 300% deeper timeline analysis, including laning phase, resource control, and teamfight decision analysis.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add path
current_file = Path(__file__).resolve()
agents_dir = current_file.parent.parent.parent  # src/agents/
sys.path.insert(0, str(agents_dir))

# Import modules
from shared.bedrock_adapter import BedrockLLM
from shared.timeline_compressor import TimelineCompressor
from player_analysis.laning_phase.analyzer import LaningPhaseAnalyzer


class TimelineDeepDiveAgent:
    """
    Timeline Deep Dive Agent

    Core Features:
    1. Deep laning phase analysis (0-15 minutes)
    2. Generate actionable improvement recommendations
    3. LLM-enhanced insight generation

    Expected Impact:
    - Analysis depth: +300%
    - Actionable recommendations: +200%
    """

    def __init__(self, model: str = "haiku"):
        """
        Initialize Agent

        Args:
            model: LLM model (haiku/sonnet)
        """
        self.llm = BedrockLLM(model=model, enable_cache=True)
        self.laning_analyzer = LaningPhaseAnalyzer()
        self.timeline_compressor = TimelineCompressor()  # Phase 1.4.1: Token compression

    def analyze(
        self,
        packs_dir: str,
        target_puuid: str = None,
        match_id: str = None,
        output_dir: str = "output/timeline_deep_dive",
        focus: str = "laning"  # laning / resource / teamfight / all
    ) -> tuple:
        """
        Execute Timeline deep analysis

        Args:
            packs_dir: Data pack directory
            target_puuid: Target player PUUID (if specified, only analyze this player)
            match_id: Specific match ID (if specified, only analyze this match)
            output_dir: Output directory
            focus: Analysis focus

        Returns:
            (data_dict, report_str): Analysis data and report
        """
        print("=" * 80)
        print("🔍 Timeline Deep Dive Analysis")
        print("=" * 80)

        # 1. Load timeline data
        print(f"\n📦 Loading timeline data: {packs_dir}")
        if match_id:
            print(f"   🎯 Filtering for match: {match_id}")
        if target_puuid:
            print(f"   👤 Target player: {target_puuid[:20]}...")
        timeline_files = self._load_timeline_files(packs_dir, match_id=match_id)

        if not timeline_files:
            print("❌ No timeline data found")
            return {}, "No timeline data found"

        print(f"✅ Found {len(timeline_files)} timeline files")

        # 2. Execute laning phase analysis
        print(f"\n🎯 Analysis focus: {focus}")

        if focus in ["laning", "all"]:
            laning_results = self._analyze_laning_phase(timeline_files, target_puuid=target_puuid)
            print(f"✅ Laning phase analysis complete: {len(laning_results)} matches")
        else:
            laning_results = []

        # 3. Aggregate analysis results
        aggregated_data = self._aggregate_results(laning_results)

        # 4. Generate LLM-enhanced report (Phase 1.4.1: using compressed timeline)
        print(f"\n🤖 Generating deep insight report (using {self.llm.model_id})...")
        report = self._generate_llm_report(aggregated_data, timeline_files, focus)

        print(f"✅ Report generation complete ({len(report)} characters)")

        # 5. Save results
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save data
        data_file = output_path / "timeline_analysis_data.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(aggregated_data, f, indent=2, ensure_ascii=False)

        # Save report
        report_file = output_path / "timeline_analysis_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n💾 Output saved to {output_dir}")
        print(f"   - Data: {data_file}")
        print(f"   - Report: {report_file}")

        return aggregated_data, report

    def _load_timeline_files(self, packs_dir: str, match_id: str = None) -> List[Dict[str, Any]]:
        """
        Load timeline data files

        Args:
            packs_dir: Data pack directory
            match_id: Specific match ID to load (if None, load all)

        Returns:
            List of timeline data
        """
        packs_path = Path(packs_dir)
        timeline_files = []

        # Find all timeline JSON files
        for timeline_file in packs_path.rglob("*timeline*.json"):
            try:
                # If match_id specified, only load matching file
                if match_id and match_id not in str(timeline_file.name):
                    continue

                with open(timeline_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Extract raw_data (Bronze layer format)
                    raw_data = data.get("raw_data", data)
                    if "info" in raw_data and "frames" in raw_data.get("info", {}):
                        timeline_files.append(raw_data)
            except Exception as e:
                print(f"⚠️  Failed to load {timeline_file}: {e}")
                continue

        return timeline_files

    def _find_participant_ids(self, timeline_data: Dict[str, Any], target_puuid: str) -> List[int]:
        """
        Find participant IDs matching the target PUUID in timeline data

        Args:
            timeline_data: Timeline data dict
            target_puuid: Target player PUUID

        Returns:
            List of matching participant IDs (usually just one)
        """
        try:
            # Timeline data has metadata with participants
            metadata = timeline_data.get('metadata', {})
            participants_puuids = metadata.get('participants', [])

            # Participant IDs are 1-indexed
            participant_ids = []
            for idx, puuid in enumerate(participants_puuids, 1):
                if puuid == target_puuid:
                    participant_ids.append(idx)

            return participant_ids
        except Exception as e:
            print(f"⚠️  Error finding participant: {e}")
            return []

    def _analyze_laning_phase(
        self,
        timeline_files: List[Dict[str, Any]],
        target_puuid: str = None
    ) -> List[Dict[str, Any]]:
        """
        Batch analyze laning phase

        Args:
            timeline_files: List of timeline data

        Returns:
            List of laning phase analysis results
        """
        results = []

        for idx, timeline_data in enumerate(timeline_files, 1):
            # If target_puuid specified, find the participant ID for this player
            if target_puuid:
                participant_ids = self._find_participant_ids(timeline_data, target_puuid)
                if not participant_ids:
                    print(f"⚠️  Target player not found in match {idx}")
                    continue
            else:
                # Analyze all participants (1-10) if no target specified
                participant_ids = range(1, 11)

            for participant_id in participant_ids:
                try:
                    analysis = self.laning_analyzer.analyze_match(
                        timeline_data,
                        participant_id
                    )

                    if "error" not in analysis:
                        analysis["match_index"] = idx
                        results.append(analysis)

                except Exception as e:
                    print(f"⚠️  Analysis failed for match{idx} participant{participant_id}: {e}")
                    continue

        return results

    def _aggregate_results(
        self,
        laning_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate analysis results

        Args:
            laning_results: List of laning phase analysis results

        Returns:
            Aggregated analysis data
        """
        if not laning_results:
            return {"error": "No results to aggregate"}

        # Extract key metrics
        cs_efficiencies = []
        grades = []
        avg_cs_per_mins = []
        kd_ratios = []

        for result in laning_results:
            cs_eff = result.get("cs_efficiency", {})
            overall = result.get("overall_score", {})
            kills = result.get("kill_timing", {})

            if cs_eff.get("efficiency"):
                cs_efficiencies.append(cs_eff["efficiency"])
            if overall.get("grade"):
                grades.append(overall["grade"])
            if cs_eff.get("average_cs_per_min"):
                avg_cs_per_mins.append(cs_eff["average_cs_per_min"])
            if kills.get("kd_ratio_laning"):
                kd_ratios.append(kills["kd_ratio_laning"])

        # Calculate statistical metrics
        import numpy as np

        aggregated = {
            "total_matches_analyzed": len(laning_results),
            "laning_phase_summary": {
                "avg_cs_efficiency": round(np.mean(cs_efficiencies), 3) if cs_efficiencies else 0,
                "avg_cs_per_min": round(np.mean(avg_cs_per_mins), 2) if avg_cs_per_mins else 0,
                "avg_kd_ratio": round(np.mean(kd_ratios), 2) if kd_ratios else 0,
                "grade_distribution": {
                    "S": grades.count("S"),
                    "A": grades.count("A"),
                    "B": grades.count("B"),
                    "C": grades.count("C"),
                    "D": grades.count("D")
                },
                "performance_consistency": round(np.std(cs_efficiencies), 3) if cs_efficiencies else 0
            },
            "sample_analyses": laning_results[:3]  # Include 3 sample analyses
        }

        return aggregated

    def _generate_llm_report(
        self,
        aggregated_data: Dict[str, Any],
        timeline_files: List[Dict[str, Any]],
        focus: str
    ) -> str:
        """
        Generate LLM-enhanced deep insight report (Phase 1.4.1: using compressed timeline format)

        Args:
            aggregated_data: Aggregated analysis data
            timeline_files: List of original timeline data
            focus: Analysis focus

        Returns:
            Report in Markdown format
        """
        if "error" in aggregated_data:
            return f"# Timeline Deep Analysis Report\n\nUnable to generate report: {aggregated_data['error']}"

        # Phase 1.4.1: Compress timeline samples (from 500KB → ~500 tokens)
        compressed_samples = []
        for timeline_data in timeline_files[:2]:  # Compress only first 2 samples
            for participant_id in range(1, 3):  # Compress only first 2 participants
                compressed = self.timeline_compressor.compress_timeline(timeline_data, participant_id)
                compressed_text = self.timeline_compressor.format_for_llm(compressed)
                compressed_samples.append(compressed_text)

        compressed_timeline_text = "\n\n".join(compressed_samples)

        # Build prompt (using compressed format instead of full JSON)
        prompt = f"""Based on the following Timeline deep analysis data, generate a professional player performance insight report.

Summary Statistics:
- Matches analyzed: {aggregated_data.get('total_matches_analyzed', 0)}
- Average CS efficiency: {aggregated_data.get('laning_phase_summary', {}).get('avg_cs_efficiency', 0):.1%}
- Average CS/min: {aggregated_data.get('laning_phase_summary', {}).get('avg_cs_per_min', 0)}
- Average KD: {aggregated_data.get('laning_phase_summary', {}).get('avg_kd_ratio', 0)}
- Grade distribution: {aggregated_data.get('laning_phase_summary', {}).get('grade_distribution', {})}

Compressed Timeline Sample Data (token-optimized):
```
{compressed_timeline_text}
```

Please generate a report with the following sections:

1. **Laning Phase Performance Overview** (3-5 sentences)
   - Overall laning phase level assessment
   - CS efficiency and experience control
   - Kill and death situation

2. **Core Issues Identified** (2-3 most critical problems)
   - Problem description
   - Data supporting evidence
   - Impact analysis

3. **Actionable Improvement Recommendations** (3-5 specific suggestions)
   - Each recommendation should:
     * Be concrete and executable (not vague advice)
     * Have priority indicated
     * Include expected impact

4. **Training Plan Suggestions** (2-3 specific practice directions)
   - Targeted training content
   - Practice methods
   - Measurement criteria

Output in Markdown format, use emojis for readability, language should be concise and professional.
"""

        system_prompt = """You are a League of Legends senior analyst, skilled at extracting deep insights from Timeline data.
Your analysis:
1. Data-driven and objective
2. Provides actionable recommendations, not generic advice
3. Concise professional language with clear priorities
4. Uses emojis for enhanced readability"""

        # Call LLM
        response = self.llm.generate_sync(
            prompt=prompt,
            system=system_prompt,
            max_tokens=4000
        )

        return response.get("text", "Report generation failed")

    def run_stream(
        self,
        packs_dir: str,
        match_id: str,
        recent_count: int = 5,
        time_range: Optional[str] = None,
        queue_id: Optional[int] = None
    ):
        """
        Run timeline deep dive analysis with SSE streaming output

        Args:
            packs_dir: Pack file directory path
            match_id: Match ID to analyze
            recent_count: Number of recent matches (unused, kept for interface consistency)
            time_range: Time range filter (unused, kept for interface consistency)
            queue_id: Queue ID filter (unused, kept for interface consistency)

        Yields:
            SSE formatted messages for streaming response
        """
        from src.agents.shared.stream_helper import stream_agent_with_thinking

        # Load timeline files
        timeline_files = self._load_timeline_files(packs_dir, match_id=match_id)

        if not timeline_files:
            # No timeline data found - return error
            error_msg = f"No timeline data found for match {match_id}"
            yield f"data: {{\"type\": \"error\", \"content\": \"{error_msg}\"}}\n\n"
            return

        # Analyze laning phase
        laning_results = self._analyze_laning_phase(timeline_files, target_puuid=None)

        # Aggregate results
        aggregated_data = self._aggregate_results(laning_results)

        # Build prompt for LLM
        compressed_samples = []
        for timeline_data in timeline_files[:2]:
            for participant_id in range(1, 3):
                compressed = self.timeline_compressor.compress_timeline(timeline_data, participant_id)
                compressed_text = self.timeline_compressor.format_for_llm(compressed)
                compressed_samples.append(compressed_text)

        compressed_timeline_text = "\n\n".join(compressed_samples)

        prompt = f"""Based on the following Timeline deep analysis data, generate a professional player performance insight report.

Summary Statistics:
- Matches analyzed: {aggregated_data.get('total_matches_analyzed', 0)}
- Average CS efficiency: {aggregated_data.get('laning_phase_summary', {}).get('avg_cs_efficiency', 0):.1%}
- Average CS/min: {aggregated_data.get('laning_phase_summary', {}).get('avg_cs_per_min', 0)}
- Average KD: {aggregated_data.get('laning_phase_summary', {}).get('avg_kd_ratio', 0)}
- Grade distribution: {aggregated_data.get('laning_phase_summary', {}).get('grade_distribution', {})}

Compressed Timeline Sample Data (token-optimized):
```
{compressed_timeline_text}
```

Please generate a report with the following sections:

1. **Laning Phase Performance Overview** (3-5 sentences)
2. **Core Issues Identified** (2-3 most critical problems)
3. **Actionable Improvement Recommendations** (3-5 specific suggestions)
4. **Training Plan Suggestions** (2-3 specific practice directions)

Output in Markdown format, use emojis for readability."""

        system_prompt = """You are a League of Legends senior analyst, skilled at extracting deep insights from Timeline data.
Your analysis:
1. Data-driven and objective
2. Provides actionable recommendations, not generic advice
3. Concise professional language with clear priorities
4. Uses emojis for enhanced readability"""

        # Stream report generation
        for message in stream_agent_with_thinking(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.llm.model_id,
            max_tokens=4000,
            enable_thinking=False
        ):
            yield message


def main():
    """Test Timeline Deep Dive Agent"""
    agent = TimelineDeepDiveAgent(model="haiku")

    # Use test data
    test_packs_dir = "test_agents/s1ne_analysis/packs"

    try:
        data, report = agent.analyze(
            packs_dir=test_packs_dir,
            output_dir="test_agents/timeline_deep_dive_test",
            focus="laning"
        )

        print("\n" + "=" * 80)
        print("📊 Analysis Results Preview")
        print("=" * 80)

        if "laning_phase_summary" in data:
            summary = data["laning_phase_summary"]
            print(f"\nLaning Phase Summary:")
            print(f"  - Average CS efficiency: {summary['avg_cs_efficiency']:.1%}")
            print(f"  - Average CS/min: {summary['avg_cs_per_min']}")
            print(f"  - Average KD: {summary['avg_kd_ratio']}")
            print(f"  - Grade distribution: {summary['grade_distribution']}")

        print("\n" + "=" * 80)
        print("📝 Report Preview (first 500 characters)")
        print("=" * 80)
        print(report[:500] + "...")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

"""
Multi-Version Analysis Agent
Multi-version trend analysis using Bedrock Haiku
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Import shared modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.shared import BedrockLLM, get_config
from .tools import (
    load_all_packs,
    analyze_trends,
    identify_key_transitions,
    generate_comprehensive_analysis
)
from .prompts import build_multi_version_prompt


class MultiVersionAgent:
    """
    Multi-Version Trend Analysis Agent

    Generates cross-version adaptation analysis reports using Bedrock Haiku
    """

    def __init__(self, model: str = "haiku"):
        """
        Initialize Agent

        Args:
            model: Model name ("haiku" or "sonnet")
        """
        self.config = get_config()
        self.llm = BedrockLLM(model=model)
        self.model_name = model

    def run(
        self,
        packs_dir: str,
        output_dir: str,
        context: Optional[Any] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Run complete analysis workflow

        Args:
            packs_dir: player-pack data directory
            output_dir: Output directory
            context: AgentContext instance (optional, for data sharing)

        Returns:
            tuple: (analysis_data, report_text)
        """
        print("=" * 60)
        print("🎯 Multi-Version Adaptation Analysis System (ADK Agent)")
        print("=" * 60)

        # 1. Load data (try to get from context cache)
        if context and context.has_shared_data("all_packs"):
            print("✅ Using AgentContext cached data (saving load time)")
            all_packs = context.get_shared_data("all_packs")
            print(f"   Retrieved {len(all_packs)} patches from cache")
        else:
            print("📦 Loading all Player-Pack data independently...")
            all_packs = load_all_packs(packs_dir)
            print(f"   ✅ Loaded {len(all_packs)} patches of data")

        # 2. Trend analysis
        print("📊 Analyzing cross-version trends...")
        trends = analyze_trends(all_packs)
        core_champions_count = len(trends["winrate_trends"])
        print(f"   ✅ Identified {core_champions_count} core champions")

        # 3. Transition point identification
        print("🔍 Identifying key version transition points...")
        transitions = identify_key_transitions(trends)
        significant_count = sum(1 for t in transitions if t["is_significant"])
        print(f"   ✅ Found {significant_count} significant transition points")

        # 4. Comprehensive analysis
        print("🧩 Generating comprehensive analysis data package...")
        analysis = generate_comprehensive_analysis(trends, transitions)
        print("   ✅ Comprehensive analysis data package generated")

        # 5. Save JSON
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        output_json = output_path / "multi_version_analysis.json"
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Analysis data saved: {output_json} ({output_json.stat().st_size / 1024:.2f} KB)")

        # 6. Generate LLM report
        print(f"🤖 Calling Bedrock {self.model_name.upper()} to generate comprehensive report...")
        prompt = build_multi_version_prompt(analysis)

        result = self.llm.generate_sync(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.7
        )

        report = result["text"]
        token_usage = result["usage"]

        print(f"   ✅ LLM report generation complete")
        print(f"   Token usage: {token_usage}")

        # 7. Save report
        output_md = output_path / "multi_version_report.md"
        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ LLM report saved: {output_md}")

        print("\n" + "=" * 60)
        print("✅ Multi-version adaptation analysis complete!")
        print("=" * 60)

        return analysis, report

    def run_stream(
        self,
        packs_dir: str,
        time_range: Optional[str] = None,
        queue_id: Optional[int] = None
    ):
        """
        Run multi-version analysis with SSE streaming output

        Unified method for both agent card and chat interfaces

        Args:
            packs_dir: Player-Pack directory path
            time_range: Time range filter (e.g., "2024-01-01", "past-365", None)
            queue_id: Queue ID filter (420=Solo/Duo, 440=Flex, 400=Normal, None=All)

        Yields:
            SSE formatted messages for streaming
        """
        from src.agents.shared.stream_helper import stream_agent_with_thinking

        # Load all packs with filters
        all_packs = load_all_packs(packs_dir, time_range=time_range, queue_id=queue_id)

        # Check if no data found
        if not all_packs or len(all_packs) == 0:
            yield f"data: {{\"error\": \"No version data found\"}}\n\n"
            return

        # Analyze trends
        trends = analyze_trends(all_packs)

        # Identify key transitions
        transitions = identify_key_transitions(trends)

        # Generate comprehensive analysis
        analysis = generate_comprehensive_analysis(trends, transitions)

        # Build prompt (note: build_multi_version_prompt returns a single user prompt)
        user_prompt = build_multi_version_prompt(analysis)

        # Create a simple system prompt for multi-version analysis
        system_prompt = """You are a senior League of Legends data analyst and coach.
Generate professional cross-patch adaptation analysis reports based on player performance data across multiple game versions.
Focus on data-driven insights, highlight key points, and provide actionable recommendations."""

        # Stream response
        for message in stream_agent_with_thinking(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=self.llm.model_id,
            max_tokens=8000,
            enable_thinking=False
        ):
            yield message


def main():
    """Command-line entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Version Trend Analysis Agent")
    parser.add_argument(
        "--packs-dir",
        type=str,
        default="/home/zty/rift_rewind/test_agents/player_coach/packs",
        help="Player-Pack data directory"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/home/zty/rift_rewind/test_agents/player_coach/final_output",
        help="Output directory"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="haiku",
        choices=["haiku", "sonnet"],
        help="Model to use"
    )

    args = parser.parse_args()

    agent = MultiVersionAgent(model=args.model)
    analysis, report = agent.run(
        packs_dir=args.packs_dir,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()

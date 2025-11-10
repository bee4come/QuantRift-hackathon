"""
BuildSimulatorAgent - Main Agent Class

Compares different build options based on historical match data.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from src.agents.shared.bedrock_adapter import BedrockLLM
from src.agents.shared.config import get_config

from .tools import (
    compare_build_options,
    format_build_comparison_for_prompt
)
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class BuildSimulatorAgent:
    """
    Build Simulator Agent

    Compares different builds and provides recommendations based on historical data.
    Generates detailed analysis of build performance.

    Example:
        >>> agent = BuildSimulatorAgent()
        >>> result = agent.run(
        ...     champion_id=92,
        ...     role="TOP",
        ...     build_a=[3071, 3142, 3053],  # Black Cleaver, Youmuu's, Sterak's
        ...     build_b=[3078, 3074, 3053]   # Trinity Force, Ravenous Hydra, Sterak's
        ... )
    """

    def __init__(
        self,
        model_id: str = None,
        parquet_path: str = "data/gold/parquet/fact_match_performance.parquet"
    ):
        """
        Args:
            model_id: Bedrock model ID for LLM
            parquet_path: Path to Gold layer parquet data
        """
        if model_id is None:
            config = get_config()
            model_id = config.default_model
        self.model_id = model_id
        self.parquet_path = parquet_path
        self.llm = BedrockLLM(model=model_id)

    def run(
        self,
        champion_id: int,
        role: str,
        build_a: List[int],
        build_b: List[int],
        game_duration_min: int = None,
        game_duration_max: int = None,
        output_dir: str = None
    ) -> Dict[str, Any]:
        """
        Run build comparison analysis

        Args:
            champion_id: Champion ID
            role: Role (TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY)
            build_a: First build option (list of item IDs)
            build_b: Second build option (list of item IDs)
            game_duration_min: Minimum game duration filter (optional)
            game_duration_max: Maximum game duration filter (optional)
            output_dir: Optional output directory for saving results

        Returns:
            {
                "comparison": {...},  # Build comparison data
                "report": "...",      # LLM-generated report
                "metadata": {...}
            }
        """
        print("\n" + "=" * 60)
        print("🛠️  Build Simulator Analysis")
        print("=" * 60)

        # Step 1: Compare builds
        print(f"\n📊 Comparing build options...")
        print(f"   Build A: {build_a}")
        print(f"   Build B: {build_b}")

        comparison_data = compare_build_options(
            champion_id=champion_id,
            role=role,
            build_a=build_a,
            build_b=build_b,
            game_duration_min=game_duration_min,
            game_duration_max=game_duration_max,
            parquet_path=self.parquet_path,
            min_samples=10
        )

        # Display basic comparison results
        comp = comparison_data['comparison']
        stats_a = comp['build_a_stats']
        stats_b = comp['build_b_stats']

        print(f"\n✅ Data statistics complete:")
        print(f"   Build A samples: {stats_a['sample_size']}")
        print(f"   Build B samples: {stats_b['sample_size']}")

        if comp['comparison']['valid_comparison']:
            winner = comp['comparison']['winner']
            print(f"   Recommended build: {winner}")
        else:
            print(f"   ⚠️ Insufficient samples, comparison invalid")

        # Step 2: Generate LLM report
        print(f"\n🤖 Generating build analysis report (using {self.model_id})...")

        formatted_data = format_build_comparison_for_prompt(comparison_data)

        user_prompt = USER_PROMPT_TEMPLATE.format(
            comparison_data=formatted_data
        )

        result = self.llm.generate_sync(
            prompt=user_prompt,
            system=SYSTEM_PROMPT
        )
        report = result['text']

        print(f"✅ Report generation complete ({len(report)} characters)")

        # Step 3: Compile results
        final_result = {
            "comparison": comparison_data,
            "report": report,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model_id": self.model_id,
                "champion_id": champion_id,
                "role": role,
                "build_a": build_a,
                "build_b": build_b
            }
        }

        if output_dir:
            self._save_results(final_result, output_dir)

        return final_result

    def _save_results(self, result: Dict[str, Any], output_dir: str) -> None:
        """Save build comparison results to files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save JSON analysis
        analysis_file = output_path / "build_comparison.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump({
                "comparison": result["comparison"],
                "metadata": result["metadata"]
            }, f, indent=2, ensure_ascii=False)

        # Save Markdown report
        report_file = output_path / "build_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(result['report'])

        print(f"\n💾 Output saved:")
        print(f"   - {analysis_file}")
        print(f"   - {report_file}")

    def run_stream(
        self,
        packs_dir: str,
        champion_id: int,
        build_a: List[int] = None,
        build_b: List[int] = None,
        role: str = None,
        recent_count: int = 5,
        time_range: str = None,
        queue_id: int = None
    ):
        """
        Run build simulator analysis with SSE streaming output

        Args:
            packs_dir: Pack file directory path (unused, kept for interface consistency)
            champion_id: Champion ID to analyze builds for
            build_a: First build option (list of item IDs)
            build_b: Second build option (list of item IDs)
            role: Role (TOP/JUNGLE/MIDDLE/BOTTOM/UTILITY)
            recent_count: Number of recent matches (unused, kept for interface consistency)
            time_range: Time range filter (unused, kept for interface consistency)
            queue_id: Queue ID filter (unused, kept for interface consistency)

        Yields:
            SSE formatted messages for streaming response
        """
        from src.agents.shared.stream_helper import stream_agent_with_thinking

        # If no builds specified, use default popular builds for this champion
        if not build_a or not build_b:
            # Default: compare two popular build paths
            # This could be enhanced to fetch from meta data
            build_a = build_a or [3071, 3142, 3053]  # Example builds
            build_b = build_b or [3078, 3074, 3053]

        # If no role specified, use TOP as default
        if not role:
            role = "TOP"

        # Compare builds
        comparison_data = compare_build_options(
            champion_id=champion_id,
            role=role,
            build_a=build_a,
            build_b=build_b,
            game_duration_min=None,
            game_duration_max=None,
            parquet_path=self.parquet_path,
            min_samples=10
        )

        # Format for prompt
        formatted_data = format_build_comparison_for_prompt(comparison_data)

        user_prompt = USER_PROMPT_TEMPLATE.format(
            comparison_data=formatted_data
        )

        # Stream report generation
        for message in stream_agent_with_thinking(
            prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            model=self.llm.model_id,
            max_tokens=8000,
            enable_thinking=False
        ):
            yield message

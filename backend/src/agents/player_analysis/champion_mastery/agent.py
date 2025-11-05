"""
ChampionMasteryAgent - Champion Mastery Analysis Agent

Analyzes player mastery of a single champion across all available match history.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from src.agents.shared.config import get_config
from src.agents.shared.bedrock_adapter import BedrockLLM
from .tools import (
    generate_comprehensive_mastery_analysis,
    format_analysis_for_prompt
)
from .prompts import build_narrative_prompt


class ChampionMasteryAgent:
    """
    Champion Mastery Analysis Agent

    Analyzes player mastery of a single champion, including:
    - Learning curve analysis (early/mid/late game)
    - Role specialization analysis (performance in different positions)
    - Version adaptability (stability across patches)
    - Mastery rating (S/A/B/C/D/F)
    - Strengths and improvement recommendations
    """

    def __init__(self, model: str = "sonnet"):
        """
        Initialize Champion Mastery Analysis Agent

        Args:
            model: LLM model selection ("sonnet" or "haiku")
        """
        self.config = get_config()
        self.llm = BedrockLLM(model=model)

    def run(
        self,
        champion_id: int,
        packs_dir: str,
        output_dir: Optional[str] = None,
        context: Optional[Any] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Run champion mastery analysis

        Args:
            champion_id: Champion ID
            packs_dir: Pack file directory path
            output_dir: Output directory (optional)
            context: AgentContext instance (optional, for data sharing)

        Returns:
            (analysis_data, report_text) - Analysis data and report text

        Raises:
            ValueError: If data for the champion is not found
        """
        print(f"\n{'='*60}")
        print(f"🎮 Champion Mastery Analysis - Champion ID: {champion_id}")
        print(f"{'='*60}\n")

        # Get cached data from AgentContext (if provided)
        all_packs_data = None
        if context and context.has_shared_data("all_packs"):
            print("✅ Using AgentContext cached data (saving 60% I/O time)")
            all_packs_data = context.get_shared_data("all_packs")

        # 1. Generate comprehensive analysis
        print("📊 Analyzing champion data...")
        analysis = generate_comprehensive_mastery_analysis(
            champion_id=champion_id,
            packs_dir=packs_dir,
            all_packs_data=all_packs_data  # Pass cached data
        )

        # Print analysis summary
        summary = analysis["summary"]
        print(f"\n✅ Analysis complete:")
        print(f"   Total games: {summary['total_games']}")
        print(f"   Overall winrate: {summary['overall_winrate']:.1%}")
        print(f"   Mastery rating: {summary['mastery_grade']} ({summary['mastery_score']} points)")
        print(f"   Version coverage: {summary['version_coverage']} patches")

        # 2. Format data
        formatted_analysis = format_analysis_for_prompt(analysis)

        # 3. Build prompts
        prompts = build_narrative_prompt(analysis, formatted_analysis)

        # 4. Generate report
        print(f"\n🤖 Generating champion mastery report (using {self.llm.model_id})...")

        result = self.llm.generate_sync(
            prompt=prompts["user"],
            system=prompts["system"],
            max_tokens=16000
        )

        report_text = result["text"]

        print(f"✅ Report generation complete ({len(report_text)} characters)")

        # 5. Store analysis results to AgentContext (for subsequent Agents)
        if context:
            context.add_agent_result(
                agent_name=f"champion_mastery_{champion_id}",
                data=analysis,
                report=report_text,
                execution_time=0.0
            )
            print(f"✅ Analysis results cached to AgentContext")

        # 6. Save output (if output directory is specified)
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Save analysis data
            analysis_file = output_path / f"champion_{champion_id}_analysis.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)

            # Save report
            report_file = output_path / f"champion_{champion_id}_mastery_report.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_text)

            print(f"\n💾 Output saved:")
            print(f"   - {analysis_file}")
            print(f"   - {report_file}")

        return analysis, report_text


def create_champion_mastery_agent(model: str = "sonnet") -> ChampionMasteryAgent:
    """
    Factory function: Create Champion Mastery Analysis Agent

    Args:
        model: LLM model selection

    Returns:
        ChampionMasteryAgent instance
    """
    return ChampionMasteryAgent(model=model)

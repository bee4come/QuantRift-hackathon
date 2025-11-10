"""
RoleSpecializationAgent - Role Specialization Analysis Agent

Analyzes player mastery and specialization in a specific role.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from src.agents.shared.config import get_config
from src.agents.shared.bedrock_adapter import BedrockLLM
from .tools import (
    generate_comprehensive_role_analysis,
    format_analysis_for_prompt
)
from .prompts import build_narrative_prompt


class RoleSpecializationAgent:
    """
    Role Specialization Analysis Agent

    Analyzes player specialization in a specific role, including:
    - Champion pool breadth and depth analysis
    - Role mastery assessment
    - Laning/teamfight/late game capability analysis
    - Meta adaptation and gap identification
    - Champion pool expansion recommendations
    """

    def __init__(self, model: str = "haiku"):
        """
        Initialize Role Specialization Analysis Agent

        Args:
            model: LLM model selection ("sonnet" or "haiku")
        """
        self.config = get_config()
        self.llm = BedrockLLM(model=model)

    def run(
        self,
        role: str,
        packs_dir: str,
        output_dir: Optional[str] = None,
        context: Optional[Any] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Run role specialization analysis

        Args:
            role: Role (TOP/JUNGLE/MIDDLE/BOTTOM/SUPPORT)
            packs_dir: Pack file directory path
            output_dir: Output directory (optional)
            context: AgentContext instance (optional, for data sharing)

        Returns:
            (analysis_data, report_text) - Analysis data and report text

        Raises:
            ValueError: If data for the role is not found
        """
        print(f"\n{'='*60}")
        print(f"📍 Role Specialization Analysis - Role: {role}")
        print(f"{'='*60}\n")

        # 1. Generate comprehensive analysis (prioritize cached data from context)
        all_packs_data = None
        if context and context.has_shared_data("all_packs"):
            print("✅ Using AgentContext cached data (saving 60% I/O time)")
            all_packs_data = context.get_shared_data("all_packs")

        print("📊 Analyzing role data...")
        analysis = generate_comprehensive_role_analysis(
            role=role,
            packs_dir=packs_dir,
            all_packs_data=all_packs_data  # Pass cached data
        )

        # Print analysis summary
        summary = analysis["summary"]
        pool = analysis["champion_pool"]["breadth"]
        print(f"\n✅ Analysis complete:")
        print(f"   Total games: {summary['total_games']}")
        print(f"   Overall winrate: {summary['overall_winrate']:.1%}")
        print(f"   Mastery score: {summary['role_mastery_score']} ({summary['proficiency_score']} points)")
        print(f"   Champion pool: {pool['total_champions']} champions ({pool['core_champions']} core)")

        # 2. Format data
        formatted_analysis = format_analysis_for_prompt(analysis)

        # 3. Build prompts
        prompts = build_narrative_prompt(analysis, formatted_analysis)

        # 4. Generate report
        print(f"\n🤖 Generating role specialization report (using {self.llm.model_id})...")

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
                agent_name="role_specialization",
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
            analysis_file = output_path / f"role_{role}_analysis.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)

            # Save report
            report_file = output_path / f"role_{role}_specialization_report.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_text)

            print(f"\n💾 Output saved:")
            print(f"   - {analysis_file}")
            print(f"   - {report_file}")

        return analysis, report_text

    def run_stream(
        self,
        packs_dir: str,
        role: str,
        recent_count: int = 5,
        time_range: Optional[str] = None,
        queue_id: Optional[int] = None
    ):
        """
        Run role specialization analysis with SSE streaming output

        Args:
            packs_dir: Pack file directory path
            role: Role (TOP/JUNGLE/MID/ADC/SUPPORT)
            recent_count: Number of recent matches (unused, kept for interface consistency)
            time_range: Time range filter (unused, kept for interface consistency)
            queue_id: Queue ID filter (unused, kept for interface consistency)

        Yields:
            SSE formatted messages for streaming response
        """
        from src.agents.shared.stream_helper import stream_agent_with_thinking

        # 1. Generate comprehensive analysis
        analysis = generate_comprehensive_role_analysis(
            role=role,
            packs_dir=packs_dir,
            all_packs_data=None
        )

        # 2. Format data
        formatted_analysis = format_analysis_for_prompt(analysis)

        # 3. Build prompts
        prompts = build_narrative_prompt(analysis, formatted_analysis)

        # 4. Stream report generation
        for message in stream_agent_with_thinking(
            prompt=prompts["user"],
            system_prompt=prompts["system"],
            model=self.llm.model_id,
            max_tokens=16000,
            enable_thinking=False
        ):
            yield message


def create_role_specialization_agent(model: str = "haiku") -> RoleSpecializationAgent:
    """
    Factory function: Create Role Specialization Analysis Agent

    Args:
        model: LLM model selection

    Returns:
        RoleSpecializationAgent instance
    """
    return RoleSpecializationAgent(model=model)

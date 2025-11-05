"""
DraftingCoachAgent - Main Agent Class

Provides BP recommendations based on counter relationships and composition analysis.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from src.agents.shared.bedrock_adapter import BedrockLLM
from src.agents.shared.config import get_config

from .tools import (
    analyze_bp_state,
    generate_pick_recommendations,
    generate_ban_recommendations,
    format_bp_analysis_for_prompt
)
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class DraftingCoachAgent:
    """
    Intelligent BP Coach Agent

    Analyzes team compositions and provides BP recommendations.
    Generates tactical advice for draft phase.

    Example:
        >>> agent = DraftingCoachAgent()
        >>> result = agent.run(
        ...     our_composition=[{"champion_id": 92, "role": "TOP"}],
        ...     enemy_composition=[{"champion_id": 122, "role": "TOP"}]
        ... )
    """

    def __init__(
        self,
        model_id: str = None,
        power_curves_path: str = "data/baselines/power_curves.json",
        counter_matrix_path: str = "data/baselines/counter_matrix.json"
    ):
        """
        Args:
            model_id: Bedrock model ID for LLM
            power_curves_path: Path to power curves baseline data
            counter_matrix_path: Path to counter matrix baseline data
        """
        if model_id is None:
            config = get_config()
            model_id = config.default_model
        self.model_id = model_id
        self.power_curves_path = power_curves_path
        self.counter_matrix_path = counter_matrix_path
        self.llm = BedrockLLM(model=model_id)

    def run(
        self,
        our_composition: List[Dict[str, Any]],
        enemy_composition: List[Dict[str, Any]],
        output_dir: str = None
    ) -> Dict[str, Any]:
        """
        Run complete BP analysis and generate recommendations

        Args:
            our_composition: Our team composition (can be partial)
                [{"champion_id": 92, "role": "TOP"}, ...]
            enemy_composition: Enemy team composition (can be partial)
                [{"champion_id": 122, "role": "TOP"}, ...]
            output_dir: Optional output directory for saving results

        Returns:
            {
                "bp_state": {...},  # Current BP state
                "recommendations": {...},  # Pick/Ban recommendations
                "report": "...",    # LLM-generated report
                "metadata": {...}
            }
        """
        print("\n" + "=" * 60)
        print("🎯 Intelligent BP Coach Analysis")
        print("=" * 60)

        # Step 1: Analyze BP state
        print("\n📊 Analyzing BP state...")
        bp_state = analyze_bp_state(
            our_composition=our_composition,
            enemy_composition=enemy_composition,
            power_curves_path=self.power_curves_path,
            counter_matrix_path=self.counter_matrix_path
        )

        print(f"✅ BP state analysis complete")

        # Step 2: Generate recommendations
        print("\n🔍 Generating pick recommendations...")

        # Determine missing roles
        all_roles = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
        our_roles = [m["role"] for m in our_composition] if our_composition else []
        missing_roles = [r for r in all_roles if r not in our_roles]

        pick_recommendations = []
        if missing_roles:
            pick_recommendations = generate_pick_recommendations(
                bp_state=bp_state,
                missing_roles=missing_roles,
                top_n=3
            )
            print(f"   Generated {len(pick_recommendations)} pick recommendations")

        # Generate ban recommendations if we have composition
        ban_recommendations = []
        if our_composition:
            ban_recommendations = generate_ban_recommendations(
                bp_state=bp_state,
                top_n=5
            )
            print(f"   Generated {len(ban_recommendations)} ban recommendations")

        # Step 3: Generate LLM report
        print(f"\n🤖 Generating BP recommendation report (using {self.model_id})...")

        formatted_data = format_bp_analysis_for_prompt(bp_state)

        user_prompt = USER_PROMPT_TEMPLATE.format(
            analysis_data=formatted_data
        )

        result = self.llm.generate_sync(
            prompt=user_prompt,
            system=SYSTEM_PROMPT
        )
        report = result['text']

        print(f"✅ Report generation complete ({len(report)} characters)")

        # Step 4: Compile results
        final_result = {
            "bp_state": {
                "our_composition": bp_state["our_composition"],
                "enemy_composition": bp_state["enemy_composition"],
                "our_analysis": bp_state["our_analysis"],
                "enemy_analysis": bp_state["enemy_analysis"],
                "matchup_analysis": bp_state["matchup_analysis"]
            },
            "recommendations": {
                "picks": pick_recommendations,
                "bans": ban_recommendations,
                "missing_roles": missing_roles
            },
            "report": report,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model_id": self.model_id,
                "our_composition": our_composition,
                "enemy_composition": enemy_composition
            }
        }

        if output_dir:
            self._save_results(final_result, output_dir)

        return final_result

    def _save_results(self, result: Dict[str, Any], output_dir: str) -> None:
        """Save BP analysis results to files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save JSON analysis
        analysis_file = output_path / "bp_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump({
                "bp_state": result["bp_state"],
                "recommendations": result["recommendations"],
                "metadata": result["metadata"]
            }, f, indent=2, ensure_ascii=False)

        # Save Markdown report
        report_file = output_path / "bp_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(result['report'])

        print(f"\n💾 Output saved:")
        print(f"   - {analysis_file}")
        print(f"   - {report_file}")

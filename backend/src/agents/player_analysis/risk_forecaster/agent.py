"""
RiskForecasterAgent - Main Agent Class

Predicts match power curves and identifies key moments based on team compositions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from src.agents.shared.bedrock_adapter import BedrockLLM
from src.agents.shared.config import get_config

from .tools import (
    analyze_composition_matchup,
    format_analysis_for_prompt
)
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class RiskForecasterAgent:
    """
    Match Risk Forecaster Agent

    Analyzes team compositions to predict power curves and key moments.
    Generates tactical recommendations for different game phases.

    Example:
        >>> agent = RiskForecasterAgent()
        >>> result = agent.run(
        ...     our_composition=[
        ...         {"champion_id": 92, "role": "TOP"},
        ...         {"champion_id": 64, "role": "JUNGLE"},
        ...         ...
        ...     ],
        ...     enemy_composition=[...]
        ... )
    """

    def __init__(
        self,
        model_id: str = None,
        power_curves_path: str = "data/baselines/power_curves.json"
    ):
        """
        Args:
            model_id: Bedrock model ID for LLM
            power_curves_path: Path to power curves baseline data
        """
        if model_id is None:
            config = get_config()
            model_id = config.default_model
        self.model_id = model_id
        self.power_curves_path = power_curves_path
        self.llm = BedrockLLM(model=model_id)

    def run(
        self,
        our_composition: List[Dict[str, Any]],
        enemy_composition: List[Dict[str, Any]],
        output_dir: str = None
    ) -> Dict[str, Any]:
        """
        Run complete risk forecast analysis

        Args:
            our_composition: Our team composition
                [{"champion_id": 92, "role": "TOP"}, ...]
            enemy_composition: Enemy team composition
                [{"champion_id": 122, "role": "TOP"}, ...]
            output_dir: Optional output directory for saving results

        Returns:
            {
                "analysis": {...},  # Raw analysis data
                "report": "...",    # LLM-generated report
                "metadata": {...}
            }
        """
        print("\n" + "=" * 60)
        print("⚔️  Match Risk Forecaster Analysis")
        print("=" * 60)

        # Step 1: Analyze compositions
        print("\n📊 Analyzing composition data...")
        analysis = analyze_composition_matchup(
            our_composition=our_composition,
            enemy_composition=enemy_composition,
            power_curves_path=self.power_curves_path
        )

        # Display key findings
        print(f"\n✅ Analysis complete:")
        print(f"   Key time points: {len(analysis['key_moments'])}")

        # Check early/mid/late advantage
        power_curves = analysis['power_curves']
        early_diff = power_curves['our_team'][10] - power_curves['enemy_team'][10]
        mid_diff = power_curves['our_team'][20] - power_curves['enemy_team'][20]
        late_diff = power_curves['our_team'][35] - power_curves['enemy_team'][35]

        print(f"   Early game power: {'Advantage' if early_diff > 0 else 'Disadvantage'} ({early_diff:+.1f})")
        print(f"   Mid game power: {'Advantage' if mid_diff > 0 else 'Disadvantage'} ({mid_diff:+.1f})")
        print(f"   Late game power: {'Advantage' if late_diff > 0 else 'Disadvantage'} ({late_diff:+.1f})")

        # Step 2: Generate LLM report
        print(f"\n🤖 Generating risk forecast report (using {self.model_id})...")

        formatted_data = format_analysis_for_prompt(analysis)

        user_prompt = USER_PROMPT_TEMPLATE.format(
            analysis_data=formatted_data
        )

        result = self.llm.generate_sync(
            prompt=user_prompt,
            system=SYSTEM_PROMPT
        )
        report = result['text']

        print(f"✅ Report generation complete ({len(report)} characters)")

        # Step 3: Save results
        result = {
            "analysis": analysis,
            "report": report,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model_id": self.model_id,
                "our_composition": our_composition,
                "enemy_composition": enemy_composition
            }
        }

        if output_dir:
            self._save_results(result, output_dir)

        return result

    def _save_results(self, result: Dict[str, Any], output_dir: str) -> None:
        """Save analysis results to files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save JSON analysis
        analysis_file = output_path / "risk_forecast_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(result['analysis'], f, indent=2, ensure_ascii=False)

        # Save Markdown report
        report_file = output_path / "risk_forecast_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(result['report'])

        print(f"\n💾 Output saved:")
        print(f"   - {analysis_file}")
        print(f"   - {report_file}")

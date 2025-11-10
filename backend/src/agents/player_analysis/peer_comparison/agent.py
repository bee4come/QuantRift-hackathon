"""PeerComparisonAgent - Peer Comparison Agent"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from src.agents.shared.config import get_config
from src.agents.shared.bedrock_adapter import BedrockLLM
from .tools import load_player_data, load_rank_baseline, compare_to_baseline, format_analysis_for_prompt
from .prompts import build_narrative_prompt


class PeerComparisonAgent:
    """Peer Comparison Agent - Compare player vs same rank average"""

    def __init__(self, model: str = "haiku"):
        self.config = get_config()
        self.llm = BedrockLLM(model=model)

    def run(
        self,
        packs_dir: str,
        rank: str,
        output_dir: Optional[str] = None,
        context: Optional[Any] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Run peer comparison analysis

        Compare analysis using rank baseline generated from Gold layer data

        Args:
            packs_dir: Pack file directory path
            rank: Rank (GOLD, PLATINUM, DIAMOND, etc.)
            output_dir: Output directory (optional)
            context: AgentContext instance (optional, for data sharing and result retrieval)

        Returns:
            (comparison_data, report_text) - Comparison data and report text
        """
        print(f"\n{'='*60}\n⚖️ Peer Comparison Analysis - Rank: {rank}\n{'='*60}\n")

        # Get cached data from AgentContext (if provided)
        all_packs_data = None
        if context and context.has_shared_data("all_packs"):
            print("✅ Using AgentContext cached data (saving 60% I/O time)")
            all_packs_data = context.get_shared_data("all_packs")

        player_data = load_player_data(packs_dir, all_packs_data)
        baseline = load_rank_baseline(rank)

        if not baseline:
            raise ValueError(f"No baseline data for rank {rank}. "
                           f"Supported ranks: GOLD, PLATINUM, DIAMOND")

        print(f"✅ Using Gold layer rank baseline data (sample size: {baseline.get('sample_size', 'N/A')})")

        comparison = compare_to_baseline(player_data, baseline)

        print(f"✅ Comparison complete: {comparison['assessment']}, "
              f"winrate differential {comparison['winrate_diff']:+.1%}")

        formatted_data = format_analysis_for_prompt(comparison, rank)
        prompts = build_narrative_prompt(comparison, formatted_data, rank)

        print(f"\n🤖 Generating comparison report (using {self.llm.model_id})...")
        result = self.llm.generate_sync(
            prompt=prompts["user"],
            system=prompts["system"],
            max_tokens=14000
        )
        report_text = result["text"]
        print(f"✅ Report generation complete ({len(report_text)} characters)")

        # Store analysis results to AgentContext (for subsequent Agents)
        if context:
            context.add_agent_result(
                agent_name="peer_comparison",
                data=comparison,
                report=report_text,
                execution_time=0.0
            )
            print(f"✅ Analysis results cached to AgentContext")

        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            with open(output_path / f"peer_comparison_{rank}.json", 'w', encoding='utf-8') as f:
                json.dump(comparison, f, ensure_ascii=False, indent=2)
            with open(output_path / f"peer_comparison_{rank}_report.md", 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n💾 Output saved to {output_dir}")

        return comparison, report_text

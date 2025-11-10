"""ChampionRecommendationAgent - Champion Recommendation Agent"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from src.agents.shared.config import get_config
from src.agents.shared.bedrock_adapter import BedrockLLM
from .tools import analyze_champion_pool, generate_recommendations, format_analysis_for_prompt
from .prompts import build_narrative_prompt
from .reinforcement_learning import create_default_recommender


class ChampionRecommendationAgent:
    """Champion Recommendation Agent - Recommends new champions based on playstyle and meta (with Reinforcement Learning support)"""

    def __init__(self, model: str = "haiku", enable_rl: bool = False):
        self.config = get_config()
        self.llm = BedrockLLM(model=model)
        self.enable_rl = enable_rl
        self.rl_recommender = None

        if enable_rl:
            self.rl_recommender = create_default_recommender()

    def run(
        self,
        packs_dir: str,
        output_dir: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Run champion recommendation analysis (with Reinforcement Learning mode support)"""
        mode_indicator = "🧠 Reinforcement Learning Mode" if self.enable_rl else "📊 Static Recommendation Mode"
        print(f"\n{'='*60}\n🎯 Champion Recommendation Analysis - {mode_indicator}\n{'='*60}\n")

        champion_pool = analyze_champion_pool(packs_dir)
        recommendations = generate_recommendations(champion_pool)

        # If RL enabled, re-rank using Thompson Sampling
        if self.enable_rl and self.rl_recommender and recommendations:
            print(f"\n🧠 Applying Thompson Sampling re-ranking...")

            # Extract base scores
            base_scores = {
                rec["champion_id"]: rec["综合评分"]
                for rec in recommendations
            }

            # Thompson Sampling ranking
            recommendations = self.rl_recommender.rank_recommendations(
                candidates=recommendations,
                base_scores=base_scores,
                bandit_weight=0.3  # 30% RL weight, 70% static weight
            )

            # Print RL status summary
            rl_summary = self.rl_recommender.get_state_summary()
            print(f"  - RL status: {rl_summary['total_champions']} champions, "
                  f"{rl_summary['total_recommendations']} recommendations, "
                  f"{rl_summary['global_acceptance_rate']:.1%} acceptance rate")

        print(f"✅ Analysis complete: {len(champion_pool['core_champions'])} core champions, "
              f"{len(recommendations)} recommended champions")

        formatted_data = format_analysis_for_prompt(champion_pool, recommendations)
        prompts = build_narrative_prompt(champion_pool, recommendations, formatted_data)

        print(f"\n🤖 Generating recommendation report (using {self.llm.model_id})...")
        result = self.llm.generate_sync(
            prompt=prompts["user"],
            system=prompts["system"],
            max_tokens=12000
        )
        report_text = result["text"]
        print(f"✅ Report generation complete ({len(report_text)} characters)")

        analysis = {
            "champion_pool": champion_pool,
            "recommendations": recommendations
        }

        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            with open(output_path / "champion_recommendations.json", 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)
            with open(output_path / "champion_recommendations_report.md", 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n💾 Output saved to {output_dir}")

        return analysis, report_text

    def provide_feedback(
        self,
        champion_id: int,
        champion_name: str,
        feedback_type: str,
        outcome: Optional[str] = None
    ):
        """
        Provide recommendation feedback (only effective in RL mode)

        Args:
            champion_id: Champion ID
            champion_name: Champion name
            feedback_type: "recommended", "accepted", "rejected"
            outcome: "win", "loss", None
        """
        if not self.enable_rl or not self.rl_recommender:
            print("⚠️  Warning: RL mode not enabled, feedback ignored")
            return

        self.rl_recommender.update_feedback(
            champion_id=champion_id,
            champion_name=champion_name,
            feedback_type=feedback_type,
            outcome=outcome
        )

    def get_rl_summary(self) -> Optional[Dict[str, Any]]:
        """Get RL status summary (only effective in RL mode)"""
        if not self.enable_rl or not self.rl_recommender:
            return None

        return self.rl_recommender.get_state_summary()

    def run_stream(
        self,
        packs_dir: str,
        time_range: Optional[str] = None,
        queue_id: Optional[int] = None
    ):
        """
        Run champion recommendation analysis with SSE streaming output

        Unified method for both agent card and chat interfaces

        Args:
            packs_dir: Player-Pack directory path
            time_range: Time range filter (e.g., "2024-01-01", "past-365", None)
            queue_id: Queue ID filter (420=Solo/Duo, 440=Flex, 400=Normal, None=All)

        Yields:
            SSE formatted messages for streaming
        """
        from src.agents.shared.stream_helper import stream_agent_with_thinking

        # Analyze champion pool
        champion_pool = analyze_champion_pool(packs_dir, time_range=time_range, queue_id=queue_id)

        # Check if no core champions found
        if not champion_pool["core_champions"]:
            yield f"data: {{\"error\": \"No core champions found. Play at least 20 games with a champion to get recommendations.\"}}\n\n"
            return

        # Generate recommendations
        recommendations = generate_recommendations(champion_pool)

        # Apply RL re-ranking if enabled
        if self.enable_rl and self.rl_recommender and recommendations:
            base_scores = {rec["champion_id"]: rec["综合评分"] for rec in recommendations}
            recommendations = self.rl_recommender.rank_recommendations(
                candidates=recommendations,
                base_scores=base_scores,
                bandit_weight=0.3
            )

        # Format data and build prompts
        formatted_data = format_analysis_for_prompt(champion_pool, recommendations)
        prompts = build_narrative_prompt(champion_pool, recommendations, formatted_data)

        # Stream response
        for message in stream_agent_with_thinking(
            prompt=prompts['user'],
            system_prompt=prompts['system'],
            model=self.llm.model_id,
            max_tokens=8000,
            enable_thinking=False
        ):
            yield message

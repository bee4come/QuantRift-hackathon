"""FriendComparisonAgent - Friend Comparison Agent"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from src.agents.shared.config import get_config
from src.agents.shared.bedrock_adapter import BedrockLLM
from .tools import load_player_data, compare_two_players, format_comparison_for_prompt
from .prompts import build_narrative_prompt


class FriendComparisonAgent:
    """Friend Comparison Agent - Compare two players directly"""

    def __init__(self, model: str = "haiku"):
        self.config = get_config()
        self.llm = BedrockLLM(model=model)

    def run(
        self,
        player1_packs_dir: str,
        player2_packs_dir: str,
        player1_name: str,
        player2_name: str,
        output_dir: Optional[str] = None,
        context: Optional[Any] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Run friend comparison analysis

        Compare two players directly

        Args:
            player1_packs_dir: Player 1's pack directory path
            player2_packs_dir: Player 2's pack directory path
            player1_name: Player 1's display name (e.g., "s1ne#na1")
            player2_name: Player 2's display name (e.g., "Faker#KR1")
            output_dir: Output directory (optional)
            context: AgentContext instance (optional)

        Returns:
            (comparison_data, report_text) - Comparison data and report text
        """
        print(f"\n{'='*60}\n👥 Friend Comparison Analysis\n{player1_name} vs {player2_name}\n{'='*60}\n")

        # Load both players' data
        player1_data = load_player_data(player1_packs_dir)
        player2_data = load_player_data(player2_packs_dir)

        # Compare two players
        comparison = compare_two_players(player1_data, player2_data, player1_name, player2_name)

        print(f"✅ Comparison complete")
        print(f"   {player1_name}: {comparison['player1']['total_games']} games, {comparison['player1']['winrate']:.1%} WR")
        print(f"   {player2_name}: {comparison['player2']['total_games']} games, {comparison['player2']['winrate']:.1%} WR")

        # Format for prompt
        formatted_data = format_comparison_for_prompt(comparison, player1_name, player2_name)
        prompts = build_narrative_prompt(comparison, formatted_data, player1_name, player2_name)

        print(f"\n🤖 Generating comparison report (using {self.llm.model_id})...")
        result = self.llm.generate_sync(
            prompt=prompts["user"],
            system=prompts["system"],
            max_tokens=14000
        )
        report_text = result["text"]
        print(f"✅ Report generation complete ({len(report_text)} characters)")

        # Store analysis results to AgentContext
        if context:
            context.add_agent_result(
                agent_name="friend_comparison",
                data=comparison,
                report=report_text,
                execution_time=0.0
            )
            print(f"✅ Analysis results cached to AgentContext")

        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            with open(output_path / f"friend_comparison_{player1_name}_{player2_name}.json", 'w', encoding='utf-8') as f:
                json.dump(comparison, f, ensure_ascii=False, indent=2)
            with open(output_path / f"friend_comparison_{player1_name}_{player2_name}_report.md", 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n💾 Output saved to {output_dir}")

        return comparison, report_text

    def run_stream(
        self,
        packs_dir: str,
        friend_packs_dir: str,
        player_name: str,
        friend_name: str,
        recent_count: int = 5,
        time_range: Optional[str] = None,
        queue_id: Optional[int] = None
    ):
        """
        Run friend comparison analysis with SSE streaming output

        Args:
            packs_dir: Player's pack directory path
            friend_packs_dir: Friend's pack directory path
            player_name: Player's display name
            friend_name: Friend's display name
            recent_count: Number of recent matches (unused, kept for interface consistency)
            time_range: Time range filter (unused, kept for interface consistency)
            queue_id: Queue ID filter (unused, kept for interface consistency)

        Yields:
            SSE formatted messages for streaming response
        """
        from src.agents.shared.stream_helper import stream_agent_with_thinking

        # Load both players' data
        player_data = load_player_data(packs_dir)
        friend_data = load_player_data(friend_packs_dir)

        # Compare two players
        comparison = compare_two_players(player_data, friend_data, player_name, friend_name)

        # Format for prompt
        formatted_data = format_comparison_for_prompt(comparison, player_name, friend_name)
        prompts = build_narrative_prompt(comparison, formatted_data, player_name, friend_name)

        # Stream report generation
        for message in stream_agent_with_thinking(
            prompt=prompts["user"],
            system_prompt=prompts["system"],
            model=self.llm.model_id,
            max_tokens=14000,
            enable_thinking=False
        ):
            yield message

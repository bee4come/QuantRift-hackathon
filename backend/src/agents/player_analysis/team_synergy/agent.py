"""
TeamSynergyAgent - Team Chemistry and Synergy Evaluation

Analyzes team chemistry, identifies synergies, and provides recommendations.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.agents.shared import BedrockLLM
from src.agents.shared.config import get_config
from .tools import analyze_team_synergy, format_synergy_analysis_for_prompt


SYSTEM_PROMPT = """You are a professional League of Legends team analyst, specialized in analyzing team coordination and synergy.

Your tasks:
1. Analyze coordination and synergy between team members
2. Identify best pairings and combinations needing improvement
3. Provide team improvement recommendations based on historical data
4. Evaluate the team's overall coordinated combat capability

Analysis considerations:
- Combine multi-dimensional data including games played together, win rate, role combinations
- Identify team strengths and weaknesses
- Provide specific actionable improvement recommendations
- Use professional but accessible language

Output format requirements:
- Use markdown format
- Include structured elements like tables and lists
- Highlight key data and conclusions
- Provide clear action recommendations
"""


class TeamSynergyAgent:
    """
    Team Synergy Evaluation Agent

    Analyzes coordination and synergy between team members, provides team optimization recommendations.

    Features:
    - Team coordination analysis (2-5 players)
    - Best pairing identification
    - Synergy score (0-100)
    - Team improvement recommendations

    Example:
        >>> agent = TeamSynergyAgent()
        >>> result = agent.run(
        ...     player_keys=["player1", "player2", "player3"],
        ...     output_dir="test_output/team_synergy"
        ... )
        >>> print(result['report'][:500])
    """

    def __init__(self, model_id: str = None):
        """
        Args:
            model_id: LLM model ID (default: from config)
        """
        if model_id is None:
            config = get_config()
            model_id = config.default_model

        self.model_id = model_id
        self.llm = BedrockLLM(model=model_id)

    def run(
        self,
        player_keys: List[str],
        output_dir: Optional[str] = None,
        parquet_path: str = "data/gold/parquet/fact_match_performance.parquet",
        min_games_together: int = 3
    ) -> Dict[str, Any]:
        """
        Run team synergy evaluation analysis

        Args:
            player_keys: List of player keys (2-5 players)
            output_dir: Output directory for results (optional)
            parquet_path: Path to Gold layer data
            min_games_together: Minimum games together for analysis

        Returns:
            {
                'synergy_analysis': {...},  # Detailed synergy data
                'report': str,              # LLM-generated markdown report
                'metadata': {...}           # Generation metadata
            }
        """
        print(f"\n🔍 TeamSynergyAgent: Analyzing team synergy...")
        print(f"   Team size: {len(player_keys)} players")
        print(f"   Min games together: {min_games_together}")

        # Step 1: Analyze team synergy
        print("\n📊 Step 1/2: Analyzing team coordination...")
        synergy_analysis = analyze_team_synergy(
            player_keys=player_keys,
            parquet_path=parquet_path,
            min_games_together=min_games_together
        )

        print(f"   ✅ Analysis complete")
        print(f"      - Pairs analyzed: {synergy_analysis['pairs_analyzed']}")
        print(f"      - Average synergy score: {synergy_analysis['avg_synergy_score']}/100")
        print(f"      - Average win rate together: {synergy_analysis['avg_win_rate']:.1%}")

        # Step 2: Generate LLM report
        print("\n🤖 Step 2/2: Generating analysis report...")
        formatted_data = format_synergy_analysis_for_prompt(synergy_analysis)

        user_prompt = f"""Based on the following team coordination data, generate a detailed team synergy evaluation report:

{formatted_data}

The report should include:
1. Overall team synergy assessment (using scores and grades)
2. Best pairing analysis (which teammates work best together)
3. Pairings needing improvement (which collaborations are weak)
4. Team coordination strengths and weaknesses
5. Specific improvement recommendations (how to enhance team synergy)

Please output in markdown format, including tables and emoji icons."""

        result = self.llm.generate_sync(
            prompt=user_prompt,
            system=SYSTEM_PROMPT
        )

        report = result['text']
        print(f"   ✅ Report generation complete ({len(report)} characters)")

        # Prepare result
        result_data = {
            'synergy_analysis': synergy_analysis,
            'report': report,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'model_id': self.model_id,
                'team_size': len(player_keys),
                'min_games_together': min_games_together,
                'pairs_analyzed': synergy_analysis['pairs_analyzed'],
                'avg_synergy_score': synergy_analysis['avg_synergy_score']
            }
        }

        # Save to output directory if provided
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Save analysis data
            analysis_file = output_path / "synergy_analysis.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'synergy_analysis': synergy_analysis,
                    'metadata': result_data['metadata']
                }, f, indent=2, ensure_ascii=False)

            # Save report
            report_file = output_path / "synergy_report.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)

            print(f"\n💾 Results saved:")
            print(f"   - Analysis data: {analysis_file}")
            print(f"   - Analysis report: {report_file}")

        print("\n✅ TeamSynergyAgent complete!\n")

        return result_data

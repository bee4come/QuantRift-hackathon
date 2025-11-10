"""
Flexible CustomAnalysisAgent - LLM自主决策分析方案

不预定义数据结构，让LLM自己决定：
1. 如何分组数据
2. 对比什么指标
3. 如何生成报告
"""

import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.shared.bedrock_adapter import BedrockLLM


class FlexibleCustomAnalysisAgent:
    """
    Flexible custom analysis agent - LLM自主决策

    工作流程：
    1. 用户query + player data → LLM
    2. LLM自己决定分析方案（不限制数据结构）
    3. LLM生成分析报告
    """

    def __init__(self, model: str = "haiku"):
        self.llm = BedrockLLM(model=model)

    def run_stream(
        self,
        user_query: str,
        packs_dir: str,
        player_data: Dict[str, Any]
    ):
        """
        Run flexible custom analysis

        Args:
            user_query: User's question (e.g., "周末vs工作日哪个厉害")
            packs_dir: Player pack directory
            player_data: Player data summary

        Yields:
            SSE formatted messages
        """
        from src.agents.shared.stream_helper import stream_agent_with_thinking

        # Load data summary
        yield f'data: {{"type": "executing", "content": "📦 Loading player data..."}}\n\n'

        data_summary = self._load_data_summary(packs_dir)

        yield f'data: {{"type": "executing", "content": "✅ Loaded {data_summary.get(\'total_games\', 0)} games"}}\n\n'
        yield f'data: {{"type": "executing", "content": "🤖 Analyzing your question..."}}\n\n'

        # Build flexible prompt
        system_prompt = """You are a League of Legends data analyst AI.

You have access to player performance data including:
- Win rate, KDA, games played
- Combat metrics (combat power, damage)
- Objective participation
- Champion usage
- Performance across different time periods and patches

**Your task**: Answer the user's question using the available data.

**Important**:
- Be honest about data limitations (e.g., "I don't have weekday/weekend tags in the data")
- Suggest alternative analysis if exact request isn't feasible
- Provide insights based on what data IS available
- Use clear markdown formatting"""

        user_prompt = f"""**User Question**: {user_query}

**Available Data**:
{self._format_data_summary(data_summary)}

**Your task**:
1. Analyze what the user is asking for
2. Check if the required data is available
3. If not available: Explain limitation and suggest closest alternative
4. If available: Provide the analysis

Generate your response now:"""

        # Stream LLM response
        for message in stream_agent_with_thinking(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=self.llm.model_id,
            max_tokens=3000,
            enable_thinking=False
        ):
            yield message

    def _load_data_summary(self, packs_dir: str) -> Dict[str, Any]:
        """Load data summary from player packs"""
        import json
        from pathlib import Path

        packs_path = Path(packs_dir)
        total_games = 0
        total_wins = 0
        patches = set()
        champions = set()

        for pack_file in packs_path.glob("pack_*.json"):
            try:
                with open(pack_file, 'r') as f:
                    pack = json.load(f)
                    patches.add(pack.get('patch'))

                    for cr in pack.get('by_cr', []):
                        total_games += cr.get('games', 0)
                        total_wins += cr.get('wins', 0)
                        champions.add(cr.get('champ_id'))
            except:
                continue

        return {
            'total_games': total_games,
            'total_wins': total_wins,
            'winrate': (total_wins / total_games * 100) if total_games > 0 else 0,
            'patches': sorted(list(patches)),
            'unique_champions': len(champions)
        }

    def _format_data_summary(self, summary: Dict[str, Any]) -> str:
        """Format data summary for prompt"""
        return f"""- Total games: {summary['total_games']}
- Win rate: {summary['winrate']:.1f}%
- Patches: {', '.join(summary['patches'])}
- Unique champions: {summary['unique_champions']}

**Data limitations**:
- Data is aggregated by patch/champion/role
- No weekday/weekend tags available
- No time-of-day information
- Cannot directly compare weekend vs weekday

**What you CAN do**:
- Compare time periods (last 30 days vs previous 30 days)
- Compare roles (ADC vs Support)
- Compare champions
- Analyze patch-by-patch trends"""

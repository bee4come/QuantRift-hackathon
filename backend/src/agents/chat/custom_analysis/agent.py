"""
CustomAnalysisAgent - Non-Standard Quantitative Analysis

Leverages full quantitative metrics from Player Pack data:
- Combat Power (cp_25)
- KDA Adjusted
- Objective Rate
- Time to Core
- Data Quality (governance_tag)

Supports flexible group comparisons with multi-dimensional filtering:
- Time periods
- Champions
- Roles
- Data quality tiers
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.shared.bedrock_adapter import BedrockLLM
from .tools import (
    GroupFilter,
    load_all_packs,
    filter_packs_by_group,
    calculate_metrics_from_packs,
    compare_two_groups,
    format_comparison_for_prompt
)


class CustomAnalysisAgent:
    """
    Custom Analysis Agent using Player Pack quantitative metrics

    Supports flexible comparative analysis:
    1. Time period comparison (e.g., last 30 days vs previous 30 days)
    2. Champion subset comparison (e.g., assassins vs tanks)
    3. Role comparison (e.g., ADC vs Support performance)
    4. Data quality comparison (e.g., CONFIDENT games vs all games)

    Example queries:
    - "Compare my performance in last 30 days vs previous 30 days"
    - "How do my ADC games compare to my Support games?"
    - "Compare weekday vs weekend performance"
    - "Compare my tank champions vs assassin champions"
    """

    def __init__(self, model: str = "haiku"):
        self.llm = BedrockLLM(model=model)

    def run_stream(
        self,
        user_query: str,
        packs_dir: str,
        group1_filter: GroupFilter,
        group2_filter: GroupFilter
    ):
        """
        Run custom analysis with SSE streaming output

        Args:
            user_query: User's natural language query
            packs_dir: Path to player pack directory
            group1_filter: Filter for first data group
            group2_filter: Filter for second data group

        Yields:
            SSE formatted messages for streaming response
        """
        from src.agents.shared.stream_helper import stream_agent_with_thinking

        # Load all packs
        yield f'data: {{"type": "executing", "content": "📦 Loading Player Pack data..."}}\n\n'

        all_packs = load_all_packs(packs_dir)
        if not all_packs:
            yield f'data: {{"type": "error", "content": "No Player Pack data available"}}\n\n'
            return

        yield f'data: {{"type": "executing", "content": "✅ Loaded {len(all_packs)} pack files"}}\n\n'

        # Filter Group 1
        yield f'data: {{"type": "executing", "content": "🔍 Filtering Group 1: {group1_filter.name}..."}}\n\n'

        group1_packs = filter_packs_by_group(all_packs, group1_filter)
        yield f'data: {{"type": "executing", "content": "   Matched {len(group1_packs)} packs"}}\n\n'

        # Filter Group 2
        yield f'data: {{"type": "executing", "content": "🔍 Filtering Group 2: {group2_filter.name}..."}}\n\n'

        group2_packs = filter_packs_by_group(all_packs, group2_filter)
        yield f'data: {{"type": "executing", "content": "   Matched {len(group2_packs)} packs"}}\n\n'

        # Calculate quantitative metrics
        yield f'data: {{"type": "executing", "content": "📊 Calculating quantitative metrics..."}}\n\n'

        group1_metrics = calculate_metrics_from_packs(group1_packs, group1_filter.name)
        group2_metrics = calculate_metrics_from_packs(group2_packs, group2_filter.name)

        yield f'data: {{"type": "executing", "content": "   Group 1: {group1_metrics.games} games"}}\n\n'
        yield f'data: {{"type": "executing", "content": "   Group 2: {group2_metrics.games} games"}}\n\n'

        # Compare two groups
        yield f'data: {{"type": "executing", "content": "⚖️  Comparing groups..."}}\n\n'

        comparison = compare_two_groups(
            group1_metrics,
            group2_metrics,
            group1_filter.name,
            group2_filter.name
        )

        # Format for LLM prompt
        formatted_data = format_comparison_for_prompt(comparison, user_query)

        # Generate analysis report
        yield f'data: {{"type": "executing", "content": "🤖 Generating analysis report..."}}\n\n'

        system_prompt = """You are a League of Legends data analyst expert.

Generate comprehensive comparative analysis reports with:
- Clear quantitative comparisons across all metrics
- Actionable insights based on the data
- Professional markdown formatting
- Evidence-based conclusions

Focus on these quantitative metrics:
1. **Win Rate**: Overall performance trend
2. **KDA Adjusted**: Combat effectiveness
3. **Combat Power (cp_25)**: Mid-game strength
4. **Objective Rate**: Teamwork and macro play
5. **Time to Core**: Economic efficiency

Highlight:
- Significant changes (>5% for winrate, >10% for other metrics)
- Consistent trends across multiple metrics
- Data quality considerations (CONFIDENT vs CAUTION/CONTEXT)
"""

        user_prompt = f"""{formatted_data}

**Analysis Task**:
Based on the quantitative metrics comparison above, generate a comprehensive analysis report that:

1. **Summarizes Key Findings**: Identify the most significant changes between the two groups
2. **Explains Trends**: Analyze why these changes occurred based on the metrics
3. **Provides Recommendations**: Suggest actionable improvements based on the data
4. **Considers Data Quality**: Note any data quality concerns that might affect conclusions

Use markdown formatting with clear sections and bullet points."""

        # Stream LLM response
        for message in stream_agent_with_thinking(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=self.llm.model_id,
            max_tokens=3000,
            enable_thinking=False
        ):
            yield message

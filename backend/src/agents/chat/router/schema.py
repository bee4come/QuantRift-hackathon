"""
Router Decision JSON Schema
Defines the structure for LLM routing decisions
"""

from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field


class RouterDecision(BaseModel):
    """LLM Router decision output schema"""

    action: Literal[
        "call_subagent",      # Call single agent
        "combine_multiple",   # Call multiple agents
        "clarify",            # Need more info from user
        "direct_answer"       # Simple answer without agent
    ] = Field(description="The action to take based on user query")

    strategy: Optional[Literal["sequential", "parallel"]] = Field(
        default="sequential",
        description="How to execute multiple agents (only for combine_multiple)"
    )

    subagent_id: Optional[str] = Field(
        default=None,
        description="Single agent ID (for call_subagent)"
    )

    endpoints: Optional[List[str]] = Field(
        default=None,
        description="Multiple agent IDs (for combine_multiple)"
    )

    params: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Parameters to pass to agent(s)"
    )

    reason: str = Field(
        description="Explanation of why this routing decision was made"
    )

    clarification_question: Optional[str] = Field(
        default=None,
        description="Question to ask user (only for clarify action)"
    )

    direct_response: Optional[str] = Field(
        default=None,
        description="Direct answer text (only for direct_answer action)"
    )

    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence in this routing decision (0-1)"
    )


class AgentMetadata(BaseModel):
    """Metadata for each available agent"""

    id: str = Field(description="Agent identifier (e.g., 'weakness-analysis')")
    name: str = Field(description="Human-readable agent name")
    description: str = Field(description="What this agent analyzes")
    required_params: List[str] = Field(
        default_factory=list,
        description="Required parameters for this agent"
    )
    optional_params: List[str] = Field(
        default_factory=list,
        description="Optional parameters"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Keywords that might trigger this agent"
    )
    use_cases: List[str] = Field(
        default_factory=list,
        description="Example use cases/questions this agent handles"
    )


# Available parameter types and their valid values
VALID_PARAM_VALUES = {
    "role": ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"],
    "time_range": ["past-7", "past-30", "past-90", "past-365"],
    "queue_id": [420, 440, 400],  # Solo/Duo, Flex, Normal
    "model": ["haiku", "sonnet"]
}


# 20 Quantitative Metrics Dictionary
METRICS_DICTIONARY = {
    # Behavioral Metrics (5)
    "pick_rate": "Champion selection frequency (picks / total games)",
    "attach_rate": "Co-occurrence with other champions in team composition",
    "rune_diversity": "Number of unique rune setups used",
    "synergy_score": "Team composition compatibility rating",
    "counter_effectiveness": "Win rate against specific enemy champions",

    # Win Rate Metrics (5)
    "baseline_winrate": "Raw win rate (wins / total games)",
    "ci_lower": "Wilson confidence interval lower bound",
    "ci_upper": "Wilson confidence interval upper bound",
    "effective_n": "Statistically adjusted sample size",
    "governance": "Data quality tier (CONFIDENT/CAUTION/CONTEXT)",

    # Objective Metrics (3)
    "objective_rate": "Combined Baron + Dragon kills per game",
    "baron_rate": "Baron kills per game",
    "dragon_rate": "Dragon kills per game",

    # Economic Metrics (3)
    "item_efficiency": "Average damage output per gold spent",
    "gold_per_min": "Total gold earned per minute",
    "cs_efficiency": "Gold earned per creep score",

    # Combat Metrics (4)
    "combat_power": "Composite power index (base stats + items + runes + skills)",
    "damage_efficiency": "Damage dealt per gold invested",
    "time_to_core": "Minutes required to complete 2 core items",
    "shock_impact": "Unexpected performance variance (meta shift indicator)",

    # Additional Common Metrics
    "kda": "Kill-Death-Assist ratio",
    "kda_adj": "Adjusted KDA considering role and game duration",
    "damage_dealt": "Total damage to champions",
    "damage_taken": "Total damage received",
    "vision_score": "Vision control rating",
    "cs": "Creep score (minions killed)",
    "gold_earned": "Total gold accumulated"
}

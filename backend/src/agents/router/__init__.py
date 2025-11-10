"""
Router module for intelligent query routing

Provides hybrid routing combining rule-based patterns and LLM intelligence.
"""

from .rule_router import RuleRouter, RuleMatch, get_rule_router
from .hybrid_router import HybridRouter, HybridRoutingResult, get_hybrid_router
from .schema import RouterDecision, AgentMetadata, VALID_PARAM_VALUES, METRICS_DICTIONARY

__all__ = [
    "RuleRouter",
    "RuleMatch",
    "get_rule_router",
    "HybridRouter",
    "HybridRoutingResult",
    "get_hybrid_router",
    "RouterDecision",
    "AgentMetadata",
    "VALID_PARAM_VALUES",
    "METRICS_DICTIONARY",
]

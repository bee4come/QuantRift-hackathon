"""
Chat Module - Intelligent multi-agent chat system with routing

Provides:
- ChatMasterAgent: LLM-based query understanding and agent selection
- HybridRouter: Combined rule-based + LLM routing
- RouterStreamGenerator: SSE streaming for real-time chat responses
- SessionManager: Conversation state management
"""

from .chat_master_agent import ChatMasterAgent, AgentDecision, ANALYSIS_SUBAGENTS
from .router.hybrid_router import HybridRouter, HybridRoutingResult, get_hybrid_router
from .router.rule_router import RuleRouter, RuleMatch, get_rule_router
from .router.router_stream import RouterStreamGenerator, stream_chat_with_routing
from .router.schema import METRICS_DICTIONARY, VALID_PARAM_VALUES, RouterDecision, AgentMetadata
from .session_manager import SessionManager

__all__ = [
    # Chat Master
    "ChatMasterAgent",
    "AgentDecision",
    "ANALYSIS_SUBAGENTS",

    # Routing
    "HybridRouter",
    "HybridRoutingResult",
    "get_hybrid_router",
    "RuleRouter",
    "RuleMatch",
    "get_rule_router",

    # Streaming
    "RouterStreamGenerator",
    "stream_chat_with_routing",

    # Schema
    "METRICS_DICTIONARY",
    "VALID_PARAM_VALUES",
    "RouterDecision",
    "AgentMetadata",

    # Session Management
    "SessionManager",
]

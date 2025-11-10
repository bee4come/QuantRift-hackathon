"""
Hybrid Router combining rule-based and LLM routing

First attempts rule-based routing for speed and accuracy on known patterns.
Falls back to LLM routing for complex or ambiguous queries.
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from dataclasses import dataclass
from .rule_router import RuleRouter, RuleMatch

if TYPE_CHECKING:
    from ..chat_master_agent import ChatMasterAgent, AgentDecision


@dataclass
class HybridRoutingResult:
    """Result from hybrid routing"""
    action: str  # "call_subagent", "ask_user", "answer_directly", "custom_analysis"
    subagent_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    content: Optional[str] = None
    options: Optional[List[str]] = None
    reason: str = ""
    routing_method: str = "unknown"  # "rule" or "llm"
    confidence: float = 0.0


class HybridRouter:
    """
    Hybrid routing system combining rules and LLM

    Architecture:
    1. Rule Router: Fast keyword-based routing for obvious patterns
    2. LLM Router (ChatMasterAgent): Flexible NLP-based routing for complex queries
    3. Confidence threshold: Use rules if confidence > 0.7, else use LLM
    """

    def __init__(
        self,
        rule_confidence_threshold: float = 0.7,
        llm_model: str = "haiku"
    ):
        """
        Initialize hybrid router

        Args:
            rule_confidence_threshold: Minimum confidence to use rule routing
            llm_model: LLM model for ChatMasterAgent (haiku/sonnet)
        """
        from ..chat_master_agent import ChatMasterAgent

        self.rule_router = RuleRouter()
        self.llm_router = ChatMasterAgent(model=llm_model)
        self.confidence_threshold = rule_confidence_threshold

    def route(
        self,
        user_message: str,
        session_history: Optional[List[Dict[str, str]]] = None,
        player_data: Optional[Dict[str, Any]] = None
    ) -> HybridRoutingResult:
        """
        Route user query using hybrid approach

        Args:
            user_message: User's current query
            session_history: Conversation history
            player_data: Player context data

        Returns:
            HybridRoutingResult with routing decision
        """
        session_history = session_history or []
        player_data = player_data or {}

        # Step 1: Try rule-based routing
        rule_result = self.rule_router.route(user_message, player_data)

        if rule_result.matched and rule_result.confidence >= self.confidence_threshold:
            # High confidence rule match - use it directly
            print(f"✅ Rule Router: {rule_result.subagent_id or 'custom_analysis'} "
                  f"(confidence: {rule_result.confidence:.2f})")

            # Handle custom_analysis case (comparison queries)
            if rule_result.subagent_id is None:
                return HybridRoutingResult(
                    action="custom_analysis",
                    reason=rule_result.reason,
                    routing_method="rule",
                    confidence=rule_result.confidence
                )

            # Normal subagent routing
            return HybridRoutingResult(
                action="call_subagent",
                subagent_id=rule_result.subagent_id,
                params=rule_result.params or {},
                reason=rule_result.reason,
                routing_method="rule",
                confidence=rule_result.confidence
            )

        # Step 2: Fallback to LLM routing
        print(f"⚡ LLM Router: Rule confidence too low ({rule_result.confidence:.2f}), using ChatMasterAgent")

        llm_decision = self.llm_router.process_message(
            user_message=user_message,
            session_history=session_history,
            player_data=player_data
        )

        return HybridRoutingResult(
            action=llm_decision.action,
            subagent_id=llm_decision.subagent_id,
            params=llm_decision.params,
            content=llm_decision.content,
            options=llm_decision.options,
            reason=llm_decision.reason,
            routing_method="llm",
            confidence=0.8  # Assume LLM has reasonable confidence
        )

    def get_routing_stats(self) -> Dict[str, int]:
        """
        Get routing statistics (for monitoring)

        Returns:
            Dict with rule/llm routing counts
        """
        # TODO: Implement stats tracking
        return {
            "rule_routes": 0,
            "llm_routes": 0,
            "total_routes": 0
        }


# Singleton instance
_hybrid_router_instance = None


def get_hybrid_router(
    rule_confidence_threshold: float = 0.7,
    llm_model: str = "haiku"
) -> HybridRouter:
    """Get singleton HybridRouter instance"""
    global _hybrid_router_instance
    if _hybrid_router_instance is None:
        _hybrid_router_instance = HybridRouter(
            rule_confidence_threshold=rule_confidence_threshold,
            llm_model=llm_model
        )
    return _hybrid_router_instance

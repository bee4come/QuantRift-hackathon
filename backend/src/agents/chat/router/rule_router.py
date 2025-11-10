"""
Rule-based Router for Simple Query Patterns

Handles common query patterns with keyword matching before falling back to LLM.
This improves response time and reduces LLM API costs for obvious intents.
"""

import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass


@dataclass
class RuleMatch:
    """Result of rule-based routing"""
    matched: bool
    subagent_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    reason: str = ""


class RuleRouter:
    """
    Rule-based router using keyword patterns

    Matches common query patterns to appropriate sub-agents without LLM call.
    Falls back to LLM router if no rule matches with high confidence.
    """

    def __init__(self):
        """Initialize rule router with keyword patterns"""

        # Role keywords mapping (Chinese + English)
        self.role_keywords = {
            "TOP": [
                r"(top|上单|上路|toplane)",
                r"(top\s*lane|baron.*lane|大龙.*lane)",
            ],
            "JUNGLE": [
                r"\b(jungle|jg|打野|野区|jungler)\b",
            ],
            "MID": [
                r"\b(mid|中单|中路|midlane)\b",
            ],
            "ADC": [
                r"\b(adc|ad|下路|bot\s*lane|底路|射手|marksman)\b",
            ],
            "SUPPORT": [
                r"\b(support|sup|辅助|辅助位)\b",
            ]
        }

        # Agent-specific keywords (Chinese + English)
        self.agent_keywords = {
            "weakness-analysis": [
                r"(weakness|弱点|问题|缺点|不足|improve|提升|改进)",
                r"(what\s*(is|are)?\s*wrong|哪里不好|哪里差)",
                r"(need\s*to\s*improve|需要提升)",
                r"(分析.*弱点|帮我.*分析)",
                r"(analyze.*performance|recent.*performance|分析.*表现)",
                r"(how.*doing|how.*play|表现.*如何|打得.*怎么样)",
                r"(最近.*玩|最近.*表现|最近.*怎么样)",
                r"(我.*玩.*怎么样|玩得.*怎么样)",
            ],
            "annual-summary": [
                r"\b(season|annual|year|赛季|全年|年度|overall|总结|summary)\b",
                r"(this\s*season|本赛季)",
                r"(year.*review|年度.*回顾)",
            ],
            "champion-recommendation": [
                r"(recommend|suggest|推荐|建议|英雄|champion|hero|什么英雄|which\s*champ)",
                r"(what.*play|玩什么|选什么)",
                r"(best.*for\s*me|适合我)",
                r"(推荐.*英雄|适合.*英雄)",
            ],
            "version-trends": [
                r"\b(patch|version|版本|meta|趋势|trend)\b",
                r"(across.*patch|跨版本|不同版本)",
                r"(patch.*compare|版本对比)",
            ],
            "champion-mastery": [
                r"\b(mastery|精通|掌握|专精|specific.*champion|某个英雄)\b",
                r"(how.*with.*\w+)",  # "How am I with Yasuo?"
                r"(玩.*[A-Z]\w+.*怎么样|[A-Z]\w+.*玩.*怎么样)",  # Must mention champion name (capitalized)
            ],
            "timeline-deep-dive": [
                r"\b(match|game|对局|比赛|specific.*game|某场|replay|复盘)\b",
                r"(what.*happen|发生了什么)",
                r"(game\s*\d+|第.*场)",
            ],
            "friend-comparison": [
                r"\b(compare.*with|vs|versus|对比.*玩家|compare.*friend|和.*比)\b",
                r"(me\s*vs|我\s*vs)",
                r"(better.*than|比.*强|比.*好)",
            ],
            "build-simulator": [
                r"\b(build|出装|装备|item|物品|equipment)\b",
                r"(what.*build|出什么|买什么)",
                r"(item.*order|出装顺序)",
            ]
        }

        # Comparison keywords (trigger custom_analysis)
        self.comparison_keywords = [
            r"(compare|对比|比较).*\s*(vs|versus|和|与)",
            r"(last|recent|最近).*(vs|versus|和|与).*(previous|before|之前)",
            r"\d+\s*天.*(vs|versus|和|与)\s*\d+\s*天",
            r"\d+\s*days?.*(vs|versus|和|与)\s*\d+\s*days?",
            r"(最近|last)\s*\d+.*天.*(之前|previous)\s*\d+.*天",
            r"weekend.*weekday",
            r"(first|last)\s*\d+.*games?",
        ]

    def route(self, user_message: str, player_data: Optional[Dict[str, Any]] = None) -> RuleMatch:
        """
        Route user query using keyword matching rules

        Args:
            user_message: User's query text
            player_data: Optional player context for additional matching

        Returns:
            RuleMatch with routing decision
        """
        message_lower = user_message.lower()

        # Check for comparison patterns first (custom_analysis)
        if self._is_comparison_query(message_lower):
            return RuleMatch(
                matched=True,
                subagent_id=None,  # Custom analysis doesn't use subagent_id
                params={},
                confidence=0.9,
                reason="Detected comparison pattern requiring custom analysis"
            )

        # Check for role-specific queries
        role_match = self._match_role(message_lower)
        if role_match:
            role, confidence = role_match
            # If role detected, likely role-specialization agent
            if confidence > 0.7:
                return RuleMatch(
                    matched=True,
                    subagent_id="role-specialization",
                    params={"role": role},
                    confidence=confidence,
                    reason=f"Detected role-specific query for {role}"
                )

        # Check for agent-specific keywords
        agent_match = self._match_agent(message_lower)
        if agent_match:
            agent_id, confidence = agent_match
            if confidence > 0.6:
                return RuleMatch(
                    matched=True,
                    subagent_id=agent_id,
                    params={},
                    confidence=confidence,
                    reason=f"Matched agent-specific keywords for {agent_id}"
                )

        # No strong rule match - fallback to LLM
        return RuleMatch(
            matched=False,
            confidence=0.0,
            reason="No rule pattern matched, fallback to LLM router"
        )

    def _is_comparison_query(self, message: str) -> bool:
        """Check if query is a comparison request"""
        for pattern in self.comparison_keywords:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    def _match_role(self, message: str) -> Optional[Tuple[str, float]]:
        """
        Match role keywords in message

        Returns:
            (role, confidence) or None
        """
        for role, patterns in self.role_keywords.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    # Higher confidence if query explicitly asks about role
                    confidence = 0.9 if any(kw in message for kw in ["analyze", "分析", "how", "怎么样"]) else 0.7
                    return (role, confidence)
        return None

    def _match_agent(self, message: str) -> Optional[Tuple[str, float]]:
        """
        Match agent-specific keywords

        Returns:
            (agent_id, confidence) or None
        """
        best_match = None
        best_score = 0.0

        for agent_id, patterns in self.agent_keywords.items():
            match_count = 0
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    match_count += 1

            if match_count > 0:
                # Confidence based on number of matched patterns
                confidence = min(0.6 + (match_count * 0.1), 0.95)
                if confidence > best_score:
                    best_score = confidence
                    best_match = (agent_id, confidence)

        return best_match


# Singleton instance
_rule_router_instance = None


def get_rule_router() -> RuleRouter:
    """Get singleton RuleRouter instance"""
    global _rule_router_instance
    if _rule_router_instance is None:
        _rule_router_instance = RuleRouter()
    return _rule_router_instance

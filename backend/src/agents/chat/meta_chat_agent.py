"""
Meta Chat Agent - Routes user queries to appropriate agents or custom analysis

Architecture:
1. Understands natural language user queries
2. Decides routing strategy: use existing agent, combine multiple agents, or custom analysis
3. Coordinates execution and returns unified response
"""

import json
from typing import Dict, Any, List, Optional
from src.agents.shared.bedrock_adapter import BedrockLLM


class MetaChatAgent:
    """
    Meta-level chat agent that routes user queries
    """

    # Available agent endpoints with descriptions
    AVAILABLE_AGENTS = [
        {
            "id": "annual-summary",
            "name": "Annual Summary",
            "description": "Season overview and statistics across all patches",
            "keywords": ["season", "annual", "year", "overall", "summary", "全赛季", "年度", "总结"]
        },
        {
            "id": "weakness-analysis",
            "name": "Performance Insights",
            "description": "Identify weaknesses, low winrate champions, and improvement areas",
            "keywords": ["weakness", "problem", "bad", "lose", "improve", "弱点", "问题", "提升"]
        },
        {
            "id": "champion-recommendation",
            "name": "Champion Recommendation",
            "description": "Recommend best champions based on playstyle and winrate",
            "keywords": ["recommend", "suggest", "champion", "hero", "推荐", "英雄", "选什么"]
        },
        {
            "id": "role-specialization",
            "name": "Role Specialization",
            "description": "Role-specific performance analysis (top, jungle, mid, adc, support)",
            "keywords": ["role", "position", "top", "jungle", "mid", "adc", "support", "位置", "上单", "打野", "中单", "下路", "辅助"]
        },
        {
            "id": "champion-mastery",
            "name": "Champion Mastery",
            "description": "Deep dive into specific champion performance",
            "keywords": ["mastery", "champion specific", "精通", "掌握"]
        },
        {
            "id": "timeline-deep-dive",
            "name": "Match Analysis",
            "description": "Timeline analysis for specific matches",
            "keywords": ["match", "game", "timeline", "replay", "比赛", "对局", "复盘"]
        },
        {
            "id": "version-trends",
            "name": "Version Trends",
            "description": "Cross-patch performance trends",
            "keywords": ["patch", "version", "meta", "trend", "版本", "补丁", "趋势"]
        },
        {
            "id": "friend-comparison",
            "name": "Comparison",
            "description": "Compare with friends or rank tier",
            "keywords": ["compare", "vs", "versus", "friend", "rank", "对比", "比较", "朋友"]
        },
        {
            "id": "build-simulator",
            "name": "Build Simulator",
            "description": "Analyze and optimize item builds",
            "keywords": ["build", "item", "equipment", "出装", "装备", "物品"]
        }
    ]

    def __init__(self, model: str = "haiku"):
        self.llm = BedrockLLM(model=model)

    def route(self, user_message: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Analyze user message and determine routing strategy

        Args:
            user_message: User's natural language query
            chat_history: Optional conversation history

        Returns:
            {
                "strategy": "use_existing" | "combine_multiple" | "custom_analysis",
                "endpoints": ["agent-id1", "agent-id2", ...],
                "execution_mode": "sequential" | "parallel",
                "reason": "explanation",
                "custom_plan_needed": bool
            }
        """
        # Build prompt
        agents_list = "\n".join([
            f"- **{a['id']}**: {a['description']}"
            for a in self.AVAILABLE_AGENTS
        ])

        history_context = ""
        if chat_history:
            history_context = "\n\n**Conversation History**:\n" + "\n".join([
                f"- {msg['role']}: {msg['content'][:100]}"
                for msg in chat_history[-3:]  # Last 3 messages
            ])

        prompt = f"""You are an AI routing assistant for a League of Legends analysis system.

{history_context}

**User Query**: {user_message}

**Available Agent Endpoints**:
{agents_list}

**Task**: Determine the best routing strategy to answer the user's query.

**Output JSON** (no additional text):
{{
  "strategy": "use_existing" | "combine_multiple" | "custom_analysis",
  "endpoints": ["agent-id"],
  "execution_mode": "sequential" | "parallel",
  "reason": "brief explanation",
  "custom_plan_needed": false
}}

**Rules**:
- Use "use_existing" if ONE agent can fully answer the query
- Use "combine_multiple" if MULTIPLE agents are needed (e.g., "analyze weaknesses and recommend champions")
- Use "custom_analysis" ONLY if existing agents cannot satisfy the request (e.g., "compare weekend vs weekday performance", "first 30 games vs last 30 games")
- Prefer existing agents over custom analysis when possible
"""

        try:
            result = self.llm.generate_sync(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3
            )

            # Parse JSON from response
            response_text = result["text"].strip()

            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            route_decision = json.loads(response_text)

            # Validate and set defaults
            if "strategy" not in route_decision:
                route_decision["strategy"] = "use_existing"
            if "endpoints" not in route_decision:
                route_decision["endpoints"] = []
            if "execution_mode" not in route_decision:
                route_decision["execution_mode"] = "sequential"
            if "reason" not in route_decision:
                route_decision["reason"] = "Default routing"
            if "custom_plan_needed" not in route_decision:
                route_decision["custom_plan_needed"] = route_decision["strategy"] == "custom_analysis"

            return route_decision

        except Exception as e:
            print(f"Error in routing: {e}")
            # Fallback: use weakness-analysis as default
            return {
                "strategy": "use_existing",
                "endpoints": ["weakness-analysis"],
                "execution_mode": "sequential",
                "reason": "Fallback to default agent due to routing error",
                "custom_plan_needed": False
            }

    def get_agent_description(self, agent_id: str) -> Optional[str]:
        """Get description of an agent by ID"""
        for agent in self.AVAILABLE_AGENTS:
            if agent["id"] == agent_id:
                return agent["description"]
        return None

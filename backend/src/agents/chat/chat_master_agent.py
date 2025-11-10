"""
ChatMasterAgent - LLM-based orchestrator for multi-agent chat system

Routes user queries to appropriate sub-agents, handles multi-turn conversations,
and performs custom analysis for non-standard requests.
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from src.agents.shared.bedrock_adapter import BedrockLLM


# Sub-agent tool schemas
ANALYSIS_SUBAGENTS = {
    "weakness-analysis": {
        "name": "Performance Insights",
        "description": "Identifies weaknesses, low winrate champions, and improvement areas across recent matches",
        "params": {},
        "keywords": ["weakness", "problem", "improve", "bad performance", "what's wrong", "弱点", "问题", "提升"]
    },

    "annual-summary": {
        "name": "Season Summary",
        "description": "Complete season overview with statistics, milestones, and performance trends across all patches",
        "params": {},
        "keywords": ["season", "annual", "summary", "overall", "year", "全赛季", "年度", "总结"]
    },

    "champion-recommendation": {
        "name": "Champion Suggestions",
        "description": "Recommends best champions to play based on playstyle, meta, and historical performance",
        "params": {},
        "keywords": ["recommend", "suggest", "which champion", "what to play", "推荐", "英雄", "选什么"]
    },

    "version-trends": {
        "name": "Patch Trends",
        "description": "Cross-patch performance trend analysis showing how performance changes across game versions",
        "params": {},
        "keywords": ["patch", "version", "trend", "meta", "across patches", "版本", "补丁", "趋势"]
    },

    "role-specialization": {
        "name": "Position Analysis",
        "description": "Deep analysis for specific role performance (TOP/JUNGLE/MID/ADC/SUPPORT)",
        "params": {
            "role": {
                "type": "enum",
                "values": ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"],
                "required": True,
                "extraction_hints": "Extract from: top, jungle, mid, adc, support, bot, 上单, 打野, 中单, 下路, 辅助"
            }
        },
        "keywords": ["role", "position", "lane", "top", "jungle", "mid", "adc", "support", "位置"]
    },

    "champion-mastery": {
        "name": "Champion Mastery",
        "description": "Deep dive into specific champion's performance, build patterns, and mastery progression",
        "params": {
            "champion_id": {
                "type": "int",
                "required": True,
                "extraction_hints": "Extract champion ID from champion name or ask user"
            }
        },
        "keywords": ["champion", "mastery", "specific hero", "精通", "掌握"]
    },

    "timeline-deep-dive": {
        "name": "Match Analysis",
        "description": "Timeline analysis for specific match with minute-by-minute breakdown",
        "params": {
            "match_id": {
                "type": "str",
                "required": True,
                "extraction_hints": "Extract match ID from match list or ask user which match to analyze"
            }
        },
        "keywords": ["match", "game", "timeline", "replay", "specific game", "比赛", "对局", "复盘"]
    },

    "friend-comparison": {
        "name": "Player Comparison",
        "description": "Compare performance with another player or friend",
        "params": {
            "friend_name": {
                "type": "str",
                "required": True,
                "extraction_hints": "Extract player name with tag (name#tag) or ask user"
            }
        },
        "keywords": ["compare", "vs", "versus", "friend", "other player", "对比", "比较", "朋友"]
    },

    "build-simulator": {
        "name": "Build Optimizer",
        "description": "Analyze and optimize item builds for specific champion",
        "params": {
            "champion_id": {
                "type": "int",
                "required": True,
                "extraction_hints": "Extract champion ID from champion name or ask user"
            }
        },
        "keywords": ["build", "item", "equipment", "出装", "装备", "物品"]
    }
}


@dataclass
class AgentDecision:
    """Decision made by ChatMasterAgent"""
    action: str  # "answer_directly", "ask_user", "call_subagent", "custom_analysis"
    content: Optional[str] = None  # For answer_directly and ask_user
    subagent_id: Optional[str] = None  # For call_subagent
    params: Optional[Dict[str, Any]] = None  # For call_subagent
    options: Optional[List[str]] = None  # For ask_user
    reason: Optional[str] = None  # Explanation of decision


class ChatMasterAgent:
    """
    LLM-based orchestrator that manages conversations and delegates to sub-agents

    Architecture:
    1. Process user message with conversation context
    2. Use LLM to decide next action (answer, ask, call subagent, custom analysis)
    3. Extract parameters from natural language if needed
    4. Execute decision and return response
    """

    def __init__(self, model: str = "haiku"):
        """
        Initialize ChatMasterAgent

        Args:
            model: LLM model to use (default: haiku for cost efficiency)
        """
        self.llm = BedrockLLM(model=model)
        self.subagents = ANALYSIS_SUBAGENTS

    def process_message(
        self,
        user_message: str,
        session_history: List[Dict[str, str]],
        player_data: Dict[str, Any]
    ) -> AgentDecision:
        """
        Process user message and decide next action

        Args:
            user_message: User's current message
            session_history: Conversation history (list of {role, content} dicts)
            player_data: Player statistics and context for decision making

        Returns:
            AgentDecision with action type and parameters
        """
        # Build decision prompt
        prompt = self._build_decision_prompt(
            user_message=user_message,
            history=session_history,
            player_data=player_data
        )

        # LLM decision
        result = self.llm.generate_sync(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.3
        )

        # Parse and validate decision
        decision = self._parse_decision(result["text"])

        return decision

    def _build_decision_prompt(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        player_data: Dict[str, Any]
    ) -> str:
        """
        Build LLM prompt for decision making

        Includes:
        - Conversation history
        - Available sub-agents with descriptions
        - Player context (total games, recent performance, etc.)
        - Decision rules
        """
        # Format sub-agent list
        subagents_list = []
        for agent_id, schema in self.subagents.items():
            params_desc = ""
            if schema["params"]:
                param_names = ", ".join(schema["params"].keys())
                params_desc = f" (requires: {param_names})"
            subagents_list.append(f"- **{agent_id}**: {schema['description']}{params_desc}")

        subagents_text = "\n".join(subagents_list)

        # Format conversation history
        history_text = ""
        if history:
            history_lines = []
            for msg in history[-5:]:  # Last 5 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")[:150]  # Truncate long messages
                history_lines.append(f"- {role}: {content}")
            history_text = "\n\n**Recent Conversation**:\n" + "\n".join(history_lines)

        # Format player context
        player_context = f"""
**Player Context**:
- Total games: {player_data.get('total_games', 'unknown')}
- Recent matches available: {player_data.get('recent_match_count', 0)}
- Patches played: {', '.join(player_data.get('patches', []))}
"""

        # Build full prompt
        prompt = f"""You are an AI assistant for a League of Legends analytics system. Your job is to understand user queries and decide the best action.

{history_text}

**Current User Message**: {user_message}

{player_context}

**Available Sub-Agents**:
{subagents_text}

**Your Task**: Analyze the user's message and decide ONE action to take.

**Action Types**:

1. **answer_directly**: Use this for simple questions that don't need sub-agent analysis
   - Examples: "How many games?", "What patches?", "Show my recent matches"
   - Return direct answer from player context

2. **ask_user**: Use this when you need more information or parameters
   - Examples: User says "analyze my role" but doesn't specify which role
   - Return clarification question with options

3. **call_subagent**: Use this when you have a clear analysis request and all required parameters
   - Examples: "analyze my weaknesses", "show season summary", "analyze top lane"
   - Return sub-agent ID and extracted parameters

4. **custom_analysis**: Use this ONLY for comparative analysis requests that existing sub-agents cannot handle
   - Use this for: Time period comparisons, role comparisons, champion subset comparisons, data quality comparisons
   - Examples:
     * "compare last 30 days vs previous 30 days"
     * "compare my ADC games vs Support games"
     * "compare weekend vs weekday performance"
     * "first 50 games vs last 50 games"
     * "compare my tank champions vs assassin champions"
     * "compare high quality games (CONFIDENT) vs all games"
   - Return custom_analysis action (no need to provide params - will be parsed automatically)

**Response Format** (JSON only, no additional text):
{{
  "action": "answer_directly" | "ask_user" | "call_subagent" | "custom_analysis",
  "content": "your answer or question (for answer_directly/ask_user)",
  "subagent_id": "agent-id (for call_subagent)",
  "params": {{"param": "value"}} (for call_subagent),
  "options": ["option1", "option2"] (for ask_user, optional),
  "reason": "brief explanation of your decision"
}}

**Rules**:
1. **Always prefer existing sub-agents over custom analysis** - custom_analysis is only for comparative queries
2. Extract parameters from user message when possible (e.g., "top lane" → role=TOP)
3. If user says "analyze" without context, look at conversation history
4. For simple data questions, use answer_directly with player_data
5. **custom_analysis decision criteria**:
   - User explicitly mentions "compare", "vs", "versus"
   - Query involves TWO distinct groups (time periods, roles, champion sets)
   - No existing sub-agent can handle the comparison
6. Be concise and helpful

**Important Parameter Extraction**:
- Role: top/jungle/mid/adc/support/bot → TOP/JUNGLE/MID/ADC/SUPPORT
- Champion names: convert to champion_id (or ask if unsure)
- Match references: "match 3", "last game", "recent game" → extract match_id from context

Now analyze the user's message and respond with JSON:"""

        return prompt

    def _parse_decision(self, llm_output: str) -> AgentDecision:
        """
        Parse and validate LLM decision JSON

        Args:
            llm_output: LLM response text

        Returns:
            AgentDecision object

        Raises:
            ValueError: If JSON parsing fails or required fields missing
        """
        try:
            # Extract JSON from markdown code blocks if present
            response_text = llm_output.strip()

            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            # Parse JSON
            decision_dict = json.loads(response_text)

            # Validate action type
            action = decision_dict.get("action")
            if action not in ["answer_directly", "ask_user", "call_subagent", "custom_analysis"]:
                raise ValueError(f"Invalid action type: {action}")

            # Create AgentDecision
            decision = AgentDecision(
                action=action,
                content=decision_dict.get("content"),
                subagent_id=decision_dict.get("subagent_id"),
                params=decision_dict.get("params", {}),
                options=decision_dict.get("options"),
                reason=decision_dict.get("reason", "No reason provided")
            )

            # Validate required fields per action type
            if action == "call_subagent" and not decision.subagent_id:
                raise ValueError("call_subagent requires subagent_id")

            if action in ["answer_directly", "ask_user"] and not decision.content:
                raise ValueError(f"{action} requires content field")

            return decision

        except json.JSONDecodeError as e:
            # Fallback: default to weakness analysis
            print(f"⚠️ ChatMasterAgent JSON parse error: {e}")
            return AgentDecision(
                action="call_subagent",
                subagent_id="weakness-analysis",
                params={},
                reason="Fallback due to parsing error"
            )
        except Exception as e:
            print(f"⚠️ ChatMasterAgent decision error: {e}")
            return AgentDecision(
                action="answer_directly",
                content=f"Sorry, I encountered an error processing your request: {str(e)}",
                reason="Error fallback"
            )

    def get_subagent_schema(self, subagent_id: str) -> Optional[Dict[str, Any]]:
        """Get sub-agent schema by ID"""
        return self.subagents.get(subagent_id)

    def list_subagents(self) -> List[str]:
        """List all available sub-agent IDs"""
        return list(self.subagents.keys())

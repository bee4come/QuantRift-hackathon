"""
Router Stream - SSE streaming wrapper for hybrid routing system

Provides real-time streaming of routing decisions and agent execution.
"""

import json
from typing import AsyncGenerator, Dict, Any, List, Optional, Generator
from pathlib import Path
from .hybrid_router import HybridRouter, HybridRoutingResult
from src.agents.player_analysis.weakness_analysis.agent import WeaknessAnalysisAgent
from src.agents.player_analysis.annual_summary.agent import AnnualSummaryAgent
from src.agents.player_analysis.champion_recommendation.agent import ChampionRecommendationAgent
from src.agents.player_analysis.role_specialization.agent import RoleSpecializationAgent
from src.agents.player_analysis.multi_version.agent import MultiVersionAgent
from src.agents.player_analysis.champion_mastery.agent import ChampionMasteryAgent
from src.agents.player_analysis.timeline_deep_dive.agent import TimelineDeepDiveAgent
from src.agents.player_analysis.friend_comparison.agent import FriendComparisonAgent
from src.agents.player_analysis.build_simulator.agent import BuildSimulatorAgent


class RouterStreamGenerator:
    """
    SSE streaming generator for hybrid routing system

    Streams:
    1. Routing decision process
    2. Agent execution status
    3. Agent output in real-time
    """

    def __init__(self, router: HybridRouter):
        """
        Initialize stream generator

        Args:
            router: HybridRouter instance
        """
        self.router = router

        # Agent registry mapping agent_id -> agent class
        self.agent_registry = {
            'weakness-analysis': WeaknessAnalysisAgent,
            'annual-summary': AnnualSummaryAgent,
            'champion-recommendation': ChampionRecommendationAgent,
            'role-specialization': RoleSpecializationAgent,
            'multi-version': MultiVersionAgent,
            'champion-mastery': ChampionMasteryAgent,
            'timeline-deep-dive': TimelineDeepDiveAgent,
            'friend-comparison': FriendComparisonAgent,
            'build-simulator': BuildSimulatorAgent,
        }

    def stream_route_and_execute(
        self,
        user_message: str,
        puuid: str,
        packs_dir: Path,
        session_history: Optional[List[Dict[str, str]]] = None,
        player_data: Optional[Dict[str, Any]] = None,
        model: str = "haiku",
        **agent_kwargs
    ) -> Generator[str, None, None]:
        """
        Stream routing decision and agent execution

        Args:
            user_message: User's natural language query
            puuid: Player PUUID
            packs_dir: Path to player packs directory
            session_history: Conversation history
            player_data: Player context data
            model: LLM model to use
            **agent_kwargs: Additional parameters for specific agents

        Yields:
            SSE messages in format: "data: {JSON}\\n\\n"

        Message types:
            - {"type": "routing_start", "query": "..."} - Routing started
            - {"type": "routing_method", "method": "rule|llm"} - Which router is being used
            - {"type": "routing_decision", "action": "...", "subagent": "...", "params": {...}} - Decision made
            - {"type": "agent_start", "agent": "..."} - Agent execution started
            - {"type": "thinking_start"} - Agent thinking started
            - {"type": "thinking", "content": "..."} - Agent thinking content
            - {"type": "thinking_end"} - Agent thinking ended
            - {"type": "chunk", "content": "..."} - Agent output chunk
            - {"type": "complete", "detailed": "..."} - Execution complete
            - {"type": "error", "error": "..."} - Error occurred
        """
        try:
            # Step 1: Stream routing start
            yield f"data: {json.dumps({'type': 'routing_start', 'query': user_message})}\n\n"

            # Step 2: Route query
            print(f"🧭 Routing query: {user_message[:50]}...")
            routing_result = self.router.route(
                user_message=user_message,
                session_history=session_history or [],
                player_data=player_data or {}
            )

            # Step 3: Stream routing method
            yield f"data: {json.dumps({'type': 'routing_method', 'method': routing_result.routing_method, 'confidence': routing_result.confidence})}\n\n"

            # Step 4: Stream routing decision
            decision_data = {
                'type': 'routing_decision',
                'action': routing_result.action,
                'subagent': routing_result.subagent_id,
                'params': routing_result.params or {},
                'reason': routing_result.reason
            }
            yield f"data: {json.dumps(decision_data)}\n\n"

            print(f"✅ Routing decision: action={routing_result.action}, subagent={routing_result.subagent_id}")

            # Step 5: Handle different action types
            if routing_result.action == 'answer_directly':
                # Direct answer without agent execution
                yield f"data: {json.dumps({'type': 'complete', 'detailed': routing_result.content})}\n\n"
                return

            elif routing_result.action == 'ask_user':
                # Ask user for clarification
                yield f"data: {json.dumps({'type': 'ask_user', 'content': routing_result.content, 'options': routing_result.options})}\n\n"
                return

            elif routing_result.action == 'custom_analysis':
                # Custom analysis (future implementation)
                yield f"data: {json.dumps({'type': 'complete', 'detailed': 'Custom comparative analysis is under development. Please use specific agent queries for now.'})}\n\n"
                return

            elif routing_result.action == 'call_subagent':
                # Execute sub-agent with streaming
                if not routing_result.subagent_id:
                    yield f"data: {json.dumps({'type': 'error', 'error': 'No subagent specified'})}\n\n"
                    return

                # Get agent class
                agent_class = self.agent_registry.get(routing_result.subagent_id)
                if not agent_class:
                    yield f"data: {json.dumps({'type': 'error', 'error': f'Unknown agent: {routing_result.subagent_id}'})}\n\n"
                    return

                # Stream agent execution
                yield f"data: {json.dumps({'type': 'agent_start', 'agent': routing_result.subagent_id})}\n\n"

                # Initialize agent
                agent = agent_class(model=model)

                # Prepare agent parameters
                agent_params = {
                    'packs_dir': str(packs_dir),
                    'recent_count': agent_kwargs.get('recent_count', 5),
                }

                # Add routing decision params
                if routing_result.params:
                    agent_params.update(routing_result.params)

                # Add additional kwargs for specific agents
                if routing_result.subagent_id == 'timeline-deep-dive':
                    agent_params['match_id'] = agent_kwargs.get('match_id', routing_result.params.get('match_id'))
                elif routing_result.subagent_id == 'champion-mastery':
                    agent_params['champion_id'] = agent_kwargs.get('champion_id', routing_result.params.get('champion_id'))
                elif routing_result.subagent_id == 'friend-comparison':
                    agent_params['friend_game_name'] = agent_kwargs.get('friend_game_name', routing_result.params.get('friend_name'))
                    agent_params['friend_tag_line'] = agent_kwargs.get('friend_tag_line')

                # Add optional time_range and queue_id filters
                if 'time_range' in agent_kwargs:
                    agent_params['time_range'] = agent_kwargs['time_range']
                if 'queue_id' in agent_kwargs:
                    agent_params['queue_id'] = agent_kwargs['queue_id']

                print(f"🤖 Executing agent {routing_result.subagent_id} with params: {agent_params}")

                # Stream agent output
                for message in agent.run_stream(**agent_params):
                    yield message

            else:
                yield f"data: {json.dumps({'type': 'error', 'error': f'Unknown action: {routing_result.action}'})}\n\n"

        except Exception as e:
            import traceback
            error_msg = f"Router stream error: {str(e)}"
            print(f"❌ {error_msg}\n{traceback.format_exc()}")
            yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"


def stream_chat_with_routing(
    user_message: str,
    puuid: str,
    packs_dir: Path,
    session_history: Optional[List[Dict[str, str]]] = None,
    player_data: Optional[Dict[str, Any]] = None,
    model: str = "haiku",
    rule_confidence_threshold: float = 0.7,
    **agent_kwargs
) -> Generator[str, None, None]:
    """
    Convenience function to stream chat with routing

    Args:
        user_message: User's query
        puuid: Player PUUID
        packs_dir: Player packs directory path
        session_history: Conversation history
        player_data: Player context
        model: LLM model
        rule_confidence_threshold: Confidence threshold for rule routing
        **agent_kwargs: Additional agent parameters

    Yields:
        SSE formatted messages
    """
    from .hybrid_router import get_hybrid_router

    # Get router instance
    router = get_hybrid_router(
        rule_confidence_threshold=rule_confidence_threshold,
        llm_model=model
    )

    # Create stream generator
    stream_gen = RouterStreamGenerator(router)

    # Stream routing and execution
    for message in stream_gen.stream_route_and_execute(
        user_message=user_message,
        puuid=puuid,
        packs_dir=packs_dir,
        session_history=session_history,
        player_data=player_data,
        model=model,
        **agent_kwargs
    ):
        yield message

"""WeaknessAnalysisAgent - Weakness Diagnosis Agent"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from src.agents.shared.config import get_config
from src.agents.shared.bedrock_adapter import BedrockLLM
from src.agents.shared.insight_detector import InsightDetector  # Phase 1.5: Automated Insights
from .tools import load_recent_data, identify_weaknesses, format_analysis_for_prompt
from .prompts import build_narrative_prompt


class WeaknessAnalysisAgent:
    """Weakness Diagnosis Agent - Identifies areas where players need improvement

    ADK-compliant agent with support for:
    - Synchronous execution (run)
    - SSE streaming (run_stream)
    - Agent card and chat interface
    """

    def __init__(self, model: str = "haiku"):
        self.config = get_config()
        self.llm = BedrockLLM(model=model)
        self.insight_detector = InsightDetector()  # Phase 1.5: Automated Insights

    def run(
        self,
        packs_dir: str,
        recent_count: int = 5,
        output_dir: Optional[str] = None,
        context: Optional[Any] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Run weakness diagnosis analysis

        Args:
            packs_dir: Player-Pack directory path
            recent_count: Analyze recent N patches (default 5)
            output_dir: Output directory (optional)
            context: AgentContext instance (optional, for data sharing)
        """
        print(f"\n{'='*60}\n🔍 Weakness Diagnosis Analysis (Recent {recent_count} patches)\n{'='*60}\n")

        # Try to get cached data from context
        if context and context.has_shared_data("all_packs"):
            print("✅ Using AgentContext cached data (saving load time)")
            all_packs = context.get_shared_data("all_packs")

            # all_packs is a list, need to convert to recent N patches as dict
            # Sort by patch and take recent N
            sorted_packs = sorted(all_packs, key=lambda p: p.get("patch", ""))
            recent_packs = sorted_packs[-recent_count:] if len(sorted_packs) >= recent_count else sorted_packs
            # Convert to dict format (tools expect dict)
            recent_data = {pack["patch"]: pack for pack in recent_packs}

            print(f"   Retrieved {len(recent_data)} recent patches from cache")
        else:
            # Independent loading
            print("📦 Loading data independently...")
            recent_data = load_recent_data(packs_dir, recent_count)

        weaknesses = identify_weaknesses(recent_data)

        print(f"✅ Diagnosis complete: Found {len(weaknesses['low_winrate_champions'])} low WR champions, "
              f"{len(weaknesses['weak_roles'])} weak roles")

        # Phase 1.5: Automated insight detection
        print("\n🔍 Running automated insight detection...")
        insights = self.insight_detector.detect_insights(weaknesses)
        print(f"✅ Detected {len(insights)} automated insights")

        # Add insights to weaknesses data
        weaknesses['automated_insights'] = [insight.to_dict() for insight in insights]
        weaknesses['insight_summary'] = self.insight_detector.generate_summary(insights)

        formatted_data = format_analysis_for_prompt(weaknesses)
        prompts = build_narrative_prompt(weaknesses, formatted_data)

        print(f"\n🤖 Generating diagnosis report (using {self.llm.model_id})...")
        import sys
        sys.stdout.flush()

        result = self.llm.generate_sync(
            prompt=prompts["user"],
            system=prompts["system"],
            max_tokens=12000
        )

        print(f"🔍 DEBUG: LLM returned, result type: {type(result)}")
        sys.stdout.flush()

        print(f"🔍 DEBUG: Result keys: {list(result.keys()) if isinstance(result, dict) else 'NOT_A_DICT'}")
        sys.stdout.flush()

        print(f"🔍 DEBUG: About to extract text...")
        sys.stdout.flush()

        # Use .get() to avoid potential blocking
        report_text = result.get("text", "") if isinstance(result, dict) else str(result)

        print(f"✅ Report generation complete ({len(report_text)} characters)")
        sys.stdout.flush()

        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            with open(output_path / "weakness_analysis.json", 'w', encoding='utf-8') as f:
                json.dump(weaknesses, f, ensure_ascii=False, indent=2)
            with open(output_path / "weakness_report.md", 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n💾 Output saved to {output_dir}")

        return weaknesses, report_text

    def run_stream(
        self,
        packs_dir: str,
        recent_count: int = 5,
        time_range: Optional[str] = None,
        queue_id: Optional[int] = None
    ):
        """
        Run weakness diagnosis analysis with SSE streaming output

        Unified method for both agent card and chat interfaces

        Args:
            packs_dir: Player-Pack directory path
            recent_count: Analyze recent N patches (default 5)
            time_range: Time range filter (e.g., "2024-01-01", "past-365", None)
            queue_id: Queue ID filter (420=Solo/Duo, 440=Flex, 400=Normal, None=All)

        Yields:
            SSE formatted messages for streaming
        """
        from src.agents.shared.stream_helper import stream_agent_with_thinking

        # Load data
        recent_data = load_recent_data(packs_dir, recent_count, time_range=time_range, queue_id=queue_id)

        # Check if no data found
        if len(recent_data) == 0:
            if queue_id == 400:
                error_msg = "No Normal game data found. Please play some Normal games first."
            elif queue_id == 440:
                error_msg = "No Ranked Flex data found. Please play some Ranked Flex games first."
            elif queue_id == 420:
                error_msg = "No Ranked Solo/Duo data found. Please play some Ranked Solo/Duo games first."
            elif time_range == "past-365":
                error_msg = "No data found for Past 365 Days"
            else:
                error_msg = "No data found"
            yield f"data: {{\"error\": \"{error_msg}\"}}\n\n"
            return

        # Identify weaknesses
        weaknesses = identify_weaknesses(recent_data)

        # Automated insight detection
        insights = self.insight_detector.detect_insights(weaknesses)
        weaknesses['automated_insights'] = [insight.to_dict() for insight in insights]
        weaknesses['insight_summary'] = self.insight_detector.generate_summary(insights)

        # Format and build prompts
        formatted_data = format_analysis_for_prompt(weaknesses)
        prompts = build_narrative_prompt(weaknesses, formatted_data)

        # Stream response
        for message in stream_agent_with_thinking(
            prompt=prompts['user'],
            system_prompt=prompts['system'],
            model=self.llm.model_id,
            max_tokens=8000,
            enable_thinking=False
        ):
            yield message

"""ProgressTrackerAgent - Progress Tracking Agent"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from src.agents.shared.config import get_config
from src.agents.shared.bedrock_adapter import BedrockLLM
from .tools import load_recent_packs, analyze_progress, format_analysis_for_prompt
from .prompts import build_narrative_prompt


class ProgressTrackerAgent:
    """Progress Tracker Agent - Track player improvement trends over recent 10-20 patches"""

    def __init__(self, model: str = "haiku"):
        self.config = get_config()
        self.llm = BedrockLLM(model=model)

    def run(
        self,
        packs_dir: str,
        window_size: int = 10,
        output_dir: Optional[str] = None,
        context: Optional[Any] = None
    ) -> Tuple[Dict[str, Any], str]:
        """Run progress tracking analysis"""
        print(f"\n{'='*60}\n📈 Progress Tracking Analysis (Recent {window_size} patches)\n{'='*60}\n")

        # Try to get cached data from context
        if context and context.has_shared_data("all_packs"):
            print("✅ Using AgentContext cached data (saving load time)")
            all_packs = context.get_shared_data("all_packs")
            # all_packs is a list, slice and convert to dict format
            recent_packs_list = all_packs[-window_size:] if len(all_packs) >= window_size else all_packs
            # analyze_progress expects dict format
            recent_packs = {pack["patch"]: pack for pack in recent_packs_list}
            print(f"   Retrieved recent {len(recent_packs)} patches from cache")
        else:
            print("📦 Loading data independently...")
            recent_packs = load_recent_packs(packs_dir, window_size)

        analysis = analyze_progress(recent_packs)

        print(f"✅ Analysis complete: {analysis['trend']}, improvement magnitude {analysis['improvement']:+.1%}")

        formatted_data = format_analysis_for_prompt(analysis)
        prompts = build_narrative_prompt(analysis, formatted_data)

        print(f"\n🤖 Generating progress report (using {self.llm.model_id})...")
        result = self.llm.generate_sync(
            prompt=prompts["user"],
            system=prompts["system"],
            max_tokens=12000
        )
        report_text = result["text"]
        print(f"✅ Report generation complete ({len(report_text)} characters)")

        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            with open(output_path / "progress_analysis.json", 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)
            with open(output_path / "progress_report.md", 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n💾 Output saved to {output_dir}")

        return analysis, report_text

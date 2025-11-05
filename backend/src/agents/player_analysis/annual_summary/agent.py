"""
Annual Summary Agent - Annual Season Summary Analysis Agent

Generates comprehensive annual summary reports for entire season (40-50 patches)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import sys

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.shared import BedrockLLM, get_config
from src.agents.shared.data_auto_fetcher import DataAutoFetcher
from src.agents.shared.prompt_optimizer import PromptOptimizer
from .tools import (
    load_all_annual_packs,
    generate_comprehensive_annual_analysis,
    format_analysis_for_prompt
)
from .prompts import build_narrative_prompt


class AnnualSummaryAgent(DataAutoFetcher):
    """
    Annual Season Summary Agent (with Auto Data Fetching)

    Features:
    - Load entire season (40-50 patches) Player-Pack data
    - Generate time-segmented analysis (monthly/quarterly/three-period)
    - Extract annual highlights and achievements
    - Analyze version adaptation trends
    - Evaluate champion pool evolution
    - Generate 3000-5000 word comprehensive annual summary report

    Args:
        model: LLM model selection ("sonnet" or "haiku", recommend sonnet)

    New Feature - Auto Data Fetching:
        Now supports three usage modes:
        1. Provide packs_dir (traditional method)
        2. Provide player_id (auto-fetch from Riot API and process)
        3. Provide matches_dir (auto-convert to Pack format)
    """

    def __init__(self, model: str = "sonnet", use_optimized_prompts: bool = True):
        """
        Initialize Annual Summary Agent

        Args:
            model: LLM model selection (default "sonnet" for detailed reports)
            use_optimized_prompts: Whether to use optimized compact prompts (Phase 4 Token Optimization)
        """
        # Initialize DataAutoFetcher (provides auto-fetch capability)
        super().__init__()

        # Initialize Agent's own configuration
        self.config = get_config()
        self.llm = BedrockLLM(model=model)
        self.use_optimized_prompts = use_optimized_prompts

    def run(
        self,
        packs_dir: Optional[str] = None,
        player_id: Optional[str] = None,
        matches_dir: Optional[str] = None,
        region: str = 'na1',
        max_matches: int = 200,
        auto_fetch: bool = True,
        output_dir: Optional[str] = None,
        context: Optional[Any] = None
    ) -> tuple[Dict[str, Any], str]:
        """
        Run annual summary analysis (with auto data fetching)

        Args:
            packs_dir: Player-Pack directory path (traditional method)
            player_id: Player ID (format: "GameName#TAG"), will auto-fetch data
            matches_dir: Raw match directory, will auto-convert to Pack format
            region: Region (default na1)
            max_matches: Maximum matches to fetch (default 200)
            auto_fetch: Whether to auto-fetch (default True)
            output_dir: Output directory (optional, saves files if provided)
            context: AgentContext instance (optional, for data sharing)

        Returns:
            (analysis_data, report_text)
            - analysis_data: Complete analysis data package (JSON format)
            - report_text: Annual summary report (Markdown format, 3000-5000 words)

        Usage examples:
            # Method 1: Traditional (provide existing Pack directory)
            agent.run(packs_dir="data/packs/s1ne")

            # Method 2: Auto-fetch (only provide player ID)
            agent.run(player_id="S1NE#NA1", region="na1")

            # Method 3: Convert existing data (provide match directory)
            agent.run(matches_dir="data/matches/s1ne")
        """
        print("=" * 60)
        print("🎮 Annual Summary Agent - Annual Season Summary Analysis")
        print("=" * 60)

        # 🔥 NEW: Auto data processing - ensure data exists and get parameters
        packs_dir, player_params = self._ensure_data(
            player_id=player_id,
            packs_dir=packs_dir,
            matches_dir=matches_dir,
            required_format='packs',
            region=region,
            max_matches=max_matches,
            auto_fetch=auto_fetch
        )

        # Step 1: Load all Player-Pack data
        print(f"\n📦 Loading Player-Pack data: {packs_dir}")
        all_packs_dict = load_all_annual_packs(packs_dir)
        print(f"✅ Loading complete: {len(all_packs_dict)} patches")

        if len(all_packs_dict) == 0:
            raise ValueError(f"No Player-Pack files found: {packs_dir}")

        # Cache to context (if provided)
        # Note: Cache as list format, since other Agents expect list
        if context:
            # Convert dict to list format (sorted by patch)
            all_packs_list = [all_packs_dict[patch] for patch in sorted(all_packs_dict.keys())]
            context.add_shared_data(
                key="all_packs",
                data=all_packs_list,
                summary=f"Player-Pack data for {len(all_packs_list)} patches"
            )
            print(f"   ✅ Data cached to AgentContext (all_packs)")

        # Step 2: Generate comprehensive analysis data
        print(f"\n📊 Generating comprehensive analysis data...")
        analysis = generate_comprehensive_annual_analysis(all_packs_dict)

        summary = analysis["summary"]
        print(f"✅ Analysis complete:")
        print(f"   Total games: {summary['total_games']}")
        print(f"   Overall winrate: {summary['overall_winrate']:.1%}")
        print(f"   Champions used: {summary['unique_champions']}")
        print(f"   Patches covered: {summary['patches_covered']}")

        # Step 3: Format data for prompt
        print(f"\n📝 Preparing LLM prompt...")

        if self.use_optimized_prompts:
            # Phase 4: Use optimized compact prompt
            print(f"   ✨ Using PromptOptimizer (Token optimization)")
            data_summary = PromptOptimizer.summarize_all_packs(list(all_packs_dict.values()))
            formatted_analysis = PromptOptimizer.format_compact_prompt(
                data_summary,
                analysis_type="annual_summary"
            )
            optimized_tokens = PromptOptimizer.estimate_token_count(formatted_analysis)
            print(f"   📊 Compact prompt: ~{optimized_tokens} tokens")
        else:
            # Traditional method: Full prompt
            formatted_analysis = format_analysis_for_prompt(analysis)
            original_tokens = PromptOptimizer.estimate_token_count(formatted_analysis)
            print(f"   📊 Full prompt: ~{original_tokens} tokens")

        # Step 4: Build narrative prompt
        print(f"\n🤖 Building narrative prompt...")
        prompt_dict = build_narrative_prompt(analysis, formatted_analysis)

        # Step 5: Generate LLM report
        print(f"🚀 Generating comprehensive annual summary report...")
        print(f"   Model: {self.llm.model_id}")
        print(f"   Expected length: 3000-5000 words")

        result = self.llm.generate_sync(
            prompt=prompt_dict["user"],
            system=prompt_dict["system"],
            max_tokens=16000,  # 3000-5000字中文需要12000-20000 tokens，16000确保完整生成
            temperature=0.7
        )

        report = result.get("text", "")
        print(f"✅ Report generated: {len(report)} characters")

        # Step 6: Save outputs (if output_dir specified)
        if output_dir:
            self._save_outputs(analysis, report, output_dir)

        print("\n" + "=" * 60)
        print("✅ Annual summary complete (JSON + Markdown report)")
        print("=" * 60)

        return analysis, report  # 返回真实的report，不是None

    def _save_outputs(self, analysis: Dict[str, Any], report: str, output_dir: str):
        """Save analysis data and report"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save analysis data (JSON)
        patch_range = analysis["metadata"]["patch_range"]
        season_label = f"{patch_range[0]}_to_{patch_range[1]}"

        analysis_file = output_path / f"annual_analysis_{season_label}.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"📄 Analysis data saved: {analysis_file}")

        # Save report (Markdown)
        report_file = output_path / f"annual_summary_{season_label}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📄 Summary report saved: {report_file}")


def main():
    """Command-line entry point (usage example)"""
    import argparse

    parser = argparse.ArgumentParser(description="Annual Season Summary Agent - with Auto Data Fetching")

    # Data source parameters (choose one)
    parser.add_argument("--packs-dir", help="Player-Pack directory path (traditional method)")
    parser.add_argument("--player-id", help="Player ID (format: GameName#TAG), will auto-fetch")
    parser.add_argument("--matches-dir", help="Raw match directory, will auto-convert")

    # Fetch parameters
    parser.add_argument("--region", default="na1", help="Region (default na1)")
    parser.add_argument("--max-matches", type=int, default=200, help="Maximum matches to fetch")

    # Output parameters
    parser.add_argument("--output-dir", default="output/annual_summary", help="Output directory")
    parser.add_argument("--model", default="sonnet", choices=["sonnet", "haiku"], help="LLM model")

    args = parser.parse_args()

    # Validate at least one data source provided
    if not any([args.packs_dir, args.player_id, args.matches_dir]):
        parser.error("Must provide one of: --packs-dir, --player-id, --matches-dir")

    # Run agent
    agent = AnnualSummaryAgent(model=args.model)
    analysis, report = agent.run(
        packs_dir=args.packs_dir,
        player_id=args.player_id,
        matches_dir=args.matches_dir,
        region=args.region,
        max_matches=args.max_matches,
        output_dir=args.output_dir
    )

    # Print report preview
    print("\n" + "=" * 60)
    print("📝 Report Preview (first 500 characters)")
    print("=" * 60)
    print(report[:500])
    print("...")
    print(f"\nFull report length: {len(report)} characters")


if __name__ == "__main__":
    main()

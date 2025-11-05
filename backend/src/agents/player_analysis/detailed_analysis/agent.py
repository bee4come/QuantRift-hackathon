"""
Detailed Analysis Agent
In-depth detailed analysis - using Bedrock Sonnet 4.5 or Haiku
"""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Reuse original DetailedAnalyzer, modified to use shared BedrockLLM
from .detailed_analyzer import DetailedAnalyzer as OriginalAnalyzer


class DetailedAnalysisAgent:
    """Detailed Analysis Agent Wrapper"""

    def __init__(self, model: str = "sonnet"):
        self.model_name = model
        self.analyzer = None

    def run(self, packs_dir: str, meta_dir: str, output_dir: str):
        """Run detailed analysis"""
        packs_path = Path(packs_dir)
        meta_path = Path(meta_dir)
        output_path = Path(output_dir)

        self.analyzer = OriginalAnalyzer(packs_path, meta_path)
        data_package, report = self.analyzer.run(output_path, model_name=self.model_name)

        return data_package, report


def main():
    """Command-line entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Detailed In-Depth Analysis Agent")
    parser.add_argument("--packs-dir", type=str, required=True)
    parser.add_argument("--meta-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, required=True)
    parser.add_argument("--model", type=str, default="sonnet", choices=["haiku", "sonnet"])

    args = parser.parse_args()

    agent = DetailedAnalysisAgent(model=args.model)
    agent.run(args.packs_dir, args.meta_dir, args.output_dir)


if __name__ == "__main__":
    main()

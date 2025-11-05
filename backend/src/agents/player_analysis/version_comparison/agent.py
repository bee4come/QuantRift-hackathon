"""
Version Comparison Agent
Dual-version comparison analysis - Coach Card generation
"""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Reuse original CoachCardGenerator
from test_agents.player_coach.coach_card_generator import CoachCardGenerator as OriginalGenerator


class VersionComparisonAgent:
    """Version Comparison Agent Wrapper"""

    def __init__(self):
        self.generator = OriginalGenerator()

    def run(self, packs_dir: str, meta_dir: str, output_dir: str):
        """Run version comparison analysis"""
        packs_path = Path(packs_dir)
        meta_path = Path(meta_dir)
        output_path = Path(output_dir)

        coach_card, report = self.generator.run(packs_path, meta_path, output_path)

        return coach_card, report


def main():
    """Command-line entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Version Comparison Agent")
    parser.add_argument("--packs-dir", type=str, required=True)
    parser.add_argument("--meta-dir", type=str, required=True)
    parser.add_argument("--output-dir", type=str, required=True)

    args = parser.parse_args()

    agent = VersionComparisonAgent()
    agent.run(args.packs_dir, args.meta_dir, args.output_dir)


if __name__ == "__main__":
    main()

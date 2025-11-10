#!/usr/bin/env python3
"""
Test CustomAnalysisAgent with example queries

Tests the two-phase custom analysis system:
1. PlanAgent generates analysis plan
2. CustomAnalysisAgent executes plan and generates report
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.chat.custom_analysis_agent import PlanAgent, CustomAnalysisAgent


def test_plan_generation():
    """Test PlanAgent plan generation"""
    print("\n" + "=" * 60)
    print("🧪 Test 1: Plan Generation")
    print("=" * 60)

    plan_agent = PlanAgent(model="haiku")

    # Example player data context
    player_data = {
        "total_games": 150,
        "patches": ["15.18", "15.19", "15.20"],
        "recent_matches": [
            {"match_id": "NA1_123456", "timestamp": 1699999999},
            {"match_id": "NA1_123457", "timestamp": 1699999988}
        ]
    }

    # Test query: weekend vs weekday performance
    query = "Compare my weekend vs weekday performance"

    print(f"\n📋 Query: {query}")
    print(f"\n📊 Available data:")
    print(f"   - Total games: {player_data['total_games']}")
    print(f"   - Patches: {', '.join(player_data['patches'])}")
    print(f"   - Recent matches: {len(player_data['recent_matches'])}")

    print(f"\n🤖 Generating analysis plan...")

    try:
        plan = plan_agent.generate_plan(query, player_data)

        print(f"\n✅ Plan generated successfully!")
        print(f"\n📝 Plan Details:")
        print(f"   Query: {plan.query}")
        print(f"   Comparison Type: {plan.comparison_type}")
        print(f"   Output Format: {plan.output_format}")
        print(f"   Explanation: {plan.explanation}")
        print(f"\n   Data Groups ({len(plan.data_groups)}):")
        for i, group in enumerate(plan.data_groups, 1):
            print(f"      {i}. {group.name}")
            if group.time_filter:
                print(f"         Time filter: {group.time_filter}")
            if group.conditions:
                print(f"         Conditions: {group.conditions}")

        print(f"\n   Metrics ({len(plan.metrics)}): {', '.join(plan.metrics)}")

        return True

    except Exception as e:
        print(f"\n❌ Plan generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_custom_analysis_execution():
    """Test CustomAnalysisAgent full execution"""
    print("\n" + "=" * 60)
    print("🧪 Test 2: Custom Analysis Execution (with real data)")
    print("=" * 60)

    # Find a player pack directory to test with
    data_dir = Path(__file__).parent.parent / "data" / "player_packs"

    if not data_dir.exists():
        print(f"\n⚠️  No player pack data found at {data_dir}")
        print("   Skipping execution test (plan generation test passed)")
        return True

    # Get first available player pack
    puuid_dirs = [d for d in data_dir.iterdir() if d.is_dir()]

    if not puuid_dirs:
        print(f"\n⚠️  No player pack directories found")
        print("   Skipping execution test (plan generation test passed)")
        return True

    packs_dir = str(puuid_dirs[0])
    print(f"\n📁 Using player pack: {puuid_dirs[0].name[:20]}...")

    # Count available pack files
    pack_files = list(Path(packs_dir).glob("pack_*.json"))
    print(f"   Available pack files: {len(pack_files)}")

    if len(pack_files) == 0:
        print(f"\n⚠️  No pack files found in {packs_dir}")
        return False

    # Example player data
    player_data = {
        "total_games": 150,
        "patches": ["15.18", "15.19"],
        "recent_matches": []
    }

    # Test query
    query = "Compare my performance in the last 30 days vs the previous 30 days"

    print(f"\n📋 Query: {query}")
    print(f"\n🔬 Running custom analysis...")

    try:
        custom_agent = CustomAnalysisAgent(model="haiku")

        # Use non-streaming execute_plan for testing
        from src.agents.chat.custom_analysis_agent import PlanAgent

        plan_agent = PlanAgent(model="haiku")
        plan = plan_agent.generate_plan(query, player_data)

        print(f"\n✅ Plan: {plan.explanation}")
        print(f"   Groups: {len(plan.data_groups)}")
        print(f"   Metrics: {', '.join(plan.metrics)}")

        # Execute plan
        print(f"\n🤖 Executing analysis plan...")
        report = custom_agent.execute_plan(plan, packs_dir)

        print(f"\n✅ Report generated successfully!")
        print(f"\n📄 Report Preview (first 500 chars):")
        print("-" * 60)
        print(report[:500] + "..." if len(report) > 500 else report)
        print("-" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Custom analysis execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_streaming_output():
    """Test CustomAnalysisAgent streaming output"""
    print("\n" + "=" * 60)
    print("🧪 Test 3: Streaming Output")
    print("=" * 60)

    # Find a player pack directory
    data_dir = Path(__file__).parent.parent / "data" / "player_packs"

    if not data_dir.exists():
        print(f"\n⚠️  No player pack data found")
        print("   Skipping streaming test")
        return True

    puuid_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
    if not puuid_dirs:
        print(f"\n⚠️  No player pack directories found")
        return True

    packs_dir = str(puuid_dirs[0])
    pack_files = list(Path(packs_dir).glob("pack_*.json"))

    if len(pack_files) == 0:
        print(f"\n⚠️  No pack files found")
        return True

    print(f"\n📁 Using player pack: {puuid_dirs[0].name[:20]}...")
    print(f"   Pack files: {len(pack_files)}")

    player_data = {
        "total_games": 100,
        "patches": ["15.19"],
        "recent_matches": []
    }

    query = "How has my performance changed over time?"

    print(f"\n📋 Query: {query}")
    print(f"\n🌊 Testing streaming output...\n")

    try:
        custom_agent = CustomAnalysisAgent(model="haiku")

        message_count = 0
        chunk_count = 0

        for message in custom_agent.run_stream(query, packs_dir, player_data):
            message_count += 1

            # Parse SSE message
            if message.startswith("data: "):
                try:
                    import json
                    data = json.loads(message[6:])
                    msg_type = data.get("type", "unknown")
                    content = data.get("content", "")

                    if msg_type == "chunk":
                        chunk_count += 1
                        # Print first few chunks
                        if chunk_count <= 5:
                            print(f"   [{msg_type}] {content[:50]}...")
                    else:
                        print(f"   [{msg_type}] {content[:80]}")

                except json.JSONDecodeError:
                    pass

        print(f"\n✅ Streaming test completed!")
        print(f"   Total messages: {message_count}")
        print(f"   Chunk messages: {chunk_count}")

        return True

    except Exception as e:
        print(f"\n❌ Streaming test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 CustomAnalysisAgent Test Suite")
    print("=" * 60)

    results = []

    # Test 1: Plan generation
    results.append(("Plan Generation", test_plan_generation()))

    # Test 2: Full execution with real data
    results.append(("Custom Analysis Execution", test_custom_analysis_execution()))

    # Test 3: Streaming output
    results.append(("Streaming Output", test_streaming_output()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\n   Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

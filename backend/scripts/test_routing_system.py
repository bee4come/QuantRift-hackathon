"""
Test script for Hybrid Routing System

Tests 10-15 representative user queries to validate routing logic.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.router.hybrid_router import get_hybrid_router


# Test queries covering different scenarios
TEST_QUERIES = [
    # Rule-based routing (should hit rule router)
    {
        "query": "How is my recent jungle performance?",
        "expected_method": "rule",
        "expected_subagent": "role-specialization",
        "description": "Simple role-specific query (English)"
    },
    {
        "query": "我最近打野怎么样？",
        "expected_method": "rule",
        "expected_subagent": "role-specialization",
        "description": "Simple role-specific query (Chinese)"
    },
    {
        "query": "Analyze my weaknesses",
        "expected_method": "rule",
        "expected_subagent": "weakness-analysis",
        "description": "Weakness analysis request (English)"
    },
    {
        "query": "帮我分析一下我的弱点",
        "expected_method": "rule",
        "expected_subagent": "weakness-analysis",
        "description": "Weakness analysis request (Chinese)"
    },
    {
        "query": "Recommend some champions for me",
        "expected_method": "rule",
        "expected_subagent": "champion-recommendation",
        "description": "Champion recommendation (English)"
    },
    {
        "query": "推荐几个适合我的英雄",
        "expected_method": "rule",
        "expected_subagent": "champion-recommendation",
        "description": "Champion recommendation (Chinese)"
    },
    {
        "query": "Show me my season summary",
        "expected_method": "rule",
        "expected_subagent": "annual-summary",
        "description": "Annual summary request"
    },
    {
        "query": "What's my top lane performance like?",
        "expected_method": "rule",
        "expected_subagent": "role-specialization",
        "description": "Top lane query"
    },
    {
        "query": "What items should I build on Yasuo?",
        "expected_method": "rule",
        "expected_subagent": "build-simulator",
        "description": "Build recommendation"
    },

    # Comparison queries (should trigger custom_analysis)
    {
        "query": "Compare my last 30 days vs previous 30 days",
        "expected_method": "rule",
        "expected_action": "custom_analysis",
        "description": "Time period comparison"
    },
    {
        "query": "对比我最近30天和之前30天的表现",
        "expected_method": "rule",
        "expected_action": "custom_analysis",
        "description": "Time period comparison (Chinese)"
    },

    # Complex/ambiguous queries (should fallback to LLM)
    {
        "query": "Analyze my performance",
        "expected_method": "llm",
        "description": "Ambiguous query requiring LLM"
    },
    {
        "query": "我想提升自己的水平",
        "expected_method": "llm",
        "description": "General improvement request (Chinese)"
    },
    {
        "query": "What should I focus on to climb ranked?",
        "expected_method": "llm",
        "description": "Complex question needing context"
    },

    # Simple data questions
    {
        "query": "How many games have I played?",
        "expected_method": "llm",  # Should be answer_directly
        "expected_action": "answer_directly",
        "description": "Simple data question"
    },
]


def run_routing_tests():
    """Run all routing tests and report results"""
    router = get_hybrid_router(rule_confidence_threshold=0.7, llm_model="haiku")

    player_data = {
        "total_games": 150,
        "recent_match_count": 20,
        "patches": ["15.17", "15.18", "15.19"]
    }

    print("=" * 80)
    print("HYBRID ROUTING SYSTEM TEST")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for i, test_case in enumerate(TEST_QUERIES, 1):
        query = test_case["query"]
        expected_method = test_case.get("expected_method", "any")
        expected_subagent = test_case.get("expected_subagent")
        expected_action = test_case.get("expected_action")
        description = test_case["description"]

        print(f"Test {i}: {description}")
        print(f"Query: \"{query}\"")

        try:
            result = router.route(
                user_message=query,
                session_history=[],
                player_data=player_data
            )

            print(f"→ Routing method: {result.routing_method}")
            print(f"→ Action: {result.action}")
            if result.subagent_id:
                print(f"→ Subagent: {result.subagent_id}")
            if result.params:
                print(f"→ Params: {result.params}")
            print(f"→ Reason: {result.reason}")

            # Validate expectations
            test_passed = True
            if expected_method != "any" and result.routing_method != expected_method:
                print(f"❌ FAILED: Expected routing method '{expected_method}', got '{result.routing_method}'")
                test_passed = False

            if expected_subagent and result.subagent_id != expected_subagent:
                print(f"❌ FAILED: Expected subagent '{expected_subagent}', got '{result.subagent_id}'")
                test_passed = False

            if expected_action and result.action != expected_action:
                print(f"❌ FAILED: Expected action '{expected_action}', got '{result.action}'")
                test_passed = False

            if test_passed:
                print("✅ PASSED")
                passed += 1
            else:
                failed += 1

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            failed += 1

        print()
        print("-" * 80)
        print()

    # Summary
    total = passed + failed
    print("=" * 80)
    print(f"TEST SUMMARY: {passed}/{total} passed ({passed/total*100:.1f}%)")
    print("=" * 80)

    return passed, failed


if __name__ == "__main__":
    passed, failed = run_routing_tests()
    sys.exit(0 if failed == 0 else 1)

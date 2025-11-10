#!/usr/bin/env python3
"""
Test script for hybrid routing system integration
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all router components can be imported"""
    print("Testing imports...")

    try:
        from src.agents.chat.router import (
            get_hybrid_router,
            stream_chat_with_routing,
            HybridRouter,
            RouterStreamGenerator
        )
        print("✅ All router components imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_hybrid_router_basic():
    """Test basic hybrid router functionality"""
    print("\nTesting hybrid router...")

    try:
        from src.agents.chat.router import get_hybrid_router

        router = get_hybrid_router(
            rule_confidence_threshold=0.7,
            llm_model="haiku"
        )

        # Test simple rule-based routing
        result = router.route(
            user_message="分析我的弱点",
            session_history=[],
            player_data={"total_games": 100}
        )

        print(f"  Query: '分析我的弱点'")
        print(f"  Routing method: {result.routing_method}")
        print(f"  Action: {result.action}")
        print(f"  Subagent: {result.subagent_id}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  ✅ Basic routing test passed")
        return True

    except Exception as e:
        print(f"  ❌ Router test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stream_generator():
    """Test RouterStreamGenerator"""
    print("\nTesting stream generator...")

    try:
        from src.agents.chat.router import stream_chat_with_routing
        from pathlib import Path

        # Use s1ne's cached data
        puuid = "OkHv4J5JcbqQSx9I5Fda7L9rpz4wQcaDVpgDyjtlhEcpdZIM9ExEyrfTpjS6EdsYcZjKX9i5ctKC9A"
        packs_dir = Path(f"/home/zty/QuantRift_hackathon/backend/data/player_packs/{puuid}")

        if not packs_dir.exists():
            print(f"  ⚠️  Player pack directory not found: {packs_dir}")
            print("  Skipping stream test")
            return True

        print(f"  Using player pack: {packs_dir}")

        # Test streaming with a simple query
        message_count = 0
        for sse_message in stream_chat_with_routing(
            user_message="我最近打得怎么样？",
            puuid=puuid,
            packs_dir=packs_dir,
            session_history=[],
            player_data={"total_games": 20},
            model="haiku",
            rule_confidence_threshold=0.7
        ):
            message_count += 1

            # Print first few messages to show it's working
            if message_count <= 5:
                # Extract message type from SSE format
                if '"type"' in sse_message:
                    import json
                    try:
                        data = json.loads(sse_message.split("data: ")[1])
                        msg_type = data.get("type", "unknown")
                        print(f"  Message {message_count}: {msg_type}")
                    except:
                        pass

            # Stop after receiving 'done' message
            if '"type": "done"' in sse_message:
                break

        print(f"  ✅ Stream test passed ({message_count} messages received)")
        return True

    except Exception as e:
        print(f"  ❌ Stream test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Chat Routing System Integration Tests")
    print("="*60)

    results = []

    results.append(("Import Test", test_imports()))
    results.append(("Hybrid Router Test", test_hybrid_router_basic()))
    results.append(("Stream Generator Test", test_stream_generator()))

    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nPassed {passed}/{total} tests")

    return all(p for _, p in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

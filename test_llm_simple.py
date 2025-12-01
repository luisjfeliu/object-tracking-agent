#!/usr/bin/env python3
"""
Simple LLM test - no interactive input needed.

Usage:
  # With API key:
  GEMINI_API_KEY='your-key' python test_llm_simple.py

  # Or pass as argument:
  python test_llm_simple.py your-api-key

  # Without API key (shows rule-based):
  python test_llm_simple.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Setup
sys.path.insert(0, Path(__file__).parent.as_posix())
from src.agents.adk_enhanced.agents.summary_agent import create_summary_agent


def load_events(limit=48):
    """Load test events."""
    events = []
    log_path = Path("imx500_events_remote.jsonl")

    if not log_path.exists():
        print(f"❌ Event log not found: {log_path}")
        return events

    with log_path.open("r") as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            try:
                event = json.loads(line.strip())
                if "event_type" not in event:
                    event["event_type"] = "object_detected"
                    event["details"] = event.copy()
                events.append(event)
            except:
                continue

    return events


async def test_llm(api_key=None):
    """Test LLM summarization."""
    # Load events
    events = load_events()
    if not events:
        return False

    print("\n" + "="*70)
    print(f"Testing with {len(events)} events")
    print("="*70)

    # Set API key if provided
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
        print(f"\n✓ Using API key: {api_key[:10]}...{api_key[-4:]}")
    else:
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        print("\n⚠️  No API key provided - using rule-based summaries")

    # Create agent and generate summary
    # Use correct model name format with models/ prefix
    agent = create_summary_agent(model_name="models/gemini-2.5-flash")

    print("\nGenerating summary...\n")

    result = await agent.generate_summary_async(events, window_minutes=60)

    # Display results
    print("="*70)
    method = "LLM (Gemini)" if result['metadata']['llm_used'] else "RULE-BASED"
    print(f"SUMMARY ({method})")
    print("="*70)
    print()
    print(result['summary'])
    print()

    # Show stats
    print("="*70)
    print("Details:")
    print("="*70)
    meta = result['metadata']
    stats = result['statistics']

    print(f"\n📊 Method: {meta.get('method', 'unknown').upper()}")
    print(f"🤖 LLM Used: {'Yes' if meta['llm_used'] else 'No'}")
    if meta['llm_used']:
        print(f"🎯 Model: {meta.get('model', 'N/A')}")

    print(f"\n📈 Statistics:")
    print(f"   - Events: {stats['total_events']}")
    print(f"   - Categories: {stats['unique_categories']}")

    if stats.get('categories'):
        print(f"\n   Categories:")
        for cat, data in stats['categories'].items():
            print(f"     • {cat.upper()}: {data['count']} detections "
                  f"(confidence: {data['avg_confidence']:.2f})")

    patterns = result.get('patterns', {})
    if patterns.get('bus_sightings', 0) > 0:
        print(f"\n⚠️  Bus sightings: {patterns['bus_sightings']}")

    print("\n" + "="*70)

    return meta['llm_used']


def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("Gemini LLM Test")
    print("="*70)

    # Check for API key in args or env
    api_key = None

    if len(sys.argv) > 1:
        api_key = sys.argv[1]
        if api_key in ['-h', '--help', 'help']:
            print(__doc__)
            return 0
    else:
        api_key = os.environ.get("GEMINI_API_KEY")

    # Run test
    try:
        llm_used = asyncio.run(test_llm(api_key))
    except Exception as exc:
        print(f"\n❌ Test failed: {exc}")
        return 1

    # Next steps
    print("\n" + "="*70)
    print("Next Steps")
    print("="*70)

    if not llm_used:
        print("\n📝 To test with Gemini LLM:")
        print("\n1. Get API key from: https://aistudio.google.com/apikey")
        print("\n2. Run with key:")
        print("   GEMINI_API_KEY='your-key' python test_llm_simple.py")
        print("\n   Or:")
        print("   python test_llm_simple.py your-api-key")
    else:
        print("\n✅ LLM is working! Now run the full coordinator:")
        print("\n   python src/agents/adk_enhanced/coordinator.py")
        print("\n   The coordinator will use LLM for all summaries automatically!")

    print("\n📚 More info: docs/GEMINI_SETUP.md")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

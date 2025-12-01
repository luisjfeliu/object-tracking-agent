#!/usr/bin/env python3
"""
Direct test with your API key - just edit the API_KEY variable below.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# ============================================
# EDIT THIS: Paste your API key here
# ============================================
API_KEY = "AIzaSyAORX...pJwY"  # Replace with your full key
# ============================================

# Setup
sys.path.insert(0, Path(__file__).parent.as_posix())
from src.agents.adk_enhanced.agents.summary_agent import create_summary_agent


async def test():
    """Test LLM with your API key."""
    # Set API key
    os.environ["GEMINI_API_KEY"] = API_KEY

    # Load events
    events = []
    with open("imx500_events_remote.jsonl") as f:
        for i, line in enumerate(f):
            if i >= 48:
                break
            event = json.loads(line.strip())
            if "event_type" not in event:
                event["event_type"] = "object_detected"
                event["details"] = event.copy()
            events.append(event)

    print("\n" + "="*70)
    print(f"Testing Gemini LLM with {len(events)} events")
    print("="*70)
    print(f"\nUsing API key: {API_KEY[:10]}...{API_KEY[-4:]}")

    # Try different models in order of preference
    models = [
        "gemini-1.5-flash",      # Stable, fast, free tier
        "gemini-1.5-pro",        # More capable, slower
        "gemini-pro",            # Older but reliable
    ]

    for model in models:
        print(f"\n🔄 Trying model: {model}")

        try:
            agent = create_summary_agent(model_name=model)
            result = await agent.generate_summary_async(events, 60)

            if result['metadata']['llm_used']:
                print(f"✅ Success with {model}!")
                print("\n" + "="*70)
                print("LLM SUMMARY")
                print("="*70)
                print("\n" + result['summary'] + "\n")

                print("="*70)
                print("Details:")
                print("="*70)
                print(f"Model: {model}")
                print(f"LLM Used: Yes")
                print(f"Events: {result['statistics']['total_events']}")
                print(f"Categories: {result['statistics']['unique_categories']}")
                print("\n✅ LLM test successful!\n")
                return True

        except Exception as exc:
            print(f"❌ {model} failed: {str(exc)[:100]}")
            continue

    print("\n❌ All models failed. Using rule-based fallback.")
    return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Gemini LLM Test - Direct")
    print("="*70)

    if API_KEY == "AIzaSyAORX...pJwY":
        print("\n⚠️  Please edit test_with_your_key.py and paste your full API key")
        print("   at the top of the file where it says API_KEY = \"...\"")
        print("\nYour key: AIzaSyAORX...pJwY")
        sys.exit(1)

    success = asyncio.run(test())
    sys.exit(0 if success else 1)

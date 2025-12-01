#!/bin/bash

# Simple test script - just run: ./test_gemini_now.sh

echo "Testing Gemini LLM with your API key..."
echo ""

python3 - <<'EOF'
import asyncio
import json
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, '.')

# Import our summary agent
from src.agents.adk_enhanced.agents.summary_agent import create_summary_agent

async def test():
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

    print(f"Testing with {len(events)} events\n")

    # Create agent with correct model name
    agent = create_summary_agent(model_name="models/gemini-2.5-flash")

    # Generate summary
    result = await agent.generate_summary_async(events, 60)

    # Display results
    print("="*70)
    if result['metadata']['llm_used']:
        print("LLM SUMMARY (Gemini 2.5 Flash)")
    else:
        print("RULE-BASED SUMMARY (LLM not available)")
    print("="*70)
    print()
    print(result['summary'])
    print()
    print("="*70)
    print(f"LLM Used: {result['metadata']['llm_used']}")
    print(f"Model: {result['metadata'].get('model', 'N/A')}")
    print(f"Events: {result['statistics']['total_events']}")
    print("="*70)

    return result['metadata']['llm_used']

# Run the test
success = asyncio.run(test())

if success:
    print("\n✅ SUCCESS! LLM is working!")
    print("\nYou can now run the full coordinator:")
    print("  python src/agents/adk_enhanced/coordinator.py")
else:
    print("\n⚠️  LLM not available, using rule-based summaries")
    print("This is normal if GEMINI_API_KEY is not set.")

sys.exit(0 if success else 1)
EOF

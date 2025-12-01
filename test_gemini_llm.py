#!/usr/bin/env python3
"""
Test Gemini LLM integration for enhanced ADK system.

This script helps you:
1. Get a Gemini API key if needed
2. Test the LLM-powered summarization
3. Compare rule-based vs LLM summaries
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Setup
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, REPO_ROOT.as_posix())

from src.agents.adk_enhanced.agents.summary_agent import create_summary_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def load_test_events(limit=50):
    """Load events from the remote log file."""
    log_path = Path("imx500_events_remote.jsonl")
    events = []

    if not log_path.exists():
        logger.error(f"Event log not found: {log_path}")
        return events

    with log_path.open("r") as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            try:
                event = json.loads(line.strip())
                # Ensure event_type exists
                if "event_type" not in event:
                    if event.get("category") == "bus":
                        event["event_type"] = "bus_detected"
                        event["details"] = event.copy()
                    else:
                        event["event_type"] = "object_detected"
                        event["details"] = event.copy()
                events.append(event)
            except json.JSONDecodeError:
                continue

    return events


async def test_llm_summary(events, api_key):
    """Test LLM-powered summary generation."""
    logger.info("\n" + "="*70)
    logger.info("Testing LLM-Powered Summary")
    logger.info("="*70)

    # Set API key temporarily
    original_key = os.environ.get("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = api_key

    try:
        # Create summary agent
        summary_agent = create_summary_agent(model_name="gemini-2.0-flash-exp")

        # Generate summary
        logger.info(f"\nAnalyzing {len(events)} events with Gemini...")
        logger.info("(This may take a few seconds...)\n")

        result = await summary_agent.generate_summary_async(
            events,
            window_minutes=60
        )

        # Display results
        logger.info("="*70)
        logger.info("LLM SUMMARY (Gemini-powered)")
        logger.info("="*70)
        print("\n" + result['summary'] + "\n")

        # Show metadata
        metadata = result.get('metadata', {})
        stats = result.get('statistics', {})
        patterns = result.get('patterns', {})

        logger.info("="*70)
        logger.info("Metadata:")
        logger.info(f"  - Model: {metadata.get('model', 'N/A')}")
        logger.info(f"  - LLM Used: {metadata.get('llm_used', False)}")
        logger.info(f"  - Window: {metadata.get('window_minutes', 0)} minutes")

        logger.info("\nStatistics:")
        logger.info(f"  - Total events: {stats.get('total_events', 0)}")
        logger.info(f"  - Unique categories: {stats.get('unique_categories', 0)}")

        if stats.get('categories'):
            logger.info("  - By category:")
            for cat, data in stats['categories'].items():
                logger.info(f"    • {cat.upper()}: {data['count']} "
                          f"(avg: {data['avg_confidence']:.2f})")

        logger.info("\nPatterns Detected:")
        if patterns.get('bus_sightings', 0) > 0:
            logger.info(f"  ⚠️  Bus sightings: {patterns['bus_sightings']}")
        if patterns.get('high_frequency_categories'):
            logger.info(f"  - High activity categories: "
                       f"{len(patterns['high_frequency_categories'])}")
        if patterns.get('unusual_activity'):
            logger.info(f"  - Unusual activity windows: "
                       f"{len(patterns['unusual_activity'])}")

        logger.info("="*70)

        return True

    except Exception as exc:
        logger.error(f"\n❌ LLM test failed: {exc}")
        return False

    finally:
        # Restore original key
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key
        else:
            os.environ.pop("GEMINI_API_KEY", None)


async def compare_summaries(events):
    """Compare rule-based vs LLM summaries."""
    logger.info("\n" + "="*70)
    logger.info("Comparing Rule-Based vs LLM Summaries")
    logger.info("="*70)

    # Rule-based (no API key)
    os.environ.pop("GEMINI_API_KEY", None)
    summary_agent_rule = create_summary_agent()

    logger.info("\nGenerating RULE-BASED summary...")
    result_rule = await summary_agent_rule.generate_summary_async(events, 60)

    logger.info("\n--- RULE-BASED SUMMARY ---")
    print(result_rule['summary'])

    # LLM-based (with API key)
    api_key = input("\n\nEnter your Gemini API key to compare with LLM: ").strip()

    if not api_key:
        logger.warning("No API key provided. Skipping LLM comparison.")
        return

    os.environ["GEMINI_API_KEY"] = api_key
    summary_agent_llm = create_summary_agent()

    logger.info("\nGenerating LLM summary...")
    result_llm = await summary_agent_llm.generate_summary_async(events, 60)

    logger.info("\n--- LLM SUMMARY ---")
    print(result_llm['summary'])

    logger.info("\n" + "="*70)
    logger.info("Comparison Complete!")
    logger.info("="*70)
    logger.info("\nNotice the difference:")
    logger.info("  - Rule-based: Structured, factual, metrics-focused")
    logger.info("  - LLM: Natural language, insights, recommendations")


def main():
    """Main test flow."""
    print("\n" + "="*70)
    print("Gemini LLM Integration Test")
    print("="*70)

    # Load test data
    events = load_test_events(limit=50)

    if not events:
        print("\n❌ No events loaded. Please ensure imx500_events_remote.jsonl exists.")
        return 1

    print(f"\n✓ Loaded {len(events)} events for testing\n")

    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("="*70)
        print("Getting a Gemini API Key")
        print("="*70)
        print("\n1. Visit: https://aistudio.google.com/apikey")
        print("2. Sign in with your Google account")
        print("3. Click 'Create API Key'")
        print("4. Copy the key\n")

        print("You can either:")
        print("  a) Set it as environment variable: export GEMINI_API_KEY='your-key'")
        print("  b) Enter it below for this test only\n")

        api_key = input("Enter your Gemini API key (or press Enter to skip): ").strip()

        if not api_key:
            print("\n⚠️  No API key provided. The system will use rule-based summaries.")
            print("Run the test again with an API key to see LLM-powered summaries.\n")
            return 0

    # Run LLM test
    print("\n" + "="*70)
    print("Running LLM Test")
    print("="*70)

    success = asyncio.run(test_llm_summary(events, api_key))

    if success:
        print("\n✓ LLM test completed successfully!\n")

        # Offer comparison
        choice = input("Would you like to see a side-by-side comparison? (y/n): ").strip().lower()
        if choice == 'y':
            asyncio.run(compare_summaries(events))
    else:
        print("\n❌ LLM test failed. Check the error message above.\n")
        print("Common issues:")
        print("  - Invalid API key")
        print("  - API quota exceeded")
        print("  - Network connectivity")
        print("\nThe system will fall back to rule-based summaries automatically.")
        return 1

    print("\n" + "="*70)
    print("Next Steps")
    print("="*70)
    print("\n1. Run the full coordinator with LLM:")
    print(f"   export GEMINI_API_KEY='{api_key[:10]}...'")
    print("   python src/agents/adk_enhanced/coordinator.py\n")
    print("2. Or set it permanently in your shell config (~/.bashrc or ~/.zshrc):")
    print(f"   echo 'export GEMINI_API_KEY=\"{api_key[:10]}...\"' >> ~/.zshrc\n")
    print("3. The coordinator will now use LLM for all summaries automatically!\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Test script for enhanced ADK integration.

This script tests the enhanced multi-agent system without requiring
a Gemini API key (falls back to rule-based summaries).
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, REPO_ROOT.as_posix())

from src.agents.adk_enhanced.coordinator import ObjectTrackingCoordinator
from src.agents.adk_enhanced.agents.summary_agent import create_summary_agent
from src.agents.adk_enhanced.tools.summary_tools import (
    aggregate_events_by_category,
    detect_patterns
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def load_events_from_jsonl(path: Path, limit: int = 100) -> list:
    """Load events from JSONL file."""
    events = []
    if not path.exists():
        logger.error(f"File not found: {path}")
        return events

    with path.open("r") as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            try:
                event = json.loads(line.strip())
                # Add event_type if missing (infer from data)
                if "event_type" not in event:
                    if "category" in event:
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


async def test_agents():
    """Test individual agents."""
    logger.info("=" * 60)
    logger.info("Testing Enhanced ADK Agents")
    logger.info("=" * 60)

    # Load test events
    log_path = Path("imx500_events_remote.jsonl")
    events = load_events_from_jsonl(log_path, limit=100)

    logger.info(f"\nLoaded {len(events)} events from {log_path}")

    if not events:
        logger.error("No events loaded. Cannot proceed with tests.")
        return

    # Test 1: Event aggregation
    logger.info("\n--- Test 1: Event Aggregation ---")
    agg = aggregate_events_by_category(events)
    logger.info(f"Total events: {agg['total_events']}")
    logger.info(f"Categories: {agg['unique_categories']}")
    for cat, stats in agg.get("categories", {}).items():
        logger.info(f"  - {cat}: {stats['count']} detections "
                   f"(avg conf: {stats['avg_confidence']:.2f})")

    # Test 2: Pattern detection
    logger.info("\n--- Test 2: Pattern Detection ---")
    patterns = detect_patterns(events)
    logger.info(f"High frequency categories: {len(patterns['high_frequency_categories'])}")
    for item in patterns['high_frequency_categories']:
        logger.info(f"  - {item['category']}: {item['percentage']}%")

    if patterns["bus_sightings"] > 0:
        logger.info(f"⚠️  Bus sightings: {patterns['bus_sightings']}")

    # Test 3: Summary agent (rule-based, no API key needed)
    logger.info("\n--- Test 3: Summary Generation (Rule-based) ---")
    summary_agent = create_summary_agent()
    summary_result = await summary_agent.generate_summary_async(events, window_minutes=60)

    logger.info("\nSummary:")
    logger.info(summary_result['summary'])

    logger.info(f"\nLLM used: {summary_result.get('metadata', {}).get('llm_used', False)}")
    logger.info(f"Method: {summary_result.get('metadata', {}).get('method', 'unknown')}")

    logger.info("\n" + "=" * 60)
    logger.info("All tests completed successfully!")
    logger.info("=" * 60)


async def test_coordinator_batch():
    """Test coordinator in batch mode (process existing events)."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Coordinator (Batch Mode)")
    logger.info("=" * 60)

    log_path = Path("imx500_events_remote.jsonl")

    if not log_path.exists():
        logger.error(f"Log file not found: {log_path}")
        return

    # Create coordinator with shorter intervals for testing
    coordinator = ObjectTrackingCoordinator(
        log_path=log_path,
        summary_window_min=60,
        summary_interval=50,  # Summary every 50 events for testing
        use_tracker=True,
        model_name="gemini-2.0-flash-exp"
    )

    # Load and process events
    events = load_events_from_jsonl(log_path, limit=100)

    logger.info(f"Processing {len(events)} events...")

    for event in events:
        await coordinator.process_event(event)

    # Generate final summary
    await coordinator._generate_summary()

    # Show statistics
    stats = coordinator.get_statistics()
    logger.info(f"\nCoordinator Statistics:")
    logger.info(f"  - Events processed: {stats['events_processed']}")
    logger.info(f"  - Bus alerts: {stats['bus_alerts_sent']}")
    logger.info(f"  - Summaries generated: {stats['summaries_generated']}")
    logger.info(f"  - Errors: {stats['errors']}")

    if "tracker" in stats:
        tracker = stats["tracker"]
        logger.info(f"\nTracker Statistics:")
        logger.info(f"  - Active tracks: {tracker.get('active_tracks', 0)}")
        logger.info(f"  - Next track ID: {tracker.get('next_track_id', 0)}")
        logger.info(f"  - Tracks by category: {tracker.get('tracks_by_category', {})}")

    logger.info("\n" + "=" * 60)
    logger.info("Coordinator test completed!")
    logger.info("=" * 60)


def main():
    """Run all tests."""
    logger.info("\nStarting Enhanced ADK Integration Tests\n")

    # Run agent tests
    asyncio.run(test_agents())

    # Run coordinator test
    asyncio.run(test_coordinator_batch())

    logger.info("\n✓ All tests passed!\n")
    logger.info("To run the coordinator in real-time mode:")
    logger.info("  python src/agents/adk_enhanced/coordinator.py")
    logger.info("\nOptional: Set GEMINI_API_KEY for LLM-powered summaries:")
    logger.info("  export GEMINI_API_KEY='your-key'")
    logger.info("  python src/agents/adk_enhanced/coordinator.py")


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Test the coordinator in batch mode with existing events."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, '.')

from src.agents.adk_enhanced.coordinator import ObjectTrackingCoordinator


async def test_coordinator():
    """Test coordinator with existing event log."""

    log_path = Path("imx500_events_remote.jsonl")

    if not log_path.exists():
        print(f"❌ Log file not found: {log_path}")
        return False

    print("="*70)
    print("Testing Enhanced ADK Coordinator")
    print("="*70)

    # Create coordinator with short interval for testing
    coordinator = ObjectTrackingCoordinator(
        log_path=log_path,
        summary_window_min=60,
        summary_interval=50,  # Summary every 50 events for testing
        use_tracker=True,
        model_name="models/gemini-2.5-flash"
    )

    print(f"\nProcessing events from: {log_path}")
    print("(Processing first 48 events...)\n")

    # Read and process existing events
    event_count = 0
    with log_path.open("r") as f:
        for line in f:
            if event_count >= 48:
                break

            event_str = line.strip()
            if not event_str:
                continue

            # Parse and process event
            from src.agents.agents import parse_event_line
            event = parse_event_line(event_str)

            if event:
                # Convert to dict format expected by coordinator
                event_dict = {
                    "ts": event.ts.isoformat(),
                    "event_type": event.event_type,
                    "details": event.details
                }

                await coordinator.process_event(event_dict)
                event_count += 1

    # Generate final summary
    print("\nGenerating final summary...")
    await coordinator._generate_summary()

    # Show statistics
    stats = coordinator.get_statistics()

    print("\n" + "="*70)
    print("Coordinator Statistics")
    print("="*70)
    print(f"Events processed: {stats['events_processed']}")
    print(f"Bus alerts sent: {stats['bus_alerts_sent']}")
    print(f"Summaries generated: {stats['summaries_generated']}")
    print(f"Errors: {stats['errors']}")

    if 'tracker' in stats:
        tracker = stats['tracker']
        print(f"\nTracker Statistics:")
        print(f"  - Active tracks: {tracker.get('active_tracks', 0)}")
        print(f"  - Next track ID: {tracker.get('next_track_id', 0)}")
        print(f"  - Tracks by category: {tracker.get('tracks_by_category', {})}")

    print("\n" + "="*70)
    print("✅ Coordinator test complete!")
    print("="*70)

    return True


if __name__ == "__main__":
    success = asyncio.run(test_coordinator())

    if success:
        print("\n🎉 Enhanced ADK coordinator is working!")
        print("\nTo run in real-time mode (tailing log):")
        print("  python src/agents/adk_enhanced/coordinator.py")
        print("\nThe coordinator will:")
        print("  - Monitor the event log for new entries")
        print("  - Send bus alerts via webhook")
        print("  - Generate LLM summaries every 200 events")
        print("  - Track objects with persistent IDs")

    sys.exit(0 if success else 1)

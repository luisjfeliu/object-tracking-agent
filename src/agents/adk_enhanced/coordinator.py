#!/usr/bin/env python3
"""
Object Tracking Coordinator - orchestrates multi-agent system using ADK.

This coordinator implements proper ADK patterns:
- Event-driven architecture
- Parallel agent execution where appropriate
- Proper error handling and telemetry
- LLM-powered intelligence
"""

import asyncio
import json
import logging
import os
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Deque

# Use standard logging - google.adk.telemetry.logger doesn't exist in this version
# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from src.agents.agents import parse_event_line
from src.agents.adk_enhanced.agents.bus_agent import create_bus_notification_agent
from src.agents.adk_enhanced.agents.summary_agent import create_summary_agent
from src.agents.adk_enhanced.agents.tracking_agent import create_tracking_agent


logger = logging.getLogger(__name__)


class ObjectTrackingCoordinator:
    """
    Coordinates multiple agents for object tracking.

    Architecture:
        Event Stream -> Ingestion -> Route to Agents:
            - Bus Agent (parallel)
            - Tracking Agent (parallel)
            - Summary Agent (periodic)
    """

    def __init__(
        self,
        log_path: Optional[Path] = None,
        summary_window_min: int = 30,
        summary_interval: int = 200,  # events
        use_tracker: bool = True,
        model_name: str = "models/gemini-2.5-flash"
    ):
        """
        Initialize the coordinator.

        Args:
            log_path: Path to JSONL event log
            summary_window_min: Time window for summaries (minutes)
            summary_interval: Generate summary every N events
            use_tracker: Enable object tracking
            model_name: Gemini model for summarization
        """
        self.log_path = log_path or Path(
            os.environ.get("IMX500_LOG_PATH", Path.home() / "imx500_events.jsonl")
        )
        self.summary_window_min = summary_window_min
        self.summary_interval = summary_interval
        self.use_tracker = use_tracker
        self.model_name = model_name

        # Initialize agents
        self.bus_agent = create_bus_notification_agent()
        self.tracking_agent = create_tracking_agent() if use_tracker else None
        self.summary_agent = create_summary_agent(model_name)

        # Event buffer for summarization
        self.event_buffer: Deque[Dict[str, Any]] = deque(maxlen=10000)

        # Statistics
        self.stats = {
            "events_processed": 0,
            "bus_alerts_sent": 0,
            "summaries_generated": 0,
            "errors": 0
        }

        logger.info("ObjectTrackingCoordinator initialized")
        logger.info(f"Coordinator watching: {self.log_path}")

    async def tail_events(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Tail the JSONL event log asynchronously.

        Yields:
            Parsed event dictionaries
        """
        pos = 0

        def _read_from_pos(path: Path, start: int):
            """Read new lines from file starting at position."""
            out = []
            if not path.exists():
                return out

            with path.open("rb") as f:
                f.seek(start)
                for line in f:
                    out.append((f.tell(), line))
            return out

        while True:
            try:
                chunks = await asyncio.to_thread(_read_from_pos, self.log_path, pos)

                for new_pos, line in chunks:
                    pos = new_pos
                    line_str = line.decode("utf-8", errors="ignore").strip()

                    if not line_str:
                        continue

                    event = parse_event_line(line_str)
                    if event:
                        yield event

            except Exception as exc:
                logger.error(f"Error reading log: {exc}")
                self.stats["errors"] += 1
                await asyncio.sleep(0.5)
                continue

            await asyncio.sleep(0.5)

    async def process_event(self, event: Dict[str, Any]) -> None:
        """
        Process a single event by routing to appropriate agents.

        Args:
            event: Event dictionary to process
        """
        self.stats["events_processed"] += 1
        self.event_buffer.append(event)

        event_type = event.get("event_type")

        try:
            # Parallel processing: bus alert + tracking
            tasks = []

            # Bus notification agent
            if event_type == "bus_detected":
                tasks.append(
                    asyncio.create_task(
                        self._handle_bus_event(event)
                    )
                )

            # Object tracking agent
            if event_type == "object_detected" and self.tracking_agent:
                tasks.append(
                    asyncio.create_task(
                        self._handle_tracking_event(event)
                    )
                )

            # Wait for parallel tasks
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            # Periodic summarization (not parallel)
            if self.stats["events_processed"] % self.summary_interval == 0:
                await self._generate_summary()

        except Exception as exc:
            logger.error(f"Error processing event: {exc}")
            self.stats["errors"] += 1

    async def _handle_bus_event(self, event: Dict[str, Any]) -> None:
        """Handle bus detection event."""
        try:
            result = await asyncio.to_thread(
                self.bus_agent.process,
                event
            )

            if result.get("status") == "sent":
                self.stats["bus_alerts_sent"] += 1
                logger.info(f"Bus alert sent: {result['alert']['message']}")
            elif result.get("status") == "debounced":
                logger.debug("Bus alert debounced")
            else:
                logger.warning(f"Bus alert failed: {result.get('message')}")

        except Exception as exc:
            logger.error(f"Bus event handling failed: {exc}")

    async def _handle_tracking_event(self, event: Dict[str, Any]) -> None:
        """Handle object detection event for tracking."""
        try:
            result = await asyncio.to_thread(
                self.tracking_agent.process_detection,
                event
            )

            frame_id = result.get("frame_id")
            active_tracks = result.get("active_tracks", 0)

            if active_tracks > 0:
                logger.debug(
                    f"Frame {frame_id}: {active_tracks} active tracks"
                )

        except Exception as exc:
            logger.error(f"Tracking event handling failed: {exc}")

    async def _generate_summary(self) -> None:
        """Generate periodic summary of events."""
        try:
            # Get events from buffer
            events = list(self.event_buffer)

            if not events:
                return

            # Generate summary using LLM agent
            summary_result = await asyncio.to_thread(
                self.summary_agent.generate_summary,
                events,
                self.summary_window_min
            )

            self.stats["summaries_generated"] += 1

            # Log summary
            summary_text = summary_result.get("summary", "")
            llm_used = summary_result.get("metadata", {}).get("llm_used", False)
            method = "LLM" if llm_used else "rule-based"

            logger.info(f"\n{'='*60}\nSUMMARY ({method}):\n{summary_text}\n{'='*60}")
            logger.info(f"Generated summary using {method}")

            # Log statistics
            stats = summary_result.get("statistics", {})
            if stats:
                logger.info(
                    f"Stats: {stats.get('total_events')} events, "
                    f"{stats.get('unique_categories')} categories"
                )

            # Log patterns
            patterns = summary_result.get("patterns", {})
            if patterns.get("bus_sightings", 0) > 0:
                logger.warning(
                    f"⚠️  Bus sightings detected: {patterns['bus_sightings']}"
                )

        except Exception as exc:
            logger.error(f"Summary generation failed: {exc}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get coordinator statistics.

        Returns:
            Statistics dictionary
        """
        stats = dict(self.stats)

        # Add tracker stats if available
        if self.tracking_agent:
            tracker_stats = self.tracking_agent.get_statistics()
            stats["tracker"] = tracker_stats

        return stats

    async def run(self) -> None:
        """
        Main event loop - tail log and process events.
        """
        logger.info(f"Starting coordinator (model: {self.model_name})")
        logger.info("ObjectTrackingCoordinator running...")

        try:
            async for event in self.tail_events():
                await self.process_event(event)

        except KeyboardInterrupt:
            logger.info("Coordinator stopped by user")
        except Exception as exc:
            logger.error(f"Coordinator error: {exc}")
            raise
        finally:
            # Final summary
            if self.event_buffer:
                logger.info("Generating final summary...")
                await self._generate_summary()

            # Log final statistics
            stats = self.get_statistics()
            logger.info(f"Final statistics: {stats}")
            logger.info(f"Coordinator shutting down. Events processed: {stats['events_processed']}")


def main():
    """Entry point for running the coordinator."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Configuration from environment
    log_path = Path(os.environ.get("IMX500_LOG_PATH", Path.home() / "imx500_events.jsonl"))
    summary_window_min = int(os.environ.get("ADK_SUMMARY_WINDOW_MIN", "30"))
    summary_interval = int(os.environ.get("ADK_SUMMARY_INTERVAL", "200"))
    use_tracker = bool(int(os.environ.get("ADK_USE_TRACKER", "1")))
    model_name = os.environ.get("ADK_MODEL", "models/gemini-2.5-flash")

    # Check for API key
    if not os.environ.get("GEMINI_API_KEY"):
        logger.warning(
            "GEMINI_API_KEY not set. LLM summaries will fall back to rule-based. "
            "Set GEMINI_API_KEY for AI-powered summaries."
        )

    # Create and run coordinator
    coordinator = ObjectTrackingCoordinator(
        log_path=log_path,
        summary_window_min=summary_window_min,
        summary_interval=summary_interval,
        use_tracker=use_tracker,
        model_name=model_name
    )

    asyncio.run(coordinator.run())


if __name__ == "__main__":
    sys.exit(main())

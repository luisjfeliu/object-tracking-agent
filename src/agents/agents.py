#!/usr/bin/env python3
"""
agents.py

Simple agent skeletons that operate on the event log written by
pi_imx500_detector.py.
"""

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Iterator, List, Optional


LOG_FILE = Path.home() / "imx500_events.jsonl"


# =========================
# Helper types
# =========================

@dataclass
class Event:
    ts: datetime
    event_type: str
    details: Dict[str, Any]


def parse_event_line(line: str) -> Optional[Event]:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    ts_str = obj.get("ts")
    event_type = obj.get("event_type")
    details = obj.get("details", {})

    if not ts_str or not event_type:
        return None

    ts = datetime.fromisoformat(ts_str)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    return Event(ts=ts, event_type=event_type, details=details)


# =========================
# Event Ingestion Agent
# =========================

class EventIngestionAgent:
    """
    Watches the events log and yields new events as they appear.

    For real-time behavior, you can run `tail_events()` in a loop.
    For offline (Kaggle notebook) use, you can read the whole file once.
    """

    def __init__(self, log_path: Path = LOG_FILE):
        self.log_path = log_path

    def read_all_events(self) -> List[Event]:
        events: List[Event] = []
        if not self.log_path.exists():
            return events

        with self.log_path.open("r") as f:
            for line in f:
                ev = parse_event_line(line)
                if ev:
                    events.append(ev)
        return events

    def tail_events(self, poll_interval: float = 1.0) -> Iterator[Event]:
        """
        Generator that yields events appended to the log in near real-time.
        """
        # Start at end of file
        pos = 0
        if self.log_path.exists():
            with self.log_path.open("rb") as f:
                f.seek(0, 2)
                pos = f.tell()

        while True:
            if self.log_path.exists():
                with self.log_path.open("rb") as f:
                    f.seek(pos)
                    for line in f:
                        pos = f.tell()
                        line_str = line.decode("utf-8", errors="ignore")
                        ev = parse_event_line(line_str)
                        if ev:
                            yield ev
            time.sleep(poll_interval)


# =========================
# Bus Notification Agent
# =========================

class BusNotificationAgent:
    """
    Reacts to bus events produced by the Pi-side script.

    For now, just prints to console. Later you can:
      - send an email
      - call a messaging API
      - forward to an LLM for generating a nicer message
    """

    def handle_event(self, event: Event):
        if event.event_type != "bus_detected":
            return
        # Basic output for now
        print(f"[BUS ALERT] {event.ts.isoformat()} - details={event.details}")


# =========================
# Event Summarizer Agent
# =========================

class EventSummarizerAgent:
    """
    Summarizes events over a given time window.
    """

    def summarize(
        self,
        events: List[Event],
        window_minutes: int = 60,
        reference_time: Optional[datetime] = None,
    ) -> str:
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)

        window_start = reference_time - timedelta(minutes=window_minutes)
        in_window = [e for e in events if window_start <= e.ts <= reference_time]

        if not in_window:
            return f"No detections in the last {window_minutes} minutes."

        # Simple aggregation: count by category and type
        counts_by_category = {}
        counts_by_type = {}

        for e in in_window:
            if e.event_type == "object_detected":
                cat = e.details.get("category", "unknown")
                counts_by_category[cat] = counts_by_category.get(cat, 0) + 1
            elif e.event_type == "bus_detected":
                counts_by_type["bus_detected"] = counts_by_type.get("bus_detected", 0) + 1

        lines = []
        lines.append(f"Summary for last {window_minutes} minutes:")
        if counts_by_category:
            lines.append("  Object detections by category:")
            for cat, count in counts_by_category.items():
                lines.append(f"    - {cat}: {count}")
        if counts_by_type:
            lines.append("  Special events:")
            for etype, count in counts_by_type.items():
                lines.append(f"    - {etype}: {count}")

        # === Place where you’d call an LLM ===
        # You can take `in_window` and construct a richer prompt
        # with timestamps, categories, durations, etc.
        #
        # For example:
        #
        # prompt = build_prompt_from_events(in_window)
        # llm_summary = call_llm(prompt)
        # lines.append("")
        # lines.append("Natural-language summary:")
        # lines.append(llm_summary)
        #
        # For now, we'll just return the basic counts.

        return "\n".join(lines)


# =========================
# Manual test runner
# =========================

if __name__ == "__main__":
    ingestion = EventIngestionAgent()
    bus_agent = BusNotificationAgent()
    summarizer = EventSummarizerAgent()

    # Example: offline summary of last 60 minutes
    all_events = ingestion.read_all_events()
    print(summarizer.summarize(all_events, window_minutes=60))

    # Example: real-time bus notifications
    # (Uncomment if you want to watch events live)
    #
    # for ev in ingestion.tail_events():
    #     bus_agent.handle_event(ev)

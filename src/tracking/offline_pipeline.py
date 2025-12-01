#!/usr/bin/env python3
"""
offline_pipeline.py

Utility functions and a small CLI to replay the detection log produced by
`pi_imx500_detector.py`. This is intended for Kaggle/offline experimentation
where you may not have the camera attached but still want to exercise the
agent logic and the tracker.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from src.agents.agents import Event, EventIngestionAgent, EventSummarizerAgent
from src.tracking.tracker import MultiObjectTracker


def load_detection_events(log_path: Path) -> List[Event]:
    """Read all events and keep only object detections."""
    ingestion = EventIngestionAgent(log_path=log_path)
    events = ingestion.read_all_events()
    return [e for e in events if e.event_type == "object_detected"]


def group_detections_by_frame(events: List[Event]) -> List[Tuple[int, List[Dict]]]:
    grouped: Dict[int, List[Dict]] = defaultdict(list)
    for e in events:
        details = dict(e.details)
        details["ts"] = e.ts
        frame_id = int(details.get("frame_id", 0))
        grouped[frame_id].append(details)
    return sorted(grouped.items(), key=lambda kv: kv[0])


def replay_tracking(
    log_path: Path,
    output_path: Path | None = None,
    summary_window: int = 60,
) -> Tuple[List[Dict], str]:
    """
    Run tracker + summarizer over a saved log file.

    Returns (track_events, textual_summary).
    """
    detection_events = load_detection_events(log_path)
    tracker = MultiObjectTracker()
    summary_agent = EventSummarizerAgent()

    track_events: List[Dict] = []

    for frame_id, detections in group_detections_by_frame(detection_events):
        track_states = tracker.update(detections, frame_id)
        if not detections:
            ts = datetime.now(timezone.utc).isoformat()
        else:
            ts = min(d["ts"] for d in detections).isoformat()
        for track_state in track_states:
            track_events.append(
                {
                    "ts": ts,
                    "event_type": "track_update",
                    "details": track_state,
                }
            )

    if detection_events:
        reference_time = max(e.ts for e in detection_events)
    else:
        reference_time = datetime.now(timezone.utc)
    summary = summary_agent.summarize(
        detection_events,
        window_minutes=summary_window,
        reference_time=reference_time,
    )

    if output_path:
        with output_path.open("w") as f:
            for ev in track_events:
                f.write(json.dumps(ev) + "\n")

    return track_events, summary


def main():
    parser = argparse.ArgumentParser(description="Offline replay of IMX500 log with tracker/agents.")
    parser.add_argument(
        "--log",
        type=Path,
        default=Path.home() / "imx500_events.jsonl",
        help="Path to the JSONL log file produced by the Pi script.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional path to write tracker events as JSONL.",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=60,
        help="Window (minutes) for the summarizer agent.",
    )
    args = parser.parse_args()

    track_events, summary = replay_tracking(args.log, args.out, args.window)
    print(f"Replayed {len(track_events)} track updates from {args.log}")
    print(summary)
    if args.out:
        print(f"Wrote tracker events to {args.out}")


if __name__ == "__main__":
    main()

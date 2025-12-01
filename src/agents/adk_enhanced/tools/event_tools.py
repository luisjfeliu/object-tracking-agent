#!/usr/bin/env python3
"""
Event processing tools for the ingestion agent.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_event_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single JSONL event line.

    Args:
        line: JSON string from event log

    Returns:
        Parsed event dictionary or None if invalid
    """
    try:
        event = json.loads(line)

        # Validate required fields
        if "ts" not in event or "event_type" not in event:
            return None

        # Ensure timestamp is properly formatted
        ts_str = event["ts"]
        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        event["ts"] = ts.isoformat()

        return event
    except (json.JSONDecodeError, ValueError, KeyError):
        return None


def filter_events_by_type(
    events: List[Dict[str, Any]],
    event_types: List[str]
) -> List[Dict[str, Any]]:
    """
    Filter events by type.

    Args:
        events: List of event dictionaries
        event_types: List of event types to keep

    Returns:
        Filtered events
    """
    return [e for e in events if e.get("event_type") in event_types]


def filter_events_by_category(
    events: List[Dict[str, Any]],
    categories: List[str]
) -> List[Dict[str, Any]]:
    """
    Filter object detection events by category.

    Args:
        events: List of event dictionaries
        categories: List of categories to keep (e.g., "car", "person", "bus")

    Returns:
        Filtered events
    """
    filtered = []
    for event in events:
        if event.get("event_type") == "object_detected":
            category = event.get("details", {}).get("category")
            if category in categories:
                filtered.append(event)
        elif event.get("event_type") == "bus_detected":
            # Always include bus events
            filtered.append(event)
    return filtered


def count_events_by_category(
    events: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Count events by category.

    Args:
        events: List of event dictionaries

    Returns:
        Dictionary mapping category to count
    """
    counts = {}
    for event in events:
        if event.get("event_type") == "object_detected":
            category = event.get("details", {}).get("category", "unknown")
            counts[category] = counts.get(category, 0) + 1
        elif event.get("event_type") == "bus_detected":
            counts["bus"] = counts.get("bus", 0) + 1
    return counts


def get_event_time_range(
    events: List[Dict[str, Any]]
) -> Optional[Dict[str, str]]:
    """
    Get the time range of a list of events.

    Args:
        events: List of event dictionaries

    Returns:
        Dictionary with "start" and "end" timestamps or None
    """
    if not events:
        return None

    timestamps = []
    for event in events:
        ts_str = event.get("ts")
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str)
                timestamps.append(ts)
            except ValueError:
                continue

    if not timestamps:
        return None

    return {
        "start": min(timestamps).isoformat(),
        "end": max(timestamps).isoformat()
    }


# Tool registration for ADK
EVENT_TOOLS = [
    {
        "name": "parse_event_line",
        "description": "Parse a JSON line from the event log",
        "function": parse_event_line,
    },
    {
        "name": "filter_events_by_type",
        "description": "Filter events by event type",
        "function": filter_events_by_type,
    },
    {
        "name": "filter_events_by_category",
        "description": "Filter object detection events by category",
        "function": filter_events_by_category,
    },
    {
        "name": "count_events_by_category",
        "description": "Count events grouped by category",
        "function": count_events_by_category,
    },
    {
        "name": "get_event_time_range",
        "description": "Get the start and end time of event list",
        "function": get_event_time_range,
    },
]

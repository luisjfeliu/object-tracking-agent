#!/usr/bin/env python3
"""
Summary tools for the LLM-powered summarization agent.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


def aggregate_events_by_category(
    events: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Aggregate events grouped by category.

    Args:
        events: List of event dictionaries

    Returns:
        Aggregation summary
    """
    category_stats = {}

    for event in events:
        event_type = event.get("event_type")

        if event_type == "object_detected":
            details = event.get("details", {})
            category = details.get("category", "unknown")

            if category not in category_stats:
                category_stats[category] = {
                    "count": 0,
                    "avg_confidence": 0.0,
                    "max_confidence": 0.0,
                    "confidences": []
                }

            stats = category_stats[category]
            score = details.get("score", 0.0)

            stats["count"] += 1
            stats["confidences"].append(score)
            stats["max_confidence"] = max(stats["max_confidence"], score)

        elif event_type == "bus_detected":
            if "bus" not in category_stats:
                category_stats["bus"] = {
                    "count": 0,
                    "avg_confidence": 0.0,
                    "max_confidence": 0.0,
                    "confidences": []
                }

            details = event.get("details", {})
            score = details.get("score", 0.0)

            category_stats["bus"]["count"] += 1
            category_stats["bus"]["confidences"].append(score)
            category_stats["bus"]["max_confidence"] = max(
                category_stats["bus"]["max_confidence"], score
            )

    # Calculate averages
    for category, stats in category_stats.items():
        if stats["confidences"]:
            stats["avg_confidence"] = sum(stats["confidences"]) / len(stats["confidences"])
        del stats["confidences"]  # Remove raw list for cleaner output

    return {
        "total_events": len(events),
        "categories": category_stats,
        "unique_categories": len(category_stats)
    }


def aggregate_events_by_time(
    events: List[Dict[str, Any]],
    window_minutes: int = 5
) -> List[Dict[str, Any]]:
    """
    Aggregate events into time windows.

    Args:
        events: List of event dictionaries
        window_minutes: Size of time window in minutes

    Returns:
        List of time window summaries
    """
    if not events:
        return []

    # Parse timestamps
    timestamped_events = []
    for event in events:
        ts_str = event.get("ts")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str)
            timestamped_events.append((ts, event))
        except ValueError:
            continue

    if not timestamped_events:
        return []

    # Sort by time
    timestamped_events.sort(key=lambda x: x[0])

    # Create windows
    windows = []
    current_window_start = timestamped_events[0][0]
    current_window_events = []

    for ts, event in timestamped_events:
        window_end = current_window_start + timedelta(minutes=window_minutes)

        if ts <= window_end:
            current_window_events.append(event)
        else:
            # Complete current window
            if current_window_events:
                window_summary = aggregate_events_by_category(current_window_events)
                window_summary["window_start"] = current_window_start.isoformat()
                window_summary["window_end"] = window_end.isoformat()
                windows.append(window_summary)

            # Start new window
            current_window_start = ts
            current_window_events = [event]

    # Add final window
    if current_window_events:
        window_end = current_window_start + timedelta(minutes=window_minutes)
        window_summary = aggregate_events_by_category(current_window_events)
        window_summary["window_start"] = current_window_start.isoformat()
        window_summary["window_end"] = window_end.isoformat()
        windows.append(window_summary)

    return windows


def detect_patterns(
    events: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Detect patterns and anomalies in events.

    Args:
        events: List of event dictionaries

    Returns:
        Pattern detection results
    """
    patterns = {
        "high_frequency_categories": [],
        "low_confidence_detections": [],
        "bus_sightings": 0,
        "unusual_activity": []
    }

    # Aggregate by category
    agg = aggregate_events_by_category(events)
    categories = agg.get("categories", {})

    # High frequency categories (>10% of total)
    total = agg.get("total_events", 0)
    if total > 0:
        for category, stats in categories.items():
            count = stats["count"]
            percentage = (count / total) * 100
            if percentage > 10:
                patterns["high_frequency_categories"].append({
                    "category": category,
                    "count": count,
                    "percentage": round(percentage, 1)
                })

    # Low confidence detections
    for event in events:
        details = event.get("details", {})
        score = details.get("score", 1.0)
        if score < 0.6:  # Low confidence threshold
            patterns["low_confidence_detections"].append({
                "event_type": event.get("event_type"),
                "category": details.get("category"),
                "confidence": score,
                "timestamp": event.get("ts")
            })

    # Bus sightings
    patterns["bus_sightings"] = categories.get("bus", {}).get("count", 0)

    # Unusual activity: sudden spike in detections
    time_windows = aggregate_events_by_time(events, window_minutes=5)
    if len(time_windows) > 1:
        avg_events = sum(w["total_events"] for w in time_windows) / len(time_windows)
        for window in time_windows:
            if window["total_events"] > avg_events * 2:  # 2x average
                patterns["unusual_activity"].append({
                    "window_start": window["window_start"],
                    "event_count": window["total_events"],
                    "note": "Spike detected (2x average)"
                })

    return patterns


def generate_summary_prompt(
    events: List[Dict[str, Any]],
    window_minutes: int = 30
) -> str:
    """
    Generate a structured prompt for LLM summarization.

    Args:
        events: List of event dictionaries
        window_minutes: Time window for summary

    Returns:
        Formatted prompt string
    """
    agg = aggregate_events_by_category(events)
    patterns = detect_patterns(events)

    # Simplified prompt to avoid hitting token limits
    cat_summary = ", ".join([f"{c.upper()}: {s['count']}" for c, s in agg.get("categories", {}).items()])

    prompt = f"""Summarize these object detection events from the last {window_minutes} minutes:

Total: {agg['total_events']} events
Categories: {cat_summary}
"""

    if patterns["bus_sightings"] > 0:
        prompt += f"⚠️ ALERT: {patterns['bus_sightings']} school bus detected!\n"

    if patterns["unusual_activity"]:
        prompt += f"Unusual activity in {len(patterns['unusual_activity'])} time windows\n"

    prompt += "\nProvide a brief summary (2-3 sentences) with key insights and recommendations."

    return prompt


def format_summary_output(
    llm_response: str,
    events: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format the final summary output.

    Args:
        llm_response: Response from LLM
        events: Original event list
        metadata: Additional metadata

    Returns:
        Formatted summary dictionary
    """
    agg = aggregate_events_by_category(events)
    patterns = detect_patterns(events)

    time_range = None
    if events:
        timestamps = []
        for e in events:
            ts_str = e.get("ts")
            if ts_str:
                try:
                    timestamps.append(datetime.fromisoformat(ts_str))
                except ValueError:
                    pass

        if timestamps:
            time_range = {
                "start": min(timestamps).isoformat(),
                "end": max(timestamps).isoformat()
            }

    return {
        "summary": llm_response,
        "statistics": agg,
        "patterns": patterns,
        "time_range": time_range,
        "metadata": metadata or {}
    }


# Tool registration for ADK
SUMMARY_TOOLS = [
    {
        "name": "aggregate_events_by_category",
        "description": "Aggregate events grouped by object category",
        "function": aggregate_events_by_category,
    },
    {
        "name": "aggregate_events_by_time",
        "description": "Aggregate events into time windows",
        "function": aggregate_events_by_time,
    },
    {
        "name": "detect_patterns",
        "description": "Detect patterns and anomalies in events",
        "function": detect_patterns,
    },
    {
        "name": "generate_summary_prompt",
        "description": "Generate structured prompt for LLM summarization",
        "function": generate_summary_prompt,
    },
    {
        "name": "format_summary_output",
        "description": "Format final summary output with statistics",
        "function": format_summary_output,
    },
]

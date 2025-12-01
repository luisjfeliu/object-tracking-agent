#!/usr/bin/env python3
"""
Tracking tools for the object tracking agent.
"""

from typing import Any, Dict, List, Optional
import sys
from pathlib import Path

# Import the existing tracker
REPO_ROOT = Path(__file__).resolve().parents[4]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from src.tracking.tracker import MultiObjectTracker, Track


# Global tracker instance (stateful)
_tracker: Optional[MultiObjectTracker] = None


def initialize_tracker(
    iou_threshold: float = 0.3,
    max_missed: int = 8
) -> Dict[str, Any]:
    """
    Initialize the multi-object tracker.

    Args:
        iou_threshold: IoU threshold for matching
        max_missed: Max frames without match before dropping track

    Returns:
        Status dictionary
    """
    global _tracker
    _tracker = MultiObjectTracker(
        iou_threshold=iou_threshold,
        max_missed=max_missed
    )
    return {
        "status": "initialized",
        "iou_threshold": iou_threshold,
        "max_missed": max_missed
    }


def update_tracker(
    detections: List[Dict[str, Any]],
    frame_id: int
) -> List[Dict[str, Any]]:
    """
    Update tracker with new detections.

    Args:
        detections: List of detection dictionaries
        frame_id: Current frame ID

    Returns:
        List of current tracks with IDs
    """
    global _tracker

    if _tracker is None:
        initialize_tracker()

    return _tracker.update(detections, frame_id)


def get_active_tracks() -> List[Dict[str, Any]]:
    """
    Get all currently active tracks.

    Returns:
        List of track dictionaries
    """
    global _tracker

    if _tracker is None:
        return []

    return [track.to_event_details() for track in _tracker.tracks.values()]


def get_track_by_id(track_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a specific track by ID.

    Args:
        track_id: Track ID to retrieve

    Returns:
        Track dictionary or None if not found
    """
    global _tracker

    if _tracker is None or track_id not in _tracker.tracks:
        return None

    return _tracker.tracks[track_id].to_event_details()


def get_tracks_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Get all tracks for a specific category.

    Args:
        category: Category to filter by (e.g., "car", "person", "bus")

    Returns:
        List of track dictionaries
    """
    global _tracker

    if _tracker is None:
        return []

    return [
        track.to_event_details()
        for track in _tracker.tracks.values()
        if track.category == category
    ]


def get_tracker_statistics() -> Dict[str, Any]:
    """
    Get tracker statistics.

    Returns:
        Dictionary with tracker stats
    """
    global _tracker

    if _tracker is None:
        return {
            "initialized": False,
            "active_tracks": 0
        }

    tracks = list(_tracker.tracks.values())

    # Count by category
    category_counts = {}
    for track in tracks:
        cat = track.category
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Track ages
    ages = [track.age() for track in tracks]

    return {
        "initialized": True,
        "active_tracks": len(tracks),
        "next_track_id": _tracker._next_id,
        "tracks_by_category": category_counts,
        "avg_track_age": sum(ages) / len(ages) if ages else 0,
        "max_track_age": max(ages) if ages else 0,
    }


def reset_tracker() -> Dict[str, str]:
    """
    Reset the tracker state.

    Returns:
        Status dictionary
    """
    global _tracker
    _tracker = None
    return {"status": "reset"}


# Tool registration for ADK
TRACKING_TOOLS = [
    {
        "name": "initialize_tracker",
        "description": "Initialize the multi-object tracker with config",
        "function": initialize_tracker,
    },
    {
        "name": "update_tracker",
        "description": "Update tracker with new detections from frame",
        "function": update_tracker,
    },
    {
        "name": "get_active_tracks",
        "description": "Get all currently active tracks",
        "function": get_active_tracks,
    },
    {
        "name": "get_track_by_id",
        "description": "Get specific track by ID",
        "function": get_track_by_id,
    },
    {
        "name": "get_tracks_by_category",
        "description": "Get tracks filtered by category",
        "function": get_tracks_by_category,
    },
    {
        "name": "get_tracker_statistics",
        "description": "Get tracker statistics and metrics",
        "function": get_tracker_statistics,
    },
    {
        "name": "reset_tracker",
        "description": "Reset tracker state",
        "function": reset_tracker,
    },
]

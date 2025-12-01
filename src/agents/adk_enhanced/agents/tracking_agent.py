#!/usr/bin/env python3
"""
Object tracking agent - maintains consistent track IDs across frames.
"""

import logging
from typing import Any, Dict, List, Optional

from ..tools.tracking_tools import (
    initialize_tracker,
    update_tracker,
    get_active_tracks,
    get_tracker_statistics,
    get_tracks_by_category
)


logger = logging.getLogger(__name__)


def create_tracking_agent():
    """
    Create the object tracking agent.

    This agent maintains consistent track IDs for detected objects.
    """
    return ObjectTrackingHandler()


class ObjectTrackingHandler:
    """Handler for object tracking logic."""

    def __init__(self):
        self._initialized = False

    def ensure_initialized(self):
        """Ensure tracker is initialized."""
        if not self._initialized:
            initialize_tracker()
            self._initialized = True
            logger.info("Object tracker initialized")

    def process_detection(
        self,
        event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process an object detection event and update tracks.

        Args:
            event: Object detection event

        Returns:
            Updated track information
        """
        self.ensure_initialized()

        details = event.get("details", {})
        frame_id = details.get("frame_id", 0)

        # Convert single detection to list format
        detections = [details]

        # Update tracker
        tracks = update_tracker(detections, frame_id)

        return {
            "frame_id": frame_id,
            "active_tracks": len(tracks),
            "tracks": tracks
        }

    def process_frame(
        self,
        detections: List[Dict[str, Any]],
        frame_id: int
    ) -> Dict[str, Any]:
        """
        Process multiple detections from a single frame.

        Args:
            detections: List of detection dictionaries
            frame_id: Frame ID

        Returns:
            Updated track information
        """
        self.ensure_initialized()

        tracks = update_tracker(detections, frame_id)

        return {
            "frame_id": frame_id,
            "detections_count": len(detections),
            "active_tracks": len(tracks),
            "tracks": tracks
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get tracker statistics.

        Returns:
            Tracker statistics
        """
        if not self._initialized:
            return {"initialized": False}

        return get_tracker_statistics()

    def get_category_tracks(self, category: str) -> List[Dict[str, Any]]:
        """
        Get tracks for a specific category.

        Args:
            category: Category to filter by

        Returns:
            List of tracks
        """
        if not self._initialized:
            return []

        return get_tracks_by_category(category)

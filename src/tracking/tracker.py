#!/usr/bin/env python3
"""
tracker.py

Lightweight multi-object tracker that can run on the event stream produced by
the Pi detector. Uses IoU matching to keep consistent track IDs across frames.
Designed to stay simple so it can run on constrained hardware or inside a
Kaggle notebook without the camera attached.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


Detection = Dict[str, Any]
BBox = List[float]  # [x_min, y_min, x_max, y_max] in pixel or normalized coords


def iou(box_a: BBox, box_b: BBox) -> float:
    """Intersection over Union for two boxes."""
    if len(box_a) != 4 or len(box_b) != 4:
        return 0.0

    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    if union <= 0.0:
        return 0.0
    return inter_area / union


@dataclass
class Track:
    track_id: int
    category: str
    bbox: BBox
    score: float
    start_frame: int
    last_frame: int
    misses: int = 0

    def age(self) -> int:
        return self.last_frame - self.start_frame + 1

    def to_event_details(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "category": self.category,
            "bbox": self.bbox,
            "score": self.score,
            "start_frame": self.start_frame,
            "last_frame": self.last_frame,
            "misses": self.misses,
            "age": self.age(),
        }


class MultiObjectTracker:
    """
    Simple tracker that maintains identities using greedy IoU matching.

    It prefers matching detections to tracks of the same category, and drops
    tracks after `max_missed` frames without a match.
    """

    def __init__(
        self,
        iou_threshold: float = 0.3,
        max_missed: int = 8,
    ):
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self.tracks: Dict[int, Track] = {}
        self._next_id = 1

    def _new_track(self, det: Detection, frame_id: int) -> Track:
        track = Track(
            track_id=self._next_id,
            category=det.get("category", "unknown"),
            bbox=det.get("bbox", [0.0, 0.0, 0.0, 0.0]),
            score=float(det.get("score", 0.0)),
            start_frame=frame_id,
            last_frame=frame_id,
        )
        self.tracks[track.track_id] = track
        self._next_id += 1
        return track

    def _match_detection(
        self,
        det: Detection,
        candidate_track_ids: Optional[List[int]] = None,
    ) -> Optional[int]:
        best_iou = 0.0
        best_track_id: Optional[int] = None
        det_box = det.get("bbox")
        det_cat = det.get("category")
        if det_box is None:
            return None

        iterable = candidate_track_ids if candidate_track_ids is not None else list(self.tracks.keys())
        for track_id in iterable:
            track = self.tracks[track_id]
            if det_cat and track.category != det_cat:
                continue  # do not mix categories
            candidate_iou = iou(det_box, track.bbox)
            if candidate_iou > best_iou:
                best_iou = candidate_iou
                best_track_id = track_id

        if best_track_id is not None and best_iou >= self.iou_threshold:
            return best_track_id
        return None

    def update(self, detections: List[Detection], frame_id: int) -> List[Dict[str, Any]]:
        """
        Update tracker state with detections from one frame.

        Returns a list of track dictionaries that describe the current state.
        """
        matched_track_ids = set()
        matched_detection_indices = set()
        available_tracks = list(self.tracks.keys())

        # Associate detections to existing tracks (greedy IoU)
        for idx, det in enumerate(detections or []):
            match_id = self._match_detection(det, available_tracks)
            if match_id is None:
                continue
            track = self.tracks[match_id]
            track.bbox = det.get("bbox", track.bbox)
            track.score = float(det.get("score", track.score))
            track.last_frame = frame_id
            track.misses = 0
            matched_track_ids.add(match_id)
            matched_detection_indices.add(idx)
            if match_id in available_tracks:
                available_tracks.remove(match_id)

        # Create new tracks for unmatched detections
        for idx, det in enumerate(detections or []):
            if idx in matched_detection_indices:
                continue
            self._new_track(det, frame_id)

        # Increment miss counts for unmatched tracks and drop stale ones
        to_remove = []
        for track_id, track in self.tracks.items():
            if track_id in matched_track_ids:
                continue
            track.misses += 1
            if track.misses > self.max_missed:
                to_remove.append(track_id)
        for track_id in to_remove:
            del self.tracks[track_id]

        return [track.to_event_details() for track in self.tracks.values()]

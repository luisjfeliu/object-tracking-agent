#!/usr/bin/env python3
"""
Image capture tools for saving frames on important detections.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np


logger = logging.getLogger(__name__)


def save_detection_image(
    frame: np.ndarray,
    detection: Dict[str, Any],
    output_dir: Optional[Path] = None,
    prefix: str = "bus"
) -> Optional[str]:
    """
    Save a frame with detection bounding box overlay.

    Args:
        frame: Image frame as numpy array
        detection: Detection dictionary with bbox, category, score
        output_dir: Output directory (default: ~/imx500_images/)
        prefix: Filename prefix

    Returns:
        Path to saved image, or None if save failed
    """
    try:
        # Import cv2 only when needed
        import cv2
    except ImportError:
        logger.warning("opencv-python not installed, cannot save images")
        return None

    # Setup output directory
    if output_dir is None:
        output_dir = Path.home() / "imx500_images"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    category = detection.get('category', 'unknown')
    score = detection.get('score', 0.0)
    filename = f"{prefix}_{category}_{score:.2f}_{timestamp}.jpg"
    output_path = output_dir / filename

    # Draw bounding box if available
    frame_copy = frame.copy()
    bbox = detection.get('bbox')

    if bbox and len(bbox) == 4:
        x, y, w, h = [int(v) for v in bbox]

        # Draw rectangle
        cv2.rectangle(
            frame_copy,
            (x, y),
            (x + w, y + h),
            color=(0, 255, 0),  # Green
            thickness=2
        )

        # Add label
        label = f"{category.upper()} {score:.2f}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(
            frame_copy,
            (x, y - label_size[1] - 5),
            (x + label_size[0], y),
            (0, 255, 0),
            -1
        )
        cv2.putText(
            frame_copy,
            label,
            (x, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1
        )

    # Save image
    cv2.imwrite(str(output_path), frame_copy)
    logger.info(f"Saved detection image: {output_path}")

    return str(output_path)


def save_frame_raw(
    frame: np.ndarray,
    output_dir: Optional[Path] = None,
    prefix: str = "frame"
) -> Optional[str]:
    """
    Save a raw frame without annotations.

    Args:
        frame: Image frame as numpy array
        output_dir: Output directory (default: ~/imx500_images/)
        prefix: Filename prefix

    Returns:
        Path to saved image, or None if save failed
    """
    try:
        import cv2
    except ImportError:
        logger.warning("opencv-python not installed, cannot save images")
        return None

    if output_dir is None:
        output_dir = Path.home() / "imx500_images"

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{prefix}_{timestamp}.jpg"
    output_path = output_dir / filename

    cv2.imwrite(str(output_path), frame)
    logger.info(f"Saved raw frame: {output_path}")

    return str(output_path)


def cleanup_old_images(
    output_dir: Optional[Path] = None,
    max_age_hours: int = 24,
    max_count: int = 1000
) -> int:
    """
    Clean up old detection images.

    Args:
        output_dir: Directory to clean (default: ~/imx500_images/)
        max_age_hours: Remove images older than this many hours
        max_count: Keep only the most recent N images

    Returns:
        Number of files deleted
    """
    if output_dir is None:
        output_dir = Path.home() / "imx500_images"

    if not output_dir.exists():
        return 0

    import time

    files = list(output_dir.glob("*.jpg"))

    # Sort by modification time
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    deleted_count = 0
    now = time.time()
    max_age_seconds = max_age_hours * 3600

    for idx, file_path in enumerate(files):
        # Delete if too old
        age = now - file_path.stat().st_mtime
        if age > max_age_seconds:
            file_path.unlink()
            deleted_count += 1
            continue

        # Delete if beyond max count
        if idx >= max_count:
            file_path.unlink()
            deleted_count += 1

    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old detection images")

    return deleted_count


# Tool registration for ADK
IMAGE_TOOLS = [
    {
        "name": "save_detection_image",
        "description": "Save frame with detection overlay",
        "function": save_detection_image,
    },
    {
        "name": "save_frame_raw",
        "description": "Save raw frame without annotations",
        "function": save_frame_raw,
    },
    {
        "name": "cleanup_old_images",
        "description": "Clean up old detection images",
        "function": cleanup_old_images,
    },
]

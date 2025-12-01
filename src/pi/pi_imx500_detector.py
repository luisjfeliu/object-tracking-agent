#!/usr/bin/env python3
"""
pi_imx500_detector.py

Run object detection on the Raspberry Pi AI Camera (IMX500),
log detections for cars/people/animals/bus, and trigger a hook
whenever a bus (proxy for school bus) is detected.

Logs to: ~/imx500_events.jsonl  (JSON lines)
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import requests
from picamera2 import Picamera2
from picamera2.devices.imx500 import IMX500


# =========================
# Configuration
# =========================

# Path to the IMX500 model (MobileNet SSD object detection model from imx500-all)
MODEL_PATH = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"

# Where to store logged events
LOG_FILE = Path.home() / "imx500_events.jsonl"

# Minimum confidence score to keep a detection
CONFIDENCE_THRESHOLD = 0.5

# Optional webhook for bus detections (can point to your agent backend later)
BUS_WEBHOOK_URL = os.environ.get("BUS_WEBHOOK_URL")  # e.g. "http://desktop:8000/bus"

# Optional forwarding of all events to a remote server
EVENT_FORWARD_URL = os.environ.get("IMX500_FORWARD_URL")  # e.g. "http://desktop:8000/event"

# Optional saving of frames when detections occur
SAVE_IMAGES = bool(int(os.environ.get("IMX500_SAVE_IMAGES", "0")))
IMAGE_DIR = Path(os.environ.get("IMX500_IMAGE_DIR", Path.home() / "imx500_images"))

# Map raw labels → high-level categories we care about
TARGET_LABELS = {
    "person": "person",
    "bicycle": "person",
    "car": "car",
    "truck": "car",
    "motorbike": "car",
    "bus": "bus",  # treat bus as school bus (MVP); refine later with custom model
    "train": "car",
    "dog": "animal",
    "cat": "animal",
    "bird": "animal",
    "horse": "animal",
    "sheep": "animal",
    "cow": "animal",
}

# COCO labels shipped with the bundled SSD MobileNet model (see imx500 intrinsics)
COCO_LABELS = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "-",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "-",
    "backpack",
    "umbrella",
    "-",
    "-",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "-",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "-",
    "dining table",
    "-",
    "-",
    "toilet",
    "-",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "-",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
]


# =========================
# Utility functions
# =========================

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def current_timestamp_iso() -> str:
    """Return current time in ISO 8601 (UTC)."""
    return datetime.now(timezone.utc).isoformat()


def forward_event(event_record: Dict[str, Any]) -> None:
    """Forward an event to a remote server if configured."""
    if not EVENT_FORWARD_URL:
        return
    try:
        requests.post(EVENT_FORWARD_URL, json=event_record, timeout=1.5)
    except Exception as exc:
        logging.debug("Forward event failed: %s", exc)


def log_event(event: Dict[str, Any]):
    """Append a single event as JSON to the log file and optionally forward it."""
    event_record = {
        **event,
        "ts": current_timestamp_iso(),
    }
    line = json.dumps(event_record, separators=(",", ":"))
    with LOG_FILE.open("a") as f:
        f.write(line + "\n")
    forward_event(event_record)


def save_frame(request, frame_id: int, label: str) -> None:
    """
    Optionally save the current frame to disk.
    Uses Picamera2 request.save to avoid extra dependencies.
    """
    if not SAVE_IMAGES:
        return
    try:
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        filename = IMAGE_DIR / f"frame_{frame_id:06d}_{label}.jpg"
        request.save("main", filename.as_posix())
        logging.info("Saved frame to %s", filename)
    except Exception as exc:
        logging.debug("Failed to save frame: %s", exc)


def process_detections(
    detections: List[Dict[str, Any]],
    frame_id: int,
) -> List[Dict[str, Any]]:
    """
    Convert raw detections from IMX500 into filtered events.

    Expected detection format per item (approx):
        {
            "label": "person",
            "score": 0.92,
            "bbox": [x_min, y_min, x_max, y_max]
        }
    """
    events = []

    for det in detections or []:
        label_id = det.get("label_id")
        label = det.get("label") or (COCO_LABELS[label_id] if label_id is not None and label_id < len(COCO_LABELS) else None)
        score = float(det.get("score", 0.0))
        bbox = det.get("bbox")

        if score < CONFIDENCE_THRESHOLD:
            continue
        if label not in TARGET_LABELS:
            continue

        category = TARGET_LABELS[label]
        event = {
            "frame_id": frame_id,
            "raw_label": label,
            "category": category,
            "score": score,
            "bbox": bbox,
        }
        events.append(event)

    return events


def _maybe_rescale_scores(scores_arr: np.ndarray) -> np.ndarray:
    """
    Scores can come as fixed-point or already float. If they look small (e.g., ints
    with max > 1), scale down by 4096. Otherwise return as-is.
    """
    if scores_arr.size == 0:
        return scores_arr
    max_val = float(scores_arr.max())
    if max_val > 1.5:
        return scores_arr * (1.0 / 4096.0)
    return scores_arr


def decode_imx500_outputs(
    outputs: List[Any],
    metadata: Dict[str, Any],
    picam2: Picamera2,
    imx500: IMX500,
) -> List[Dict[str, Any]]:
    """
    Decode IMX500 raw outputs into detection dictionaries.

    For the MobileNet SSD model shipped with imx500-all, the network produces 4 tensors:
      - boxes: shape (100, 4) int16, normalized coords in sensor space scaled by 4096
      - scores: shape (100,) int16 or int32, scaled by 4096
      - classes: shape (100,) uint8 class IDs
      - valid count: shape (1,) indicates how many entries are populated
    """
    if not outputs or len(outputs) < 4:
        return []

    try:
        boxes_raw, scores_raw, classes_raw, count_raw = outputs[:4]
    except Exception:
        return []

    # Boxes come as signed ints scaled by 4096 in sensor space
    boxes_arr = np.array(boxes_raw).reshape(-1, 4)

    scores_arr = _maybe_rescale_scores(np.array(scores_raw).flatten())
    classes_arr = np.array(classes_raw).flatten()
    count = int(np.array(count_raw).flatten()[0]) if len(np.array(count_raw).flatten()) else len(scores_arr)

    detections: List[Dict[str, Any]] = []
    for i in range(min(count, len(boxes_arr), len(scores_arr), len(classes_arr))):
        score = float(scores_arr[i])
        cls_id = int(classes_arr[i])
        # Skip invalid/zero boxes
        if score <= 0:
            continue

        # Convert coords to output image space
        # Pass raw coords to SDK converter; it will handle scaling to output space.
        coords = tuple(boxes_arr[i])
        try:
            x0, y0, x1, y1 = imx500.convert_inference_coords(coords, metadata, picam2, stream="main")
        except Exception:
            # fallback: treat as normalized
            norm = boxes_arr[i] * (1.0 / 4096.0)
            x0, y0, x1, y1 = norm

        detections.append(
            {
                "label_id": cls_id,
                "score": score,
                "bbox": [float(x0), float(y0), float(x1), float(y1)],
            }
        )

    return detections


def try_enable_ai_metadata(picam2: Picamera2, imx500: IMX500):
    """
    Some IMX500 SDK versions require registering AI results into metadata explicitly.
    We try a few known method names in a safe way.
    """
    candidates = [
        "configure_ai_results",
        "enable_ai_results",
        "configure_ai_output",
        "configure_ai",
        "register_ai_results",
    ]
    for name in candidates:
        if hasattr(imx500, name):
            try:
                getattr(imx500, name)(picam2)
                logging.info("Called imx500.%s to enable AI metadata.", name)
                return
            except Exception as exc:
                logging.warning("imx500.%s failed: %s", name, exc)
    logging.info("No explicit AI metadata enable method found on IMX500 object.")


def handle_bus_event(event: Dict[str, Any]):
    """
    Handle a bus detection (MVP: treat 'bus' as 'school bus').

    Later you can:
      - capture a frame thumbnail
      - send richer data to agent
      - debounce multiple frames of the same bus, etc.
    """
    logging.info("BUS DETECTED (treating as school bus): %s", event)

    # Log a dedicated bus event
    bus_event = {
        "event_type": "bus_detected",
        "details": event,
    }
    log_event(bus_event)

    if BUS_WEBHOOK_URL:
        try:
            requests.post(BUS_WEBHOOK_URL, json=bus_event, timeout=2)
        except Exception as exc:
            logging.warning("Failed to POST bus event webhook: %s", exc)


# =========================
# Main loop
# =========================

class GracefulExit(Exception):
    pass


def _signal_handler(signum, frame):
    raise GracefulExit()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    logging.info("Starting IMX500 object detector")

    # 1. IMX500 MUST be created before Picamera2()
    imx500 = IMX500(MODEL_PATH)
    imx500.show_network_fw_progress_bar()

    # 2. Create and configure Picamera2
    picam2 = Picamera2()

    # Optional: if you kept this helper around; it's safe to remove if you want
    try:
        try_enable_ai_metadata(picam2, imx500)
    except NameError:
        # Helper not defined; that's fine, it's purely optional
        logging.debug("try_enable_ai_metadata not defined; skipping.")

    # Many SDK builds require linking the input tensor to Picamera2; try both signatures
    try:
        imx500.input_tensor_image(picam2)
        logging.info("Called imx500.input_tensor_image(picam2) to enable AI pipeline.")
    except TypeError:
        try:
            imx500.input_tensor_image()
            logging.info("Called imx500.input_tensor_image() (no args).")
        except Exception as exc:
            logging.warning("imx500.input_tensor_image failed or missing: %s", exc)
    except Exception as exc:
        logging.warning("imx500.input_tensor_image failed or missing: %s", exc)

    config = picam2.create_preview_configuration()
    picam2.configure(config)
    picam2.start()

    frame_id = 0

    try:
        while True:
            # 3. Capture a full request so frame + metadata + AI outputs are coherent
            req = picam2.capture_request()
            try:
                metadata = req.get_metadata()

                # Optionally grab the frame if you want to save / debug images later
                # (not used by the rest of this function, but handy to keep around)
                # frame = req.make_array("main")

                if frame_id == 0:
                    # First-frame debug info
                    logging.info("Metadata keys: %s", list(metadata.keys()))
                    shapes = imx500.get_output_shapes(metadata)
                    logging.info("IMX500 output shapes on first frame: %s", shapes)

                raw_outputs = imx500.get_outputs(metadata)

                if raw_outputs is None:
                    logging.debug(
                        "Frame %d: no AI outputs present in metadata", frame_id
                    )
                    detections = []
                else:
                    detections = decode_imx500_outputs(
                        raw_outputs,
                        metadata,
                        picam2,
                        imx500,
                    )

                # Turn detections into higher-level events (e.g., cars, people, bus, etc.)
                events = process_detections(detections, frame_id)

                if events:
                    logging.info(
                        "Frame %d: %d events after processing",
                        frame_id,
                        len(events),
                    )
                    for event in events:
                        log_event(event)

                        # Bus-specific handling; adjust key name if your event schema differs
                        if event.get("category") == "bus":
                            handle_bus_event(event)

                        # Optionally save the frame for the first detection in this frame
                        save_frame(req, frame_id, event.get("raw_label", "det"))

                frame_id += 1

            finally:
                # Always release the request so buffers are returned to the camera
                req.release()

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received; stopping detector.")
    finally:
        try:
            picam2.stop()
        except Exception:
            pass
        try:
            picam2.close()
        except Exception:
            pass
        logging.info("IMX500 detector shut down cleanly.")



if __name__ == "__main__":
    sys.exit(main())

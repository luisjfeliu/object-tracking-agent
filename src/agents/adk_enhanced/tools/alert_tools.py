#!/usr/bin/env python3
"""
Alert tools for the bus notification agent.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import aiohttp


# Debounce state: track recent alerts to prevent duplicates
_recent_alerts: Dict[str, datetime] = {}
_debounce_seconds = 30  # Minimum time between alerts (default)

# Enhanced tracking: track bus positions and IDs
_bus_tracks: Dict[int, Dict[str, Any]] = {}  # track_id -> {last_seen, bbox, alerts_sent}


def format_bus_alert_message(event: Dict[str, Any], track_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Format a bus detection event into an alert message.

    Args:
        event: Bus detection event dictionary
        track_id: Optional tracking ID for this bus

    Returns:
        Formatted alert payload
    """
    details = event.get("details", {})

    alert = {
        "alert_type": "school_bus_detected",
        "timestamp": event.get("ts", datetime.now(timezone.utc).isoformat()),
        "message": f"School bus detected with confidence {details.get('score', 0):.2f}",
        "details": {
            "frame_id": details.get("frame_id"),
            "category": details.get("category", "bus"),
            "confidence": details.get("score"),
            "bounding_box": details.get("bbox"),
            "raw_label": details.get("raw_label", "bus"),
            "track_id": track_id,  # Include tracking ID if available
            "image_path": details.get("image_path"),  # Path to captured image
        }
    }

    # Add rich message if we have tracking info
    if track_id is not None:
        alert["message"] = f"School bus (Track #{track_id}) detected with confidence {details.get('score', 0):.2f}"

    return alert


def should_send_alert(
    event: Dict[str, Any],
    debounce_key: str = "default",
    track_id: Optional[int] = None,
    debounce_window: int = None
) -> bool:
    """
    Check if an alert should be sent based on enhanced debounce logic.

    Args:
        event: Event to check
        debounce_key: Key for tracking this alert type
        track_id: Optional tracking ID for spatial debouncing
        debounce_window: Custom debounce window in seconds (overrides default)

    Returns:
        True if alert should be sent, False if debounced
    """
    global _recent_alerts, _bus_tracks, _debounce_seconds

    now = datetime.now(timezone.utc)
    window = debounce_window if debounce_window is not None else _debounce_seconds

    # Enhanced: Track-based debouncing (if we have a track_id)
    if track_id is not None:
        if track_id in _bus_tracks:
            track_info = _bus_tracks[track_id]
            time_since_last = (now - track_info['last_seen']).total_seconds()

            # Only send alert once per track per debounce window
            if time_since_last < window:
                logging.debug(
                    f"Alert debounced for track {track_id}: "
                    f"last seen {time_since_last:.1f}s ago"
                )
                return False

            # Update track
            track_info['last_seen'] = now
            track_info['alerts_sent'] += 1
        else:
            # New track - send alert
            details = event.get("details", {})
            _bus_tracks[track_id] = {
                'last_seen': now,
                'bbox': details.get('bbox'),
                'alerts_sent': 1,
                'first_seen': now
            }

        return True

    # Fallback: Time-based debouncing (original logic)
    if debounce_key in _recent_alerts:
        last_alert = _recent_alerts[debounce_key]
        time_since_last = (now - last_alert).total_seconds()

        if time_since_last < window:
            logging.debug(
                f"Alert debounced: {debounce_key} "
                f"(last alert {time_since_last:.1f}s ago)"
            )
            return False

    # Update last alert time
    _recent_alerts[debounce_key] = now

    # Clean up old entries (older than 5 minutes)
    cutoff = now - timedelta(minutes=5)
    _recent_alerts = {
        k: v for k, v in _recent_alerts.items()
        if v > cutoff
    }

    # Clean up old bus tracks (older than 10 minutes)
    cutoff_tracks = now - timedelta(minutes=10)
    _bus_tracks = {
        tid: info for tid, info in _bus_tracks.items()
        if info['last_seen'] > cutoff_tracks
    }

    return True


async def send_webhook_async(
    url: str,
    payload: Dict[str, Any],
    timeout: float = 2.0
) -> Dict[str, Any]:
    """
    Send alert to webhook URL asynchronously.

    Args:
        url: Webhook URL
        payload: JSON payload to send
        timeout: Request timeout in seconds

    Returns:
        Result dictionary with status and message
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                status = response.status

                if 200 <= status < 300:
                    return {
                        "success": True,
                        "status_code": status,
                        "message": "Alert sent successfully"
                    }
                else:
                    text = await response.text()
                    return {
                        "success": False,
                        "status_code": status,
                        "message": f"Webhook returned {status}: {text[:100]}"
                    }

    except asyncio.TimeoutError:
        return {
            "success": False,
            "message": f"Webhook timeout after {timeout}s"
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"Webhook error: {exc}"
        }


def send_webhook_sync(
    url: str,
    payload: Dict[str, Any],
    timeout: float = 2.0
) -> Dict[str, Any]:
    """
    Send alert to webhook URL (synchronous wrapper).

    Args:
        url: Webhook URL
        payload: JSON payload to send
        timeout: Request timeout in seconds

    Returns:
        Result dictionary with status and message
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        send_webhook_async(url, payload, timeout)
    )


def log_alert(alert: Dict[str, Any], level: str = "INFO") -> None:
    """
    Log an alert to the application logs.

    Args:
        alert: Alert payload
        level: Log level (INFO, WARNING, ERROR)
    """
    log_func = getattr(logging, level.lower(), logging.info)
    log_func(f"[BUS ALERT] {alert.get('message')} at {alert.get('timestamp')}")


def set_debounce_window(seconds: int) -> None:
    """
    Set the global debounce window.

    Args:
        seconds: Debounce window in seconds
    """
    global _debounce_seconds
    _debounce_seconds = seconds
    logging.info(f"Debounce window set to {seconds} seconds")


def get_bus_track_statistics() -> Dict[str, Any]:
    """
    Get statistics about tracked buses.

    Returns:
        Dictionary with tracking statistics
    """
    global _bus_tracks

    if not _bus_tracks:
        return {
            "active_tracks": 0,
            "total_alerts_sent": 0
        }

    now = datetime.now(timezone.utc)
    total_alerts = sum(info['alerts_sent'] for info in _bus_tracks.values())

    # Calculate average track duration
    durations = [
        (now - info['first_seen']).total_seconds()
        for info in _bus_tracks.values()
    ]
    avg_duration = sum(durations) / len(durations) if durations else 0

    return {
        "active_tracks": len(_bus_tracks),
        "total_alerts_sent": total_alerts,
        "average_track_duration_seconds": avg_duration,
        "track_ids": list(_bus_tracks.keys())
    }


# Tool registration for ADK
ALERT_TOOLS = [
    {
        "name": "format_bus_alert_message",
        "description": "Format bus detection event into alert message",
        "function": format_bus_alert_message,
    },
    {
        "name": "should_send_alert",
        "description": "Check if alert should be sent (debounce logic)",
        "function": should_send_alert,
    },
    {
        "name": "send_webhook",
        "description": "Send alert to webhook URL",
        "function": send_webhook_sync,
    },
    {
        "name": "log_alert",
        "description": "Log alert to application logs",
        "function": log_alert,
    },
]

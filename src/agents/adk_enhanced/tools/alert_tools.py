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
_debounce_seconds = 30  # Minimum time between alerts


def format_bus_alert_message(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a bus detection event into an alert message.

    Args:
        event: Bus detection event dictionary

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
        }
    }

    return alert


def should_send_alert(event: Dict[str, Any], debounce_key: str = "default") -> bool:
    """
    Check if an alert should be sent based on debounce logic.

    Args:
        event: Event to check
        debounce_key: Key for tracking this alert type

    Returns:
        True if alert should be sent, False if debounced
    """
    global _recent_alerts

    now = datetime.now(timezone.utc)

    # Check if we recently sent this alert type
    if debounce_key in _recent_alerts:
        last_alert = _recent_alerts[debounce_key]
        time_since_last = (now - last_alert).total_seconds()

        if time_since_last < _debounce_seconds:
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

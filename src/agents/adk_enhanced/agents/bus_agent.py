#!/usr/bin/env python3
"""
Bus notification agent - handles school bus detection alerts.
"""

import logging
import os
from typing import Any, Dict, Optional

from ..tools.alert_tools import (
    format_bus_alert_message,
    should_send_alert,
    send_webhook_sync,
    log_alert,
    set_debounce_window,
    get_bus_track_statistics
)


logger = logging.getLogger(__name__)


def create_bus_notification_agent():
    """
    Create the bus notification agent.

    This agent handles bus detection events and sends alerts.
    """
    # Note: In proper ADK setup, this would be an Agent instance
    # For now, we create a functional handler that can be called
    return BusNotificationHandler()


class BusNotificationHandler:
    """
    Handler for bus notification logic with enhanced debouncing.

    Features:
    - Track-based debouncing (same bus won't trigger multiple alerts)
    - Configurable debounce window
    - Rich alert messages with tracking info
    - Image path support
    """

    def __init__(self, debounce_window: int = 30):
        """
        Initialize bus notification handler.

        Args:
            debounce_window: Time window in seconds between alerts for the same bus
        """
        self.webhook_url = os.environ.get("ADK_BUS_WEBHOOK_URL")
        self.debounce_window = debounce_window

        # Set global debounce window
        set_debounce_window(debounce_window)

        logger.info(f"Bus agent initialized with {debounce_window}s debounce window")

    async def handle_bus_event(
        self,
        event: Dict[str, Any],
        track_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Handle a bus detection event with enhanced tracking.

        Args:
            event: Bus detection event dictionary
            track_id: Optional tracking ID from object tracker

        Returns:
            Result of alert handling
        """
        # Format the alert message with track ID
        alert = format_bus_alert_message(event, track_id=track_id)

        # Enhanced debounce check with track ID
        debounce_key = f"bus_alert_track_{track_id}" if track_id else "bus_alert"
        if not should_send_alert(
            event,
            debounce_key=debounce_key,
            track_id=track_id,
            debounce_window=self.debounce_window
        ):
            return {
                "status": "debounced",
                "message": f"Alert debounced for track {track_id}" if track_id else "Alert debounced",
                "alert": alert,
                "track_id": track_id
            }

        # Log the alert
        log_alert(alert, level="WARNING")

        # Send webhook if configured
        if self.webhook_url:
            result = send_webhook_sync(
                self.webhook_url,
                alert,
                timeout=2.0
            )

            if result.get("success"):
                logger.info(f"Bus alert sent successfully: {alert['message']}")
                return {
                    "status": "sent",
                    "alert": alert,
                    "webhook_result": result
                }
            else:
                logger.error(f"Failed to send bus alert: {result.get('message')}")
                return {
                    "status": "failed",
                    "alert": alert,
                    "webhook_result": result
                }
        else:
            logger.info(f"Bus alert (no webhook configured): {alert['message']}")
            return {
                "status": "logged",
                "alert": alert,
                "message": "No webhook URL configured"
            }

    def process(self, event: Dict[str, Any], track_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Synchronous wrapper for event processing.

        Args:
            event: Event to process
            track_id: Optional tracking ID

        Returns:
            Processing result
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.handle_bus_event(event, track_id=track_id))

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get bus detection statistics.

        Returns:
            Statistics dictionary with tracking info
        """
        return get_bus_track_statistics()

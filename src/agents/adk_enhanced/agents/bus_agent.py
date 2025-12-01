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
    log_alert
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
    """Handler for bus notification logic."""

    def __init__(self):
        self.webhook_url = os.environ.get("ADK_BUS_WEBHOOK_URL")

    async def handle_bus_event(
        self,
        event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a bus detection event.

        Args:
            event: Bus detection event dictionary

        Returns:
            Result of alert handling
        """
        # Format the alert message
        alert = format_bus_alert_message(event)

        # Check debounce
        debounce_key = "bus_alert"
        if not should_send_alert(event, debounce_key):
            return {
                "status": "debounced",
                "message": "Alert skipped due to recent alert",
                "alert": alert
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

    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous wrapper for event processing.

        Args:
            event: Event to process

        Returns:
            Processing result
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.handle_bus_event(event))

#!/usr/bin/env python3
"""
Rich alert message templates for different notification channels.
"""

from datetime import datetime
from typing import Any, Dict, Optional


def format_slack_alert(
    alert: Dict[str, Any],
    include_image: bool = True
) -> Dict[str, Any]:
    """
    Format alert for Slack webhook.

    Args:
        alert: Base alert dictionary
        include_image: Whether to include image attachment

    Returns:
        Slack-formatted message payload
    """
    details = alert.get("details", {})
    track_id = details.get("track_id")
    confidence = details.get("confidence", 0)
    timestamp = alert.get("timestamp", "")

    # Build title
    if track_id is not None:
        title = f"🚌 School Bus Detected (Track #{track_id})"
    else:
        title = "🚌 School Bus Detected"

    # Build description
    description = f"Confidence: {confidence:.1%}"
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            description += f"\nTime: {dt.strftime('%I:%M:%S %p')}"
        except:
            pass

    # Build Slack blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": title,
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": description
            }
        }
    ]

    # Add image if available
    image_path = details.get("image_path")
    if include_image and image_path:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📸 Image saved: `{image_path}`"
            }
        })

    # Add bounding box info if available
    bbox = details.get("bounding_box")
    if bbox:
        x, y, w, h = bbox
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📍 Position: ({x:.0f}, {y:.0f}) Size: {w:.0f}×{h:.0f}px"
                }
            ]
        })

    return {
        "text": alert.get("message"),  # Fallback text
        "blocks": blocks
    }


def format_discord_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format alert for Discord webhook.

    Args:
        alert: Base alert dictionary

    Returns:
        Discord-formatted embed payload
    """
    details = alert.get("details", {})
    track_id = details.get("track_id")
    confidence = details.get("confidence", 0)
    timestamp = alert.get("timestamp", "")

    # Build embed
    embed = {
        "title": "🚌 School Bus Detected",
        "color": 16744272,  # Orange
        "timestamp": timestamp,
        "fields": [
            {
                "name": "Confidence",
                "value": f"{confidence:.1%}",
                "inline": True
            }
        ]
    }

    if track_id is not None:
        embed["fields"].append({
            "name": "Track ID",
            "value": f"#{track_id}",
            "inline": True
        })

    # Add image if available
    image_path = details.get("image_path")
    if image_path:
        embed["footer"] = {
            "text": f"Image: {image_path}"
        }

    return {
        "content": "⚠️ School bus alert!",
        "embeds": [embed]
    }


def format_email_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format alert for email notification.

    Args:
        alert: Base alert dictionary

    Returns:
        Email-formatted payload with subject and body
    """
    details = alert.get("details", {})
    track_id = details.get("track_id")
    confidence = details.get("confidence", 0)
    timestamp = alert.get("timestamp", "")
    image_path = details.get("image_path")

    # Subject
    if track_id is not None:
        subject = f"🚌 School Bus Alert - Track #{track_id}"
    else:
        subject = "🚌 School Bus Detected"

    # HTML body
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #ff6b35; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
        .content {{ background: #f4f4f4; padding: 20px; border-radius: 0 0 5px 5px; }}
        .detail {{ margin: 10px 0; padding: 10px; background: white; border-left: 3px solid #ff6b35; }}
        .label {{ font-weight: bold; color: #ff6b35; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🚌 School Bus Alert</h2>
        </div>
        <div class="content">
            <div class="detail">
                <span class="label">Detection Time:</span> {timestamp}
            </div>
            <div class="detail">
                <span class="label">Confidence:</span> {confidence:.1%}
            </div>
"""

    if track_id is not None:
        html_body += f"""
            <div class="detail">
                <span class="label">Track ID:</span> #{track_id}
            </div>
"""

    if image_path:
        html_body += f"""
            <div class="detail">
                <span class="label">Image:</span> {image_path}
            </div>
"""

    html_body += """
        </div>
    </div>
</body>
</html>
"""

    # Plain text body
    text_body = f"""
SCHOOL BUS ALERT

Detection Time: {timestamp}
Confidence: {confidence:.1%}
"""

    if track_id is not None:
        text_body += f"Track ID: #{track_id}\n"

    if image_path:
        text_body += f"Image: {image_path}\n"

    return {
        "subject": subject,
        "html": html_body,
        "text": text_body
    }


def format_sms_alert(alert: Dict[str, Any]) -> str:
    """
    Format alert for SMS (short text).

    Args:
        alert: Base alert dictionary

    Returns:
        SMS text (160 chars or less)
    """
    details = alert.get("details", {})
    track_id = details.get("track_id")
    confidence = details.get("confidence", 0)

    if track_id is not None:
        return f"🚌 Bus #{track_id} detected ({confidence:.0%} confidence)"
    else:
        return f"🚌 School bus detected ({confidence:.0%} confidence)"


def format_webhook_alert(
    alert: Dict[str, Any],
    format_type: str = "slack"
) -> Dict[str, Any]:
    """
    Format alert for generic webhook based on type.

    Args:
        alert: Base alert dictionary
        format_type: One of "slack", "discord", "email", "sms", or "generic"

    Returns:
        Formatted alert payload
    """
    if format_type == "slack":
        return format_slack_alert(alert)
    elif format_type == "discord":
        return format_discord_alert(alert)
    elif format_type == "email":
        return format_email_alert(alert)
    elif format_type == "sms":
        return {"message": format_sms_alert(alert)}
    else:
        # Generic JSON format
        return alert


# Template registry for easy access
ALERT_TEMPLATES = {
    "slack": format_slack_alert,
    "discord": format_discord_alert,
    "email": format_email_alert,
    "sms": format_sms_alert,
    "generic": lambda x: x
}

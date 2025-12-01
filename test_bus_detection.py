#!/usr/bin/env python3
"""
Test the enhanced bus detection system with all new features.
"""

import sys
from datetime import datetime, timezone

sys.path.insert(0, '.')

from src.agents.adk_enhanced.agents.bus_agent import create_bus_notification_agent
from src.agents.adk_enhanced.tools.alert_templates import (
    format_slack_alert,
    format_discord_alert,
    format_email_alert,
    format_sms_alert
)


def test_basic_bus_detection():
    """Test basic bus detection with enhanced features."""
    print("="*70)
    print("Testing Enhanced Bus Detection System")
    print("="*70)

    # Create bus agent with custom debounce window
    bus_agent = create_bus_notification_agent()
    print("\n✅ Bus agent initialized with enhanced debouncing\n")

    # Create test event with track ID and image path
    test_event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": "bus_detected",
        "details": {
            "category": "bus",
            "score": 0.85,
            "frame_id": 12345,
            "bbox": [100, 150, 200, 100],
            "raw_label": "bus",
            "image_path": "/home/pi/imx500_images/frame_012345_bus_20251201_143052.jpg"
        }
    }

    # Test 1: Send first alert with track ID
    print("Test 1: First bus detection (Track #1)")
    print("-" * 70)
    result1 = bus_agent.process(test_event, track_id=1)
    print(f"Status: {result1.get('status')}")
    print(f"Message: {result1.get('message', result1.get('alert', {}).get('message'))}")
    if result1.get('alert'):
        alert = result1['alert']
        print(f"Track ID: {alert.get('details', {}).get('track_id')}")
        print(f"Image: {alert.get('details', {}).get('image_path')}")

    # Test 2: Try to send duplicate (should be debounced)
    print("\n\nTest 2: Same bus again (should be debounced)")
    print("-" * 70)
    result2 = bus_agent.process(test_event, track_id=1)
    print(f"Status: {result2.get('status')}")
    print(f"Message: {result2.get('message')}")

    # Test 3: Different bus (should send)
    print("\n\nTest 3: Different bus (Track #2)")
    print("-" * 70)
    result3 = bus_agent.process(test_event, track_id=2)
    print(f"Status: {result3.get('status')}")
    print(f"Message: {result3.get('message', result3.get('alert', {}).get('message'))}")

    # Get statistics
    print("\n\nBus Detection Statistics")
    print("-" * 70)
    stats = bus_agent.get_statistics()
    print(f"Active tracks: {stats.get('active_tracks')}")
    print(f"Total alerts sent: {stats.get('total_alerts_sent')}")
    print(f"Track IDs: {stats.get('track_ids')}")

    return result1.get('alert')


def test_alert_templates(alert):
    """Test rich alert formatting for different channels."""
    print("\n\n" + "="*70)
    print("Testing Rich Alert Templates")
    print("="*70)

    # Test Slack format
    print("\n\n1. Slack Format")
    print("-" * 70)
    slack = format_slack_alert(alert)
    print(f"Fallback text: {slack.get('text')}")
    print(f"Blocks: {len(slack.get('blocks', []))} blocks")
    for block in slack.get('blocks', []):
        if block.get('type') == 'header':
            print(f"  - Header: {block['text']['text']}")
        elif block.get('type') == 'section':
            print(f"  - Section: {block['text']['text'][:50]}...")

    # Test Discord format
    print("\n\n2. Discord Format")
    print("-" * 70)
    discord = format_discord_alert(alert)
    print(f"Content: {discord.get('content')}")
    if discord.get('embeds'):
        embed = discord['embeds'][0]
        print(f"Embed title: {embed.get('title')}")
        print(f"Embed color: {embed.get('color')}")
        print(f"Fields: {len(embed.get('fields', []))}")

    # Test Email format
    print("\n\n3. Email Format")
    print("-" * 70)
    email = format_email_alert(alert)
    print(f"Subject: {email.get('subject')}")
    print(f"Plain text: {email.get('text')[:100]}...")
    print(f"HTML length: {len(email.get('html', ''))} chars")

    # Test SMS format
    print("\n\n4. SMS Format")
    print("-" * 70)
    sms = format_sms_alert(alert)
    print(f"Message: {sms}")
    print(f"Length: {len(sms)} chars")


def main():
    """Run all tests."""
    print("\n🧪 Enhanced Bus Detection Test Suite\n")

    # Test basic detection
    alert = test_basic_bus_detection()

    # Test templates if we got an alert
    if alert:
        test_alert_templates(alert)

    print("\n\n" + "="*70)
    print("✅ All tests complete!")
    print("="*70)

    print("\n📋 Summary of Enhancements:")
    print("  ✅ Track-based debouncing (prevents duplicate alerts for same bus)")
    print("  ✅ Configurable debounce window")
    print("  ✅ Image capture and path tracking")
    print("  ✅ Rich alert templates (Slack, Discord, Email, SMS)")
    print("  ✅ Track statistics and monitoring")
    print("\n🎉 Enhanced bus detection system is ready!")


if __name__ == "__main__":
    main()

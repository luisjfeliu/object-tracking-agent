"""
Enhanced ADK multi-agent system for object tracking.

This package provides a proper ADK integration with:
- Structured agent definitions using google.adk.Agent
- Tool-based architecture
- LLM-powered summarization
- Event-driven coordination
"""

from .coordinator import ObjectTrackingCoordinator

__all__ = ["ObjectTrackingCoordinator"]

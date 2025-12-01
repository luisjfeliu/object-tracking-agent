#!/usr/bin/env python3
"""
LLM-powered summarization agent - generates intelligent summaries of detections.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from ..tools.summary_tools import (
    aggregate_events_by_category,
    detect_patterns,
    generate_summary_prompt,
    format_summary_output
)


logger = logging.getLogger(__name__)


def create_summary_agent(model_name: str = "models/gemini-2.5-flash"):
    """
    Create the LLM-powered summary agent.

    Args:
        model_name: Gemini model to use

    Returns:
        SummaryAgentHandler instance
    """
    return SummaryAgentHandler(model_name=model_name)


class SummaryAgentHandler:
    """Handler for LLM-powered event summarization."""

    def __init__(self, model_name: str = "models/gemini-2.5-flash"):
        self.model_name = model_name
        self._client: Optional[genai.Client] = None
        self._api_key = os.environ.get("GEMINI_API_KEY")

    def _ensure_client(self):
        """Ensure the Gemini client is initialized."""
        if self._client is None:
            if not self._api_key:
                logger.warning(
                    "GEMINI_API_KEY not set. "
                    "Summarization will fall back to rule-based summaries."
                )
                return False

            try:
                self._client = genai.Client(api_key=self._api_key)
                logger.info(f"Initialized Gemini client with model: {self.model_name}")
                return True
            except Exception as exc:
                logger.error(f"Failed to initialize Gemini client: {exc}")
                return False

        return True

    async def generate_summary_async(
        self,
        events: List[Dict[str, Any]],
        window_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Generate an LLM-powered summary of events.

        Args:
            events: List of event dictionaries
            window_minutes: Time window for summary

        Returns:
            Summary dictionary
        """
        if not events:
            return {
                "summary": "No events to summarize.",
                "statistics": {},
                "patterns": {},
                "llm_used": False
            }

        # Try LLM-powered summary
        if self._ensure_client():
            try:
                # Generate structured prompt
                prompt = generate_summary_prompt(events, window_minutes)

                # Try different model name formats
                # If model_name already has models/ prefix, use it
                # Otherwise try adding the prefix
                if self.model_name.startswith("models/"):
                    model_names_to_try = [
                        self.model_name,
                        "models/gemini-2.5-flash",
                        "models/gemini-flash-latest"
                    ]
                else:
                    model_names_to_try = [
                        f"models/{self.model_name}",
                        self.model_name,
                        "models/gemini-2.5-flash",
                        "models/gemini-flash-latest"
                    ]

                response = None
                last_error = None

                for model_name in model_names_to_try:
                    try:
                        # Call Gemini
                        response = self._client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                temperature=0.3,
                                max_output_tokens=2000  # Increased to handle thinking tokens
                            )
                        )
                        # Success! Update the model name for future calls
                        self.model_name = model_name
                        logger.info(f"Successfully using model: {model_name}")
                        break
                    except Exception as model_exc:
                        last_error = model_exc
                        logger.debug(f"Model {model_name} failed: {model_exc}")
                        continue

                if response is None:
                    raise last_error or Exception("All model attempts failed")

                # Extract text from response
                try:
                    llm_summary = response.text

                    # Check if text is None or empty
                    if not llm_summary:
                        logger.warning("Response text is None or empty, trying candidates fallback")
                        # Try candidates fallback with better error handling
                        if hasattr(response, 'candidates') and response.candidates:
                            candidate = response.candidates[0]
                            if hasattr(candidate, 'content') and candidate.content:
                                content = candidate.content
                                if hasattr(content, 'parts') and content.parts:
                                    parts_text = []
                                    for part in content.parts:
                                        if hasattr(part, 'text') and part.text:
                                            parts_text.append(part.text)
                                    if parts_text:
                                        llm_summary = '\n'.join(parts_text)
                                        logger.info(f"Extracted text from candidates: {len(llm_summary)} chars")

                except Exception as text_exc:
                    logger.error(f"Exception extracting text: {text_exc}")
                    llm_summary = None

                if not llm_summary:
                    # Provide helpful error message
                    error_info = "LLM response received but text could not be extracted."
                    if hasattr(response, 'candidates') and response.candidates:
                        finish_reason = response.candidates[0].finish_reason if hasattr(response.candidates[0], 'finish_reason') else 'unknown'
                        error_info += f" Finish reason: {finish_reason}"
                        logger.error(error_info)
                    llm_summary = error_info

                # Format output
                result = format_summary_output(
                    llm_summary,
                    events,
                    metadata={
                        "model": self.model_name,
                        "window_minutes": window_minutes,
                        "llm_used": True
                    }
                )

                logger.info(f"Generated LLM summary for {len(events)} events")
                return result

            except Exception as exc:
                logger.error(f"LLM summary failed: {exc}. Falling back to rule-based.")

        # Fallback: rule-based summary
        return self._generate_rule_based_summary(events, window_minutes)

    def _generate_rule_based_summary(
        self,
        events: List[Dict[str, Any]],
        window_minutes: int
    ) -> Dict[str, Any]:
        """
        Generate a rule-based summary without LLM.

        Args:
            events: List of event dictionaries
            window_minutes: Time window

        Returns:
            Summary dictionary
        """
        agg = aggregate_events_by_category(events)
        patterns = detect_patterns(events)

        # Build text summary
        lines = [f"Summary of {len(events)} detections in the last {window_minutes} minutes:"]

        categories = agg.get("categories", {})
        if categories:
            lines.append("\nDetections by category:")
            for cat, stats in categories.items():
                lines.append(
                    f"  - {cat.upper()}: {stats['count']} "
                    f"(avg confidence: {stats['avg_confidence']:.2f})"
                )

        if patterns.get("bus_sightings", 0) > 0:
            lines.append(
                f"\n⚠️  ALERT: {patterns['bus_sightings']} school bus sighting(s) detected!"
            )

        if patterns.get("high_frequency_categories"):
            lines.append("\nHigh activity categories:")
            for item in patterns["high_frequency_categories"]:
                lines.append(f"  - {item['category']}: {item['percentage']}% of detections")

        if patterns.get("unusual_activity"):
            lines.append(f"\nUnusual activity detected in {len(patterns['unusual_activity'])} time window(s)")

        summary_text = "\n".join(lines)

        return format_summary_output(
            summary_text,
            events,
            metadata={
                "window_minutes": window_minutes,
                "llm_used": False,
                "method": "rule_based"
            }
        )

    def generate_summary(
        self,
        events: List[Dict[str, Any]],
        window_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for summary generation.

        Args:
            events: List of event dictionaries
            window_minutes: Time window

        Returns:
            Summary dictionary
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.generate_summary_async(events, window_minutes)
        )

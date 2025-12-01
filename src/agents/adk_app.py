#!/usr/bin/env python3
"""
adk_app.py

Lightweight ADK-ready loop that tails the IMX500 event log and wires it into
Google's Agents Development Kit. This module is defensive: if `google-agents`
is not installed, it will print a clear message instead of crashing.

Features:
- Tails ~/imx500_events.jsonl produced by the Pi script.
- Emits bus alerts via a webhook (env: ADK_BUS_WEBHOOK_URL) or console.
- Periodic summarization using the existing EventSummarizerAgent.
- Optional tracker passthrough if you want track IDs on the ADK side.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

import aiohttp

# Ensure repo root is on sys.path for `src.*` imports when run as a script
REPO_ROOT = Path(__file__).resolve().parents[2]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from src.agents.agents import Event, EventSummarizerAgent, parse_event_line
from src.tracking.tracker import MultiObjectTracker

# ADK imports are optional; handle missing dependency gracefully. Prefer the modern
# `google-adk` package but keep compatibility with the older `google-agents`
# runtime if it is present. We also avoid treating telemetry logger import failures
# as fatal so users with slimmer `google-adk` builds can still run the ADK loop.
AgentRuntime = None
_adk_import_errors: List[str] = []

try:
    from google.agents import AgentRuntime as _LegacyAgentRuntime  # type: ignore

    AgentRuntime = _LegacyAgentRuntime
except Exception as exc:  # pragma: no cover - defensive: import differs by SDK
    _adk_import_errors.append(f"google.agents unavailable: {exc}")

    try:
        from google.adk import AgentRuntime as _AdkAgentRuntime  # type: ignore

        AgentRuntime = _AdkAgentRuntime
    except Exception as adk_runtime_exc:  # pragma: no cover - fallback to console runtime
        _adk_import_errors.append(f"google.adk AgentRuntime unavailable: {adk_runtime_exc}")

        _adk_logger = None
        try:
            import google.adk.telemetry as _adk_telemetry  # type: ignore

            def _resolve_adk_logger():
                # Prefer an explicit logger object if exposed, otherwise accept a getter
                if hasattr(_adk_telemetry, "logger"):
                    return _adk_telemetry.logger  # type: ignore[attr-defined]
                if hasattr(_adk_telemetry, "get_logger"):
                    try:
                        return _adk_telemetry.get_logger()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                if hasattr(_adk_telemetry, "getLogger"):
                    try:
                        return _adk_telemetry.getLogger()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                return None

            try:
                _adk_logger = _resolve_adk_logger()
            except Exception as logger_exc:  # pragma: no cover - defensive fallback
                _adk_import_errors.append(f"google.adk telemetry logger unavailable: {logger_exc}")
                _adk_logger = None
        except Exception as adk_telemetry_exc:  # pragma: no cover - telemetry not present
            _adk_import_errors.append(f"google.adk telemetry unavailable: {adk_telemetry_exc}")
            _adk_logger = None

        class AgentRuntime:  # type: ignore[override]
            """Lightweight runtime wrapper using the `google-adk` telemetry hooks."""

            def log(self, message: str) -> None:
                if hasattr(_adk_logger, "info"):
                    _adk_logger.info(message)  # type: ignore[union-attr]
                elif callable(_adk_logger):
                    _adk_logger(message)
                else:
                    print(f"[ADK] {message}")

ADK_IMPORT_ERROR: Optional[str] = "".join(
    [f"{err}; " for err in _adk_import_errors]
)[:-2] or None


LOG_PATH = Path(os.environ.get("IMX500_LOG_PATH", Path.home() / "imx500_events.jsonl"))
BUS_WEBHOOK_URL = os.environ.get("ADK_BUS_WEBHOOK_URL")
SUMMARY_WINDOW_MIN = int(os.environ.get("ADK_SUMMARY_WINDOW_MIN", "30"))


async def tail_events(log_path: Path) -> AsyncIterator[Event]:
    """Async tail of the JSONL log, yielding parsed Event objects."""
    pos = 0

    def _read_from_pos(path: Path, start: int):
        out = []
        with path.open("rb") as f:
            f.seek(start)
            for line in f:
                out.append((f.tell(), line))
        return out

    while True:
        if log_path.exists():
            try:
                chunks = await asyncio.to_thread(_read_from_pos, log_path, pos)
                for new_pos, line in chunks:
                    pos = new_pos
                    ev = parse_event_line(line.decode("utf-8", errors="ignore"))
                    if ev:
                        yield ev
            except Exception:
                # swallow transient read errors
                await asyncio.sleep(0.5)
                continue
        await asyncio.sleep(0.5)


async def send_bus_webhook(payload: Dict[str, Any]) -> None:
    """Send bus alert to a webhook if configured."""
    if not BUS_WEBHOOK_URL:
        print(f"[ADK BUS ALERT] {payload}")
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(BUS_WEBHOOK_URL, json=payload, timeout=2)
    except Exception as exc:
        print(f"[ADK BUS ALERT] webhook failed: {exc} payload={payload}")


async def run_event_loop(use_tracker: bool = False) -> None:
    """Standalone runner without ADK (useful for debugging)."""
    summarizer = EventSummarizerAgent()
    tracker: Optional[MultiObjectTracker] = MultiObjectTracker() if use_tracker else None
    buffer: List[Event] = []

    async for ev in tail_events(LOG_PATH):
        buffer.append(ev)

        if tracker and ev.event_type == "object_detected":
            details = ev.details
            track_states = tracker.update([details], frame_id=int(details.get("frame_id", 0)))
            if track_states:
                print(f"[TRACK] frame={details.get('frame_id')} tracks={track_states}")

        if ev.event_type == "bus_detected":
            await send_bus_webhook(
                {"ts": ev.ts.isoformat(), "details": ev.details, "event_type": ev.event_type}
            )

        if len(buffer) % 200 == 0:
            summary = summarizer.summarize(buffer, window_minutes=SUMMARY_WINDOW_MIN)
            print(f"[SUMMARY]\n{summary}")


async def run_with_adk(use_tracker: bool = False) -> None:
    """Entry for ADK runtime; falls back to standalone if ADK is unavailable."""
    if AgentRuntime is None:
        extra = f" ({ADK_IMPORT_ERROR})" if ADK_IMPORT_ERROR else ""
        print(f"ADK runtime unavailable{extra}. Falling back to standalone loop.")
        await run_event_loop(use_tracker=use_tracker)
        return

    runtime = AgentRuntime()
    summarizer = EventSummarizerAgent()
    tracker: Optional[MultiObjectTracker] = MultiObjectTracker() if use_tracker else None
    buffer: List[Event] = []

    async for ev in tail_events(LOG_PATH):
        buffer.append(ev)

        # Tracker integration (optional)
        if tracker and ev.event_type == "object_detected":
            track_states = tracker.update([ev.details], frame_id=int(ev.details.get("frame_id", 0)))
            # Example: you could emit a custom ADK event here
            runtime.log(f"Tracks: {track_states}")

        if ev.event_type == "bus_detected":
            await send_bus_webhook(
                {"ts": ev.ts.isoformat(), "details": ev.details, "event_type": ev.event_type}
            )

        # Periodic summary - replace with an LLM call inside ADK if desired
        if len(buffer) % 200 == 0:
            summary = summarizer.summarize(buffer, window_minutes=SUMMARY_WINDOW_MIN)
            runtime.log(f"Summary:\n{summary}")


def main():
    use_tracker = bool(int(os.environ.get("ADK_USE_TRACKER", "1")))
    asyncio.run(run_with_adk(use_tracker=use_tracker))


if __name__ == "__main__":
    sys.exit(main())

# Object Tracking Agent

Capstone project scaffold for the Kaggle "Agents Intensive" course. The goal is
to detect and track objects with the Sony IMX500 camera on a Raspberry Pi, log
events, and have lightweight agents react to them (bus alerts, summaries, and
tracking IDs).

The repo is split so you can run the detection loop on the Pi (with IMX500
packages installed) and still experiment in a Kaggle notebook using the saved
JSONL event log.

## Repo layout

- `src/pi/pi_imx500_detector.py` — runs on the Pi, produces `~/imx500_events.jsonl`.
- `src/agents/agents.py` — ingestion/summarization/notification agents that read the log.
- `src/agents/adk_app.py` — ADK-ready tailer/agents for bus alerts and summaries.
- `src/agents/event_receiver.py` — tiny HTTP server to receive forwarded events.
- `src/tracking/tracker.py` — simple IoU-based multi-object tracker.
- `src/tracking/offline_pipeline.py` — replay the saved log to exercise agents/tracker offline.
- `data/sample_events.jsonl` — tiny sample log for Kaggle/offline demos.
- `tests/` — quick pytest checks for the tracker and offline replay.

## Raspberry Pi (IMX500) runtime

1. Install the IMX500 SDK and model pack on the Pi:
   ```bash
   sudo apt update && sudo apt install -y imx500-all python3-picamera2 python3-opencv python3-numpy python3-requests
   ```
2. Copy `src/pi/pi_imx500_detector.py` to the Pi and run:

   ```bash
   python3 src/pi/pi_imx500_detector.py
   ```

   This writes JSONL events to `~/imx500_events.jsonl`. Bus detections are logged
   as special events (`event_type="bus_detected"`).
3. (Optional) set `BUS_WEBHOOK_URL` in the script to hit your backend when a bus is found.

## Offline/Kaggle notebook usage

You can explore the log without hardware using the sample file:

```python
from pathlib import Path
from src.tracking.offline_pipeline import replay_tracking

track_events, summary = replay_tracking(Path("data/sample_events.jsonl"), summary_window=120)
print(summary)
print(f"tracks emitted: {len(track_events)}")
```

Or via CLI:

```bash
python src/tracking/offline_pipeline.py --log data/sample_events.jsonl --out tracking_events.jsonl
```

This runs the tracker, emits `track_update` events, and prints a textual summary
from the summarizer agent.

## Agents in brief

- `EventIngestionAgent` tails or reads the JSONL log.
- `BusNotificationAgent` reacts to `bus_detected` events (currently prints).
- `EventSummarizerAgent` aggregates detections over a time window.
- `MultiObjectTracker` keeps per-object IDs using IoU matching on bounding boxes.

Wire them together however you like (e.g., tailing the log and pushing bus
alerts to email/Slack, or letting an LLM write richer summaries).

## ADK multi-agent glue

If you want to orchestrate agents with Google’s Agents Development Kit (ADK),
use `src/agents/adk_app.py`:

```bash
# On a machine that can see the Pi’s log file
IMX500_LOG_PATH=~/imx500_events.jsonl \
ADK_BUS_WEBHOOK_URL="https://your-webhook" \
python src/agents/adk_app.py
```

- It tails the JSONL log, emits bus alerts (webhook or console), and prints periodic summaries.
- Set `ADK_USE_TRACKER=0` to disable the IoU tracker in the loop.
- If `google-agents` is not installed, it falls back to a standalone loop; install the ADK
  package to integrate with a full ADK runtime/LLM tools.

## Forwarding events to a desktop server

If you prefer to run agents on your desktop, forward events from the Pi and receive them locally:

1. On the desktop, start the receiver:
   ```bash
   python src/agents/event_receiver.py --host 0.0.0.0 --port 8000 --out imx500_events_remote.jsonl
   ```
2. On the Pi, set the forwarding URL (and optional bus webhook) before running the detector:
   ```bash
   export IMX500_FORWARD_URL="http://<desktop-ip>:8000/event"
   export BUS_WEBHOOK_URL="http://<desktop-ip>:8000/event"  # optional bus-only
   python3 src/pi/pi_imx500_detector.py
   ```
   This keeps local logging on the Pi and mirrors each event to the desktop.

## Development

- Python 3.10+ recommended.
- Run tests locally (camera imports are isolated to the Pi script):

  ```bash
  PYTHONPATH=src pytest
  ```

- When running on Kaggle, add `PYTHONPATH=./src` in the notebook before imports.

## Next steps you might try

- Swap the default MobileNet model for a fine-tuned bus/school-bus detector.
- Capture and store image crops for each bus event, then summarize with an LLM.
- Debounce near-duplicate bus frames so you only alert once per arrival.

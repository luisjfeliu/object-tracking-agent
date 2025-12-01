#!/usr/bin/env python3
"""
event_receiver.py

Tiny HTTP server to receive forwarded IMX500 events from the Pi.

Usage:
    python src/agents/event_receiver.py --host 0.0.0.0 --port 8000 \
        --out imx500_events_remote.jsonl

Endpoints:
    POST /event  -> accepts JSON event; appends to file if provided; echoes 200.
    GET  /health -> returns 200 for liveness.

No external deps; uses Python stdlib http.server.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional


class EventHandler(BaseHTTPRequestHandler):
    out_path: Optional[Path] = None

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path != "/event":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            obj = json.loads(body)
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        if self.out_path:
            with self.out_path.open("a") as f:
                f.write(json.dumps(obj) + "\n")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def log_message(self, fmt, *args):
        # Quieter logging
        return


def main():
    parser = argparse.ArgumentParser(description="Receive forwarded IMX500 events.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--out", type=Path, default=Path("imx500_events_remote.jsonl"))
    args = parser.parse_args()

    EventHandler.out_path = args.out
    server = HTTPServer((args.host, args.port), EventHandler)
    print(f"Listening on {args.host}:{args.port}, writing to {args.out}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""Serve the report as a phone-readable page.

Checking on the bot meant SSHing in and typing commands, which is
unpleasant on a laptop and worse on a phone. This regenerates the report
on a timer and serves it over plain HTTP so a phone browser can read it.

Read-only by construction: it renders text the report already produces and
exposes no way to alter anything. There is no secret in the output -- mint
addresses, prices and counts are all public chain data -- but the page IS
reachable by anyone who finds the port, so it serves on a random path
printed at startup rather than at the root.
"""
from __future__ import annotations

import html
import os
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get("MEMEBOT_WEB_PORT", "8080"))
REFRESH_SEC = 300
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.environ.get("MEMEBOT_WEB_TOKEN") or secrets.token_urlsafe(8)

_lock = threading.Lock()
_report = "starting up..."
_generated = 0.0


def regenerate() -> None:
    global _report, _generated
    try:
        out = subprocess.run(
            [sys.executable, os.path.join(REPO, "scripts", "report.py")],
            cwd=REPO, capture_output=True, text=True, timeout=300)
        text = out.stdout or out.stderr or "(no output)"
    except Exception as e:
        text = f"report failed: {type(e).__name__}: {e}"
    with _lock:
        _report = text
        _generated = time.time()


def loop() -> None:
    while True:
        regenerate()
        time.sleep(REFRESH_SEC)


PAGE = """<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>memebot</title>
<style>
 :root{{color-scheme:light dark}}
 body{{margin:0;padding:12px;font:13px/1.45 ui-monospace,Menlo,monospace;
      background:#0f1115;color:#d7dae0}}
 h1{{font-size:15px;margin:0 0 4px;color:#8ab4f8}}
 .age{{color:#7d8590;font-size:12px;margin-bottom:10px}}
 pre{{white-space:pre;overflow-x:auto;margin:0;font-size:12px}}
 .off{{color:#f85149}}
</style>
<h1>memebot</h1>
<div class=age>generated {age} ago &middot; refreshes every 5 min</div>
<pre>{body}</pre>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith(f"/{TOKEN}"):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")
            return
        with _lock:
            body, gen = _report, _generated
        age = int(time.time() - gen)
        age_s = f"{age}s" if age < 90 else f"{age // 60}m"
        page = PAGE.format(age=age_s, body=html.escape(body))
        data = page.encode()
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):        # keep the journal readable
        pass


def main() -> int:
    threading.Thread(target=loop, daemon=True).start()
    print(f"memebot status page on port {PORT}, path /{TOKEN}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

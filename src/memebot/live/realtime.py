"""Real-time launch detection via Helius WebSocket.

The validated signal decays fast with latency: trimmed expectancy runs
~+19% when acted on immediately, ~+11% at 2-3 minutes, and ~0 by 5. Our
GeckoTerminal feed discovers pools at a median 2.4 minutes of age — right
on the boundary where the edge dies.

This closes that gap. Helius `logsSubscribe` on the PumpSwap AMM program
surfaces pool creations within seconds of the block, so a launch can be
watched from its first minute of life rather than found after the move
has happened.

Design notes:
  * the log stream is enormous (~700 events/sec); we filter to creations
    and hand off only the addresses, never blocking the socket
  * a watcher then samples price via Jupiter on a few-second cadence to
    build the first-minute features the strategy needs (range, activity)
  * everything is best-effort: a dropped socket reconnects, and the bot
    keeps trading from its slower feed in the meantime
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

PUMP_AMM = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
CREATE_MARKERS = ("CreatePool", "create_pool", "Instruction: CreatePool")


@dataclass
class LaunchEvent:
    signature: str
    detected_ts: float
    logs: list = field(default_factory=list, repr=False)


class RealtimeLaunchFeed:
    """Streams pool-creation signatures from Helius with seconds of latency."""

    def __init__(self, rpc_url: str | None = None, maxlen: int = 500):
        url = rpc_url or os.environ.get("MEMEBOT_RPC_URL") or ""
        if not url.startswith("http"):
            raise RuntimeError("MEMEBOT_RPC_URL must be set for realtime feed")
        self.ws_url = url.replace("https://", "wss://").replace("http://", "ws://")
        self.events: deque[LaunchEvent] = deque(maxlen=maxlen)
        self._seen: set[str] = set()
        self._running = False

    async def _run(self) -> None:
        import websockets
        backoff = 1.0
        while self._running:
            try:
                async with websockets.connect(self.ws_url, ping_interval=20,
                                              max_size=None) as ws:
                    await ws.send(json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                        "params": [{"mentions": [PUMP_AMM]},
                                   {"commitment": "processed"}]}))
                    await ws.recv()
                    log.info("realtime launch feed connected")
                    backoff = 1.0
                    while self._running:
                        msg = json.loads(await ws.recv())
                        v = (msg.get("params", {}).get("result", {})
                             .get("value", {}))
                        logs = v.get("logs") or []
                        sig = v.get("signature")
                        if not sig or sig in self._seen:
                            continue
                        if any(m in l for l in logs for m in CREATE_MARKERS):
                            self._seen.add(sig)
                            self.events.append(
                                LaunchEvent(sig, time.time(), logs))
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("realtime feed dropped (%s); reconnecting in %.0fs",
                            e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 2)

    def start(self) -> None:
        """Run the feed on a background thread with its own event loop."""
        import threading
        self._running = True

        def runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._run())

        t = threading.Thread(target=runner, daemon=True, name="rt-launch-feed")
        t.start()
        self._thread = t

    def stop(self) -> None:
        self._running = False

    def recent(self, max_age_sec: float = 300) -> list[LaunchEvent]:
        now = time.time()
        return [e for e in list(self.events) if now - e.detected_ts <= max_age_sec]

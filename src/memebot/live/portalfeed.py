"""Real-time launch detection at zero credit cost.

Three feeds have now been tried, and the trade-offs are worth recording
because two of them failed in opposite directions:

  logsSubscribe on the PumpSwap program -- instant, and streams EVERY swap
    on every pump pool to keep the handful that are pool creations. Over 99%
    of what it paid to receive was discarded. It consumed a million credits
    in under a day.

  polling GeckoTerminal's new-pools -- free, but pools surface four to
    eleven minutes old. Measured directly: of eight freshly polled pools,
    SEVEN showed an identical price across thirteen samples. They were
    already dead. This strategy's edge is early access; arriving late buys
    corpses, and the live funnel showed it -- 74 decisions, 0 entries, range
    0.0% on nearly every candidate.

  PumpPortal's migration stream -- instant AND free. It publishes exactly
    the event the paid subscription was filtered down to: a token graduating
    to a PumpSwap pool. Measured 1.1/min against the 2.4/min the paid feed
    saw, the same order of magnitude.

The lesson generalises: the expensive feed was not expensive because the
data was valuable, it was expensive because it was unfiltered. Paying for a
firehose to keep 0.1% of it is a design error, not a cost of doing business.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

WS_URL = "wss://pumpportal.fun/api/data"


@dataclass
class PortalEvent:
    signature: str
    detected_ts: float
    logs: list = field(default_factory=list)
    mint: str | None = None


class PortalLaunchFeed:
    """Graduations to PumpSwap, in real time, for free."""

    def __init__(self, maxlen: int = 2000):
        self.events: deque = deque(maxlen=maxlen)
        self._seen: set[str] = set()
        self._running = False
        self.thread_error: BaseException | None = None

    async def _run(self) -> None:
        import websockets
        backoff = 1.0
        while self._running:
            try:
                async with websockets.connect(WS_URL, ping_interval=20,
                                              max_size=None) as ws:
                    await ws.send(json.dumps({"method": "subscribeMigration"}))
                    log.info("portal launch feed connected (no credits used)")
                    backoff = 1.0
                    while self._running:
                        msg = json.loads(await ws.recv())
                        mint = msg.get("mint")
                        sig = msg.get("signature") or mint
                        if not mint or sig in self._seen:
                            continue
                        self._seen.add(sig)
                        self.events.append(
                            PortalEvent(signature=sig, detected_ts=time.time(),
                                        mint=mint))
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("portal feed dropped (%s); reconnecting in %.0fs",
                            e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 2)

    def start(self) -> None:
        self._running = True

        def runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._run())
            except BaseException as e:
                # A dead feed must be visible: the scalper checks this and
                # exits rather than heartbeating blind with no candidates.
                self.thread_error = e
                log.error("portal feed thread died: %s: %s",
                          type(e).__name__, e)
                raise

        threading.Thread(target=runner, name="portal-launch-feed",
                         daemon=True).start()

    def stop(self) -> None:
        self._running = False

    def recent(self, max_age_sec: float = 900) -> list:
        now = time.time()
        return [e for e in list(self.events)
                if now - e.detected_ts <= max_age_sec]

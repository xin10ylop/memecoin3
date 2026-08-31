"""Launch discovery that costs no RPC credits.

The websocket feed subscribed to every transaction touching the PumpSwap
program -- every swap on every pump pool on Solana -- and kept only the pool
creations, discarding well over 99% of what it paid to receive. At tens of
swaps per second that is millions of billed messages per day, and it
consumed a million credits in under a day of running.

GeckoTerminal's new-pools endpoint is free and returns pools roughly four to
five minutes old. That latency is the trade, and the evidence says it is an
acceptable one: waits of 2, 3, 5, 7 and 10 minutes were tested on the
harvest and their intervals all overlap, with 5 and 7 minutes scoring
slightly HIGHER than 2 rather than lower (research/wait_longer.py). There is
no measured penalty for arriving later, and there is a large measured cost
to the firehose.

Same interface as RealtimeLaunchFeed so the scalper does not care which is
running.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass

from ..data.gt import GeckoTerminal

log = logging.getLogger(__name__)


@dataclass
class PollEvent:
    signature: str          # the pool address; the scalper only needs a key
    detected_ts: float
    logs: list
    mint: str | None = None
    created_ts: float | None = None


class PollingLaunchFeed:
    """Discovers new pools by polling, at zero credit cost."""

    def __init__(self, per_min: float = 25.0, maxlen: int = 2000,
                 max_age_min: float = 12.0):
        self.gt = GeckoTerminal(per_min=per_min)
        self.events: deque = deque(maxlen=maxlen)
        self._seen: set[str] = set()
        self._running = False
        self.max_age_min = max_age_min
        self.thread_error: BaseException | None = None

    def _poll_once(self) -> int:
        found = 0
        for page in (1, 2):
            for p in self.gt.new_pools(page=page):
                if not p.address or p.address in self._seen:
                    continue
                age = p.age_minutes
                if age is None or age > self.max_age_min:
                    continue
                self._seen.add(p.address)
                self.events.append(PollEvent(
                    signature=p.address, detected_ts=time.time(), logs=[],
                    mint=p.base_mint,
                    created_ts=(p.created_ts if p.created_ts else None)))
                found += 1
        return found

    def _loop(self) -> None:
        while self._running:
            try:
                n = self._poll_once()
                if n:
                    log.info("polling feed: %d new pools", n)
            except Exception as e:                 # never kill the thread
                log.warning("polling feed error: %s", e)
            time.sleep(20)

    def start(self) -> None:
        self._running = True
        t = threading.Thread(target=self._loop, name="poll-launch-feed",
                             daemon=True)
        t.start()
        log.info("polling launch feed started (no RPC credits used)")

    def stop(self) -> None:
        self._running = False

    def recent(self, max_age_sec: float = 900) -> list:
        now = time.time()
        return [e for e in list(self.events)
                if now - e.detected_ts <= max_age_sec]

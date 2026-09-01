"""Run several launch feeds at once and take the union.

Feeds disagree about what a launch is, and the disagreement is large enough
to change results. Measured over one hour:

  Helius firehose (whole PumpSwap program)  300 creations/hour, 772 msg/sec
  PumpPortal subscribeMigration              66 events/hour, free
  Helius on the migration AUTHORITY only     ~37/hour, 888 messages/DAY,
                                             100% of them useful

The first is unaffordable -- 66.7 million messages a day to keep 7,000
events, 0.011% useful, and it drained a key. The second is free but appears
to see roughly a fifth of what the firehose saw, and candidates from it
carry twice the drawdown and a tenth of the range of the ones that
produced the only profitable trades here. The third costs almost nothing
and every message is a real event, but a 90-second sample of ONE event
proves the mechanism, not the coverage.

So run the cheap ones together, dedupe by mint, and record which feed saw
each candidate first. Union means better coverage than either alone, and
the attribution turns "which feed is better" from an argument into a query.
"""
from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)


class MultiLaunchFeed:
    def __init__(self, feeds: dict):
        self.feeds = feeds                    # name -> feed instance
        self._first_seen: dict[str, str] = {}  # mint -> feed that saw it first
        self.thread_error: BaseException | None = None

    def start(self) -> None:
        for name, f in self.feeds.items():
            try:
                f.start()
                log.info("feed %s started", name)
            except Exception as e:
                log.error("feed %s failed to start: %s", name, e)

    def stop(self) -> None:
        for f in self.feeds.values():
            try:
                f.stop()
            except Exception:
                pass

    def source_of(self, key: str | None) -> str | None:
        """Look up by mint OR signature, since feeds identify events
        differently and one of them has no mint until later."""
        return self._first_seen.get(key) if key else None

    def alive(self) -> dict:
        """Per-feed liveness, so a silent feed is visible rather than
        merely absent from the attribution table."""
        out = {}
        for name, f in self.feeds.items():
            try:
                out[name] = {"events": len(getattr(f, "events", [])),
                             "error": getattr(f, "thread_error", None)}
            except Exception:
                out[name] = {"events": -1, "error": "unreadable"}
        return out

    def recent(self, max_age_sec: float = 900) -> list:
        """Union across feeds, first sighting wins.

        A feed dying must not look like a quiet market, so if EVERY feed has
        a dead thread the error is surfaced for the scalper's health check.
        One feed dying while another still delivers is survivable and only
        logged -- that redundancy is the point of running more than one.
        """
        errs = [getattr(f, "thread_error", None) for f in self.feeds.values()]
        if errs and all(e is not None for e in errs):
            self.thread_error = errs[0]
        out, seen = [], set()
        for name, f in self.feeds.items():
            try:
                events = f.recent(max_age_sec=max_age_sec)
            except Exception as e:
                log.warning("feed %s recent() failed: %s", name, e)
                continue
            for ev in events:
                mint = getattr(ev, "mint", None)
                key = mint or getattr(ev, "signature", None)
                if not key or key in seen:
                    continue
                seen.add(key)
                # Attribute by whatever key identifies the event. The
                # narrow feed yields only a SIGNATURE -- its mint is
                # resolved later, in the scalper -- so keying attribution
                # on mint alone made that feed permanently invisible: it
                # could be delivering launches and still show zero rows.
                sig = getattr(ev, "signature", None)
                for k in (mint, sig):
                    if k and k not in self._first_seen:
                        self._first_seen[k] = name
                out.append(ev)
        return out

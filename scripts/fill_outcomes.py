#!/usr/bin/env python3
"""Complete the candidate journal by recording what HAPPENED to each coin.

The journal already stores every feature the live system computed for
every candidate -- range, volume acceleration, dollar volume, distinct
buyers -- whether or not the coin was bought. That makes it a shadow test:
any combination of those features can be scored retroactively on exactly
the same coins, with no money and no live experiment.

The half that was missing is the outcome. This fills it in for candidates
old enough to have settled, using the same exit rule the live system
trades (30% trail, 30-minute cap, entry at the close of minute 2), so a
shadow result is directly comparable to a real one.

Runs as a loop; safe to restart.
"""
from __future__ import annotations

import logging
import sqlite3
import sys
import time

sys.path.insert(0, "src")
from memebot.data.gt import GeckoTerminal  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("outcomes")

DB = "data/scalp.db"
COST, DEAD_RECOVERY, TRAIL, HORIZON = 0.016, 0.10, 0.30, 30
SETTLE_MIN = 40          # a 30-minute hold plus slack before judging


def outcome_from_bars(bars: list) -> float | None:
    """Entry at the close of minute 2; 30% trail; 30-minute cap."""
    if len(bars) < 4:
        return None
    entry_px = float(bars[1][4])
    if entry_px <= 0:
        return None
    fwd = bars[2:]
    t0 = fwd[0][0]
    traded = [b[0] for b in fwd if (b[5] or 0) > 0]
    last = max(traded) if traded else t0
    peak = entry_px
    for b in fwd:
        ts, hi, lo, c = b[0], float(b[2]), float(b[3]), float(b[4])
        if ts > last:
            return DEAD_RECOVERY - 1 - COST
        if (ts - t0) / 60 > HORIZON:
            return c / entry_px - 1 - COST
        peak = max(peak, hi)
        if lo <= peak * (1 - TRAIL):
            return max(peak * (1 - TRAIL), lo) / entry_px - 1 - COST
    return DEAD_RECOVERY - 1 - COST


def main() -> int:
    gt = GeckoTerminal()
    while True:
        db = sqlite3.connect(DB, timeout=60)
        db.execute("PRAGMA busy_timeout=60000")
        cutoff = time.time() - SETTLE_MIN * 60
        todo = list(db.execute(
            "SELECT mint FROM candidate_journal WHERE outcome IS NULL "
            "AND ts < ? ORDER BY ts DESC LIMIT 40", (cutoff,)))
        db.close()
        if not todo:
            time.sleep(300)
            continue
        done = 0
        for (mint,) in todo:
            try:
                pools = gt.token_pools(mint)
                if not pools:
                    continue
                bars = gt.ohlcv(pools[0].address, limit=60)
                ret = outcome_from_bars(bars)
                if ret is None:
                    continue
                db = sqlite3.connect(DB, timeout=60)
                db.execute("PRAGMA busy_timeout=60000")
                db.execute("UPDATE candidate_journal SET outcome=?, "
                           "outcome_ts=? WHERE mint=?",
                           (float(ret), time.time(), mint))
                db.commit()
                db.close()
                done += 1
            except Exception as e:
                log.warning("outcome for %s failed: %s", mint[:10], e)
        log.info("filled %d outcomes (%d pending)", done, len(todo))
        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())

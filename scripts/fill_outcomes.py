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
from memebot.data.gt import GeckoTerminal, sanitize_bars  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("outcomes")

DB = "data/scalp.db"
COST, DEAD_RECOVERY, TRAIL, HORIZON = 0.016, 0.10, 0.30, 30
SETTLE_MIN = 40          # a 30-minute hold plus slack before judging


# Every exit rule worth comparing, scored on the SAME coins.
#
# The live ledger returns -15.2% while the identical rule scored on bars
# returns +24.3%. That 40-point gap is not coin selection -- deaths are
# zero -- it is the difference between a price that appears in a chart and
# a price we can trade at. Two positions peaked at 2.3x and 2.4x and exited
# at -64% and -58%, because the spike never landed in a sample.
#
# A trail must SEE a peak to arm against it. A take-profit and a timed exit
# do not. So record all of them per candidate and let the comparison be a
# query rather than an argument.
EXITS = {
    "trail30": ("trail", 0.30, 30),
    "trail15": ("trail", 0.15, 30),
    "trail10": ("trail", 0.10, 30),
    "tp1_5x": ("tp", 1.5, 30),
    "tp2x": ("tp", 2.0, 30),
    "time10": ("time", 0.0, 10),
    "time30": ("time", 0.0, 30),
}


def outcome_under(bars: list, kind: str, param: float,
                  horizon: float) -> float | None:
    """Score one exit rule. Peaks come from bar highs, which FLATTERS the
    trail -- it is the optimistic bound, and the live gap against it is
    precisely what we are measuring."""
    if len(bars) < 4:
        return None
    entry = float(bars[1][4])
    if entry <= 0:
        return None
    fwd = bars[2:]
    t0 = fwd[0][0]
    traded = [b[0] for b in fwd if (b[5] or 0) > 0]
    last = max(traded) if traded else t0
    peak = entry
    for b in fwd:
        ts, hi, lo, c = b[0], float(b[2]), float(b[3]), float(b[4])
        if ts > last:
            return DEAD_RECOVERY - 1 - COST
        if (ts - t0) / 60 > horizon:
            return min(c / entry - 1 - COST, 20.0)
        if kind == "tp" and hi >= entry * param:
            return param - 1 - COST
        if kind == "trail":
            peak = max(peak, hi)
            if lo <= peak * (1 - param):
                return min(max(peak * (1 - param), lo) / entry - 1 - COST,
                           20.0)
    return DEAD_RECOVERY - 1 - COST


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
                bars = sanitize_bars(gt.ohlcv(pools[0].address, limit=60))
                ret = outcome_from_bars(bars)
                if ret is None:
                    continue
                db = sqlite3.connect(DB, timeout=60)
                db.execute("PRAGMA busy_timeout=60000")
                cols, vals = ["outcome=?", "outcome_ts=?"], [float(ret),
                                                             time.time()]
                for name, (kind, param, hz) in EXITS.items():
                    r2 = outcome_under(bars, kind, param, hz)
                    if r2 is not None:
                        cols.append(f"out_{name}=?")
                        vals.append(float(r2))
                vals.append(mint)
                db.execute("UPDATE candidate_journal SET "
                           + ", ".join(cols) + " WHERE mint=?", vals)
                db.commit()
                db.close()
                done += 1
            except Exception as e:
                log.warning("outcome for %s failed: %s", mint[:10], e)
        log.info("filled %d outcomes (%d pending)", done, len(todo))
        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())

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
MAX_TRIES = 3            # attempts before a row is written off as unscoreable


def bump(mint: str) -> None:
    """Record that this row was attempted, so a permanently unscoreable one
    cannot occupy the batch forever."""
    try:
        db = sqlite3.connect(DB, timeout=60)
        db.execute("PRAGMA busy_timeout=60000")
        db.execute("UPDATE candidate_journal SET outcome_tries = "
                   "COALESCE(outcome_tries, 0) + 1 WHERE mint = ?", (mint,))
        db.commit()
        db.close()
    except sqlite3.Error as e:
        log.warning("could not record attempt for %s: %s", mint[:10], e)


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
    # The trail branch above arms on a bar's HIGH and may fill inside the
    # bar that set it. On the live migration population that overstates the
    # mean by 47 points: 2EoFtZ scores +374% off a 5.3x high printed on
    # $6,339 against a $915 median bar, and the position actually closed at
    # -26%. These columns arm the peak only once a bar has CLOSED and let
    # the stop fill from the NEXT bar, which is a price that survived a
    # full minute. Rank rules on these.
    "exec30": ("exec", 0.30, 30),
    "exec15": ("exec", 0.15, 30),
    "exec10": ("exec", 0.10, 30),
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
        if kind == "exec":
            # stop first, from the peak as it stood when the LAST bar closed
            stop = peak * (1 - param)
            if lo <= stop:
                op = float(b[1])
                fill = min(stop, op) if op > 0 else stop
                return min(fill / entry - 1 - COST, 20.0)
            peak = max(peak, c)
    return DEAD_RECOVERY - 1 - COST


def window_from(bars: list, det_ts: float) -> list:
    """The bars belonging to THIS candidate's launch, not the latest hour.

    outcome_from_bars takes its entry from bars[1], so if the list starts
    somewhere other than the detection minute the entry price belongs to a
    different day. Verified against the aggregator: an unanchored fetch for
    a pool observed six days ago returns bars 136 hours after the launch it
    is supposed to measure.

    Detection lands at an arbitrary second, so the start is floored to the
    minute: that keeps the bar detection happened IN and no earlier one. A
    60-second tolerance instead admits the preceding bar, which shifts every
    later index by one and takes the entry from the wrong minute.
    """
    start = int(det_ts // 60) * 60
    return [b for b in bars if b[0] >= start]


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
        # Also pick up rows that HAVE an outcome but are missing the
        # per-exit columns. Selecting only on "outcome IS NULL" meant every
        # column added later stayed empty forever on existing rows -- the
        # exit comparison reported zero candidates and looked like a lack
        # of data rather than a backfill that never ran.
        # Give up on a row after MAX_TRIES. A pool the aggregator has
        # dropped can never be scored, and without this the newest such rows
        # are re-selected every pass, accumulate at the head of the DESC
        # ordering, and eventually fill the batch so the backfill spins on
        # them and coverage freezes short of an answer.
        todo = list(db.execute(
            "SELECT mint, ts FROM candidate_journal "
            "WHERE (outcome IS NULL OR out_trail30 IS NULL "
            "OR out_exec10 IS NULL) "
            "AND COALESCE(outcome_tries, 0) < ? "
            "AND ts < ? ORDER BY ts DESC LIMIT 40", (MAX_TRIES, cutoff)))
        db.close()
        if not todo:
            time.sleep(300)
            continue
        done = 0
        for mint, det_ts in todo:
            try:
                pools = gt.token_pools(mint)
                if not pools:
                    # An empty list means "no pools" OR "no answer". Counting
                    # a throttled call as evidence the pool is gone writes
                    # off scoreable rows, and does it fastest exactly when
                    # the aggregator is busiest -- which is now.
                    if gt.http.last_error is None:
                        bump(mint)
                    else:
                        log.info("%s: no answer (%s) — not counted against "
                                 "it", mint[:10], gt.http.last_error)
                    continue
                # Anchor the fetch to WHEN THIS CANDIDATE WAS SEEN. Without
                # before_timestamp the aggregator returns the most recent
                # hour, which is right only while the row is fresh. Widening
                # the selection to backfill columns added later made every
                # historical row eligible, and each would have been scored
                # against today's prices -- entry taken from a bar hours
                # after the launch it is supposed to measure. Silent, and it
                # would have poisoned the exact dataset the go/no-go
                # decision rests on.
                bars = sanitize_bars(gt.ohlcv(
                    pools[0].address, limit=60,
                    before_timestamp=int(det_ts) + (HORIZON + 10) * 60))
                bars = window_from(bars, det_ts)
                ret = outcome_from_bars(bars)
                if ret is None:
                    # bars in hand and still not scoreable: a real verdict
                    if gt.http.last_error is None:
                        bump(mint)
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
                # A raise here is a code or data fault, not throttling --
                # get_json swallows transport errors and returns None. Count
                # it, so one poisonous row cannot occupy the batch forever.
                bump(mint)
                log.warning("outcome for %s failed: %s", mint[:10], e)
        log.info("filled %d outcomes (%d pending)", done, len(todo))
        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())

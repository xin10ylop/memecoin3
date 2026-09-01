#!/usr/bin/env python3
"""Which exit rule actually captures these coins?

The live ledger returns -15.2%/trade while the identical entry rule scored
on price bars returns +24.3%. Deaths are zero, so the entries are not the
problem: the gap is between prices that appear in a chart and prices a bot
can trade at. Two positions peaked at 2.3x and 2.4x and exited at -64% and
-58%, because a trail must SEE a peak to arm against it and those spikes
never landed in a sample.

A take-profit or a timed exit needs no peak. This scores every rule on the
SAME candidates so the choice is made by data.

One caveat stated up front: all of these are scored from bar highs and
lows, which FLATTERS the trailing exits specifically -- they get credit for
peaks a live bot may never see. The take-profit and timed rules do not
benefit, so if a trail only wins here by a little, it loses in reality.
"""
from __future__ import annotations

import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else "data/scalp.db"
RULES = ["outcome", "out_trail30", "out_trail15", "out_trail10",
         "out_tp1_5x", "out_tp2x", "out_time10", "out_time30"]


def main() -> int:
    db = sqlite3.connect(DB)
    have = {r[1] for r in db.execute("PRAGMA table_info(candidate_journal)")}
    cols = [c for c in RULES if c in have]
    if len(cols) < 2:
        print("exit columns not populated yet — let fill_outcomes run for a"
              " while after updating, then re-run this")
        return 0
    where = ("feed IN ('portal','narrow') AND range_frac >= 0.172 "
             "AND accel BETWEEN 1.0 AND 10.0")
    n = db.execute(f"SELECT COUNT(*) FROM candidate_journal WHERE {where} "
                   f"AND out_trail30 IS NOT NULL").fetchone()[0]
    print(f"candidates the LIVE RULE would have bought, with outcomes: {n}")
    if n < 15:
        print("(too few to compare yet — needs ~15+)")
        return 0
    print()
    print(f"{'exit rule':<14} {'n':>4} {'mean':>9} {'median':>9} "
          f"{'2x':>6} {'win':>6}")
    for c in cols:
        row = db.execute(
            f"SELECT COUNT({c}), AVG({c}), "
            f"AVG(CASE WHEN {c} >= 1 THEN 1.0 ELSE 0 END), "
            f"AVG(CASE WHEN {c} > 0 THEN 1.0 ELSE 0 END) "
            f"FROM candidate_journal WHERE {where} AND {c} IS NOT NULL"
        ).fetchone()
        cnt, mean, r2x, win = row
        if not cnt:
            continue
        med = db.execute(
            f"SELECT {c} FROM candidate_journal WHERE {where} AND {c} IS NOT "
            f"NULL ORDER BY {c} LIMIT 1 OFFSET {cnt // 2}").fetchone()
        label = "trail30 (live)" if c == "outcome" else c.replace("out_", "")
        print(f"{label:<14} {cnt:>4} {mean:>+8.1%} "
              f"{(med[0] if med else 0):>+8.1%} {r2x:>5.0%} {win:>5.0%}")
    print()
    print("Trailing rules are scored against bar HIGHS and so are flattered:")
    print("they are credited with peaks a live bot may never sample. The")
    print("take-profit and timed rules get no such help, so a trail that")
    print("only just wins here loses in practice.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

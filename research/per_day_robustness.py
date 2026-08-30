#!/usr/bin/env python3
"""Does the rule work on each day separately, or is it one good day?

Capacity work exposed the real limit: every result rests on a handful of
days, and resampling two positive days can only produce positive answers.
Pool count is no longer the binding constraint -- REGIME count is. Until
more days accumulate, the strongest available test is whether each day
stands on its own.

An edge carried by a single day is a regime, not an edge, however many
pools support it.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "research")
from full_sample_test import MIN_RANGE, boot, entry, load_all, simulate  # noqa

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"


def main() -> int:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    bars = load_all(db)
    rows = []
    for p, b in bars.items():
        f = entry(b)
        if f is None or f["range"] < MIN_RANGE:
            continue
        f["day"] = pd.to_datetime(float(b.ts.iloc[0]), unit="s").date()
        f["ret"] = simulate(b, f["entry_px"])
        f["passes"] = 1.0 <= f["vol_ratio"] < 10.0
        rows.append(f)
    df = pd.DataFrame(rows)
    print(f"qualifying-on-range pools: {len(df)}\n")

    print(f"{'day':<12} {'rule':<16} {'n':>4} {'mean':>9} {'CI':>21} {'win':>5}")
    day_means = {}
    for day, g in df.groupby("day"):
        for lab, sub in [("range only", g), ("+ acceleration", g[g.passes])]:
            a = sub.ret.to_numpy()
            if len(a) < 8:
                print(f"{str(day):<12} {lab:<16} {len(a):>4}   (too few)")
                continue
            cl, ch = boot(a)
            print(f"{str(day):<12} {lab:<16} {len(a):>4} {a.mean():>+8.1%} "
                  f"[{cl:>+7.1%},{ch:>+7.1%}] {(a>0).mean():>5.0%}")
            if lab == "+ acceleration":
                day_means[day] = (a.mean(), len(a))
        print()

    if len(day_means) >= 2:
        vals = [m for m, _ in day_means.values()]
        pos = sum(v > 0 for v in vals)
        print(f"days where the filtered rule is positive: {pos}/{len(vals)}")
        # how much does the single best day carry?
        tot = df[df.passes]
        best_day = max(day_means.items(), key=lambda kv: kv[1][0])[0]
        without = tot[tot.day != best_day].ret.to_numpy()
        print(f"best day: {best_day} ({day_means[best_day][0]:+.1%})")
        if len(without) >= 8:
            cl, ch = boot(without)
            print(f"WITHOUT the best day: n={len(without)} "
                  f"{without.mean():+.1%} CI [{cl:+.1%},{ch:+.1%}]")
            print("  -> " + ("survives dropping its best day"
                             if without.mean() > 0 and cl > 0 else
                             "does NOT survive dropping its best day — this "
                             "is a regime, not yet a proven edge"))
    print("\nNOTE: with only a few clean days, no amount of pools can "
          "establish regime robustness. More DAYS is the binding need.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

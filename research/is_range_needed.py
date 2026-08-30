#!/usr/bin/env python3
"""Is the range filter earning its keep, or is acceleration the whole signal?

Every test so far conditioned on range >= 17.2% first and asked what
acceleration added. That ordering was inherited, never justified -- and it
matters more than it looks, because this edge scales with TRADE COUNT and
nothing else. Capacity is fixed at a few dollars per pool, so the only way
to make it bigger is to qualify more launches.

If acceleration alone does the work, dropping range roughly triples the
opportunity set for free. If range adds real selectivity, it stays.
Deaths included, nothing dropped for dying young.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "research")
from full_sample_test import boot, entry, load_all, simulate  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"


def main() -> int:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    bars = load_all(db)
    rows = []
    for p, b in bars.items():
        f = entry(b)
        if f is None:
            continue
        f["ret"] = simulate(b, f["entry_px"])
        f["day"] = pd.to_datetime(float(b.ts.iloc[0]), unit="s").date()
        rows.append(f)
    df = pd.DataFrame(rows)
    n_all = len(df)
    print(f"all pools with a computable entry: {n_all}\n")

    accel = (df.vol_ratio >= 1.0) & (df.vol_ratio < 10.0)
    rng_ok = df["range"] >= 0.172
    variants = [
        ("no filter at all", df),
        ("range only", df[rng_ok]),
        ("acceleration only", df[accel]),
        ("range + acceleration", df[rng_ok & accel]),
        ("acceleration + range>=5%", df[accel & (df["range"] >= 0.05)]),
        ("acceleration + range>=10%", df[accel & (df["range"] >= 0.10)]),
    ]
    print(f"{'rule':<26} {'n':>4} {'share':>6} {'mean':>9} {'CI':>21} "
          f"{'median':>8} {'win':>5}")
    res = {}
    for lab, sub in variants:
        a = sub.ret.to_numpy()
        if len(a) < 10:
            print(f"{lab:<26} {len(a):>4}   (too few)")
            continue
        cl, ch = boot(a)
        res[lab] = (a, cl, sub)
        print(f"{lab:<26} {len(a):>4} {len(a)/n_all:>5.0%} {a.mean():>+8.1%} "
              f"[{cl:>+7.1%},{ch:>+7.1%}] {np.median(a):>+8.1%} "
              f"{(a>0).mean():>5.0%}")

    print("\nthroughput view -- what matters when capacity per trade is fixed:")
    print(f"{'rule':<26} {'trades/day*':>12} {'usd/day @ $10':>14}")
    for lab, (a, cl, sub) in res.items():
        per_day = 2.4 * 60 * 24 * (len(a) / n_all)
        per_day = min(per_day, 6 * (24 * 60 / 30))     # concurrency cap
        print(f"{lab:<26} {per_day:>12.0f} {per_day * 10 * a.mean():>13,.0f}")
    print("  *launch supply at 2.4 creations/min, capped by 6 slots x 30min")

    # does either filter survive per-day?
    print("\nper-day, the two candidates:")
    for lab in ["acceleration only", "range + acceleration"]:
        if lab not in res:
            continue
        sub = res[lab][2]
        parts = []
        for day, g in sub.groupby("day"):
            if len(g) >= 8:
                parts.append(f"{day} {g.ret.mean():+.0%} (n={len(g)})")
        print(f"  {lab:<24} " + " | ".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

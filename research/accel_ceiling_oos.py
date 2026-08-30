#!/usr/bin/env python3
"""Does an acceleration CEILING survive out of sample, or is it curve-fit?

The magnitude buckets suggest a hump: moderate acceleration pays, a >5x
second minute does not. That is a plausible mechanism -- an explosive
second minute is a frenzy at its peak rather than demand building -- but
bucket boundaries chosen after seeing the buckets are exactly how
overfitting happens. Same time split and placebo as before.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "research")
from full_sample_test import MIN_RANGE, boot, entry, load_all, simulate  # noqa

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
RULES = [("accel >= 1.0 (no ceiling)", 1.0, np.inf),
         ("1.0 <= accel < 10", 1.0, 10.0),
         ("1.0 <= accel < 5", 1.0, 5.0),
         ("1.0 <= accel < 3", 1.0, 3.0),
         ("1.2 <= accel < 5", 1.2, 5.0)]


def main() -> int:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    bars = load_all(db)
    rows = []
    for p, b in bars.items():
        f = entry(b)
        if f is None or f["range"] < MIN_RANGE:
            continue
        f["t0"] = float(b.ts.iloc[0])
        f["ret"] = simulate(b, f["entry_px"])
        rows.append(f)
    df = pd.DataFrame(rows).sort_values("t0").reset_index(drop=True)
    cut = df.t0.quantile(0.5)
    early, late = df[df.t0 <= cut], df[df.t0 > cut]

    print(f"{'rule':<28} {'sample':<6} {'n':>4} {'mean':>9} {'CI':>21}")
    oos = {}
    for lab, lo_a, hi_a in RULES:
        for nm, part in [("EARLY", early), ("LATE", late)]:
            sub = part[(part.vol_ratio >= lo_a) & (part.vol_ratio < hi_a)]
            a = sub.ret.to_numpy()
            if len(a) < 10:
                print(f"{lab:<28} {nm:<6} {len(a):>4}   (too few)")
                continue
            cl, ch = boot(a)
            print(f"{lab:<28} {nm:<6} {len(a):>4} {a.mean():>+8.1%} "
                  f"[{cl:>+7.1%},{ch:>+7.1%}]")
            if nm == "LATE":
                oos[lab] = (a, cl, ch)
        print()

    print("out-of-sample ranking (LATE half only, the honest half):")
    for lab, (a, cl, ch) in sorted(oos.items(), key=lambda kv: -kv[1][0].mean()):
        print(f"  {lab:<28} n={len(a):>3} {a.mean():>+8.1%} floor {cl:>+7.1%}")

    base = oos.get("accel >= 1.0 (no ceiling)")
    best = max(oos.items(), key=lambda kv: kv[1][0].mean())
    if base is not None:
        gain = best[1][0].mean() - base[0].mean()
        print(f"\nceiling adds {gain:+.1%}/trade out of sample "
              f"({best[0].strip()} vs no ceiling)")
        if gain < 0.05:
            print("  -> NOT WORTH IT: keep the simple floor, fewer knobs to "
                  "overfit.")
        elif best[1][1] > 0:
            print("  -> KEEP THE CEILING: it improves OOS and its floor "
                  "clears zero.")
        else:
            print("  -> improves the mean but the OOS floor still spans "
                  "zero; adopt only if the mechanism holds on more data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

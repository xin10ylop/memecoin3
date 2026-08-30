#!/usr/bin/env python3
"""Out-of-sample test of the acceleration filter.

vol_ratio was chosen for predicting SURVIVAL, then found to predict
RETURNS -- but eight variants were compared to land on it, so the in-sample
number is optimistic by construction. This splits the harvest by TIME:
fit nothing on the later half, just apply the rule and see what happens.

Also runs a placebo -- the same filter applied to a random subset of equal
size -- so the result has to beat luck, not merely beat zero.
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
        f["pool"], f["t0"] = p, float(b.ts.iloc[0])
        f["ret"] = simulate(b, f["entry_px"])
        rows.append(f)
    df = pd.DataFrame(rows).sort_values("t0").reset_index(drop=True)
    print(f"qualifying pools: {len(df)}")
    cut = df.t0.quantile(0.5)
    early, late = df[df.t0 <= cut], df[df.t0 > cut]
    print(f"split at {pd.to_datetime(cut, unit='s')}  "
          f"early={len(early)} late={len(late)}\n")

    print(f"{'sample':<22} {'rule':<20} {'n':>4} {'mean':>9} {'CI':>21}")
    for name, part in [("EARLY (in-sample)", early), ("LATE (out-of-sample)", late)]:
        for lab, sub in [("all range>=17.2%", part),
                         ("vol_ratio>=1.0", part[part.vol_ratio >= 1.0])]:
            a = sub.ret.to_numpy()
            if len(a) < 10:
                print(f"{name:<22} {lab:<20} {len(a):>4}   (too few)")
                continue
            lo, hi = boot(a)
            print(f"{name:<22} {lab:<20} {len(a):>4} {a.mean():>+8.1%} "
                  f"[{lo:>+7.1%},{hi:>+7.1%}]")

    # placebo: does a random filter of the same size do as well?
    late_f = late[late.vol_ratio >= 1.0]
    n_keep = len(late_f)
    rng = np.random.default_rng(3)
    placebo = [late.ret.sample(n_keep, random_state=int(rng.integers(1e9))).mean()
               for _ in range(2000)] if n_keep >= 10 and len(late) > n_keep else []
    if placebo:
        obs = late_f.ret.mean()
        pval = float((np.array(placebo) >= obs).mean())
        print(f"\nplacebo (random subsets of {n_keep} from the same period):")
        print(f"  observed {obs:+.1%} vs placebo median "
              f"{np.median(placebo):+.1%}   p = {pval:.3f}")
        print("  -> " + ("beats chance" if pval < 0.05 else
                         "NOT distinguishable from a random subset"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

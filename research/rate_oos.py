#!/usr/bin/env python3
"""Out-of-sample test on RATES, the statistic the sample can support.

Mean-based OOS testing failed (placebo p=0.43) for a reason that is about
the estimator, not the filter: with a top trade near +800%, a sample mean
of 100 fat-tailed trades mostly reports its single largest observation, so
it cannot detect a selection effect it is drowning in.

Rates are stable. Pooled, the filter makes a 2x 4.5x more likely and a
total loss 3x less likely, both at p<1e-4. The question this answers is
whether that holds on data the filter was never chosen on.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, "research")
from full_sample_test import MIN_RANGE, entry, load_all, simulate  # noqa: E402


def main() -> int:
    db = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else "data/panel.db",
                         timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    bars = load_all(db)
    rows = []
    for p, b in bars.items():
        f = entry(b)
        if f is None or f["range"] < MIN_RANGE:
            continue
        f["ret"] = simulate(b, f["entry_px"])
        f["t0"] = float(b.ts.iloc[0])
        f["pass"] = 1.0 <= f["vol_ratio"] < 10.0
        rows.append(f)
    df = pd.DataFrame(rows).sort_values("t0").reset_index(drop=True)
    cut = df.t0.quantile(0.5)
    parts = [("EARLY (in-sample)", df[df.t0 <= cut]),
             ("LATE (out-of-sample)", df[df.t0 > cut])]

    for name, part in parts:
        A, B = part[part["pass"]], part[~part["pass"]]
        if len(A) < 15 or len(B) < 15:
            print(f"{name}: too few to test")
            continue
        print(f"\n{name}  kept n={len(A)}  rejected n={len(B)}")
        for lab, fn in [("2x+ winners", lambda g: (g.ret >= 1).sum()),
                        ("deaths <=-85%", lambda g: (g.ret <= -0.85).sum())]:
            ka, kb = int(fn(A)), int(fn(B))
            odds, p = stats.fisher_exact([[ka, len(A) - ka],
                                          [kb, len(B) - kb]])
            star = "***" if p < 0.001 else "**" if p < 0.01 else \
                   "*" if p < 0.05 else "ns"
            print(f"  {lab:<15} kept {ka/len(A):>5.0%}  rejected "
                  f"{kb/len(B):>5.0%}  OR={odds:>5.2f}  p={p:.4f} {star}")

    # A permutation test on the LATE half: shuffle the pass/reject labels
    # and see how often chance produces this large a gap in 2x rate.
    late = df[df.t0 > cut]
    A = late[late["pass"]]
    obs = (A.ret >= 1).mean() - (late[~late["pass"]].ret >= 1).mean()
    rng = np.random.default_rng(5)
    lab = late["pass"].to_numpy()
    ret = late.ret.to_numpy()
    null = []
    for _ in range(20000):
        s = rng.permutation(lab)
        null.append((ret[s] >= 1).mean() - (ret[~s] >= 1).mean())
    p = float((np.array(null) >= obs).mean())
    print(f"\npermutation test on the OOS half (20k shuffles):")
    print(f"  observed 2x-rate gap {obs:+.1%}, chance median "
          f"{np.median(null):+.1%}, p = {p:.4f}")
    print("  -> " + ("the selection effect is real out of sample"
                     if p < 0.05 else
                     "NOT significant out of sample"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

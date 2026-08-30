#!/usr/bin/env python3
"""Judge the filter on a statistic that small samples can actually support.

Daily means here are decided by whether one enormous winner happened to
land inside the subset: with 14-82 trades a day and a distribution whose
top trade can return +800%, the mean is mostly noise about a single
observation. The filter looked transformative on Aug 28 (+84% vs -14%) and
harmful on Aug 27 and 29, which is the signature of an unstable estimator
rather than an unstable edge -- or of no edge at all.

RATES are far better behaved. If acceleration genuinely selects launches
with more forward potential, it should raise the FREQUENCY of large
winners and lower the frequency of instant deaths, consistently, on every
day. If it does not, the mean improvements were luck.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "research")
from full_sample_test import MIN_RANGE, entry, load_all, simulate  # noqa: E402


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """CI for a rate -- honest at small n, unlike a normal approximation."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


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
        f["day"] = pd.to_datetime(float(b.ts.iloc[0]), unit="s").date()
        f["pass"] = 1.0 <= f["vol_ratio"] < 10.0
        rows.append(f)
    df = pd.DataFrame(rows)
    print(f"range-qualifying pools: {len(df)}\n")

    def rates(g):
        n = len(g)
        return {"n": n,
                "win": (g.ret > 0).mean(),
                "2x": (g.ret >= 1.0).mean(),
                "dead": (g.ret <= -0.85).mean()}

    print("BIG-WINNER RATE (ret >= +100%), by day")
    print(f"{'day':<12} {'unfiltered':>22} {'filtered':>22} {'lift':>7}")
    lifts = []
    for day, g in df.groupby("day"):
        a, b_ = g, g[g["pass"]]
        if len(b_) < 8:
            print(f"{str(day):<12} {'(too few filtered)':>22}")
            continue
        ka, kb = int((a.ret >= 1).sum()), int((b_.ret >= 1).sum())
        la, ha = wilson(ka, len(a))
        lb, hb = wilson(kb, len(b_))
        lift = kb / len(b_) - ka / len(a)
        lifts.append(lift)
        print(f"{str(day):<12} {ka/len(a):>7.0%} [{la:.0%},{ha:.0%}] n={len(a):<4} "
              f"{kb/len(b_):>7.0%} [{lb:.0%},{hb:.0%}] n={len(b_):<4} {lift:>+6.1%}")

    print("\nDEATH RATE (ret <= -85%), by day")
    print(f"{'day':<12} {'unfiltered':>12} {'filtered':>12} {'lift':>8}")
    dlifts = []
    for day, g in df.groupby("day"):
        a, b_ = g, g[g["pass"]]
        if len(b_) < 8:
            continue
        da, db_ = (a.ret <= -0.85).mean(), (b_.ret <= -0.85).mean()
        dlifts.append(db_ - da)
        print(f"{str(day):<12} {da:>11.0%} {db_:>11.0%} {db_-da:>+8.1%}")

    print("\noverall (pooled):")
    for lab, g in [("unfiltered", df), ("filtered", df[df["pass"]])]:
        r = rates(g)
        lo, hi = wilson(int((g.ret >= 1).sum()), len(g))
        print(f"  {lab:<11} n={r['n']:<4} win {r['win']:.0%}  "
              f"2x {r['2x']:.0%} [{lo:.0%},{hi:.0%}]  dead {r['dead']:.0%}")

    print("\nverdict:")
    if lifts:
        pos = sum(x > 0 for x in lifts)
        print(f"  big-winner rate improved on {pos}/{len(lifts)} days "
              f"(mean lift {np.mean(lifts):+.1%})")
    if dlifts:
        neg = sum(x < 0 for x in dlifts)
        print(f"  death rate reduced on {neg}/{len(dlifts)} days "
              f"(mean change {np.mean(dlifts):+.1%})")
    print("  a filter that genuinely selects survivors should do BOTH, "
          "on every day. Anything less is a story about one lucky day.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

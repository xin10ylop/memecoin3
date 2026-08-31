#!/usr/bin/env python3
"""The trader's full setup, tested end to end and out of sample.

Two guides describe one setup: strong volume, rising holders, and a clean
chart. Volume is in the live rule. Holders started recording tonight. The
chart half tested significant on its own -- buying within 10% of the
window high triples the doubling rate (OR 2.81, p=0.014) and an upward
drift of 10-50% marks the best bucket.

This stacks them. Four filters have now been examined on this dataset, so
the in-sample number is optimistic by construction and only the time-split
result carries weight. Rates are used rather than means, because a mean
over ~50 fat-tailed trades mostly reports its largest observation.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, "research")
from full_sample_test import (COST, DEAD_RECOVERY, MIN_RANGE,  # noqa: E402
                              entry, load_all)

TRAIL, HORIZON, CAPTURE = 0.30, 30, 0.43


def sim(b, entry_px, *, perfect):
    """perfect=True arms the trail on bar HIGHS (what a backtest sees);
    False arms it on closes (what 10-second polling can miss). Live trail
    exits measured ~43% capture between the two, so the honest number is
    the blend, not the headline."""
    fwd = b.iloc[2:]
    if fwd.empty:
        return DEAD_RECOVERY - 1 - COST
    ts = fwd.ts.to_numpy(float)
    hi, lo, c = (fwd.h.to_numpy(float), fwd.l.to_numpy(float),
                 fwd.c.to_numpy(float))
    vol = fwd.vol_usd.to_numpy(float)
    t0 = ts[0]
    last = ts[vol > 0].max() if (vol > 0).any() else t0
    peak = entry_px
    for j in range(len(ts)):
        if ts[j] > last:
            return DEAD_RECOVERY - 1 - COST
        if (ts[j] - t0) / 60 > HORIZON:
            return min(c[j] / entry_px - 1 - COST, 20.0)
        peak = max(peak, hi[j] if perfect else c[j])
        stop = peak * (1 - TRAIL)
        if perfect:
            if lo[j] <= stop:
                return min(max(stop, lo[j]) / entry_px - 1 - COST, 20.0)
        elif c[j] <= stop:
            return min(c[j] / entry_px - 1 - COST, 20.0)
    return DEAD_RECOVERY - 1 - COST


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def build(db) -> pd.DataFrame:
    bars = load_all(db)
    rows = []
    for p, b in bars.items():
        f = entry(b)
        if f is None or f["range"] < MIN_RANGE:
            continue
        w = b.iloc[:2]
        hi = float(np.nanmax(w.h.to_numpy(float)))
        opened = float(w.c.iloc[0])
        px = f["entry_px"]
        if hi <= 0 or opened <= 0 or px <= 0:
            continue
        ideal = sim(b, px, perfect=True)
        real = sim(b, px, perfect=False)
        rows.append({"ret": ideal, "ret_real": real + CAPTURE * (ideal - real),
                     "t0": float(b.ts.iloc[0]),
                     "accel": f["vol_ratio"], "drawdown": 1 - px / hi,
                     "drift": px / opened - 1})
    return pd.DataFrame(rows).sort_values("t0").reset_index(drop=True)


def report(df: pd.DataFrame, label: str) -> None:
    vol = (df.accel >= 1.0) & (df.accel < 10.0)
    clean = df.drawdown < 0.10
    up = (df.drift >= 0.10) & (df.drift < 0.50)
    print(f"\n{label}  (n={len(df)})")
    print(f"  {'rule':<28} {'n':>4} {'share':>6} {'2x':>16} {'death':>7} "
          f"{'mean':>9} {'mean(real)':>10}")
    for lab, m in [("range only", pd.Series(True, index=df.index)),
                   ("+ volume (live rule)", vol),
                   ("+ clean chart", vol & clean),
                   ("+ upward drift", vol & clean & up)]:
        g = df[m]
        if len(g) < 5:
            print(f"  {lab:<28} {len(g):>4}   (too few)")
            continue
        k = int((g.ret >= 1).sum())
        lo, hi = wilson(k, len(g))
        print(f"  {lab:<28} {len(g):>4} {len(g)/len(df):>5.0%} "
              f"{k/len(g):>6.0%} [{lo:.0%},{hi:.0%}]  "
              f"{(g.ret<=-0.85).mean():>6.0%} {g.ret.mean():>+8.1%} "
              f"{g.ret_real.mean():>+9.1%}")


def main() -> int:
    db = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else "data/panel.db",
                         timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    df = build(db)
    cut = df.t0.quantile(0.5)
    report(df, "ALL DATA (in-sample: four filters were chosen here)")
    report(df[df.t0 <= cut], "EARLY half")
    report(df[df.t0 > cut], "LATE half -- OUT OF SAMPLE, the honest read")

    late = df[df.t0 > cut]
    vol = (late.accel >= 1.0) & (late.accel < 10.0)
    a = late[vol & (late.drawdown < 0.10)]
    b = late[vol & (late.drawdown >= 0.10)]
    if len(a) >= 6 and len(b) >= 6:
        ka, kb = int((a.ret >= 1).sum()), int((b.ret >= 1).sum())
        odds, p = stats.fisher_exact([[ka, len(a) - ka], [kb, len(b) - kb]])
        print(f"\nOUT OF SAMPLE, does the clean-chart filter add to volume?")
        print(f"  clean n={len(a)} 2x {ka/len(a):.0%} | crashed n={len(b)} "
              f"2x {kb/len(b):.0%} | OR={odds:.2f} p={p:.4f}")
        print("  -> " + ("holds out of sample" if p < 0.05 else
                         "NOT significant out of sample at this n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Two questions aimed at making the edge bigger rather than merely real.

1. Does the SIZE of the acceleration matter? If a launch trading 5x its
   first minute pays more than one trading 1.1x, conviction should scale
   with it and sizing becomes a lever. If not, it is a clean binary gate
   and pretending otherwise would just add variance.
2. Is a 30% trail still right? That exit was fitted to a population that
   included the fast deaths this rule now refuses to buy. The survivors
   are a different animal and may deserve a different leash.

Full sample, nothing excluded for dying young.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "research")
from full_sample_test import (COST, DEAD_RECOVERY, MIN_RANGE,  # noqa: E402
                             boot, entry, load_all)

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"


def sim(b: pd.DataFrame, entry_px: float, trail: float, horizon: float,
        tp: float | None = None) -> float:
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
        if (ts[j] - t0) / 60 > horizon:
            return c[j] / entry_px - 1 - COST
        if tp and hi[j] >= entry_px * tp:
            return tp - 1 - COST
        peak = max(peak, hi[j])
        if lo[j] <= peak * (1 - trail):
            return max(peak * (1 - trail), lo[j]) / entry_px - 1 - COST
    return DEAD_RECOVERY - 1 - COST


def main() -> int:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    bars = load_all(db)
    rows = []
    for p, b in bars.items():
        f = entry(b)
        if f is None or f["range"] < MIN_RANGE or f["vol_ratio"] < 1.0:
            continue
        f["bars"] = b
        rows.append(f)
    print(f"pools passing range + acceleration: {len(rows)}\n")

    print("1. does acceleration MAGNITUDE predict return?")
    print(f"   {'accel':<12} {'n':>4} {'mean':>9} {'CI':>21} {'median':>8} {'win':>5}")
    edges = [(1.0, 1.5), (1.5, 2.5), (2.5, 5.0), (5.0, np.inf)]
    for lo_e, hi_e in edges:
        sub = [r for r in rows if lo_e <= r["vol_ratio"] < hi_e]
        if len(sub) < 12:
            continue
        a = np.array([sim(r["bars"], r["entry_px"], 0.30, 30) for r in sub])
        cl, ch = boot(a)
        lab = f"{lo_e:g}-{hi_e:g}x" if np.isfinite(hi_e) else f">{lo_e:g}x"
        print(f"   {lab:<12} {len(a):>4} {a.mean():>+8.1%} "
              f"[{cl:>+7.1%},{ch:>+7.1%}] {np.median(a):>+8.1%} "
              f"{(a>0).mean():>5.0%}")
    r_all = np.array([r["vol_ratio"] for r in rows])
    ret_all = np.array([sim(r["bars"], r["entry_px"], 0.30, 30) for r in rows])
    keep = np.isfinite(r_all) & np.isfinite(ret_all)
    rho = float(pd.Series(np.log(r_all[keep])).corr(
        pd.Series(ret_all[keep]), method="spearman"))
    print(f"   rank correlation log(accel) vs return: {rho:+.3f}")
    print("   -> " + ("SCALE size with acceleration" if rho > 0.15 else
                      "BINARY gate: magnitude adds nothing, do not size on it"))

    print("\n2. what exit fits the pools this rule actually buys?")
    print(f"   {'exit':<26} {'n':>4} {'mean':>9} {'CI':>21} {'median':>8}")
    variants = [("trail 30%, 30min", 0.30, 30, None),
                ("trail 40%, 30min", 0.40, 30, None),
                ("trail 50%, 30min", 0.50, 30, None),
                ("trail 30%, 60min", 0.30, 60, None),
                ("trail 50%, 60min", 0.50, 60, None),
                ("trail 50%, 120min", 0.50, 120, None),
                ("trail 30% + 3x TP", 0.30, 30, 3.0),
                ("trail 50% + 5x TP", 0.50, 60, 5.0)]
    best = None
    for lab, tr, hz, tp in variants:
        a = np.array([sim(r["bars"], r["entry_px"], tr, hz, tp) for r in rows])
        cl, ch = boot(a)
        print(f"   {lab:<26} {len(a):>4} {a.mean():>+8.1%} "
              f"[{cl:>+7.1%},{ch:>+7.1%}] {np.median(a):>+8.1%}")
        if np.isfinite(cl) and (best is None or cl > best[1]):
            best = (lab, cl, a.mean())
    if best:
        print(f"\n   most robust by CI floor: {best[0]} "
              f"(floor {best[1]:+.1%}, mean {best[2]:+.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

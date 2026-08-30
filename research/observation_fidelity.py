#!/usr/bin/env python3
"""What does the backtest's perfect eyesight cost when we only poll?

A live winner peaked at 7.5x entry inside its holding window and exited at
2.4x -- giving back 68% from the high under a 30% trail. The trail is not
broken; the backtest's assumption is. run_exit arms the trail against each
bar's HIGH, i.e. the best price the token touched at any instant. The
scalper samples every 10 seconds and simply never sees most intra-minute
spikes, so its peak is lower, its trail arms lower, and it exits lower.

This re-runs the same rule with the same data under an observation model
the live system can actually achieve -- the trail may only arm on prices
we would have SAMPLED -- and reports the gap. Anything the backtest earns
from prices it could not have seen is not available in production.
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
HORIZON, TRAIL = 30, 0.30


def sim(b: pd.DataFrame, entry_px: float, *, perfect: bool) -> float:
    """perfect=True  -> trail arms on bar HIGHS (the backtest's assumption)
       perfect=False -> trail arms on bar CLOSES only (what polling sees)"""
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
            return c[j] / entry_px - 1 - COST
        peak = max(peak, hi[j] if perfect else c[j])
        stop = peak * (1 - TRAIL)
        # the exit itself still fills at a realistic price: a poll sees the
        # close, and a gap below the stop fills at the low
        if perfect:
            if lo[j] <= stop:
                return max(stop, lo[j]) / entry_px - 1 - COST
        else:
            if c[j] <= stop:
                return c[j] / entry_px - 1 - COST
    return DEAD_RECOVERY - 1 - COST


def sim_exit(b: pd.DataFrame, entry_px: float, style: str,
             *, perfect: bool) -> float:
    """Exit styles that differ in how much they depend on SEEING a peak.

    A trailing stop must observe the high to work; a timed exit and a
    fixed take-profit do not, so they are immune to the sampling gap that
    destroyed the trail's edge.
    """
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
    horizon = {"time5": 5, "time10": 10, "time15": 15, "time30": 30}.get(style, 30)
    for j in range(len(ts)):
        if ts[j] > last:
            return DEAD_RECOVERY - 1 - COST
        if (ts[j] - t0) / 60 > horizon:
            return c[j] / entry_px - 1 - COST
        obs = hi[j] if perfect else c[j]
        if style.startswith("tp"):
            mult = float(style[2:])
            if obs >= entry_px * mult:
                return mult - 1 - COST
        elif style == "trail":
            peak = max(peak, obs)
            stop = peak * (1 - TRAIL)
            if (lo[j] if perfect else c[j]) <= stop:
                return (max(stop, lo[j]) if perfect else c[j]) / entry_px \
                    - 1 - COST
    return DEAD_RECOVERY - 1 - COST


def main() -> int:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    bars = load_all(db)
    rows = []
    for p, b in bars.items():
        f = entry(b)
        if f is None or f["range"] < MIN_RANGE:
            continue
        if not (1.0 <= f["vol_ratio"] < 10.0):
            continue
        rows.append((sim(b, f["entry_px"], perfect=True),
                     sim(b, f["entry_px"], perfect=False)))
    a = np.array([r[0] for r in rows])
    b_ = np.array([r[1] for r in rows])
    print(f"filtered trades: {len(a)}\n")
    print(f"{'observation model':<34} {'mean':>9} {'CI':>21} {'median':>8} "
          f"{'2x rate':>8}")
    for lab, x in [("bar HIGHS (backtest assumption)", a),
                   ("polled CLOSES (achievable)", b_)]:
        lo, hi = boot(x)
        print(f"{lab:<34} {x.mean():>+8.1%} [{lo:>+7.1%},{hi:>+7.1%}] "
              f"{np.median(x):>+8.1%} {(x>=1).mean():>8.0%}")
    print("\nEXITS THAT DO NOT DEPEND ON SEEING A PEAK")
    print(f"{'exit':<22} {'perfect':>10} {'achievable':>12} {'gap':>9} "
          f"{'CI (achievable)':>22}")
    for style in ["trail", "time5", "time10", "time15", "time30",
                  "tp1.5", "tp2.0", "tp3.0"]:
        pa, pb = [], []
        for p, bb in bars.items():
            f = entry(bb)
            if f is None or f["range"] < MIN_RANGE:
                continue
            if not (1.0 <= f["vol_ratio"] < 10.0):
                continue
            pa.append(sim_exit(bb, f["entry_px"], style, perfect=True))
            pb.append(sim_exit(bb, f["entry_px"], style, perfect=False))
        pa, pb = np.array(pa), np.array(pb)
        lo, hi = boot(pb)
        print(f"{style:<22} {pa.mean():>+9.1%} {pb.mean():>+11.1%} "
              f"{pa.mean()-pb.mean():>+8.1%} [{lo:>+7.1%},{hi:>+7.1%}]")

    print("\nTRAIL WIDTH under achievable observation")
    print("(imperfect sampling makes a trail behave WIDER than its setting:")
    print(" the peak we arm against is lower than the true one, so we give")
    print(" back more. A tighter setting may compensate.)")
    print(f"{'trail':<10} {'perfect':>10} {'achievable':>12} "
          f"{'CI (achievable)':>22} {'median':>9}")
    global TRAIL
    best = None
    for tw in [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]:
        TRAIL = tw
        pa, pb = [], []
        for p, bb in bars.items():
            f = entry(bb)
            if f is None or f["range"] < MIN_RANGE:
                continue
            if not (1.0 <= f["vol_ratio"] < 10.0):
                continue
            pa.append(sim_exit(bb, f["entry_px"], "trail", perfect=True))
            pb.append(sim_exit(bb, f["entry_px"], "trail", perfect=False))
        pa, pb = np.array(pa), np.array(pb)
        lo, hi = boot(pb)
        print(f"{tw:>9.0%} {pa.mean():>+9.1%} {pb.mean():>+11.1%} "
              f"[{lo:>+7.1%},{hi:>+7.1%}] {np.median(pb):>+8.1%}")
        if best is None or pb.mean() > best[1]:
            best = (tw, pb.mean(), lo)
    TRAIL = 0.30
    if best:
        print(f"\nbest achievable trail: {best[0]:.0%} -> {best[1]:+.1%}/trade "
              f"(CI floor {best[2]:+.1%})")

    gap = a.mean() - b_.mean()
    print(f"\ncost of perfect eyesight: {gap:+.1%}/trade "
          f"({gap / max(abs(a.mean()), 1e-9):.0%} of the headline)")
    lo2, _ = boot(b_)
    print("verdict: " + ("edge SURVIVES realistic observation"
                        if lo2 > 0 else
                        "edge does NOT survive realistic observation — the "
                        "headline depends on prices we cannot see"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

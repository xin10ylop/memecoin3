#!/usr/bin/env python3
"""How big is this really, once the binding constraints are honoured?

A first pass compounded a fixed FRACTION of equity and produced 1e38x,
which is not a forecast but a bug report: it assumed you can always deploy
a percentage of a growing bankroll. You cannot. These pools hold a few
thousand dollars and a clip that is a meaningful share of the pool moves
the price against you before you are filled. The edge is capacity-bound in
DOLLARS, so P&L is closer to linear than exponential and the real question
is what the ceiling is.

It also resampled individual trades, which assumes independence. Memecoin
launches share a regime -- a dead Tuesday is dead for all of them at once
-- so days are resampled as BLOCKS, preserving that correlation.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "research")
from full_sample_test import MIN_RANGE, entry, load_all, simulate  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
MAX_CONCURRENT, HOLD_MIN = 6, 30
POOL_SHARE = 0.01      # clip as a share of pool reserve; 1% costs ~2% impact
N_PATHS, DAYS = 4000, 30


def main() -> int:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    bars = load_all(db)

    trades = []
    n_pools = 0
    for p, b in bars.items():
        n_pools += 1
        f = entry(b)
        if f is None or f["range"] < MIN_RANGE:
            continue
        if not (1.0 <= f["vol_ratio"] < 10.0):
            continue
        # first-2-minute volume is the honest proxy for how much this pool
        # can absorb: it is what actually traded, not what a reserve implies
        trades.append({"ret": simulate(b, f["entry_px"]),
                       "vol2": f["vol2"], "day": int(b.ts.iloc[0] // 86400)})
    df = pd.DataFrame(trades)
    r = df.ret.to_numpy()
    print(f"pools {n_pools} | qualifying {len(df)} ({len(df)/n_pools:.1%})")
    print(f"mean {r.mean():+.1%}  median {np.median(r):+.1%}  "
          f"win {(r>0).mean():.0%}  worst {r.min():+.0%}\n")

    # ---- the ceiling nobody can trade past ----
    clip = df.vol2 * POOL_SHARE
    print("CAPACITY -- what one trade can absorb:")
    for q in [0.25, 0.50, 0.75]:
        print(f"  {q:.0%} of qualifying pools take a clip <= "
              f"${clip.quantile(q):,.0f}")
    slots = MAX_CONCURRENT * (24 * 60 / HOLD_MIN)
    supply = 2.4 * 60 * 24 * (len(df) / n_pools)
    per_day = int(min(slots, supply))
    med_clip = float(clip.median())
    print(f"  binding: {per_day} trades/day "
          f"({'capacity' if slots < supply else 'launch supply'})")
    print(f"  median clip ${med_clip:,.0f} -> deployable at once "
          f"~${med_clip*MAX_CONCURRENT:,.0f}")

    # ---- day-block resampling: regimes are shared, trades are not iid ----
    by_day = [g.ret.to_numpy() for _, g in df.groupby("day") if len(g) >= 3]
    print(f"\nday blocks available: {len(by_day)} "
          f"(mean/day: {[f'{d.mean():+.0%}' for d in by_day]})")
    if len(by_day) < 2:
        print("  too few distinct days to resample regimes honestly.")
        return 0

    rng = np.random.default_rng(17)
    print(f"\nFIXED-DOLLAR sizing, {DAYS} days, {per_day} trades/day, "
          f"day-blocks resampled:")
    print(f"{'clip':>8} {'median P&L':>12} {'5th pct':>11} {'95th pct':>12} "
          f"{'p(loss)':>8} {'med maxDD':>10}")
    for clip_usd in [10, 25, 50, 100]:
        finals, dds = [], []
        for _ in range(N_PATHS):
            pnl, peak, dd = 0.0, 0.0, 0.0
            for _ in range(DAYS):
                blk = by_day[rng.integers(0, len(by_day))]
                draws = blk[rng.integers(0, len(blk), per_day)]
                pnl += clip_usd * draws.sum()
                peak = max(peak, pnl)
                dd = min(dd, pnl - peak)
            finals.append(pnl)
            dds.append(dd)
        f = np.array(finals)
        print(f"${clip_usd:>7,} {np.median(f):>11,.0f} "
              f"{np.quantile(f,0.05):>10,.0f} {np.quantile(f,0.95):>11,.0f} "
              f"{(f<0).mean():>7.1%} {np.median(dds):>9,.0f}")

    print("\nthe honest ceiling: clip size cannot exceed what the pool "
          "absorbs, so this scales with TRADE COUNT, not with bankroll.")
    print("More capital does NOT buy more edge here -- it buys the same "
          "edge until the pools stop absorbing it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

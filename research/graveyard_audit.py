#!/usr/bin/env python3
"""How much of the measured edge is an artifact of pools we never loaded?

Two filters silently shrink the evaluated sample:
  * n_bars >= 3, which drops pools that traded a minute or two and stopped
  * the join to pool metadata, which drops pools whose creation time is
    missing or unparseable
Both remove SHORT-LIVED pools, and a short-lived pool is not a neutral
omission — it is the exact outcome the entry rule is most likely to buy
into and lose everything on. A backtest that cannot see them reports the
expectancy of the tokens that survived long enough to be measured.

This asks the only question that matters: of the excluded pools, how many
would the LIVE RULE have actually bought (both of the first two minutes
traded, range >= 17.2%)? Those are real trades. It then re-states
expectancy with them included at a realistic recovery.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "research")
from harvest_grid import boot_ci, features_at, load_bars, run_exit  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
OBS, HORIZON, STYLE = 1, 30, "trail"
MIN_RANGE = 0.172
# what a position is actually worth when the pool stops trading a minute
# after entry: not zero (some exit into the last bids) but close to it
DEAD_RECOVERY, COST = 0.10, 0.016


def main() -> int:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")

    harvested = pd.read_sql_query(
        "SELECT pool_address, n_bars FROM retro_harvest", db)
    loaded = load_bars(db)
    print(f"harvested pools        : {len(harvested)}")
    print(f"evaluable in backtest  : {len(loaded)}")
    excluded = set(harvested.pool_address) - set(loaded)
    print(f"EXCLUDED               : {len(excluded)} "
          f"({len(excluded)/max(1,len(harvested)):.0%})\n")

    # Would the live rule have bought the excluded pools? Judge each on its
    # own first two traded minutes, exactly as the scalper does.
    would_buy, checked, no_data = 0, 0, 0
    for pool in excluded:
        b = pd.read_sql_query(
            "SELECT ts,h,l,c,vol_usd FROM ohlcv WHERE pool_address=? "
            "ORDER BY ts LIMIT 3", db, params=(pool,))
        if len(b) < 2:
            no_data += 1
            continue
        checked += 1
        first2 = b.iloc[:2]
        traded = int((first2.vol_usd.to_numpy(float) > 0).sum())
        p = first2.c.to_numpy(float)
        p = p[np.isfinite(p) & (p > 0)]
        if len(p) < 2 or traded < 2:
            continue
        rng = float(np.nanmax(p) / np.nanmin(p) - 1)
        if rng >= MIN_RANGE:
            would_buy += 1

    print(f"of the excluded, with >=2 bars to judge : {checked}")
    print(f"  the LIVE RULE would have BOUGHT      : {would_buy}")
    print(f"  (too little data to even judge)      : {no_data}")
    print("  these pools stop trading immediately after -> "
          f"treat each as {DEAD_RECOVERY - 1:.0%}\n")

    # measured expectancy on the evaluable sample, same cell as before
    feats = {p: f for p, bars in loaded.items()
             if (f := features_at(bars, OBS)) is not None}
    fdf = pd.DataFrame(feats).T
    thr_t = fdf.traded_min.quantile(0.66)
    sel = [p for p in feats if feats[p]["traded_min"] >= thr_t
           and feats[p]["range_first"] >= MIN_RANGE]
    rets = []
    for pool in sel:
        f = feats[pool]
        r, status = run_exit(loaded[pool], f["i"], f["t_obs"], f["entry"],
                             HORIZON, STYLE)
        if status != "unresolved":
            rets.append(r)
    a = np.array(rets)
    lo, hi = boot_ci(a)
    print(f"AS MEASURED (survivors only)  n={len(a):>4}  "
          f"{a.mean():+.1%}/trade  CI [{lo:+.1%},{hi:+.1%}]  "
          f"median {np.median(a):+.1%}  win {(a>0).mean():.0%}")

    # now add the buys we could not see, each a near-total loss
    dead = np.full(would_buy, DEAD_RECOVERY - 1 - COST)
    full = np.concatenate([a, dead])
    lo2, hi2 = boot_ci(full)
    print(f"WITH THE GRAVEYARD ADDED      n={len(full):>4}  "
          f"{full.mean():+.1%}/trade  CI [{lo2:+.1%},{hi2:+.1%}]  "
          f"median {np.median(full):+.1%}  win {(full>0).mean():.0%}")

    drop = a.mean() - full.mean()
    print(f"\ncost of the omission: {drop:+.1%}/trade "
          f"({would_buy} unseen losers on {len(a)} seen trades = "
          f"{would_buy/max(1,len(a)):.0%} more trades, all losses)")
    print("verdict: " + ("EDGE SURVIVES the correction" if lo2 > 0
                         else "EDGE DOES NOT SURVIVE — the CI floor crosses zero"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

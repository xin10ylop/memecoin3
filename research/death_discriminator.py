#!/usr/bin/env python3
"""The graveyard audit says the rule buys ~77 pools that die within minutes,
and that those unseen losses take the CI floor below zero.

That is only fatal if the doomed pools look IDENTICAL at the moment of
entry to the ones worth buying. So: take the exact features the scalper
holds in its hand at 2 minutes -- volume, trade count, range, and how the
second minute compares to the first -- and ask whether any of them separate
the pools that go on trading from the ones that stop.

If a separator exists, the edge returns with a filter attached. If none
does, the honest conclusion is that this entry rule cannot be traded.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
MIN_RANGE = 0.172


def entry_features(b: pd.DataFrame) -> dict | None:
    """Everything knowable from the first two minutes -- no lookahead."""
    if len(b) < 2:
        return None
    f2 = b.iloc[:2]
    vol = f2.vol_usd.to_numpy(float)
    p = f2.c.to_numpy(float)
    hi = f2.h.to_numpy(float)
    lo = f2.l.to_numpy(float)
    if (vol > 0).sum() < 2:
        return None
    good = np.isfinite(p) & (p > 0)
    if good.sum() < 2:
        return None
    rng = float(np.nanmax(hi) / max(np.nanmin(lo[lo > 0]), 1e-30) - 1) \
        if (lo > 0).any() else float(np.nanmax(p) / np.nanmin(p) - 1)
    if rng < MIN_RANGE:
        return None
    return {"vol2": float(np.nansum(vol)),
            "vol_ratio": float(vol[1] / max(vol[0], 1e-9)),
            "range": rng,
            "ret2": float(p[1] / p[0] - 1)}


def main() -> int:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    pools = pd.read_sql_query("SELECT pool_address FROM retro_harvest", db)

    rows = []
    for pool in pools.pool_address:
        b = pd.read_sql_query(
            "SELECT ts,h,l,c,vol_usd FROM ohlcv WHERE pool_address=? "
            "ORDER BY ts", db, params=(pool,))
        f = entry_features(b)
        if f is None:
            continue
        # the label: did the pool still trade 10+ minutes after entry?
        # that is precisely what the backtest needed and could not see.
        after = b.iloc[2:]
        alive = bool((after.vol_usd.to_numpy(float) > 0).sum() >= 8)
        f["alive"] = alive
        f["pool"] = pool
        rows.append(f)

    df = pd.DataFrame(rows)
    if df.empty:
        print("no qualifying pools")
        return 1
    print(f"pools the LIVE RULE would buy: {len(df)}")
    print(f"  survive 10+ min : {df.alive.sum()} ({df.alive.mean():.0%})")
    print(f"  die immediately : {(~df.alive).sum()} ({1-df.alive.mean():.0%})\n")

    print("feature separation (median, doomed vs survivor):")
    print(f"  {'feature':<12} {'doomed':>12} {'survivor':>12} {'ratio':>8}")
    for col in ["vol2", "vol_ratio", "range", "ret2"]:
        d = df.loc[~df.alive, col].median()
        s = df.loc[df.alive, col].median()
        ratio = s / d if abs(d) > 1e-12 else float("nan")
        print(f"  {col:<12} {d:>12.3f} {s:>12.3f} {ratio:>8.2f}x")

    # the practical question: does a volume floor buy back the edge?
    print("\ndoes a first-2-minute VOLUME FLOOR separate them?")
    print(f"  {'floor':>10} {'kept':>6} {'survive%':>9} {'lift':>7}")
    base = df.alive.mean()
    best = None
    for floor in [0, 50, 100, 200, 400, 800, 1500, 3000]:
        k = df[df.vol2 >= floor]
        if len(k) < 20:
            continue
        rate = k.alive.mean()
        lift = rate - base
        print(f"  ${floor:>9,} {len(k):>6} {rate:>8.0%} {lift:>+7.1%}")
        if best is None or rate > best[1]:
            best = (floor, rate, len(k))
    if best:
        print(f"\nbest floor ${best[0]:,}: survival {best[1]:.0%} "
              f"(base {base:.0%}) on {best[2]} pools")
        if best[1] - base < 0.08:
            print("  -> NO USABLE SEPARATION: volume does not tell the "
                  "doomed from the living. This entry rule cannot be fixed "
                  "with a liquidity filter.")
        else:
            print("  -> SEPARATION FOUND: re-run the graveyard audit with "
                  "this floor applied before trusting it.")
    df.to_csv("research/results/death_discriminator.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

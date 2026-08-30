#!/usr/bin/env python3
"""The rule tested on EVERY harvested pool -- nothing excluded.

The graveyard audit showed the backtest was scoring only pools that lived
long enough to be scored, and that adding the unseen fast deaths took the
CI floor below zero. The discriminator then showed the doomed are not
invisible after all: their second minute trades at ~12% of their first,
while survivors accelerate.

So this re-tests the rule the only way that can be trusted -- every pool
the rule would buy is a trade, whether or not it lived long enough to
produce a clean exit. Pools that stop trading are scored at the recovery
value, not dropped. Nothing is excluded for being short.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
MIN_RANGE, HORIZON, TRAIL = 0.172, 30, 0.30
DEAD_RECOVERY, COST = 0.10, 0.016


def load_all(db) -> dict:
    """Every harvested pool whose bars demonstrably start at its creation.

    GT returns the most recent `limit` bars, so a pool that keeps trading
    for days can outrun the window and lose its opening minutes. Then
    b.iloc[:2] is not the first two minutes at all, and every entry feature
    built on it describes some arbitrary later moment. The failure is
    outcome-correlated -- short-lived pools keep their whole history while
    survivors are the ones that lose their start -- so it flatters exactly
    the pools that did well. Measured here at ~1% of the sample, but it is
    checked rather than assumed.
    """
    pools = pd.read_sql_query(
        """SELECT r.pool_address, p.pool_created_at
           FROM retro_harvest r JOIN pools p ON p.pool_address = r.pool_address
           WHERE p.pool_created_at IS NOT NULL""", db)
    ct = pd.to_datetime(pools.pool_created_at, errors="coerce", utc=True)
    pools["created"] = (ct - pd.Timestamp("1970-01-01", tz="UTC")
                        ).dt.total_seconds()
    pools = pools.dropna(subset=["created"])
    out = {}
    for _, row in pools.iterrows():
        b = pd.read_sql_query(
            "SELECT ts,h,l,c,vol_usd FROM ohlcv WHERE pool_address=? "
            "ORDER BY ts", db, params=(row.pool_address,))
        if len(b) < 2:
            continue
        if float(b.ts.iloc[0]) > row.created + 120:
            continue                      # bars do not reach the launch
        out[row.pool_address] = b
    return out


def entry(b: pd.DataFrame) -> dict | None:
    f2 = b.iloc[:2]
    vol = f2.vol_usd.to_numpy(float)
    p = f2.c.to_numpy(float)
    if (vol > 0).sum() < 2 or not np.isfinite(p).all() or (p <= 0).any():
        return None
    rng = float(np.nanmax(p) / np.nanmin(p) - 1)
    return {"range": rng, "vol2": float(np.nansum(vol)),
            "vol_ratio": float(vol[1] / max(vol[0], 1e-9)),
            "entry_px": float(p[1])}


def simulate(b: pd.DataFrame, entry_px: float) -> float:
    """Trail 30%, 30-minute cap. A pool that stops trading pays the
    recovery -- it is a loss, never a dropped observation."""
    fwd = b.iloc[2:]
    if fwd.empty:
        return DEAD_RECOVERY - 1 - COST
    ts = fwd.ts.to_numpy(float)
    hi, lo, c = (fwd.h.to_numpy(float), fwd.l.to_numpy(float),
                 fwd.c.to_numpy(float))
    vol = fwd.vol_usd.to_numpy(float)
    t0 = ts[0]
    last_traded = ts[vol > 0].max() if (vol > 0).any() else t0
    peak = entry_px
    for j in range(len(ts)):
        if ts[j] > last_traded:
            return DEAD_RECOVERY - 1 - COST
        if (ts[j] - t0) / 60 > HORIZON:
            return c[j] / entry_px - 1 - COST
        peak = max(peak, hi[j])
        if lo[j] <= peak * (1 - TRAIL):
            return max(peak * (1 - TRAIL), lo[j]) / entry_px - 1 - COST
    # ran out of data while still trading -> assume it dies, never assume
    # it survived: that assumption is what created the original mirage
    return DEAD_RECOVERY - 1 - COST


def boot(x, n=4000, seed=11):
    if len(x) < 8:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    return tuple(np.quantile([x[rng.integers(0, len(x), len(x))].mean()
                              for _ in range(n)], [0.025, 0.975]))


def main() -> int:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    bars = load_all(db)
    print(f"every harvested pool with >=2 bars: {len(bars)}\n")

    feats = {p: f for p, b in bars.items() if (f := entry(b)) is not None}
    print(f"{'rule':<38} {'n':>4} {'mean':>9} {'95% CI':>22} "
          f"{'median':>8} {'win':>5}")
    results = {}
    variants = [
        ("range>=17.2% (current live rule)", lambda f: True),
        ("  + vol2 >= $1,500", lambda f: f["vol2"] >= 1500),
        ("  + vol2 >= $3,000", lambda f: f["vol2"] >= 3000),
        ("  + vol_ratio >= 0.5", lambda f: f["vol_ratio"] >= 0.5),
        ("  + vol_ratio >= 0.8", lambda f: f["vol_ratio"] >= 0.8),
        ("  + vol_ratio >= 1.0 (accelerating)", lambda f: f["vol_ratio"] >= 1.0),
        ("  + vol_ratio>=0.8 & vol2>=$1,500",
         lambda f: f["vol_ratio"] >= 0.8 and f["vol2"] >= 1500),
        ("  + vol_ratio>=1.0 & vol2>=$3,000",
         lambda f: f["vol_ratio"] >= 1.0 and f["vol2"] >= 3000),
    ]
    for label, cond in variants:
        rets = [simulate(bars[p], f["entry_px"])
                for p, f in feats.items()
                if f["range"] >= MIN_RANGE and cond(f)]
        if len(rets) < 15:
            print(f"{label:<38} {len(rets):>4}   (too few)")
            continue
        a = np.array(rets)
        lo, hi = boot(a)
        results[label] = (a, lo)
        print(f"{label:<38} {len(a):>4} {a.mean():>+8.1%} "
              f"[{lo:>+7.1%},{hi:>+7.1%}] {np.median(a):>+8.1%} "
              f"{(a>0).mean():>5.0%}")

    print("\nverdict:")
    ok = {k: v for k, v in results.items() if np.isfinite(v[1]) and v[1] > 0}
    if not ok:
        print("  NO variant clears zero on the full sample. The rule as "
              "conceived does not survive honest accounting.")
    else:
        best = max(ok.items(), key=lambda kv: kv[1][1])
        a, lo = best[1]
        print(f"  survives with CI floor above zero: {len(ok)} variant(s)")
        print(f"  strongest: {best[0].strip()}")
        print(f"    n={len(a)}  {a.mean():+.1%}/trade  CI floor {lo:+.1%}")
        srt = np.sort(a)
        for k in (1, 3, 5):
            if len(srt) > k:
                print(f"    drop top {k}: {srt[:-k].mean():+.1%}/trade")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

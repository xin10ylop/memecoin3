#!/usr/bin/env python3
"""Where does the signal leak? A full sweep of WHEN to look and HOW to exit.

We have a stable, replicated signal: early volatility + activity doubles
the 2x-rate. And we lose it in execution — winners round-trip before a
stop banks them. That is a harvesting problem, not an absence of edge,
and so far it has been attacked from exactly one angle: observe at 5
minutes, exit on stop/trail/TP over 60-240 minutes.

This sweeps the whole space:
  * observation age   — 1, 3, 5, 10, 15, 30 minutes
  * holding horizon   — 5, 15, 30, 60, 120 minutes
  * exit style        — pure timed, trailing, take-profit, and scale-out
Honest accounting throughout: real deaths take the recovery haircut,
pools still alive at the data edge are flagged unresolved and reported
separately, and every cell prints its median as well as its mean.

Looking for a PLATEAU of positive cells, not a single lucky spike.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
COST, DEAD_RECOVERY = 0.016, 0.10
OBS_AGES = [1, 3, 5, 10, 15, 30]
HORIZONS = [5, 15, 30, 60, 120]


def load_bars(db):
    pools = pd.read_sql_query("""
        SELECT r.pool_address, p.base_symbol, p.pool_created_at
        FROM retro_harvest r JOIN pools p ON p.pool_address = r.pool_address
        WHERE r.n_bars >= 3""", db)
    cts = pd.to_datetime(pools.pool_created_at, errors="coerce", utc=True)
    pools["created_ts"] = (cts - pd.Timestamp("1970-01-01", tz="UTC")
                           ).dt.total_seconds()
    pools = pools.dropna(subset=["created_ts"])
    out = {}
    for _, p in pools.iterrows():
        b = pd.read_sql_query(
            "SELECT ts,h,l,c,vol_usd FROM ohlcv WHERE pool_address=? ORDER BY ts",
            db, params=(p.pool_address,))
        if len(b) >= 3:
            out[p.pool_address] = (float(p.created_ts), b.ts.to_numpy(),
                                   b.h.to_numpy(float), b.l.to_numpy(float),
                                   b.c.to_numpy(float),
                                   b.vol_usd.to_numpy(float))
    return out


def features_at(bars, obs_min):
    """Tail-filter features known at the observation moment."""
    birth, ts, hi, lo, c, vol = bars
    t_obs = birth + obs_min * 60
    i = int(np.searchsorted(ts, t_obs))
    if i < 2 or i >= len(ts) - 1:
        return None
    pre_p, pre_v = c[:i], vol[:i]
    if np.nanmin(pre_p) <= 0 or not np.isfinite(c[i]) or c[i] <= 0:
        return None
    return {"i": i, "t_obs": t_obs, "entry": c[i],
            "traded_min": int((pre_v > 0).sum()),
            "range_first": float(np.nanmax(pre_p) / np.nanmin(pre_p) - 1)}


def run_exit(bars, i, t_obs, entry, horizon, style):
    """Returns (net_return, status). Styles: timed, trail, tp_trail, scale."""
    birth, ts, hi, lo, c, vol = bars
    lt = ts[vol > 0].max() if (vol > 0).any() else ts[0]
    peak = entry
    banked, frac_left = 0.0, 1.0
    for j in range(i + 1, len(ts)):
        if ts[j] > lt:
            return banked + frac_left * (DEAD_RECOVERY - 1) - COST, "dead"
        if (ts[j] - t_obs) / 60 > horizon:
            return banked + frac_left * (c[j] / entry - 1) - COST, "rule"
        peak = max(peak, hi[j])
        if style == "trail" and lo[j] <= peak * 0.7:
            px = max(peak * 0.7, lo[j])
            return banked + frac_left * (px / entry - 1) - COST, "rule"
        if style == "tp_trail":
            if hi[j] >= entry * 2:
                return banked + frac_left * 1.0 - COST, "rule"
            if lo[j] <= peak * 0.75:
                px = max(peak * 0.75, lo[j])
                return banked + frac_left * (px / entry - 1) - COST, "rule"
        if style == "scale":
            # bank half at +50%, ride the rest on a wide trail
            if frac_left == 1.0 and hi[j] >= entry * 1.5:
                banked += 0.5 * 0.5
                frac_left = 0.5
            if frac_left < 1.0 and lo[j] <= peak * 0.6:
                px = max(peak * 0.6, lo[j])
                return banked + frac_left * (px / entry - 1) - COST, "rule"
    if ts[-1] - lt < 300:
        return banked + frac_left * (c[-1] / entry - 1) - COST, "unresolved"
    return banked + frac_left * (DEAD_RECOVERY - 1) - COST, "dead"


def boot_ci(x, n=3000, seed=4):
    if len(x) < 8:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    b = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(n)]
    return np.quantile(b, [0.025, 0.975])


def main() -> int:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    allbars = load_bars(db)
    print(f"unbiased sample: {len(allbars)} pools\n")

    rows = []
    for obs in OBS_AGES:
        feats = {}
        for pool, bars in allbars.items():
            f = features_at(bars, obs)
            if f:
                feats[pool] = f
        if len(feats) < 40:
            continue
        fdf = pd.DataFrame(feats).T
        thr_t = fdf.traded_min.quantile(0.66)
        thr_r = fdf.range_first.quantile(0.50)
        sel = [p for p in feats
               if feats[p]["traded_min"] >= thr_t
               and feats[p]["range_first"] >= thr_r]
        for horizon in HORIZONS:
            for style in ["timed", "trail", "tp_trail", "scale"]:
                res, unres = [], 0
                for pool in sel:
                    f = feats[pool]
                    out = run_exit(allbars[pool], f["i"], f["t_obs"],
                                   f["entry"], horizon, style)
                    if out is None:
                        continue
                    v, st = out
                    if st == "unresolved":
                        unres += 1
                    res.append(v)
                if len(res) < 15:
                    continue
                a = np.array(res)
                lo, hi = boot_ci(a)
                rows.append({"obs_min": obs, "horizon": horizon,
                             "style": style, "n": len(a), "unres": unres,
                             "mean": a.mean(), "median": np.median(a),
                             "win": (a > 0).mean(), "ci_lo": lo, "ci_hi": hi})
    r = pd.DataFrame(rows)
    if r.empty:
        print("insufficient data")
        return 0
    r = r.sort_values("ci_lo", ascending=False)
    print("=== TOP 15 CELLS BY CI FLOOR (the honest ranking) ===")
    print(r.head(15).to_string(index=False,
                               float_format=lambda v: f"{v:+.3f}"))
    pos = r[r.ci_lo > 0]
    print(f"\ncells with CI floor above zero: {len(pos)} of {len(r)}")
    if len(pos):
        print(pos.to_string(index=False, float_format=lambda v: f"{v:+.3f}"))
        print("\n=== PLATEAU CHECK — are the winners neighbours? ===")
        for _, w in pos.head(5).iterrows():
            nb = r[(r.obs_min == w.obs_min) & (r.style == w.style)]
            print(f"  obs{w.obs_min:.0f}m {w.style}: " + ", ".join(
                f"h{int(x.horizon)}={x.mean:+.0%}" for _, x in nb.iterrows()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Does memecoin activity predict SOL? — the low-cost front.

Every memecoin strategy died on the same wall: a ~2% round-trip toll on a
zero-drift asset. SOL/USDC costs ~5bps round trip, is deep enough for any
size we will ever trade, and cannot rug. So an edge 40x too small to
survive in memecoins is tradeable in SOL.

We hold something nobody else does: minute-level activity across tens of
thousands of memecoin launches. Plausible causal channel — buying
memecoins REQUIRES SOL, so a launch/volume frenzy creates mechanical SOL
demand. If that flow leads SOL even slightly, it is exploitable.

Statistical care (this is ONE time series, not a panel):
  * overlapping forward returns are autocorrelated -> moving-block
    bootstrap for CIs, never iid resampling
  * SOL's own momentum is the benchmark any meme signal must beat
  * strict time-split out-of-sample, and costs netted at 5bps round trip

Usage: python3 research/macro_signal.py [db]
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
BAR_MIN = 5                     # aggregate to 5-minute bars
HORIZONS = [3, 12, 48]          # in bars: 15m, 1h, 4h
COST_RT = 0.0005                # 5bps round trip on deep SOL/USDC
BLOCK = 24                      # 2h blocks for the moving-block bootstrap


def block_bootstrap_mean(x: np.ndarray, n_boot: int = 3000,
                         block: int = BLOCK, seed: int = 11):
    """CI for the mean of an autocorrelated series."""
    n = len(x)
    if n < block * 3:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    nblocks = int(np.ceil(n / block))
    starts = rng.integers(0, n - block, size=(n_boot, nblocks))
    means = np.empty(n_boot)
    for b in range(n_boot):
        idx = (starts[b][:, None] + np.arange(block)[None, :]).ravel()[:n]
        means[b] = x[idx].mean()
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def build() -> pd.DataFrame:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    sol = pd.read_sql_query(
        "SELECT ts, c, vol_usd FROM sol_ohlcv ORDER BY ts", db)
    snaps = pd.read_sql_query(
        "SELECT ts, pool_address, price_change_m5, vol_m5, reserve_usd "
        "FROM snapshots WHERE reserve_usd >= 8000", db)
    pools = pd.read_sql_query(
        "SELECT pool_address, pool_created_at FROM pools", db)
    db.close()

    # memecoin activity aggregated onto the same 5-minute grid
    snaps["bar"] = (snaps.ts // (BAR_MIN * 60)) * BAR_MIN * 60
    agg = snaps.groupby("bar").agg(
        meme_vol=("vol_m5", "sum"),
        n_active=("pool_address", "nunique"),
        breadth=("price_change_m5", lambda s: (s > 0).mean()),
        med_mom=("price_change_m5", "median"),
    ).reset_index()

    # launch rate from creation timestamps
    pools["cts"] = pd.to_datetime(pools.pool_created_at, errors="coerce",
                                  utc=True)
    pools = pools.dropna(subset=["cts"])
    epoch = (pools.cts - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()
    launch = (epoch // (BAR_MIN * 60) * (BAR_MIN * 60)).value_counts()
    agg["launches"] = agg.bar.map(launch).fillna(0)

    sol["bar"] = (sol.ts // (BAR_MIN * 60)) * BAR_MIN * 60
    solbar = sol.groupby("bar").agg(sol_c=("c", "last"),
                                    sol_vol=("vol_usd", "sum")).reset_index()

    df = solbar.merge(agg, on="bar", how="inner").sort_values("bar")
    df["sol_ret"] = df.sol_c.pct_change()
    for h in HORIZONS:
        df[f"fwd_{h}"] = df.sol_c.shift(-h) / df.sol_c - 1.0
    # causal signal transforms (z-scores on trailing windows only)
    for col in ["meme_vol", "launches", "breadth", "med_mom", "n_active"]:
        m = df[col].rolling(72, min_periods=24).mean()
        s = df[col].rolling(72, min_periods=24).std()
        df[f"z_{col}"] = (df[col] - m) / s.replace(0, np.nan)
    df["z_sol_mom"] = (df.sol_ret.rolling(12, min_periods=6).mean()
                       / df.sol_ret.rolling(72, min_periods=24).std())
    return df.dropna(subset=["sol_ret"])



def reversal_study(df: pd.DataFrame) -> None:
    """Drift-controlled test of the reversal hint.

    A negative IC in a falling market can be pure drift: high-momentum bars
    are simply local tops in a downtrend. The honest test is the SPREAD
    between the bottom and top terciles of the signal — drift affects both
    equally, so it cancels. That spread is what a long/short or a
    timing rule could actually harvest.
    """
    print("\n=== DRIFT-CONTROLLED REVERSAL TEST (bottom minus top tercile) ===")
    rows = []
    for sig in ["z_sol_mom", "z_med_mom", "z_breadth"]:
        for h in HORIZONS:
            d = df[[sig, f"fwd_{h}"]].dropna()
            if len(d) < 200:
                continue
            x, y = d[sig].to_numpy(), d[f"fwd_{h}"].to_numpy()
            lo_t, hi_t = np.quantile(x, 1 / 3), np.quantile(x, 2 / 3)
            bot, top = y[x <= lo_t], y[x >= hi_t]
            # bootstrap the SPREAD, preserving autocorrelation in each leg
            lo1, hi1 = block_bootstrap_mean(bot)
            lo2, hi2 = block_bootstrap_mean(top)
            spread = bot.mean() - top.mean()
            rows.append({"signal": sig, "h_min": h * BAR_MIN,
                         "bottom_mean": bot.mean(), "top_mean": top.mean(),
                         "spread": spread,
                         "bot_ci": f"[{lo1:+.4f},{hi1:+.4f}]",
                         "top_ci": f"[{lo2:+.4f},{hi2:+.4f}]",
                         "spread_net_2way": spread - 2 * COST_RT,
                         "n_bot": len(bot), "n_top": len(top)})
    r = pd.DataFrame(rows)
    print(r.to_string(index=False, float_format=lambda v: f"{v:+.5f}"))

    # honest OOS on the strongest reversal cell
    print("\n--- reversal OOS (60/40 time split, long bottom tercile only) ---")
    cut = int(len(df) * 0.6)
    tr, te = df.iloc[:cut], df.iloc[cut:]
    for h in HORIZONS:
        sig = "z_sol_mom"
        d_tr = tr[[sig, f"fwd_{h}"]].dropna()
        d_te = te[[sig, f"fwd_{h}"]].dropna()
        if len(d_tr) < 100 or len(d_te) < 80:
            continue
        thr = d_tr[sig].quantile(1 / 3)
        sel = d_te[d_te[sig] <= thr][f"fwd_{h}"].to_numpy()
        if len(sel) < 50:
            continue
        lo, hi = block_bootstrap_mean(sel)
        base = d_te[f"fwd_{h}"].to_numpy().mean()
        print(f"h={h * BAR_MIN:3d}m  OOS long-after-drop mean {sel.mean():+.5f} "
              f"net {sel.mean() - COST_RT:+.5f} CI [{lo:+.5f},{hi:+.5f}] "
              f"vs OOS base {base:+.5f}  n={len(sel)}")



def main() -> int:
    df = build()
    print(f"aligned bars: {len(df)} x {BAR_MIN}min "
          f"({len(df) * BAR_MIN / 60:.1f}h of overlap)\n")
    if len(df) < 200:
        print("insufficient overlap between SOL and memecoin data")
        return 0

    signals = ["z_meme_vol", "z_launches", "z_breadth", "z_med_mom",
               "z_n_active", "z_sol_mom"]
    rows = []
    for sig in signals:
        for h in HORIZONS:
            d = df[[sig, f"fwd_{h}"]].dropna()
            if len(d) < 200:
                continue
            x, y = d[sig].to_numpy(), d[f"fwd_{h}"].to_numpy()
            ic = float(pd.Series(x).corr(pd.Series(y), method="spearman"))
            # long-only rule: hold SOL when the signal is in its top tercile
            hi = np.quantile(x, 2 / 3)
            sel = y[x >= hi]
            lo95, hi95 = block_bootstrap_mean(sel) if len(sel) > 100 else (np.nan,) * 2
            rows.append({"signal": sig, "h_min": h * BAR_MIN, "n": len(d),
                         "spearman_ic": ic, "n_signal": len(sel),
                         "mean_when_on": sel.mean() if len(sel) else np.nan,
                         "ci_lo": lo95, "ci_hi": hi95,
                         "net_when_on": (sel.mean() - COST_RT) if len(sel) else np.nan,
                         "base_rate": y.mean()})
    res = pd.DataFrame(rows)
    print(res.to_string(index=False, float_format=lambda v: f"{v:+.5f}"))

    # strict time-split OOS on the best in-sample cell
    cut = int(len(df) * 0.6)
    tr, te = df.iloc[:cut], df.iloc[cut:]
    best = res.loc[res.ci_lo.idxmax()] if res.ci_lo.notna().any() else None
    print("\n--- out-of-sample check (60/40 time split) ---")
    if best is not None:
        sig, h = best.signal, int(best.h_min // BAR_MIN)
        thr = tr[sig].quantile(2 / 3)
        d = te[[sig, f"fwd_{h}"]].dropna()
        sel = d[d[sig] >= thr][f"fwd_{h}"].to_numpy()
        if len(sel) > 50:
            lo, hi = block_bootstrap_mean(sel)
            print(f"{sig} @ {best.h_min:.0f}m: IS ci_lo {best.ci_lo:+.5f} -> "
                  f"OOS mean {sel.mean():+.5f} net {sel.mean() - COST_RT:+.5f} "
                  f"CI [{lo:+.5f}, {hi:+.5f}] on {len(sel)} bars")
            print("VERDICT:", "OOS edge clears costs — investigate further"
                  if (lo > COST_RT) else "no OOS edge above costs")
        else:
            print("insufficient OOS observations")
    else:
        print("no cell produced a usable CI")
    reversal_study(df)
    return 0



if __name__ == "__main__":
    raise SystemExit(main())

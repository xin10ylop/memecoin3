#!/usr/bin/env python3
"""Can we predict the TAIL — not the average?

The average launch loses money and a death-filter would at best convert
that into a grind. The only treasure-sized outcome in this market is the
right tail: in the unbiased sample ~15% of launches double and a few run
4-8x. Small bets across many launches compound violently IF the tail is
even slightly predictable in advance.

So this asks two SEPARATE questions on the unbiased retro-harvested
sample, using only information available at the observation moment:

  DEATH:  which launches stop trading within the hour?
  TAIL:   which launches go on to run >=2x / >=5x from the observation
          price?

They are treated separately on purpose — the features that avoid rugs and
the features that catch monsters need not be the same, and only the second
one is worth chasing.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
OBS_MIN = 5          # decide at 5 minutes of pool age
FWD_MIN = 120        # judge the outcome over the next 2 hours


def build() -> pd.DataFrame:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    pools = pd.read_sql_query("""
        SELECT r.pool_address, p.base_symbol, p.dex_id, p.pool_created_at
        FROM retro_harvest r JOIN pools p ON p.pool_address = r.pool_address
        WHERE r.n_bars >= 3""", db)
    cts = pd.to_datetime(pools.pool_created_at, errors="coerce", utc=True)
    pools["created_ts"] = (cts - pd.Timestamp("1970-01-01", tz="UTC")
                           ).dt.total_seconds()
    pools = pools.dropna(subset=["created_ts"])

    rows = []
    for _, p in pools.iterrows():
        b = pd.read_sql_query(
            "SELECT ts, o, h, l, c, vol_usd FROM ohlcv WHERE pool_address=? "
            "ORDER BY ts", db, params=(p.pool_address,))
        if len(b) < 3:
            continue
        ts = b.ts.to_numpy()
        px = b.c.to_numpy(dtype=float)
        hi = b.h.to_numpy(dtype=float)
        vol = b.vol_usd.to_numpy(dtype=float)
        birth = float(p.created_ts)
        t_obs = birth + OBS_MIN * 60
        i = int(np.searchsorted(ts, t_obs))
        if i < 2 or i >= len(ts) - 1:
            continue
        pre_v = vol[:i]
        pre_p = px[:i]
        p_obs = px[i]
        if not np.isfinite(p_obs) or p_obs <= 0:
            continue
        # --- features known AT the observation moment only ---
        traded = int((pre_v > 0).sum())
        feats = {
            "vol_first": float(np.nansum(pre_v)),
            "traded_min": traded,
            "trade_density": traded / max(i, 1),
            "ret_first": float(p_obs / pre_p[0] - 1) if pre_p[0] > 0 else np.nan,
            "range_first": float((np.nanmax(pre_p) / np.nanmin(pre_p) - 1)
                                 if np.nanmin(pre_p) > 0 else np.nan),
            "dd_first": float(p_obs / np.nanmax(pre_p) - 1)
                        if np.nanmax(pre_p) > 0 else np.nan,
            "vol_per_min": float(np.nansum(pre_v)) / max(OBS_MIN, 1),
        }
        # --- outcomes AFTER the observation ---
        j = int(np.searchsorted(ts, t_obs + FWD_MIN * 60))
        seg_hi = hi[i:j] if j > i else hi[i:]
        seg_v = vol[i:j] if j > i else vol[i:]
        peak = float(np.nanmax(seg_hi) / p_obs) if len(seg_hi) else 1.0
        last_traded = ts[vol > 0].max() if (vol > 0).any() else ts[0]
        died_1h = int(last_traded < t_obs + 3600)
        rows.append({"pool": p.pool_address, "symbol": p.base_symbol,
                     "t_obs": t_obs,
                     **feats, "peak_fwd": peak, "died_1h": died_1h,
                     "x2": int(peak >= 2.0), "x5": int(peak >= 5.0),
                     "fwd_vol": float(np.nansum(seg_v))})
    return pd.DataFrame(rows)


def lift_table(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """For each feature, does its top tercile concentrate the target?"""
    base = df[target].mean()
    out = []
    for f in ["vol_first", "traded_min", "trade_density", "ret_first",
              "range_first", "dd_first", "vol_per_min"]:
        d = df[[f, target]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(d) < 40 or d[f].nunique() < 3:
            continue
        hi_t = d[f].quantile(2 / 3)
        lo_t = d[f].quantile(1 / 3)
        top, bot = d[d[f] >= hi_t], d[d[f] <= lo_t]
        # bootstrap the difference in rates
        rng = np.random.default_rng(3)
        diffs = []
        for _ in range(3000):
            a = top[target].to_numpy()
            b = bot[target].to_numpy()
            diffs.append(a[rng.integers(0, len(a), len(a))].mean()
                         - b[rng.integers(0, len(b), len(b))].mean())
        lo95, hi95 = np.quantile(diffs, [0.025, 0.975])
        out.append({"feature": f, "base_rate": base,
                    "top_tercile": top[target].mean(),
                    "bot_tercile": bot[target].mean(),
                    "lift": top[target].mean() - bot[target].mean(),
                    "ci_lo": lo95, "ci_hi": hi95,
                    "signif": "YES" if (lo95 > 0 or hi95 < 0) else ""})
    return pd.DataFrame(out).sort_values("lift", ascending=False)


def trade_sim(df: pd.DataFrame) -> None:
    """Doubling rate is not profit. Simulate the actual trade.

    A filter that doubles the 2x-rate is worthless if those coins round-trip
    before you can sell, or if the ones that fail cannot be exited at all.
    This prices a real rule on the filtered set: buy at the observation
    moment, exit on a take-profit / trailing / time rule, and treat
    positions in pools that stop trading as unexitable at a punitive
    recovery — the same accounting that killed every earlier strategy.
    """
    import sqlite3
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    COST = 0.016
    DEAD_RECOVERY = 0.10

    def simulate(pool, t_obs, tp, trail, max_hold):
        b = pd.read_sql_query(
            "SELECT ts, h, l, c, vol_usd FROM ohlcv WHERE pool_address=? "
            "ORDER BY ts", db, params=(pool,))
        if len(b) < 3:
            return None
        ts = b.ts.to_numpy(); hi = b.h.to_numpy(dtype=float)
        lo = b.l.to_numpy(dtype=float); c = b.c.to_numpy(dtype=float)
        vol = b.vol_usd.to_numpy(dtype=float)
        i = int(np.searchsorted(ts, t_obs))
        if i >= len(ts) - 1:
            return None
        entry = c[i]
        if not np.isfinite(entry) or entry <= 0:
            return None
        last_traded = ts[vol > 0].max() if (vol > 0).any() else ts[0]
        peak = entry
        for j in range(i + 1, len(ts)):
            if (ts[j] - t_obs) / 60 > max_hold:
                return c[j] / entry - 1 - COST
            if ts[j] > last_traded:                 # pool died holding
                return DEAD_RECOVERY - 1 - COST
            peak = max(peak, hi[j])
            if hi[j] >= entry * (1 + tp):
                return tp - COST
            if lo[j] <= peak * (1 - trail):
                return max(peak * (1 - trail), lo[j]) / entry - 1 - COST
        if last_traded <= ts[-1] and (ts[-1] - last_traded) < 300:
            return c[-1] / entry - 1 - COST
        return DEAD_RECOVERY - 1 - COST

    d = df.replace([np.inf, -np.inf], np.nan).dropna(
        subset=["traded_min", "range_first"])
    filt = d[(d.traded_min >= d.traded_min.quantile(0.66)) &
             (d.range_first >= d.range_first.quantile(0.5))]
    print(f"\n=== DOES THE FILTER MAKE MONEY? (n={len(filt)} filtered, "
          f"{len(d)} all) ===")
    print(f"{'rule':<28} {'filtered net':>13} {'all net':>10} {'win%':>6} {'n':>5}")
    for tp, trail, hold in [(1.0, 0.30, 120), (2.0, 0.35, 120),
                            (0.5, 0.25, 60), (4.0, 0.50, 240),
                            (99.0, 0.30, 120)]:
        res_f, res_a = [], []
        for _, r in filt.iterrows():
            v = simulate(r.pool, r.t_obs, tp, trail, hold)
            if v is not None:
                res_f.append(v)
        for _, r in d.iterrows():
            v = simulate(r.pool, r.t_obs, tp, trail, hold)
            if v is not None:
                res_a.append(v)
        if not res_f:
            continue
        rf, ra = np.array(res_f), np.array(res_a)
        rng = np.random.default_rng(7)
        boot = [rf[rng.integers(0, len(rf), len(rf))].mean() for _ in range(3000)]
        lo95, hi95 = np.quantile(boot, [0.025, 0.975])
        name = (f"tp{tp:g} trail{trail:g} hold{hold}"
                if tp < 99 else f"trail{trail:g} only hold{hold}")
        print(f"{name:<28} {rf.mean():>+12.1%} {ra.mean():>+9.1%} "
              f"{(rf > 0).mean():>5.0%} {len(rf):>5}   CI [{lo95:+.1%},{hi95:+.1%}]")



def main() -> int:
    df = build()
    print(f"unbiased sample: {len(df)} launches observed at {OBS_MIN}m of age\n")
    if len(df) < 60:
        print("sample still too small — let the harvest run")
        return 0
    print(f"base rates: died within 1h {df.died_1h.mean():.1%} | "
          f">=2x in {FWD_MIN}m {df.x2.mean():.1%} | >=5x {df.x5.mean():.1%} | "
          f"median forward peak {df.peak_fwd.median():.2f}x")

    for target, label in [("died_1h", "DEATH (stops trading within 1h)"),
                          ("x2", "TAIL >=2x"), ("x5", "TAIL >=5x")]:
        print(f"\n=== {label} — feature lift (top vs bottom tercile) ===")
        t = lift_table(df, target)
        if t.empty:
            print("  insufficient data")
            continue
        print(t.to_string(index=False, float_format=lambda v: f"{v:+.3f}"))

    print("\n=== THE TREASURE TEST: best combined filter for the tail ===")
    # simple 2-feature screen, chosen by the lift table above being honest
    # about it being in-sample: this is a feasibility probe, not a strategy
    for fa, fb in [("vol_per_min", "trade_density"), ("vol_first", "ret_first"),
                   ("traded_min", "range_first")]:
        d = df.replace([np.inf, -np.inf], np.nan).dropna(subset=[fa, fb])
        if len(d) < 60:
            continue
        sel = d[(d[fa] >= d[fa].quantile(0.66)) & (d[fb] >= d[fb].quantile(0.5))]
        if len(sel) < 10:
            continue
        print(f"  {fa} high AND {fb} high: n={len(sel):3d} | "
              f"death {sel.died_1h.mean():.0%} (base {d.died_1h.mean():.0%}) | "
              f">=2x {sel.x2.mean():.0%} (base {d.x2.mean():.0%}) | "
              f">=5x {sel.x5.mean():.0%} (base {d.x5.mean():.0%}) | "
              f"median peak {sel.peak_fwd.median():.2f}x")
    trade_sim(df)
    return 0



if __name__ == "__main__":
    raise SystemExit(main())

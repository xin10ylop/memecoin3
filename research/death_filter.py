#!/usr/bin/env python3
"""Can on-chain data predict death BEFORE entry — and does it pay?

The tail filter (early range + activity) doubles the 2x-rate but loses to
a 32% death rate: each unexitable position costs ~90%, roughly -29pp of
expectancy. That single term is what stands between a +17.8% point
estimate and a result that clears zero.

So: join pre-entry on-chain features (mint/freeze authority, Token-2022
extension count, holder concentration excluding the AMM vault, supply) to
realised fate on the unbiased sample, and then re-price the actual trade
with the surviving filters stacked on the tail filter.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
OBS_MIN, FWD_MIN = 5, 120
COST, DEAD_RECOVERY = 0.016, 0.10


def load() -> pd.DataFrame:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    meta = pd.read_sql_query("""
        SELECT r.pool_address, p.base_symbol, p.base_token_address AS mint,
               p.pool_created_at, s.program, s.mint_auth, s.freeze_auth,
               s.n_ext, s.supply, s.top1_frac, s.ex_vault_top10_frac
        FROM retro_harvest r
        JOIN pools p ON p.pool_address = r.pool_address
        LEFT JOIN token_safety s ON s.mint = p.base_token_address
        WHERE r.n_bars >= 3""", db)
    cts = pd.to_datetime(meta.pool_created_at, errors="coerce", utc=True)
    meta["created_ts"] = (cts - pd.Timestamp("1970-01-01", tz="UTC")
                          ).dt.total_seconds()
    meta = meta.dropna(subset=["created_ts"])

    rows = []
    for _, p in meta.iterrows():
        b = pd.read_sql_query(
            "SELECT ts,h,l,c,vol_usd FROM ohlcv WHERE pool_address=? ORDER BY ts",
            db, params=(p.pool_address,))
        if len(b) < 3:
            continue
        ts = b.ts.to_numpy(); hi = b.h.to_numpy(float)
        lo = b.l.to_numpy(float); c = b.c.to_numpy(float)
        vol = b.vol_usd.to_numpy(float)
        t_obs = float(p.created_ts) + OBS_MIN * 60
        i = int(np.searchsorted(ts, t_obs))
        if i < 2 or i >= len(ts) - 1:
            continue
        entry = c[i]
        if not np.isfinite(entry) or entry <= 0:
            continue
        pre_p, pre_v = c[:i], vol[:i]
        last_traded = ts[vol > 0].max() if (vol > 0).any() else ts[0]
        j = int(np.searchsorted(ts, t_obs + FWD_MIN * 60))
        seg_hi = hi[i:j] if j > i else hi[i:]
        rows.append({
            "pool": p.pool_address, "symbol": p.base_symbol, "t_obs": t_obs,
            "traded_min": int((pre_v > 0).sum()),
            "range_first": float(np.nanmax(pre_p) / np.nanmin(pre_p) - 1)
                           if np.nanmin(pre_p) > 0 else np.nan,
            "program": p.program, "mint_auth": p.mint_auth,
            "freeze_auth": p.freeze_auth, "n_ext": p.n_ext,
            "top1": p.top1_frac, "conc": p.ex_vault_top10_frac,
            "died_1h": int(last_traded < t_obs + 3600),
            "peak_fwd": float(np.nanmax(seg_hi) / entry) if len(seg_hi) else 1.0,
        })
    return pd.DataFrame(rows)


def rate_ci(x, n_boot=4000, seed=9):
    if len(x) == 0:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    b = [x[rng.integers(0, len(x), len(x))].mean() for _ in range(n_boot)]
    return np.quantile(b, [0.025, 0.975])


def simulate(db, pool, t_obs, tp, trail, hold):
    b = pd.read_sql_query(
        "SELECT ts,h,l,c,vol_usd FROM ohlcv WHERE pool_address=? ORDER BY ts",
        db, params=(pool,))
    if len(b) < 3:
        return None
    ts = b.ts.to_numpy(); hi = b.h.to_numpy(float)
    lo = b.l.to_numpy(float); c = b.c.to_numpy(float)
    vol = b.vol_usd.to_numpy(float)
    i = int(np.searchsorted(ts, t_obs))
    if i >= len(ts) - 1:
        return None
    entry = c[i]
    if not np.isfinite(entry) or entry <= 0:
        return None
    lt = ts[vol > 0].max() if (vol > 0).any() else ts[0]
    peak = entry
    for j in range(i + 1, len(ts)):
        if (ts[j] - t_obs) / 60 > hold:
            return c[j] / entry - 1 - COST, "rule"
        if ts[j] > lt:                       # pool stopped trading: real death
            return DEAD_RECOVERY - 1 - COST, "dead"
        peak = max(peak, hi[j])
        if tp < 90 and hi[j] >= entry * (1 + tp):
            return tp - COST, "rule"
        if lo[j] <= peak * (1 - trail):
            return max(peak * (1 - trail), lo[j]) / entry - 1 - COST, "rule"
    # Data ran out. Distinguish a pool that DIED from one still trading when
    # our window ended — charging a 90% haircut to a live pool is censoring
    # dressed up as a loss, and flips the sign of the whole result.
    if ts[-1] - lt < 300:
        return c[-1] / entry - 1 - COST, "unresolved_alive"
    return DEAD_RECOVERY - 1 - COST, "dead"


def main() -> int:
    df = load()
    have = df.dropna(subset=["conc"])
    print(f"sample: {len(df)} observations, {len(have)} with on-chain safety data")
    print(f"base death rate {df.died_1h.mean():.1%}\n")

    print("=== 1. DOES ON-CHAIN DATA PREDICT DEATH? ===")
    for name, mask in [
        ("mint authority live", have.mint_auth == 1),
        ("token-2022 program", have.program == "spl-token-2022"),
        ("extensions > 2", have.n_ext > 2),
        ("top1 holder > 20%", have.top1 > 0.20),
        ("conc(ex-vault top10) > 15%", have.conc > 0.15),
        ("conc < 5%", have.conc < 0.05),
    ]:
        sub, rest = have[mask], have[~mask]
        if len(sub) < 15:
            print(f"  {name:30s} n={len(sub):3d}  (too few)")
            continue
        lo, hi = rate_ci(sub.died_1h.to_numpy())
        print(f"  {name:30s} n={len(sub):3d} death {sub.died_1h.mean():.0%} "
              f"CI[{lo:.0%},{hi:.0%}] vs rest {rest.died_1h.mean():.0%}")

    print("\n=== 2. CONCENTRATION TERCILES (the most promising axis) ===")
    h = have.dropna(subset=["conc"]).copy()
    h["bucket"] = pd.qcut(h.conc, 3, labels=["low", "mid", "high"],
                          duplicates="drop")
    for b, g in h.groupby("bucket", observed=True):
        lo, hi = rate_ci(g.died_1h.to_numpy())
        print(f"  conc {b:5s} (median {g.conc.median():.1%}) n={len(g):3d} "
              f"death {g.died_1h.mean():.0%} CI[{lo:.0%},{hi:.0%}] "
              f"| 2x rate {(g.peak_fwd >= 2).mean():.0%}")

    print("\n=== 3. DOES STACKING SAFETY ON THE TAIL FILTER PAY? ===")
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    d = have.replace([np.inf, -np.inf], np.nan).dropna(
        subset=["traded_min", "range_first", "conc"])
    tail = d[(d.traded_min >= d.traded_min.quantile(0.66)) &
             (d.range_first >= d.range_first.quantile(0.5))]
    variants = {
        "tail filter only": tail,
        "tail + conc<10%": tail[tail.conc < 0.10],
        "tail + conc<15%": tail[tail.conc < 0.15],
        "tail + no mint auth": tail[tail.mint_auth == 0],
    }
    for label, sub in variants.items():
        if len(sub) < 10:
            print(f"  {label:22s} n={len(sub)} — too few")
            continue
        for tp, trail, hold in [(99.0, 0.30, 120), (2.0, 0.35, 120)]:
            raw = [simulate(db, r.pool, r.t_obs, tp, trail, hold)
                   for _, r in sub.iterrows()]
            raw = [x for x in raw if x is not None]
            if len(raw) < 10:
                continue
            res = np.array([v for v, _ in raw])
            kinds = [k for _, k in raw]
            n_unres = sum(1 for k in kinds if k == "unresolved_alive")
            resolved = np.array([v for v, k in raw if k != "unresolved_alive"])
            lo, hi = rate_ci(res)
            rlo, rhi = rate_ci(resolved) if len(resolved) >= 10 else (np.nan, np.nan)
            rule = "trail0.3/120m" if tp > 90 else "tp2/trail0.35/120m"
            print(f"  {label:22s} {rule:20s} n={len(res):3d} "
                  f"(unresolved {n_unres}) death {sub.died_1h.mean():.0%} | "
                  f"ALL mean {res.mean():+.1%} med {np.median(res):+.1%} "
                  f"CI[{lo:+.1%},{hi:+.1%}] | RESOLVED-only mean "
                  f"{resolved.mean() if len(resolved) else float('nan'):+.1%} "
                  f"CI[{rlo:+.1%},{rhi:+.1%}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

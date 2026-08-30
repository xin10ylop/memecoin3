#!/usr/bin/env python3
"""Analyse the UNCONDITIONAL cohort — the honest young-pool measurement.

Unlike the main panel, cohort membership is decided at birth and every
member's full history is harvested regardless of outcome, so censoring is
a property of the clock rather than of fate. This is the only sample on
which the young-pool cell — the single cell that ever looked positive —
can be measured without the winners-only bias that invalidated everything
before it.

Reports, for entries at each age and each holding horizon:
  * coverage: what fraction of the cohort we can actually price (should be
    HIGH here; if it is not, the instrument is still broken)
  * the honest return distribution INCLUDING pools that died, valued at
    what a forced exit would really have recovered
  * expectancy net of costs, cluster-bootstrapped, vs the cost line

Usage: python3 research/cohort_analysis.py [db] [--min-age-hours N]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memebot.backtest.metrics import _cluster_bootstrap_means  # noqa: E402

ENTRY_AGES_MIN = [5, 15, 30, 60]
HORIZONS_MIN = [15, 30, 60, 120]
COST_ROUNDTRIP = 0.016          # 0.8%/side at a small clip in a live pool
DEAD_RECOVERY = 0.10            # forced exit into a dead pool recovers ~10%


def load(db_path: str, min_age_hours: float):
    db = sqlite3.connect(db_path, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    cohort = pd.read_sql_query(
        "SELECT pool_address, symbol, dex_id, created_ts, registered_ts, "
        "n_fetches, n_bars FROM cohort WHERE n_fetches > 0", db)
    if cohort.empty:
        return cohort, {}
    bars = {}
    for addr in cohort["pool_address"]:
        df = pd.read_sql_query(
            "SELECT ts, o, h, l, c, vol_usd FROM ohlcv WHERE pool_address=? "
            "ORDER BY ts", db, params=(addr,))
        if len(df):
            bars[addr] = df
    db.close()
    return cohort, bars


def outcomes(cohort: pd.DataFrame, bars: dict) -> pd.DataFrame:
    rows = []
    for _, c in cohort.iterrows():
        df = bars.get(c["pool_address"])
        if df is None or len(df) < 5 or not c["created_ts"]:
            continue
        ts = df["ts"].to_numpy()
        px = df["c"].to_numpy(dtype=float)
        vol = df["vol_usd"].to_numpy(dtype=float)
        birth = int(c["created_ts"])
        last_traded = ts[vol > 0].max() if (vol > 0).any() else ts.min()
        for age in ENTRY_AGES_MIN:
            t_entry = birth + age * 60
            i = int(np.searchsorted(ts, t_entry))
            if i >= len(ts) or vol[i] <= 0:      # entry must be a traded minute
                continue
            p_entry = px[i]
            if not np.isfinite(p_entry) or p_entry <= 0:
                continue
            for h in HORIZONS_MIN:
                t_exit = t_entry + h * 60
                j = int(np.searchsorted(ts, t_exit))
                if t_exit > last_traded:
                    # pool stopped trading before the horizon: a real forced
                    # exit, not a missing observation. Value it honestly.
                    gross = DEAD_RECOVERY - 1.0
                    status = "dead"
                elif j >= len(ts):
                    continue
                else:
                    near = vol[max(0, j - 2): j + 3]
                    if not (near > 0).any():
                        continue                  # untradable print, skip
                    gross = px[j] / p_entry - 1.0
                    status = "live"
                rows.append({"pool": c["pool_address"], "symbol": c["symbol"],
                             "age": age, "horizon": h, "status": status,
                             "gross": gross, "net": gross - COST_ROUNDTRIP})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("db", nargs="?", default="data/panel.db")
    ap.add_argument("--min-age-hours", type=float, default=0.0)
    args = ap.parse_args()

    cohort, bars = load(args.db, args.min_age_hours)
    print(f"cohort harvested: {len(cohort)} pools, bars for {len(bars)}")
    if cohort.empty:
        print("no harvested cohort yet — let the tracker run")
        return 0
    df = outcomes(cohort, bars)
    if df.empty:
        print("no measurable entries yet")
        return 0

    print(f"\nobservations: {len(df)}  "
          f"({(df.status == 'dead').mean():.0%} died before horizon)\n")
    out = []
    for age in ENTRY_AGES_MIN:
        for h in HORIZONS_MIN:
            d = df[(df.age == age) & (df.horizon == h)]
            if len(d) < 10:
                continue
            nets = d["net"].to_numpy()
            boot = _cluster_bootstrap_means(nets, d["pool"].to_numpy(),
                                            n_boot=3000)
            out.append({
                "entry_age": age, "horizon": h, "n": len(d),
                "tokens": d["pool"].nunique(),
                "dead%": round(100 * (d.status == "dead").mean()),
                "net_mean": nets.mean(), "ci_lo": np.quantile(boot, 0.025),
                "ci_hi": np.quantile(boot, 0.975),
                "median": np.median(nets), "win%": round(100 * (nets > 0).mean()),
            })
    res = pd.DataFrame(out)
    print(res.to_string(index=False, float_format=lambda x: f"{x:+.3f}"))
    if not res.empty:
        best = res.loc[res.ci_lo.idxmax()]
        print(f"\nbest cell by CI floor: entry age {best.entry_age:.0f}m, "
              f"horizon {best.horizon:.0f}m -> net {best.net_mean:+.1%} "
              f"CI [{best.ci_lo:+.1%}, {best.ci_hi:+.1%}] on {best.n:.0f} obs")
        print("VERDICT:", "a cell clears zero after costs — investigate"
              if best.ci_lo > 0 else
              "no cell clears zero after costs on the honest cohort")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

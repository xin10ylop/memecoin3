#!/usr/bin/env python3
"""Does the LIVE feature measure the same thing the BACKTEST validated?

The backtest used minute-2/minute-1 USD VOLUME from OHLCV bars. The live
scalper cannot see volume in time, so it counts transactions per minute
off-chain instead -- and inherited the 1.0 threshold without checking that
the two scales agree. First live evidence says they do not: ten
range-qualifying candidates scored 0.01..0.94, every one below 1.0, when
roughly 30% should have cleared it.

A threshold ported across a change of measurement is not the same rule.
This measures both features on the SAME recent pools and reports what
transaction-count threshold reproduces the selectivity the volume
threshold actually had.
"""
from __future__ import annotations

import sqlite3
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, "research")
from memebot.data.rpc import SolanaRpc  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
MAX_AGE_H = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
VOL_THRESHOLD = 1.0


def main() -> int:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    # Pools must be young enough that signature history still reaches
    # their creation, so they are sourced LIVE rather than from the
    # harvest, whose sampled pools are mostly older than that window.
    from memebot.data.gt import GeckoTerminal
    gt = GeckoTerminal()
    cutoff = time.time() - MAX_AGE_H * 3600
    cands = []
    for page in range(1, 6):
        for ps in gt.new_pools(page=page):
            age = ps.age_minutes
            if age is not None and 3 <= age <= MAX_AGE_H * 60:
                cands.append(ps)
    print(f"live pools in the measurable age window: {len(cands)}")
    rpc = SolanaRpc()
    rows = []
    for p in cands:
        bars = gt.ohlcv(p.address, limit=3)
        if len(bars) < 2:
            continue
        v = np.array([bars[0][5], bars[1][5]], dtype=float)
        if v[0] <= 0:
            continue
        vol_ratio = v[1] / v[0]
        mint = p.base_mint
        if not mint:
            continue
        # the live feature, measured the way the scalper measures it
        a = rpc.activity_per_minute(mint, limit=1000)
        if len(a) < 2 or a[0] <= 0:
            continue
        rows.append({"pool": p.address, "vol_ratio": vol_ratio,
                     "tx_ratio": a[1] / a[0], "tx_m1": a[0], "tx_m2": a[1]})
        if len(rows) >= 80:
            break

    if len(rows) < 12:
        print(f"only {len(rows)} pools recent enough to measure both "
              f"(need pools young enough that signature history still "
              f"reaches their creation). Widen MAX_AGE_H or wait for the "
              f"harvest to cover more of today.")
        return 1

    df = pd.DataFrame(rows)
    print(f"pools measured with BOTH features: {len(df)}\n")
    print(f"{'feature':<12} {'p25':>8} {'median':>8} {'p75':>8} {'p90':>8}")
    for col in ["vol_ratio", "tx_ratio"]:
        q = df[col].quantile([.25, .5, .75, .9])
        print(f"{col:<12} {q[.25]:>8.2f} {q[.5]:>8.2f} {q[.75]:>8.2f} "
              f"{q[.9]:>8.2f}")

    rho = df.vol_ratio.corr(df.tx_ratio, method="spearman")
    print(f"\nrank correlation between them: {rho:+.3f}")

    kept = (df.vol_ratio >= VOL_THRESHOLD).mean()
    print(f"volume rule (>= {VOL_THRESHOLD}) keeps {kept:.0%} of pools")
    if kept > 0:
        equiv = float(df.tx_ratio.quantile(1 - kept))
        print(f"the tx-count threshold with the SAME selectivity: "
              f"{equiv:.2f}")
        agree = ((df.vol_ratio >= VOL_THRESHOLD) ==
                 (df.tx_ratio >= equiv)).mean()
        print(f"the two rules agree on {agree:.0%} of individual pools")
        print("\n-> " + ("thresholds are interchangeable; the live rule is "
                         "sound as written" if abs(equiv - VOL_THRESHOLD) < 0.15
                         else f"RECALIBRATE: live threshold should be "
                              f"~{equiv:.2f}, not {VOL_THRESHOLD}"))
    df.to_csv("research/results/accel_calibration.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Extract names for BLIND semantic scoring, and outcomes separately.

The strategies tested so far were all mechanical filters on price and
volume. The traders who actually make money in this market are doing
something else: judging whether a meme is funny, timely, and culturally
alive. That is the one dimension never tested here — and the one an LLM
can evaluate at a scale no human trader can.

This writes TWO files that are never joined until scoring is finished:
  scoring_input.json   name + symbol only — what the scorer sees
  scoring_truth.json   outcomes — never shown to the scorer
so the test is genuinely blind.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("research/results")
OUT.mkdir(parents=True, exist_ok=True)
DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"

db = sqlite3.connect(DB, timeout=60)
db.execute("PRAGMA busy_timeout=60000")

pools = pd.read_sql_query("""
    SELECT r.pool_address, p.base_symbol, p.base_name, p.dex_id,
           p.pool_created_at, r.n_bars
    FROM retro_harvest r JOIN pools p ON p.pool_address = r.pool_address
    WHERE r.n_bars > 0 AND p.base_symbol IS NOT NULL
""", db)

rows_in, rows_truth = [], []
for _, p in pools.iterrows():
    bars = pd.read_sql_query(
        "SELECT ts, c, vol_usd FROM ohlcv WHERE pool_address=? ORDER BY ts",
        db, params=(p.pool_address,))
    if len(bars) < 3:
        continue
    px = bars.c.to_numpy(dtype=float)
    vol = bars.vol_usd.to_numpy(dtype=float)
    ts = bars.ts.to_numpy()
    traded = ts[vol > 0]
    life_min = float((traded.max() - traded.min()) / 60) if len(traded) > 1 else 0.0
    peak_mult = float(px.max() / px[0]) if px[0] > 0 else np.nan
    final_mult = float(px[-1] / px[0]) if px[0] > 0 else np.nan
    total_vol = float(np.nansum(vol))
    rows_in.append({"id": p.pool_address[:12],
                    "symbol": p.base_symbol, "name": p.base_name})
    rows_truth.append({"id": p.pool_address[:12], "pool": p.pool_address,
                       "life_min": life_min, "peak_mult": peak_mult,
                       "final_mult": final_mult, "total_vol": total_vol,
                       "n_bars": int(p.n_bars)})

(OUT / "scoring_input.json").write_text(json.dumps(rows_in, indent=1))
(OUT / "scoring_truth.json").write_text(json.dumps(rows_truth, indent=1))
print(f"scoring set: {len(rows_in)} launches")
t = pd.DataFrame(rows_truth)
print(f"outcome spread — life(min): median {t.life_min.median():.0f} "
      f"p90 {t.life_min.quantile(.9):.0f} | peak_mult: median "
      f"{t.peak_mult.median():.2f} p90 {t.peak_mult.quantile(.9):.2f} | "
      f"{(t.peak_mult >= 2).mean():.0%} ever doubled")

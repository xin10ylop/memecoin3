#!/usr/bin/env python3
"""Re-discover the strategy on EXECUTABLE scoring, from scratch.

Every prior number in this project was scored on bar HIGHS -- peaks a live
bot cannot sell into. On the live population that overstates returns by ~47
points (research/peak_reality.py), which is the whole reason paper and live
diverged. This redoes the discovery on prices a seller could actually meet,
so an edge found here is one that should survive live by construction.

Stage 1 (this file): build one honest row per pool and cache it --
  entry at the close of minute 2, features from the first two minutes,
  outcomes from an EXECUTABLE trailing stop (peak armed only once a bar has
  CLOSED, stop fills from the NEXT bar), fate from the collector's own
  record so a dead pool is scored as the death it was, not dropped.

Run it once; stage 2 (optimise) reads the cache.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from memebot.data.gt import sanitize_bars  # noqa: E402

PANEL = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
CACHE = "data/honest_features.jsonl"
COST = 0.016
HORIZON = 30
DEAD_RECOVERY = 0.10          # what a stuck position is assumed to recover
TRAILS = (0.10, 0.15, 0.20, 0.30)


def exec_trail(bars, entry: float, died: bool, trail: float) -> float:
    """A stop a bot could actually have worked: peak armed on CLOSED bars,
    fill from the next bar (at the open on a gap)."""
    peak = entry
    for _, o, h, l, c, v in bars:
        stop = peak * (1 - trail)
        lo, op = float(l), float(o)
        if lo <= stop:
            return (min(stop, op) if op > 0 else stop) / entry - 1 - COST
        peak = max(peak, float(c))
    if died:
        return DEAD_RECOVERY - 1 - COST
    return float(bars[-1][4]) / entry - 1 - COST


def main() -> int:
    db = sqlite3.connect(PANEL)
    panel_end = db.execute("SELECT MAX(ts) FROM ohlcv").fetchone()[0]
    dexid = {a: d for a, d in db.execute(
        "SELECT pool_address, dex_id FROM pools")}
    fate = {a: (b, c) for a, b, c in db.execute(
        "SELECT pool_address, last_bar_ts, last_fetch_at FROM ohlcv_state "
        "WHERE last_bar_ts IS NOT NULL AND last_fetch_at IS NOT NULL")}
    pools = [r[0] for r in db.execute(
        "SELECT pool_address FROM ohlcv GROUP BY pool_address "
        "HAVING COUNT(*) >= 3")]

    n_written = n_censored = n_skipped = 0
    with open(CACHE, "w") as out:
        for pa in pools:
            bars = sanitize_bars([list(r) for r in db.execute(
                "SELECT ts,o,h,l,c,vol_usd FROM ohlcv WHERE pool_address=? "
                "ORDER BY ts LIMIT 45", (pa,))])
            if len(bars) < 3:
                n_skipped += 1
                continue
            obs, fwd = bars[:2], bars[2:2 + HORIZON]
            if not fwd:
                n_skipped += 1
                continue
            o0, o1 = obs
            v0, v1 = float(o0[5] or 0), float(o1[5] or 0)
            entry = float(o1[4])
            his = [float(o0[2]), float(o1[2])]
            los = [float(o0[3]), float(o1[3])]
            if entry <= 0 or min(los) <= 0:
                n_skipped += 1
                continue

            died = False
            if len(fwd) < HORIZON:
                f = fate.get(pa)
                if not f:
                    n_censored += 1
                    continue
                if f[1] - f[0] > 1800:
                    died = True
                else:
                    n_censored += 1
                    continue

            row = {
                "pool": pa,
                "dex": dexid.get(pa) or "unknown",
                "t0": int(o0[0]),
                # entry features, all from the first two minutes only
                "range": max(his) / min(los) - 1.0,
                "both_traded": bool(v0 > 0 and v1 > 0),
                "accel": (v1 / v0) if v0 > 0 else None,   # min2/min1 volume
                "drawdown": 1.0 - entry / max(his),       # clean-chart: dist below high
                "vol2_usd": v0 + v1,                      # early liquidity/tradability
                "died": died,
                "n_fwd": len(fwd),
            }
            for t in TRAILS:
                row[f"exec{int(t*100)}"] = exec_trail(fwd, entry, died, t)
            out.write(json.dumps(row) + "\n")
            n_written += 1

    print(f"pools scanned:        {len(pools)}")
    print(f"rows written:         {n_written}  -> {CACHE}")
    print(f"censored (fate unknown, dropped): {n_censored}")
    print(f"skipped (too few/dirty bars):     {n_skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

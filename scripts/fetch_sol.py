#!/usr/bin/env python3
"""Fetch SOL/USDC minute bars — the macro leg of the hunt.

Every strategy so far died on the same wall: a ~2% round-trip toll on an
asset class with zero drift. SOL itself costs ~0.02-0.05% to trade, is
deep, and cannot rug. If our proprietary memecoin-activity data leads or
lags SOL at all, a tiny edge survives there that could never survive in
the memecoins themselves.

Stores into a `sol_ohlcv` table in the same panel DB, paginating backwards
so the series covers the whole collection window.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time

sys.path.insert(0, "src")
from memebot.data.gt import GeckoTerminal  # noqa: E402

# deepest SOL/USDC pool on GT ($25M reserve, $75M/24h)
SOL_USDC_POOL = "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sol_ohlcv (
    ts INTEGER PRIMARY KEY,
    o REAL, h REAL, l REAL, c REAL, vol_usd REAL
);
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/panel.db")
    ap.add_argument("--pages", type=int, default=8,
                    help="1000 minute-bars each, paginating backwards")
    args = ap.parse_args()

    db = sqlite3.connect(args.db, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    db.executescript(SCHEMA)
    gt = GeckoTerminal(per_min=10)

    before = None
    total = 0
    for page in range(args.pages):
        bars = gt.ohlcv(SOL_USDC_POOL, "minute", limit=1000,
                        before_timestamp=before)
        if not bars:
            break
        rows = [(int(b[0]), b[1], b[2], b[3], b[4], b[5]) for b in bars]
        db.executemany("INSERT OR REPLACE INTO sol_ohlcv VALUES (?,?,?,?,?,?)",
                       rows)
        db.commit()
        total += len(rows)
        before = min(r[0] for r in rows)
        print(f"page {page + 1}: {len(rows)} bars, oldest "
              f"{time.strftime('%m-%d %H:%M', time.gmtime(before))}")
    rng = db.execute("SELECT MIN(ts), MAX(ts), COUNT(*) FROM sol_ohlcv").fetchone()
    print(f"sol_ohlcv: {rng[2]} bars, "
          f"{time.strftime('%m-%d %H:%M', time.gmtime(rng[0]))} -> "
          f"{time.strftime('%m-%d %H:%M', time.gmtime(rng[1]))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

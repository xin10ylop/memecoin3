#!/usr/bin/env python3
"""Deep SOL minute history from Coinbase — statistical power for the macro leg.

The memecoin panel is 4 days old and censored; SOL history is free, clean,
complete and goes back years. A hint that rests on 38 overlapping
observations (the reversal signal) can be tested here on tens of thousands
of independent ones — the difference between a lead and a mirage.

Coinbase public candles: 300 bars/request, [time, low, high, open, close,
volume], no key required.
"""
from __future__ import annotations

import argparse
import sqlite3
import time

import requests

URL = "https://api.exchange.coinbase.com/products/{p}/candles"
SCHEMA = """
CREATE TABLE IF NOT EXISTS sol_deep (
    ts INTEGER PRIMARY KEY, o REAL, h REAL, l REAL, c REAL, vol REAL
);
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/panel.db")
    ap.add_argument("--product", default="SOL-USD")
    ap.add_argument("--days", type=float, default=120.0)
    ap.add_argument("--rps", type=float, default=5.0)
    args = ap.parse_args()

    db = sqlite3.connect(args.db, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    db.executescript(SCHEMA)
    sess = requests.Session()

    end = int(time.time())
    stop_at = end - int(args.days * 86400)
    total = fails = 0
    while end > stop_at:
        start = end - 300 * 60
        try:
            r = sess.get(URL.format(p=args.product),
                         params={"granularity": 60, "start": start, "end": end},
                         timeout=20)
        except requests.RequestException:
            fails += 1
            time.sleep(2)
            continue
        if r.status_code != 200:
            fails += 1
            if fails > 30:
                print(f"stopping after repeated HTTP {r.status_code}")
                break
            time.sleep(2)
            continue
        rows = [(int(c[0]), float(c[3]), float(c[2]), float(c[1]),
                 float(c[4]), float(c[5])) for c in r.json() or []]
        if not rows:
            end = start                      # gap: keep walking back
            continue
        db.executemany("INSERT OR REPLACE INTO sol_deep VALUES (?,?,?,?,?,?)",
                       rows)
        db.commit()
        total += len(rows)
        end = min(x[0] for x in rows)
        if total % 15000 < 300:
            print(f"  {total} bars, back to "
                  f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(end))}")
        time.sleep(1.0 / args.rps)
    rng = db.execute("SELECT MIN(ts), MAX(ts), COUNT(*) FROM sol_deep").fetchone()
    print(f"sol_deep: {rng[2]} bars, "
          f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(rng[0]))} -> "
          f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(rng[1]))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

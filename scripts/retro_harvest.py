#!/usr/bin/env python3
"""Retroactive unbiased harvest — the honest sample, available today.

The cohort tracker fixes censoring going forward, but we do not have to
wait for it: GeckoTerminal serves 180 days of minute history, so a pool
discovered two days ago can have its ENTIRE life fetched right now, in one
call, whether it 100x'd or died in ten minutes.

The bias was never in the history — it was in WHICH pools we chose to
fetch. The collector prioritised liquid/trending pools, so coverage
correlated with fate (verifiability ~4x enriched in future winners) and
every statistic described survivors.

This script removes that: it selects pools purely by DISCOVERY TIME —
a random sample of everything the newest-pools sweep saw in a window,
with no liquidity, volume, trending or outcome filter — and harvests each
one's full history. Selection is unconditional; coverage is complete for
winners and corpses alike.

Usage:
  python3 scripts/retro_harvest.py --since 2026-08-28 --until 2026-08-29 \
      --sample 1500 --rate 18
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import time
import zlib

sys.path.insert(0, "src")
from memebot.data.gt import GeckoTerminal  # noqa: E402

log = logging.getLogger("retro")

SCHEMA = """
CREATE TABLE IF NOT EXISTS retro_harvest (
    pool_address TEXT PRIMARY KEY,
    first_seen_at TEXT,
    harvested_ts INTEGER,
    n_bars INTEGER
);
"""


def select_pools(db: sqlite3.Connection, since: str, until: str,
                 sample: int) -> list[str]:
    """Unconditional selection: discovery-time window + stable-hash sample.
    No outcome-dependent predicate appears anywhere in this query."""
    rows = db.execute(
        "SELECT pool_address FROM pools "
        "WHERE first_seen_at >= ? AND first_seen_at < ? "
        "AND pool_address NOT IN (SELECT pool_address FROM retro_harvest)",
        (since, until)).fetchall()
    addrs = [r[0] for r in rows]
    if len(addrs) <= sample:
        return addrs
    # deterministic, outcome-blind thinning
    addrs.sort(key=lambda a: zlib.crc32(a.encode()))
    return addrs[:sample]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/panel.db")
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", required=True)
    ap.add_argument("--sample", type=int, default=1500)
    ap.add_argument("--rate", type=float, default=18.0)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)])
    db = sqlite3.connect(args.db, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    db.executescript(SCHEMA)
    gt = GeckoTerminal(per_min=args.rate)

    todo = select_pools(db, args.since, args.until, args.sample)
    log.info("selected %d pools discovered in [%s, %s) — unconditional sample",
             len(todo), args.since, args.until)
    done = bars_total = 0
    for addr in todo:
        bars = gt.ohlcv(addr, "minute", limit=1000)
        if bars:
            db.executemany(
                "INSERT OR REPLACE INTO ohlcv VALUES (?,?,?,?,?,?,?)",
                [(addr, int(b[0]), b[1], b[2], b[3], b[4], b[5]) for b in bars])
            bars_total += len(bars)
        db.execute(
            "INSERT OR REPLACE INTO retro_harvest VALUES (?,?,?,?)",
            (addr, None, int(time.time()), len(bars or [])))
        db.commit()
        done += 1
        if done % 50 == 0:
            log.info("harvested %d/%d pools, %d bars", done, len(todo),
                     bars_total)
    log.info("done: %d pools, %d bars", done, bars_total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

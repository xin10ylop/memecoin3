#!/usr/bin/env python3
"""Unconditional cohort tracker — the fix for the censoring that makes this
market unmeasurable.

The opportunity-surface and failure-anatomy digs both concluded the same
thing: 67-93% of observations cannot be priced at a tradable exit, and
73-79% of those discards happen because our OHLCV fetcher ROTATED AWAY
(median re-fetch gap 29h), not because pools died. Worse, the coverage we
do have is fate-correlated — verifiability is ~4x enriched in pools that
go on to trend. Every statistic computed on it describes winners.

This tracker removes that bias by construction:

  * REGISTER every newly-created pool it sees, unconditionally — no
    liquidity, volume, trending or performance filter. Registration is
    decided by birth, not by fate.
  * HARVEST each pool's full minute history once its observation window
    has elapsed. GT returns up to 1000 minutes per call, so a single call
    at T+window captures the pool's entire life — moon, rug, or silence,
    at identical cost. A second late harvest catches anything after.

Censoring then depends only on the clock, never on the outcome — the only
kind of sample on which the young-pool cell (the one cell that ever looked
positive) can be honestly measured. Cost is ~2 calls per pool instead of
~18 for polling, so essentially every new launch can be covered.

Runs alongside collect_panel.py against the same WAL database.
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import time

sys.path.insert(0, "src")

from memebot.data.gt import GeckoTerminal, parse_iso_ts  # noqa: E402

log = logging.getLogger("cohort")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cohort (
    pool_address TEXT PRIMARY KEY,
    base_mint TEXT,
    symbol TEXT,
    dex_id TEXT,
    created_ts INTEGER,
    registered_ts INTEGER,
    track_until INTEGER,          -- first harvest due at this time
    last_fetch_ts INTEGER DEFAULT 0,
    n_fetches INTEGER DEFAULT 0,
    n_bars INTEGER DEFAULT 0,
    final_harvest_ts INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_cohort_due ON cohort(track_until, n_fetches);
"""


def register(gt: GeckoTerminal, db: sqlite3.Connection, max_age_min: int,
             track_hours: float, pages: int) -> int:
    """Register every pool younger than max_age_min. NO other filter — that
    unconditionality is the whole point."""
    now = int(time.time())
    fresh = []
    for page in range(1, pages + 1):          # network first, no DB lock held
        for p in gt.new_pools(page):
            if not p.address or p.created_ts is None:
                continue
            if now - p.created_ts > max_age_min * 60:
                continue
            fresh.append((p.address, p.base_mint, p.symbol, p.dex_id,
                          p.created_ts, now, now + int(track_hours * 3600)))
    if not fresh:
        return 0
    cur = db.executemany(                     # one short write transaction
        "INSERT OR IGNORE INTO cohort (pool_address, base_mint, symbol,"
        " dex_id, created_ts, registered_ts, track_until) VALUES (?,?,?,?,?,?,?)",
        fresh)
    db.commit()
    return cur.rowcount


def harvest(gt: GeckoTerminal, db: sqlite3.Connection, budget: int,
            late_hours: float) -> tuple[int, int, int]:
    """Harvest full histories for pools whose window has elapsed.

    Pass 1: first harvest at track_until (captures the whole observation
    window in one call). Pass 2: a late harvest `late_hours` later, so a
    pool that kept trading past the window is still fully recorded.
    Dying pools and running pools are treated identically — that symmetry
    is what makes deaths measurable.
    """
    now = int(time.time())
    first = db.execute(
        "SELECT pool_address FROM cohort WHERE n_fetches = 0 "
        "AND track_until <= ? ORDER BY track_until ASC LIMIT ?",
        (now, budget)).fetchall()
    remaining = max(0, budget - len(first))
    late = db.execute(
        "SELECT pool_address FROM cohort WHERE n_fetches = 1 "
        "AND final_harvest_ts = 0 AND last_fetch_ts <= ? "
        "ORDER BY last_fetch_ts ASC LIMIT ?",
        (now - int(late_hours * 3600), remaining)).fetchall() if remaining else []

    late_set = {a for (a,) in late}
    calls = bars_written = 0
    for (addr,) in first + late:
        bars = gt.ohlcv(addr, "minute", limit=1000)   # network: no lock held
        calls += 1
        if bars:
            db.executemany(
                "INSERT OR REPLACE INTO ohlcv VALUES (?,?,?,?,?,?,?)",
                [(addr, int(b[0]), b[1], b[2], b[3], b[4], b[5])
                 for b in bars])
            bars_written += len(bars)
        is_late = addr in late_set
        db.execute(
            "UPDATE cohort SET last_fetch_ts=?, n_fetches=n_fetches+1, "
            "n_bars=?, final_harvest_ts=? WHERE pool_address=?",
            (int(time.time()), len(bars or []),
             int(time.time()) if is_late else 0, addr))
        db.commit()
    return calls, bars_written, len(first)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/panel.db")
    ap.add_argument("--hours", type=float, default=12.0)
    ap.add_argument("--track-hours", type=float, default=3.0,
                    help="how long each registered pool is tracked")
    ap.add_argument("--late-hours", type=float, default=3.0,
                    help="delay before the second (late) harvest")
    ap.add_argument("--max-age-min", type=int, default=45,
                    help="register pools younger than this")
    ap.add_argument("--rate", type=float, default=6.0, help="GT calls/min")
    ap.add_argument("--track-budget", type=int, default=10,
                    help="harvests per cycle")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)])
    db = sqlite3.connect(args.db, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    db.executescript(SCHEMA)
    cols = [r[1] for r in db.execute("PRAGMA table_info(cohort)")]
    if "final_harvest_ts" not in cols:      # migrate older cohort tables
        db.execute("ALTER TABLE cohort ADD COLUMN final_harvest_ts "
                   "INTEGER DEFAULT 0")
        db.commit()
    gt = GeckoTerminal(per_min=args.rate)

    deadline = time.time() + args.hours * 3600
    cycle = 0
    while time.time() < deadline:
        start = time.time()
        cycle += 1
        try:
            reg = register(gt, db, args.max_age_min, args.track_hours,
                           pages=1 if cycle % 2 else 2)
            calls, bars, firsts = harvest(gt, db, args.track_budget,
                                          args.late_hours)
            pending = db.execute(
                "SELECT COUNT(*) FROM cohort WHERE n_fetches = 0").fetchone()[0]
            done = db.execute(
                "SELECT COUNT(*) FROM cohort WHERE n_fetches > 0").fetchone()[0]
            total = db.execute("SELECT COUNT(*) FROM cohort").fetchone()[0]
            log.info("cycle=%d registered=%d harvested=%d (first=%d) bars=%d "
                     "pending=%d harvested_total=%d cohort=%d",
                     cycle, reg, calls, firsts, bars, pending, done, total)
        except Exception:
            log.exception("cycle %d failed", cycle)
            time.sleep(20)
        elapsed = time.time() - start
        if elapsed < 60:
            time.sleep(60 - elapsed)
    log.info("deadline reached")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

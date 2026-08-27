#!/usr/bin/env python3
"""Survivorship-free launch-panel collector for Solana memecoin pools.

Snapshots GeckoTerminal's new_pools feed (pages 1..N) on a fixed cadence and
continuously backfills minute OHLCV for every pool discovered, so the dataset
retains pools that later die/rug (they stay in the DB with their full price
history). This is the raw material for honest backtests.

Runs standalone (stdlib + requests only) so it can start before the rest of
the package exists. Usage:

    python3 scripts/collect_panel.py --hours 6 --db data/panel.db
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sqlite3
import sys
import time
from datetime import datetime, timezone

import requests

GT_BASE = "https://api.geckoterminal.com/api/v2"
HEADERS = {"accept": "application/json", "user-agent": "memebot-panel-collector/0.1"}

log = logging.getLogger("collector")


class RateLimiter:
    """Simple pacing: at most `per_min` calls/minute, evenly spaced."""

    def __init__(self, per_min: float = 25.0):
        self.min_interval = 60.0 / per_min
        self._last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delta = now - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last = time.monotonic()


class GTClient:
    def __init__(self, limiter: RateLimiter):
        self.limiter = limiter
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get(self, path: str, params: dict | None = None) -> dict | None:
        url = f"{GT_BASE}{path}"
        for attempt in range(4):
            self.limiter.wait()
            try:
                r = self.session.get(url, params=params, timeout=20)
            except requests.RequestException as e:
                log.warning("request error %s (%s), attempt %d", path, e, attempt)
                time.sleep(3 * (attempt + 1))
                continue
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    return None
            if r.status_code == 429:
                log.warning("429 rate limited on %s; backing off", path)
                time.sleep(20 * (attempt + 1))
                continue
            if r.status_code == 404:
                return None
            log.warning("HTTP %d on %s", r.status_code, path)
            time.sleep(3 * (attempt + 1))
        return None


SCHEMA = """
CREATE TABLE IF NOT EXISTS pools (
    pool_address TEXT PRIMARY KEY,
    base_token_address TEXT,
    base_symbol TEXT,
    base_name TEXT,
    dex_id TEXT,
    pool_created_at TEXT,
    first_seen_at TEXT
);
CREATE TABLE IF NOT EXISTS snapshots (
    pool_address TEXT,
    ts INTEGER,
    price_usd REAL,
    reserve_usd REAL,
    fdv_usd REAL,
    market_cap_usd REAL,
    vol_m5 REAL, vol_h1 REAL, vol_h24 REAL,
    buys_m5 INTEGER, sells_m5 INTEGER, buyers_m5 INTEGER, sellers_m5 INTEGER,
    buys_h1 INTEGER, sells_h1 INTEGER,
    price_change_m5 REAL, price_change_h1 REAL,
    PRIMARY KEY (pool_address, ts)
);
CREATE TABLE IF NOT EXISTS trending (
    pool_address TEXT,
    ts INTEGER,
    PRIMARY KEY (pool_address, ts)
);
CREATE TABLE IF NOT EXISTS ohlcv (
    pool_address TEXT,
    ts INTEGER,
    o REAL, h REAL, l REAL, c REAL,
    vol_usd REAL,
    PRIMARY KEY (pool_address, ts)
);
CREATE TABLE IF NOT EXISTS ohlcv_state (
    pool_address TEXT PRIMARY KEY,
    last_bar_ts INTEGER,
    earliest_bar_ts INTEGER,
    last_fetch_at INTEGER,
    backfill_done INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_snapshots_pool ON snapshots(pool_address);
CREATE INDEX IF NOT EXISTS idx_ohlcv_pool ON ohlcv(pool_address);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def f(x):
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


def snapshot_new_pools(gt: GTClient, db: sqlite3.Connection, pages: int) -> int:
    ts = int(time.time())
    n = 0
    for page in range(1, pages + 1):
        data = gt.get("/networks/solana/new_pools", {"page": page, "include": "base_token,dex"})
        if not data or "data" not in data:
            continue
        tokens = {}
        dexes = {}
        for inc in data.get("included", []) or []:
            if inc.get("type") == "token":
                tokens[inc["id"]] = inc.get("attributes", {})
            elif inc.get("type") == "dex":
                dexes[inc["id"]] = inc.get("attributes", {})
        for item in data["data"]:
            a = item.get("attributes", {})
            rel = item.get("relationships", {})
            addr = a.get("address")
            if not addr:
                continue
            bt_id = (((rel.get("base_token") or {}).get("data") or {}).get("id")) or ""
            base_mint = bt_id.split("_", 1)[1] if "_" in bt_id else None
            tok = tokens.get(bt_id, {})
            dex_id = (((rel.get("dex") or {}).get("data") or {}).get("id")) or None
            db.execute(
                "INSERT OR IGNORE INTO pools VALUES (?,?,?,?,?,?,?)",
                (addr, base_mint, tok.get("symbol"), tok.get("name"), dex_id,
                 a.get("pool_created_at"), now_iso()),
            )
            vol = a.get("volume_usd") or {}
            tx = a.get("transactions") or {}
            m5 = tx.get("m5") or {}
            h1 = tx.get("h1") or {}
            pc = a.get("price_change_percentage") or {}
            db.execute(
                "INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (addr, ts, f(a.get("base_token_price_usd")), f(a.get("reserve_in_usd")),
                 f(a.get("fdv_usd")), f(a.get("market_cap_usd")),
                 f(vol.get("m5")), f(vol.get("h1")), f(vol.get("h24")),
                 m5.get("buys"), m5.get("sells"), m5.get("buyers"), m5.get("sellers"),
                 h1.get("buys"), h1.get("sells"),
                 f(pc.get("m5")), f(pc.get("h1"))),
            )
            n += 1
    db.commit()
    return n


def _insert_snapshot_row(db: sqlite3.Connection, ts: int, a: dict) -> None:
    addr = a.get("address")
    if not addr:
        return
    vol = a.get("volume_usd") or {}
    tx = a.get("transactions") or {}
    m5 = tx.get("m5") or {}
    h1 = tx.get("h1") or {}
    pc = a.get("price_change_percentage") or {}
    db.execute(
        "INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (addr, ts, f(a.get("base_token_price_usd")), f(a.get("reserve_in_usd")),
         f(a.get("fdv_usd")), f(a.get("market_cap_usd")),
         f(vol.get("m5")), f(vol.get("h1")), f(vol.get("h24")),
         m5.get("buys"), m5.get("sells"), m5.get("buyers"), m5.get("sellers"),
         h1.get("buys"), h1.get("sells"),
         f(pc.get("m5")), f(pc.get("h1"))),
    )


def snapshot_tracked(gt: GTClient, db: sqlite3.Connection,
                     min_reserve: float = 2000.0, cap: int = 300) -> int:
    """Keep snapshotting pools that left the newest-200 window but matter
    (ever reached min_reserve liquidity, or ever trended). Uses the
    30-addresses-per-call multi endpoint to stay inside rate budget."""
    rows = db.execute(
        """
        SELECT DISTINCT p.pool_address FROM pools p
        WHERE EXISTS (SELECT 1 FROM snapshots s WHERE s.pool_address=p.pool_address
                      AND s.reserve_usd >= ?)
           OR EXISTS (SELECT 1 FROM trending t WHERE t.pool_address=p.pool_address)
        ORDER BY p.first_seen_at DESC LIMIT ?
        """,
        (min_reserve, cap),
    ).fetchall()
    addrs = [r[0] for r in rows]
    ts = int(time.time())
    n = 0
    for i in range(0, len(addrs), 30):
        chunk = ",".join(addrs[i:i + 30])
        data = gt.get(f"/networks/solana/pools/multi/{chunk}")
        for item in (data or {}).get("data") or []:
            _insert_snapshot_row(db, ts, item.get("attributes") or {})
            n += 1
    db.commit()
    return n


def snapshot_trending(gt: GTClient, db: sqlite3.Connection) -> int:
    ts = int(time.time())
    n = 0
    for page in (1, 2):
        data = gt.get("/networks/solana/trending_pools", {"page": page})
        if not data or "data" not in data:
            continue
        for item in data["data"]:
            addr = (item.get("attributes") or {}).get("address")
            if addr:
                db.execute("INSERT OR IGNORE INTO trending VALUES (?,?)", (addr, ts))
                n += 1
    db.commit()
    return n


def parse_created_ts(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def store_bars(db: sqlite3.Connection, addr: str, bars: list) -> tuple[int, int]:
    """Insert bars; returns (min_ts, max_ts) of inserted set (0,0 if none)."""
    if not bars:
        return 0, 0
    rows = []
    for b in bars:
        # GT bar: [ts, o, h, l, c, volume]
        if not isinstance(b, list) or len(b) < 6:
            continue
        rows.append((addr, int(b[0]), f(b[1]), f(b[2]), f(b[3]), f(b[4]), f(b[5])))
    if not rows:
        return 0, 0
    db.executemany("INSERT OR REPLACE INTO ohlcv VALUES (?,?,?,?,?,?,?)", rows)
    tss = [r[1] for r in rows]
    return min(tss), max(tss)


def backfill_ohlcv(gt: GTClient, db: sqlite3.Connection, budget_calls: int,
                   min_reserve: float = 2000.0, min_age_min: int = 20) -> int:
    """Spend up to budget_calls fetching minute OHLCV for panel pools.

    Priority: pools never fetched, then most-stale. Pools must have shown at
    least `min_reserve` USD liquidity in some snapshot (skip dust) and be at
    least `min_age_min` minutes old.
    """
    now = int(time.time())
    cur = db.execute(
        """
        SELECT p.pool_address, p.pool_created_at,
               COALESCE(s.last_bar_ts, 0), COALESCE(s.last_fetch_at, 0),
               COALESCE(s.backfill_done, 0), COALESCE(s.earliest_bar_ts, 0)
        FROM pools p
        LEFT JOIN ohlcv_state s ON s.pool_address = p.pool_address
        WHERE (SELECT MAX(reserve_usd) FROM snapshots WHERE pool_address = p.pool_address) >= ?
        ORDER BY COALESCE(s.last_fetch_at, 0) ASC
        LIMIT 200
        """,
        (min_reserve,),
    )
    candidates = cur.fetchall()
    calls = 0
    for addr, created_at, last_bar, last_fetch, bf_done, earliest in candidates:
        if calls >= budget_calls:
            break
        created_ts = parse_created_ts(created_at) or 0
        if created_ts and now - created_ts < min_age_min * 60:
            continue
        if now - last_fetch < 600:  # refreshed within 10 min -> skip
            continue
        params = {"aggregate": 1, "limit": 1000, "currency": "usd", "token": "base"}
        data = gt.get(f"/networks/solana/pools/{addr}/ohlcv/minute", params)
        calls += 1
        bars = (((data or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
        mn, mx = store_bars(db, addr, bars)
        new_earliest = min(earliest, mn) if earliest and mn else (mn or earliest)
        new_last = max(last_bar, mx)
        done = bf_done
        # If earliest bar is still well after creation and we got a full page,
        # paginate once more back in time.
        if mn and created_ts and mn > created_ts + 120 and len(bars) >= 990 and calls < budget_calls:
            data2 = gt.get(
                f"/networks/solana/pools/{addr}/ohlcv/minute",
                {**params, "before_timestamp": mn},
            )
            calls += 1
            bars2 = (((data2 or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
            mn2, _ = store_bars(db, addr, bars2)
            if mn2:
                new_earliest = min(new_earliest or mn2, mn2)
        if new_earliest and created_ts and new_earliest <= created_ts + 180:
            done = 1
        if len(bars) < 990:
            done = 1  # reached start of available history
        db.execute(
            "INSERT OR REPLACE INTO ohlcv_state VALUES (?,?,?,?,?)",
            (addr, new_last or None, new_earliest or None, now, done),
        )
        db.commit()
    return calls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=6.0)
    ap.add_argument("--db", default="data/panel.db")
    ap.add_argument("--pages", type=int, default=10)
    ap.add_argument("--rate", type=float, default=25.0)
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    db = sqlite3.connect(args.db)
    db.executescript(SCHEMA)
    gt = GTClient(RateLimiter(args.rate))
    deadline = time.time() + args.hours * 3600
    cycle = 0
    while time.time() < deadline:
        cycle_start = time.time()
        cycle += 1
        try:
            n = snapshot_new_pools(gt, db, args.pages)
            trend = snapshot_trending(gt, db) if cycle % 4 == 1 else 0
            tracked = snapshot_tracked(gt, db)
            ohlcv_calls = backfill_ohlcv(gt, db, budget_calls=35)
            npools = db.execute("SELECT COUNT(*) FROM pools").fetchone()[0]
            nbars = db.execute("SELECT COUNT(*) FROM ohlcv").fetchone()[0]
            log.info(
                "cycle=%d snap_rows=%d trend=%d tracked=%d ohlcv_calls=%d "
                "pools=%d bars=%d",
                cycle, n, trend, tracked, ohlcv_calls, npools, nbars,
            )
        except Exception:
            log.exception("cycle %d failed", cycle)
            time.sleep(30)
        # target cadence: at least one snapshot sweep every ~3 min
        elapsed = time.time() - cycle_start
        if elapsed < 60:
            time.sleep(60 - elapsed)
    log.info("deadline reached; exiting")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

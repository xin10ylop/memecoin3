#!/usr/bin/env python3
"""Fetch on-chain safety features for the unbiased sample.

The tail filter (early range + activity) doubles the 2x-rate but still
loses to a 32% death rate: each unexitable position costs ~90%, roughly
-29pp of expectancy. If death can be predicted from data available BEFORE
buying, that drag shrinks and the arithmetic changes.

Pulls, per token: mint/freeze authority, Token-2022 extensions, supply,
and top-holder concentration — all from Helius RPC (fast, reliable),
for pools already in the unbiased retro-harvest sample.
"""
from __future__ import annotations

import argparse
import logging
import os
import sqlite3
import sys
import time

sys.path.insert(0, "src")
from memebot.data.rpc import SolanaRpc  # noqa: E402

log = logging.getLogger("safety")

SCHEMA = """
CREATE TABLE IF NOT EXISTS token_safety (
    mint TEXT PRIMARY KEY,
    pool_address TEXT,
    fetched_ts INTEGER,
    program TEXT,
    mint_auth INTEGER,
    freeze_auth INTEGER,
    n_ext INTEGER,
    supply REAL,
    top1_frac REAL,
    top10_frac REAL,
    ex_vault_top10_frac REAL,
    n_holders_listed INTEGER
);
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/panel.db")
    ap.add_argument("--limit", type=int, default=800)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)])
    if not os.environ.get("MEMEBOT_RPC_URL"):
        log.warning("MEMEBOT_RPC_URL unset — public RPC will be slow/throttled")

    db = sqlite3.connect(args.db, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    db.executescript(SCHEMA)
    rpc = SolanaRpc()

    todo = db.execute("""
        SELECT p.base_token_address, r.pool_address
        FROM retro_harvest r JOIN pools p ON p.pool_address = r.pool_address
        WHERE r.n_bars >= 3 AND p.base_token_address IS NOT NULL
          AND p.base_token_address NOT IN (SELECT mint FROM token_safety)
        LIMIT ?""", (args.limit,)).fetchall()
    log.info("fetching safety for %d tokens", len(todo))

    done = 0
    for mint, pool in todo:
        info = rpc.mint_info(mint)
        if info is None:
            db.execute(
                "INSERT OR REPLACE INTO token_safety VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?)",
                (mint, pool, int(time.time()), None, None, None, None,
                 None, None, None, None, 0))
            db.commit()
            continue
        supply = info["supply"] or 0
        largest = rpc.token_largest_accounts(mint)
        top1 = top10 = ex_vault = None
        if largest and supply > 0:
            amts = [a["amount"] for a in largest]
            top1 = amts[0] / supply
            top10 = sum(amts[:10]) / supply
            ex_vault = sum(amts[1:11]) / supply
        db.execute(
            "INSERT OR REPLACE INTO token_safety VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (mint, pool, int(time.time()), info.get("program"),
             1 if info.get("mint_authority") else 0,
             1 if info.get("freeze_authority") else 0,
             len(info.get("extensions") or []), float(supply),
             top1, top10, ex_vault, len(largest)))
        db.commit()
        done += 1
        if done % 50 == 0:
            log.info("  %d/%d tokens", done, len(todo))
    log.info("done: %d tokens", done)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

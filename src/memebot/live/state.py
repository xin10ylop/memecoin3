"""Restart-safe live/paper trading state in SQLite."""
from __future__ import annotations

import json
import sqlite3
import time

from ..risk import OpenPosition

SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    pool TEXT PRIMARY KEY,
    mint TEXT, symbol TEXT,
    entry_ts REAL, entry_price REAL,
    tokens REAL, size_usd REAL, hwm_price REAL,
    tp_taken TEXT DEFAULT '[]',
    decimals INTEGER DEFAULT 6
);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pool TEXT, mint TEXT, symbol TEXT,
    entry_ts REAL, exit_ts REAL,
    entry_price REAL, exit_price REAL,
    size_usd REAL, pnl_usd REAL, reason TEXT
);
CREATE TABLE IF NOT EXISTS equity (
    ts REAL PRIMARY KEY,
    equity_usd REAL, cash_usd REAL, n_positions INTEGER
);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);

CREATE TABLE IF NOT EXISTS candidate_journal (
    mint TEXT PRIMARY KEY,
    ts REAL,
    range_frac REAL,
    samples INTEGER,
    accel REAL,
    taken INTEGER,
    vol2 REAL,
    buyers_m1 INTEGER,
    buyers_m2 INTEGER,
    outcome REAL,
    outcome_ts REAL,
    drawdown REAL,
    drift REAL
);
"""


class StateStore:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)
        # migrate pre-decimals databases
        cols = [r[1] for r in self.db.execute("PRAGMA table_info(positions)")]
        if "decimals" not in cols:
            self.db.execute("ALTER TABLE positions ADD COLUMN decimals "
                            "INTEGER DEFAULT 6")
        self.db.commit()

    # -- kv ------------------------------------------------------------------
    def get_kv(self, k: str, default: str | None = None) -> str | None:
        row = self.db.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return row[0] if row else default

    def set_kv(self, k: str, v: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (k, v))
        self.db.commit()

    # -- positions -----------------------------------------------------------
    def load_positions(self) -> dict[str, OpenPosition]:
        out = {}
        rows = self.db.execute(
            "SELECT pool, mint, symbol, entry_ts, entry_price, tokens, "
            "size_usd, hwm_price, tp_taken, decimals FROM positions").fetchall()
        for r in rows:
            out[r[0]] = OpenPosition(
                pool=r[0], mint=r[1], symbol=r[2], entry_ts=r[3],
                entry_price=r[4], tokens=r[5], size_usd=r[6], hwm_price=r[7],
                tp_taken=json.loads(r[8] or "[]"), decimals=int(r[9] or 6),
            )
        return out

    def save_position(self, p: OpenPosition) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO positions "
            "(pool, mint, symbol, entry_ts, entry_price, tokens, size_usd, "
            "hwm_price, tp_taken, decimals) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (p.pool, p.mint, p.symbol, p.entry_ts, p.entry_price, p.tokens,
             p.size_usd, p.hwm_price, json.dumps(p.tp_taken), p.decimals),
        )
        self.db.commit()

    def delete_position(self, pool: str) -> None:
        self.db.execute("DELETE FROM positions WHERE pool=?", (pool,))
        self.db.commit()

    # -- trades / equity -----------------------------------------------------
    def record_trade(self, p: OpenPosition, exit_price: float, pnl_usd: float,
                     reason: str) -> None:
        self.db.execute(
            "INSERT INTO trades (pool,mint,symbol,entry_ts,exit_ts,entry_price,"
            "exit_price,size_usd,pnl_usd,reason) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (p.pool, p.mint, p.symbol, p.entry_ts, time.time(), p.entry_price,
             exit_price, p.size_usd, pnl_usd, reason),
        )
        self.db.commit()

    def snapshot_equity(self, equity: float, cash: float, n_pos: int) -> None:
        self.db.execute("INSERT OR REPLACE INTO equity VALUES (?,?,?,?)",
                        (time.time(), equity, cash, n_pos))
        self.db.commit()

    def pnl_summary(self) -> dict:
        row = self.db.execute(
            "SELECT COUNT(*), COALESCE(SUM(pnl_usd),0), "
            "COALESCE(SUM(pnl_usd > 0),0) FROM trades").fetchone()
        return {"n_trades": row[0], "total_pnl_usd": row[1], "wins": row[2]}

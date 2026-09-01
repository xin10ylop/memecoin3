"""Restart-safe live/paper trading state in SQLite."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import time

from ..risk import OpenPosition

log = logging.getLogger(__name__)

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

-- When the trading rule changed, so a ledger spanning several rules can be
-- read as several ledgers. Judging a restored configuration by a P&L still
-- dominated by trades the previous one took is how a correct change gets
-- reverted for looking broken.
CREATE TABLE IF NOT EXISTS config_epochs (
    ts REAL PRIMARY KEY,
    cfg TEXT
);

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
    drift REAL,
    feed TEXT
);
"""


class StateStore:
    def __init__(self, path: str):
        # A fresh checkout has no data/ directory -- git does not track
        # empty ones -- and sqlite will not create the parent, so the
        # process died at startup with "unable to open database file".
        # Belt and braces: the installer makes the directory, and so does
        # the code, because a deploy should not depend on remembering.
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)
        # migrate pre-decimals databases
        # Rows written before the feed column existed came from the
        # websocket and polling feeds, and are NOT comparable to real-time
        # ones. Naming them 'legacy' lets analysis exclude them explicitly;
        # leaving them NULL made a filter of "NULL or portal" silently
        # readmit the very rows it was written to keep out.
        # Add any journal column this build expects but an existing
        # database lacks. The previous attempt put `feed` in CREATE TABLE
        # and wrote the backfill, but never ALTERed an existing table -- so
        # on every already-running deployment the INSERT referenced a column
        # that did not exist, failed, and was swallowed by the journal's own
        # try/except. The bot kept trading while recording NOTHING, and the
        # only symptom was a candidate count that quietly stopped moving.
        jcols = [r[1] for r in
                 self.db.execute("PRAGMA table_info(candidate_journal)")]
        for col, decl in (("vol2", "REAL"), ("buyers_m1", "INTEGER"),
                          ("buyers_m2", "INTEGER"), ("outcome", "REAL"),
                          ("outcome_ts", "REAL"), ("drawdown", "REAL"),
                          ("drift", "REAL"), ("feed", "TEXT"),
                          # one column per exit rule, so "which exit works"
                          # is a query over the SAME coins rather than an
                          # argument between backtests
                          ("out_trail30", "REAL"), ("out_trail15", "REAL"),
                          ("out_trail10", "REAL"), ("out_tp1_5x", "REAL"),
                          ("out_tp2x", "REAL"), ("out_time10", "REAL"),
                          ("out_time30", "REAL"),
                          # the same trails scored on prices a seller could
                          # actually have met. On the live population the
                          # bar-high scoring overstates by 47 points, so
                          # these are the columns to rank rules with.
                          ("out_exec30", "REAL"), ("out_exec15", "REAL"),
                          ("out_exec10", "REAL"),
                          # how many times the backfill has tried and failed
                          # on this row. Without it a permanently unscoreable
                          # row -- pool gone from the aggregator, no bars --
                          # is re-selected every pass forever, and since the
                          # batch is the NEWEST 40, those rows pile up at the
                          # top until nothing else is ever reached.
                          ("outcome_tries", "INTEGER DEFAULT 0")):
            if col not in jcols:
                self.db.execute(
                    f"ALTER TABLE candidate_journal ADD COLUMN {col} {decl}")
        self.db.execute("UPDATE candidate_journal SET feed = 'legacy' "
                        "WHERE feed IS NULL")
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

    def record_config(self, cfg: str) -> None:
        """Note the rule in force, if it differs from the last one noted.

        Called on every start, but a restart is not a rule change -- only a
        different threshold string opens a new epoch.
        """
        try:
            row = self.db.execute(
                "SELECT cfg FROM config_epochs ORDER BY ts DESC "
                "LIMIT 1").fetchone()
            if row and row[0] == cfg:
                return
            self.db.execute("INSERT OR REPLACE INTO config_epochs (ts, cfg) "
                            "VALUES (?, ?)", (time.time(), cfg))
            self.db.commit()
            log.info("config epoch recorded: %s", cfg)
        except sqlite3.Error as e:
            log.error("could not record config epoch: %s", e)

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

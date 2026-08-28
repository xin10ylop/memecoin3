import sqlite3

import numpy as np
import pytest

from memebot.data.store import _load_pool_df, load_panel

SCHEMA = """
CREATE TABLE pools (
    pool_address TEXT PRIMARY KEY, base_token_address TEXT,
    base_symbol TEXT, base_name TEXT, dex_id TEXT,
    pool_created_at TEXT, first_seen_at TEXT
);
CREATE TABLE snapshots (
    pool_address TEXT, ts INTEGER, price_usd REAL, reserve_usd REAL,
    fdv_usd REAL, market_cap_usd REAL, vol_m5 REAL, vol_h1 REAL,
    vol_h24 REAL, buys_m5 INTEGER, sells_m5 INTEGER, buyers_m5 INTEGER,
    sellers_m5 INTEGER, buys_h1 INTEGER, sells_h1 INTEGER,
    price_change_m5 REAL, price_change_h1 REAL,
    PRIMARY KEY (pool_address, ts)
);
CREATE TABLE trending (pool_address TEXT, ts INTEGER,
                       PRIMARY KEY (pool_address, ts));
CREATE TABLE ohlcv (pool_address TEXT, ts INTEGER, o REAL, h REAL, l REAL,
                    c REAL, vol_usd REAL, PRIMARY KEY (pool_address, ts));
"""

T0 = 1_700_000_000


def make_db(tmp_path, bars, snapshots=(), created_iso="2023-11-14T22:13:20Z"):
    path = str(tmp_path / "t.db")
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    db.execute("INSERT INTO pools VALUES ('P','M','S','N','pumpswap',?,?)",
               (created_iso, created_iso))
    for b in bars:
        db.execute("INSERT INTO ohlcv VALUES ('P',?,?,?,?,?,?)", b)
    for s in snapshots:
        db.execute(
            "INSERT INTO snapshots (pool_address, ts, reserve_usd) "
            "VALUES ('P',?,?)", s)
    db.commit()
    db.close()
    return path


def test_gap_reindexing_fills_empty_minutes_with_resting_price(tmp_path):
    # bars at T0, T0+60, then a 10-minute gap, then T0+720
    bars = [(T0, 1.0, 1.1, 0.9, 1.0, 100.0),
            (T0 + 60, 1.0, 1.2, 1.0, 1.1, 200.0),
            (T0 + 720, 1.1, 1.3, 1.1, 1.2, 300.0)]
    path = make_db(tmp_path, bars)
    db = sqlite3.connect(path)
    df = _load_pool_df(db, "P", created_ts=T0)
    # continuous minute grid: 13 rows from T0 to T0+720
    assert len(df) == 13
    # synthetic minutes carry the resting price (prev close) and zero volume
    row = df.loc[T0 + 300]
    assert row["c"] == pytest.approx(1.1)
    assert row["o"] == row["h"] == row["l"] == row["c"]
    assert row["vol_usd"] == 0.0


def test_wick_clamp_only_at_creation(tmp_path):
    # data starting 2h after creation keeps its real wicks
    bars = [(T0 + 7200 + 60 * i, 1.0, 1.1, 0.0001, 1.0, 100.0)
            for i in range(5)]
    path = make_db(tmp_path, bars)
    db = sqlite3.connect(path)
    df = _load_pool_df(db, "P", created_ts=T0)
    assert df["l"].iloc[0] == pytest.approx(0.0001)
    # data starting AT creation clamps the first-bar artifact wick
    df2 = _load_pool_df(db, "P", created_ts=T0 + 7200)
    assert df2["l"].iloc[0] >= 0.5  # clamped to half the body


def test_load_panel_keeps_short_lived_rugs(tmp_path):
    # a pool with only 8 bars (fast rug) must stay in the panel
    bars = [(T0 + 60 * i, 1.0, 1.1, 0.9, 1.0, 100.0) for i in range(8)]
    snaps = [(T0 + 60, 20_000.0)]
    path = make_db(tmp_path, bars, snaps)
    pools = load_panel(path, min_max_reserve=2000.0)
    assert len(pools) == 1
    assert len(pools[0].df) == 8

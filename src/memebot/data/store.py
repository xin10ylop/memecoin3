"""Panel store: loads the collector's SQLite DB into backtest-ready frames."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .gt import parse_iso_ts


@dataclass
class PoolMeta:
    address: str
    base_mint: str | None
    symbol: str | None
    name: str | None
    dex_id: str | None
    created_ts: int | None
    first_seen_ts: int | None
    max_reserve_usd: float
    n_bars: int


@dataclass
class PoolData:
    meta: PoolMeta
    df: pd.DataFrame  # index: ts (epoch sec, minutes); columns below

    BAR_COLS = ["o", "h", "l", "c", "vol_usd"]
    SNAP_COLS = ["reserve_usd", "fdv_usd", "buys_m5", "sells_m5",
                 "buyers_m5", "sellers_m5", "vol_h1_snap"]


def _pool_metas(db: sqlite3.Connection, min_max_reserve: float) -> list[PoolMeta]:
    rows = db.execute(
        """
        SELECT p.pool_address, p.base_token_address, p.base_symbol, p.base_name,
               p.dex_id, p.pool_created_at, p.first_seen_at,
               COALESCE((SELECT MAX(reserve_usd) FROM snapshots s
                         WHERE s.pool_address = p.pool_address), 0),
               (SELECT COUNT(*) FROM ohlcv o WHERE o.pool_address = p.pool_address)
        FROM pools p
        """
    ).fetchall()
    out = []
    for r in rows:
        if (r[7] or 0) < min_max_reserve:
            continue
        out.append(PoolMeta(
            address=r[0], base_mint=r[1], symbol=r[2], name=r[3], dex_id=r[4],
            created_ts=parse_iso_ts(r[5]), first_seen_ts=parse_iso_ts(r[6]),
            max_reserve_usd=float(r[7] or 0), n_bars=int(r[8] or 0),
        ))
    return out


MAX_GRID_ROWS = 10_000  # cap reindexed frames (~1 week of minutes)


def sanitize_bars(bars: pd.DataFrame, max_dev: float = 50.0) -> pd.DataFrame:
    """Drop indexer-glitch bars: isolated prints 50x+ away from the local
    price median (GeckoTerminal occasionally emits denomination/decimals
    glitches — e.g. a $0.00005 token printing a $1,500 bar that reverts a
    minute later). Real pumps are path-connected through intermediate
    prices, so a centered 5-bar median is never 50x away from a genuine
    move. This is DATA CLEANING of physically impossible AMM prices, run
    identically in backtest and live loading.

    Bars whose close deviates >max_dev from the local median are removed
    entirely (they become no-trade minutes); surviving bars get h/l clamped
    into the plausible band.
    """
    if bars.empty:
        return bars
    c = bars["c"].astype(float)
    med = c.rolling(5, center=True, min_periods=1).median()
    bad = (c > med * max_dev) | (c < med / max_dev) | ~np.isfinite(c) | (c <= 0)
    out = bars.loc[~bad].copy()
    if out.empty:
        return out
    med_ok = out["c"].rolling(5, center=True, min_periods=1).median()
    out["h"] = np.minimum(out["h"].astype(float), med_ok * max_dev)
    out["l"] = np.maximum(out["l"].astype(float), med_ok / max_dev)
    return out


def _repair_rebased_segments(merged: pd.DataFrame,
                             jump: float = 30.0,
                             snap_band: float = 10.0) -> pd.DataFrame:
    """Neutralize permanently re-based price segments.

    GT's OHLCV stream occasionally re-bases a pool's price denomination
    (e.g. a lasting 38,000x step). A >`jump`x move between ADJACENT traded
    minutes is physically implausible in a CPAMM (it needs several times
    the pool's entire reserve as one-minute inflow), so such jumps split
    the series into segments. A segment is kept iff (a) any overlapping
    snapshot price (independent GT endpoint) agrees within `snap_band`x,
    or (b) it has no snapshot coverage but is < `jump`x displaced from the
    last kept segment. Dropped segments become resting-price no-trade
    minutes at the last trusted close.
    """
    c = merged["c"].astype(float)
    lr = np.abs(np.log10(c / c.shift(1)))
    seg_id = (lr > np.log10(jump)).fillna(False).cumsum()
    if seg_id.iloc[-1] == 0:
        return merged
    ps = merged["price_snap"].astype(float)
    keep = pd.Series(False, index=merged.index)
    last_kept_close: float | None = None
    for sid in range(int(seg_id.iloc[-1]) + 1):
        m = seg_id == sid
        seg_c = c[m]
        seg_ps = ps[m].dropna()
        if len(seg_ps):
            ratio = (seg_c[seg_ps.index] / seg_ps).abs()
            ok = bool(((ratio < snap_band) & (ratio > 1 / snap_band)).median())
        elif last_kept_close is None:
            ok = True                      # nothing to compare against yet
        else:
            disp = seg_c.iloc[0] / last_kept_close
            ok = 1 / jump < disp < jump
        keep[m] = ok
        if ok:
            last_kept_close = float(seg_c.iloc[-1])
    if keep.all():
        return merged
    out = merged.copy()
    for col in ("o", "h", "l", "c"):
        out.loc[~keep, col] = np.nan
    out.loc[~keep, "vol_usd"] = 0.0
    prev = out["c"].ffill()
    for col in ("o", "h", "l", "c"):
        out[col] = out[col].fillna(prev)
    return out[out["c"].notna()]


def _load_pool_df(db: sqlite3.Connection, addr: str,
                  created_ts: int | None = None) -> pd.DataFrame:
    bars = pd.read_sql_query(
        "SELECT ts, o, h, l, c, vol_usd FROM ohlcv WHERE pool_address=? ORDER BY ts",
        db, params=(addr,))
    if bars.empty:
        return bars
    bars = bars.drop_duplicates("ts").set_index("ts")
    bars = sanitize_bars(bars)
    if bars.empty:
        return bars

    # Pool-initialization artifacts: the first minutes routinely print wicks
    # thousands of x below the bar body (liquidity being seeded from ~zero).
    # Clamp the first 3 bars to the bar body — but ONLY when the stored data
    # actually starts at pool creation; mid-life data starts keep their real
    # wicks (flash moves are genuine there).
    starts_at_creation = (created_ts is None
                          or bars.index[0] <= created_ts + 300)
    if starts_at_creation:
        head = bars.index[:3]
        body_lo = bars.loc[head, ["o", "c"]].min(axis=1)
        body_hi = bars.loc[head, ["o", "c"]].max(axis=1)
        bars.loc[head, "l"] = pd.concat([bars.loc[head, "l"], body_lo * 0.5],
                                        axis=1).max(axis=1)
        bars.loc[head, "h"] = pd.concat([bars.loc[head, "h"], body_hi * 2.0],
                                        axis=1).min(axis=1)

    # Reindex to a CONTINUOUS minute grid. GT omits minutes with no trades;
    # without this, every "N-bar" rolling window silently spans arbitrary
    # wall-clock time on sparse pools. Empty minutes carry the AMM's resting
    # price (previous close) and zero volume — which is exactly the market
    # state: the pool is tradable at that price even when nobody printed.
    ts0, ts1 = int(bars.index[0]), int(bars.index[-1])
    if (ts1 - ts0) // 60 + 1 <= MAX_GRID_ROWS:
        grid = np.arange(ts0, ts1 + 60, 60, dtype=np.int64)
        bars = bars.reindex(grid)
        prev_close = bars["c"].ffill()
        for col in ("o", "h", "l", "c"):
            bars[col] = bars[col].fillna(prev_close)
        bars["vol_usd"] = bars["vol_usd"].fillna(0.0)

    snaps = pd.read_sql_query(
        """SELECT ts, price_usd AS price_snap, reserve_usd, fdv_usd, buys_m5,
                  sells_m5, buyers_m5, sellers_m5, vol_h1 AS vol_h1_snap
           FROM snapshots WHERE pool_address=? ORDER BY ts""",
        db, params=(addr,))
    if not snaps.empty:
        snaps = snaps.drop_duplicates("ts").set_index("ts")
        # As-of merge: each bar gets the latest snapshot at-or-before the
        # bar's OPEN label (safe direction; effective staleness at bar close
        # is up to ~11 minutes).
        merged = pd.merge_asof(
            bars.reset_index().sort_values("ts"),
            snaps.reset_index().sort_values("ts"),
            on="ts", direction="backward", tolerance=600,
        ).set_index("ts")
        merged = _repair_rebased_segments(merged)
        merged = merged.drop(columns=["price_snap"])
    else:
        merged = bars.copy()
        for col in PoolData.SNAP_COLS:
            merged[col] = np.nan
    return merged


def load_panel(db_path: str, min_max_reserve: float = 2000.0,
               min_bars: int = 5) -> list[PoolData]:
    """min_bars is deliberately tiny: bar count is a LIFETIME OUTCOME, and
    excluding short-lived pools would drop exactly the fast rugs a strategy
    could have entered — survivorship bias in its purest form."""
    db = sqlite3.connect(db_path, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    try:
        pools = []
        for meta in _pool_metas(db, min_max_reserve):
            if meta.n_bars < min_bars:
                continue
            df = _load_pool_df(db, meta.address, meta.created_ts)
            if df.empty or len(df) < min_bars:
                continue
            pools.append(PoolData(meta=meta, df=df))
        return pools
    finally:
        db.close()


def trending_first_seen(db_path: str) -> dict[str, int]:
    """pool_address -> first ts it appeared in GT trending."""
    db = sqlite3.connect(db_path, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    try:
        rows = db.execute(
            "SELECT pool_address, MIN(ts) FROM trending GROUP BY pool_address"
        ).fetchall()
        return {r[0]: int(r[1]) for r in rows}
    finally:
        db.close()


def boost_first_seen(db_path: str) -> dict[str, int]:
    """pool_address -> first DexScreener paid-boost payment ts for its token."""
    db = sqlite3.connect(db_path, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    try:
        rows = db.execute(
            """SELECT p.pool_address, MIN(b.payment_ts)
               FROM boosts b JOIN pools p
                 ON p.base_token_address = b.token_address
               GROUP BY p.pool_address""").fetchall()
        return {r[0]: int(r[1]) for r in rows if r[1]}
    finally:
        db.close()


def cohort_momentum(pools: list["PoolData"], min_liq: float = 15_000,
                    window_min: int = 30) -> dict[int, float]:
    """Per-minute MEDIAN trailing `window_min`-return across pools that are
    liquidity-qualified at that minute. Strictly trailing (causal). This is
    the 'is the meme tape paying right now' factor."""
    buckets: dict[int, list[float]] = {}
    for p in pools:
        df = p.df
        if "reserve_usd" not in df.columns:
            continue
        c = df["c"].astype(float)
        r = c.pct_change(window_min)
        ok = df["reserve_usd"].fillna(0) >= min_liq
        for ts, ret, qual in zip(df.index, r, ok):
            if qual and np.isfinite(ret):
                buckets.setdefault(int(ts), []).append(float(ret))
    return {ts: float(np.median(v)) for ts, v in buckets.items() if v}


def cohort_gate(cohort: dict[int, float], on: float = 0.02,
                off: float = 0.0) -> dict[int, int]:
    """Hysteresis regime gate over the cohort-momentum series: switches ON
    when momentum crosses `on`, stays on until it drops below `off`.
    Mining showed this beats a plain threshold (more time-in-market, fewer
    whipsaws, CI-positive conditional returns in the hot window)."""
    state = 0
    out = {}
    for ts in sorted(cohort):
        m = cohort[ts]
        if state == 0 and m >= on:
            state = 1
        elif state == 1 and m < off:
            state = 0
        out[ts] = state
    return out


def panel_summary(pools: list[PoolData]) -> pd.DataFrame:
    rows = []
    for p in pools:
        df = p.df
        launch = p.meta.created_ts or (df.index.min() if len(df) else None)
        peak = df["h"].max() if len(df) else np.nan
        first = df["o"].iloc[0] if len(df) else np.nan
        last = df["c"].iloc[-1] if len(df) else np.nan
        rows.append({
            "address": p.meta.address,
            "symbol": p.meta.symbol,
            "dex": p.meta.dex_id,
            "created": datetime.fromtimestamp(launch, timezone.utc).isoformat()
                        if launch else None,
            "bars": len(df),
            "max_reserve": p.meta.max_reserve_usd,
            "first_price": first,
            "peak_over_first": peak / first if first else np.nan,
            "last_over_first": last / first if first else np.nan,
            "last_over_peak": last / peak if peak else np.nan,
        })
    return pd.DataFrame(rows)

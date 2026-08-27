"""Feature engineering on per-pool minute-bar frames.

All features at row t use ONLY information available at the close of bar t.
Rolling windows are right-aligned; nothing peeks forward. The backtest engine
enforces next-bar-open fills on top of this.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_features(df: pd.DataFrame, created_ts: int | None = None) -> pd.DataFrame:
    """Returns a copy with feature columns added. Index must be epoch-sec minutes."""
    out = df.copy()
    c = out["c"].astype(float)
    ts = out.index.to_numpy()

    if created_ts:
        out["age_min"] = (ts - created_ts) / 60.0
    else:
        out["age_min"] = (ts - ts[0]) / 60.0 if len(ts) else np.nan

    out["ret_1m"] = c.pct_change(1)
    out["ret_5m"] = c.pct_change(5)
    out["ret_15m"] = c.pct_change(15)

    out["hwm"] = c.cummax()
    out["dd_from_high"] = c / out["hwm"] - 1.0          # <= 0
    out["run_from_first"] = c / c.iloc[0] - 1.0 if len(c) else np.nan

    out["roll_high_15"] = c.rolling(15, min_periods=5).max()
    out["roll_high_60"] = c.rolling(60, min_periods=15).max()
    out["roll_low_15"] = c.rolling(15, min_periods=5).min()

    out["ema_5"] = c.ewm(span=5, adjust=False).mean()
    out["ema_20"] = c.ewm(span=20, adjust=False).mean()

    v = out["vol_usd"].astype(float).fillna(0.0)
    out["vol_5m"] = v.rolling(5, min_periods=1).sum()
    vol_60m_mean = v.rolling(60, min_periods=20).mean()
    vol_60m_std = v.rolling(60, min_periods=20).std()
    out["vol_z"] = (v - vol_60m_mean) / vol_60m_std.replace(0.0, np.nan)

    # realized vol of 1m returns (fraction, not annualized)
    out["rv_30"] = out["ret_1m"].rolling(30, min_periods=10).std()

    # snapshot-derived (may be NaN where no snapshot coverage)
    if "buys_m5" in out.columns:
        b = out["buys_m5"].astype(float)
        s = out["sells_m5"].astype(float)
        out["buy_frac"] = b / (b + s).replace(0.0, np.nan)
        out["buyers_per_min"] = out["buyers_m5"].astype(float) / 5.0
    if "reserve_usd" in out.columns:
        r = out["reserve_usd"].astype(float)
        out["reserve_chg_5m"] = r.pct_change(5)

    return out


def liquidity_at(df: pd.DataFrame, i: int, fallback: float | None = None) -> float | None:
    """Most recent known reserve at or before row i (may be stale/NaN)."""
    if "reserve_usd" not in df.columns:
        return fallback
    r = df["reserve_usd"].iloc[: i + 1].dropna()
    if r.empty:
        return fallback
    return float(r.iloc[-1])

"""Strategy rule families.

These are PRE-REGISTERED hypothesis families (defined before seeing backtest
results) so that validation is hypothesis-testing, not curve-fitting:

  A. grad_momentum   — young pool, liquidity + volume floor, 15m-high breakout
                        with buyer dominance. Bets on launch momentum
                        continuation ("winners keep winning for minutes-hours").
  B. dip_reclaim     — pool that pumped hard, retraced deeply, then reclaims
                        its short EMA with liquidity intact. Bets on the
                        "first dip after launch" being bought.
  C. attention_cont  — pool aged 6-48h in a mcap band making a fresh 1h high
                        with rising lows + volume expansion. Bets on
                        sustained-attention continuation.
  D. trending_follow — enter on first appearance in GT trending list (event
                        study on an public attention signal).

Signal at bar-close i ==> engine fills at bar open i+1. Strategies only read
columns produced by features.add_features (no forward information).
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from .data.store import PoolData
from .features import add_features


@dataclass
class ExitRules:
    stop_frac: float = 0.20
    trail_frac: float = 0.25
    tp_levels: tuple = ((0.5, 0.4),)   # ((gain_frac, sell_frac), ...)
    max_hold_min: int = 360
    liq_drop_exit_frac: float = 0.5


@dataclass
class Strategy:
    name: str
    params: dict
    exit_rules: ExitRules
    entry_fn: Callable[[pd.DataFrame, dict], np.ndarray]
    # optional per-pool external events (e.g. trending timestamps)
    events: dict = field(default_factory=dict)

    def prepare(self, pool: PoolData) -> pd.DataFrame:
        return add_features(pool.df, pool.meta.created_ts)

    def entries(self, pool: PoolData, df: pd.DataFrame) -> np.ndarray:
        sig = self.entry_fn(df, {**self.params, "_pool": pool, "_events": self.events})
        return np.asarray(sig, dtype=bool)


# ---------------------------------------------------------------------------
# helpers

# universe constants mirroring the LIVE safety gate's market-shape checks
# (config safety.*), applied in backtests too so the backtested universe is
# the live-tradable one. Pre-registered, not tuned.
UNIVERSE_FDV_MIN = 100_000
UNIVERSE_FDV_MAX = 30_000_000
UNIVERSE_VOL_H1_MIN = 10_000


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df.columns:
        return df[name].astype(float)
    return pd.Series(np.nan, index=df.index)


def _liq_ok(df: pd.DataFrame, min_liq: float) -> pd.Series:
    r = _col(df, "reserve_usd")
    # liquidity unknown (no snapshot coverage) counts as NOT ok — we only
    # trade pools we can size against.
    return r.ge(min_liq).fillna(False)


def _universe_ok(df: pd.DataFrame) -> pd.Series:
    """Live-parity market gate: FDV band + 1h volume floor (NaN fails)."""
    fdv = _col(df, "fdv_usd")
    vol = _col(df, "vol_h1_snap")
    return (fdv.between(UNIVERSE_FDV_MIN, UNIVERSE_FDV_MAX).fillna(False)
            & vol.ge(UNIVERSE_VOL_H1_MIN).fillna(False))


def _buyer_ok(df: pd.DataFrame, min_frac: float) -> pd.Series:
    bf = _col(df, "buy_frac")
    # missing buyer data is treated as neutral (pass) — it is snapshot-cadence
    # limited; the liquidity gate above already requires snapshot coverage.
    return bf.ge(min_frac) | bf.isna()


# ---------------------------------------------------------------------------
# A. graduation momentum

def _grad_momentum(df: pd.DataFrame, p: dict) -> np.ndarray:
    c = df["c"].astype(float)
    prior_high = df["roll_high_15"].shift(1)
    cond = (
        (df["age_min"] >= p["min_age_min"])
        & (df["age_min"] <= p["max_age_min"])
        & _liq_ok(df, p["min_liq"])
        & _universe_ok(df)
        & (df["vol_5m"] >= p["min_vol5"])
        & (c > prior_high)
        & (df["ret_5m"] > 0)
        & (df["dd_from_high"] > -0.5)
        & _buyer_ok(df, p["min_buy_frac"])
    )
    return cond.fillna(False).to_numpy()


# B. first-dip reclaim

def _dip_reclaim(df: pd.DataFrame, p: dict) -> np.ndarray:
    c = df["c"].astype(float)
    # the "pumped from launch" baseline is only meaningful when stored data
    # actually starts at pool creation; mid-life data starts never signal
    age0 = df["age_min"].iloc[0] if len(df) else np.nan
    if not np.isfinite(age0) or age0 > 15:
        return np.zeros(len(df), dtype=bool)
    first = c.iloc[0] if len(c) else np.nan
    pumped = df["hwm"] / first >= (1.0 + p["min_run"])
    dipped_now_or_before = (df["dd_from_high"] <= -p["min_dip"]).cummax()
    reclaim = (c > df["ema_5"]) & (c.shift(1) <= df["ema_5"].shift(1))
    liq_stable = _col(df, "reserve_chg_5m").gt(-0.2) | _col(df, "reserve_chg_5m").isna()
    cond = (
        pumped
        & dipped_now_or_before
        & (df["dd_from_high"] <= -p["min_dip"] * 0.5)   # still well below high
        & reclaim
        & (df["age_min"] <= p["max_age_min"])
        & _liq_ok(df, p["min_liq"])
        & _universe_ok(df)
        & liq_stable
        & (df["ret_5m"] > -0.05)
    )
    return cond.fillna(False).to_numpy()


# C. attention continuation (hours horizon)

def _attention_cont(df: pd.DataFrame, p: dict) -> np.ndarray:
    c = df["c"].astype(float)
    fdv = _col(df, "fdv_usd")
    rising_lows = df["roll_low_15"] > df["roll_low_15"].shift(30)
    cond = (
        (df["age_min"] >= p["min_age_min"])
        & (df["age_min"] <= p["max_age_min"])
        & _liq_ok(df, p["min_liq"])
        & _universe_ok(df)
        & fdv.between(p["fdv_min"], p["fdv_max"])
        & (c > df["roll_high_60"].shift(1))
        & rising_lows
        & (df["vol_z"] >= p["min_vol_z"])
    )
    return cond.fillna(False).to_numpy()


# D. trending follow (event entry)

def _trending_follow(df: pd.DataFrame, p: dict) -> np.ndarray:
    pool: PoolData = p["_pool"]
    events: dict = p["_events"]
    trend_ts = events.get(pool.meta.address)
    n = len(df)
    sig = np.zeros(n, dtype=bool)
    if trend_ts is None or n == 0:
        return sig
    ts = df.index.to_numpy()
    idx = int(np.searchsorted(ts, trend_ts, side="left"))
    if idx >= n:
        return sig
    age = df["age_min"].iloc[idx]
    if age is not None and not np.isnan(age) and age > p["max_age_min"]:
        return sig
    liq = _liq_ok(df, p["min_liq"]) & _universe_ok(df)
    # first bar at/after the trending event where the pool qualifies
    for j in range(idx, min(idx + 30, n)):
        if liq.iloc[j]:
            sig[j] = True
            break
    return sig


# placebo negative control: random entries through the SAME liquidity gate,
# exits, and cost machinery. If a "real" strategy doesn't beat this by a
# clear margin, its edge is the exit/cost machinery or the window, not the
# entry signal.

def _random_entries(df: pd.DataFrame, p: dict) -> np.ndarray:
    pool: PoolData = p["_pool"]
    # stable digest: Python's built-in hash() is salted per process, which
    # would make the negative control irreproducible
    seed = (zlib.crc32(pool.meta.address.encode()) ^ p.get("seed", 0)) & 0x7FFFFFFF
    rng = np.random.default_rng(seed)
    eligible = (
        _liq_ok(df, p["min_liq"])
        & _universe_ok(df)
        & (df["age_min"] >= p["min_age_min"])
        & (df["age_min"] <= p["max_age_min"])
    ).fillna(False).to_numpy()
    fire = rng.random(len(df)) < p["prob_per_bar"]
    return eligible & fire


# ---------------------------------------------------------------------------
# registry with tuned-by-default parameter sets (grids live in walkforward)

DEFAULTS: dict[str, dict] = {
    "grad_momentum": {
        "min_age_min": 15, "max_age_min": 360, "min_liq": 15_000,
        "min_vol5": 3_000, "min_buy_frac": 0.55,
    },
    "dip_reclaim": {
        "min_run": 1.0, "min_dip": 0.35, "max_age_min": 720, "min_liq": 15_000,
    },
    "attention_cont": {
        "min_age_min": 360, "max_age_min": 2880, "min_liq": 30_000,
        "fdv_min": 200_000, "fdv_max": 30_000_000, "min_vol_z": 1.0,
    },
    "trending_follow": {
        "max_age_min": 2880, "min_liq": 30_000,
    },
    "random_entries": {
        "min_age_min": 15, "max_age_min": 720, "min_liq": 15_000,
        "prob_per_bar": 0.01, "seed": 0,
    },
}

ENTRY_FNS = {
    "grad_momentum": _grad_momentum,
    "dip_reclaim": _dip_reclaim,
    "attention_cont": _attention_cont,
    "trending_follow": _trending_follow,
    "random_entries": _random_entries,
}


def make_strategy(name: str, params: dict | None = None,
                  exit_rules: ExitRules | None = None,
                  events: dict | None = None) -> Strategy:
    if name not in ENTRY_FNS:
        raise ValueError(f"unknown strategy {name!r}; have {sorted(ENTRY_FNS)}")
    merged = {**DEFAULTS[name], **(params or {})}
    return Strategy(name=name, params=merged,
                    exit_rules=exit_rules or ExitRules(),
                    entry_fn=ENTRY_FNS[name], events=events or {})

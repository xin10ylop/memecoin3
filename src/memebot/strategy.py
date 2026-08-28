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

    def __post_init__(self):
        levels = tuple(tuple(lv) for lv in (self.tp_levels or ()))
        for lv in levels:
            if len(lv) != 2:
                raise ValueError(
                    f"tp_levels must be pairs [[gain, sell_frac], ...]; "
                    f"got {self.tp_levels!r}")
        self.tp_levels = levels


@dataclass
class Strategy:
    name: str
    params: dict
    exit_rules: ExitRules
    entry_fn: Callable[[pd.DataFrame, dict], np.ndarray]
    # optional per-pool external events (e.g. trending timestamps)
    events: dict = field(default_factory=dict)

    def prepare(self, pool: PoolData) -> pd.DataFrame:
        # features depend only on (df, created_ts) — identical across every
        # strategy/config, so memoize on the pool object (grid searches
        # re-prepare each pool hundreds of times otherwise)
        cached = getattr(pool, "_feat_cache", None)
        if cached is not None:
            return cached
        feat = add_features(pool.df, pool.meta.created_ts)
        try:
            pool._feat_cache = feat
        except AttributeError:
            pass
        return feat

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


# E. regime-gated machinery (pre-registered 2026-08-28 after the window-2
# placebo result showed the exit machinery harvests tape beta): trade the
# SAME machinery as the placebo, but only when the meme-cohort's own
# trailing momentum is positive — timing the factor instead of picking
# tokens. NOTE: designed after observing window 2, so window-2 results are
# EXPLORATORY for this family; confirmation requires later windows.

def _regime_gated(df: pd.DataFrame, p: dict) -> np.ndarray:
    cohort: dict = p.get("cohort") or p["_events"].get("__cohort__") or {}
    n = len(df)
    if not cohort or n == 0:
        return np.zeros(n, dtype=bool)
    ts = df.index.to_numpy()
    keys = np.array(sorted(cohort))
    vals = np.array([cohort[k] for k in keys])
    idx = np.searchsorted(keys, ts, side="right") - 1
    mom = np.where(idx >= 0, vals[np.clip(idx, 0, None)], np.nan)
    stale = np.where(idx >= 0, ts - keys[np.clip(idx, 0, None)], 1e12)
    mom = np.where(stale <= 600, mom, np.nan)
    cond = (
        _liq_ok(df, p["min_liq"])
        & _universe_ok(df)
        & (df["age_min"] >= p["min_age_min"])
        & (df["age_min"] <= p["max_age_min"])
        & pd.Series(mom, index=df.index).ge(p["min_cohort_mom"])
        & (df["ret_15m"] > 0)
    )
    return cond.fillna(False).to_numpy()


# F. boost follow (pre-registered 2026-08-28): entry at a token's first
# DexScreener paid-boost event — promoter conviction as a timestamped
# public attention signal.

def _boost_follow(df: pd.DataFrame, p: dict) -> np.ndarray:
    pool: PoolData = p["_pool"]
    events: dict = p["_events"]
    ev_ts = events.get(pool.meta.address)
    n = len(df)
    sig = np.zeros(n, dtype=bool)
    if ev_ts is None or n == 0:
        return sig
    ts = df.index.to_numpy()
    idx = int(np.searchsorted(ts, ev_ts, side="left"))
    if idx >= n:
        return sig
    age = df["age_min"].iloc[idx] if idx < n else np.nan
    if not np.isfinite(age) or age > p["max_age_min"]:
        return sig
    ok = _liq_ok(df, p["min_liq"]) & _universe_ok(df)
    for j in range(idx, min(idx + 30, n)):
        if ok.iloc[j]:
            sig[j] = True
            break
    return sig


# G. composite v2 (pre-registered 2026-08-28 from the alpha-mining pass;
# see research/mining/*.md). Every condition is a mining survivor that was
# sign-consistent across both collected windows:
#   * hysteresis cohort regime gate (on@+2%, off@0%)
#   * near high-water mark (dd_from_high floor)  — strongest IC
#   * turnover floor (vol_5m/reserve) with a wash-cap (vol_h1/reserve <= 10)
#   * buyer-flow floor (buyers_per_min) and buyer dominance (buy_frac)
#   * chop filter (rv_30 cap)
#   * NO-CHASE: no entry within 30 min after first trending appearance
# Data through 2026-08-28 is the DESIGN sample for this family — results on
# it are exploratory; confirmation requires later windows / paper forward.

def _composite_v2(df: pd.DataFrame, p: dict) -> np.ndarray:
    pool: PoolData = p["_pool"]
    events: dict = p["_events"]
    n = len(df)
    if n == 0:
        return np.zeros(0, dtype=bool)
    gate: dict = events.get("__cohort_gate__") or {}
    if not gate:
        return np.zeros(n, dtype=bool)
    ts = df.index.to_numpy()
    keys = np.array(sorted(gate))
    vals = np.array([gate[k] for k in keys])
    idx = np.searchsorted(keys, ts, side="right") - 1
    on = np.where(idx >= 0, vals[np.clip(idx, 0, None)], 0)
    stale = np.where(idx >= 0, ts - keys[np.clip(idx, 0, None)], 1e12)
    regime_on = pd.Series((on == 1) & (stale <= 600), index=df.index)

    turnover = (df["vol_5m"].astype(float)
                / df["reserve_usd"].astype(float).replace(0.0, np.nan))
    wash = (df["vol_h1_snap"].astype(float)
            / df["reserve_usd"].astype(float).replace(0.0, np.nan))
    trend_ts = events.get(pool.meta.address)
    no_chase = pd.Series(True, index=df.index)
    if trend_ts is not None:
        no_chase = ~pd.Series(
            (ts >= trend_ts) & (ts < trend_ts + 1800), index=df.index)

    cond = (
        regime_on
        & _liq_ok(df, p["min_liq"])
        & _universe_ok(df)
        & (df["age_min"] >= p["min_age_min"])
        & (df["age_min"] <= p["max_age_min"])
        & (df["dd_from_high"] >= -p["max_dd"])
        & turnover.ge(p["min_turnover"])
        & (wash.le(10.0) | wash.isna())
        & df["buyers_per_min"].pipe(
            lambda s: s.ge(p["min_buyers_pm"]) | s.isna())
        & _buyer_ok(df, p["min_buy_frac"])
        & df["rv_30"].pipe(lambda s: s.le(p["max_rv30"]) | s.isna())
        & (df["ret_15m"] > 0)
        & no_chase
    )
    return cond.fillna(False).to_numpy()


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
    "regime_gated": {
        "min_age_min": 15, "max_age_min": 2880, "min_liq": 15_000,
        "min_cohort_mom": 0.02, "cohort": None,
    },
    "boost_follow": {
        "max_age_min": 2880, "min_liq": 15_000,
    },
    "composite_v2": {
        "min_age_min": 15, "max_age_min": 720, "min_liq": 15_000,
        "max_dd": 0.15, "min_turnover": 0.02, "min_buyers_pm": 1.0,
        "min_buy_frac": 0.55, "max_rv30": 0.08,
    },
}

ENTRY_FNS = {
    "grad_momentum": _grad_momentum,
    "dip_reclaim": _dip_reclaim,
    "attention_cont": _attention_cont,
    "trending_follow": _trending_follow,
    "random_entries": _random_entries,
    "regime_gated": _regime_gated,
    "boost_follow": _boost_follow,
    "composite_v2": _composite_v2,
}


def make_strategy(name: str, params: dict | None = None,
                  exit_rules: ExitRules | None = None,
                  events: dict | None = None) -> Strategy:
    if name not in ENTRY_FNS:
        raise ValueError(f"unknown strategy {name!r}; have {sorted(ENTRY_FNS)}")
    unknown = set(params or {}) - set(DEFAULTS[name])
    if unknown:
        raise ValueError(f"unknown params for {name}: {sorted(unknown)}; "
                         f"valid: {sorted(DEFAULTS[name])}")
    merged = {**DEFAULTS[name], **(params or {})}
    return Strategy(name=name, params=merged,
                    exit_rules=exit_rules or ExitRules(),
                    entry_fn=ENTRY_FNS[name], events=events or {})

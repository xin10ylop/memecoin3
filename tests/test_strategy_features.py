import numpy as np
import pandas as pd

from memebot.features import add_features
from memebot.strategy import DEFAULTS, make_strategy
from tests.test_engine import _pool, make_df


def test_features_are_causal():
    """Perturbing FUTURE bars must not change features at earlier rows."""
    df1 = make_df(list(np.linspace(1.0, 2.0, 120)))
    df2 = df1.copy()
    df2.iloc[-10:, df2.columns.get_loc("c")] = 99.0
    df2.iloc[-10:, df2.columns.get_loc("h")] = 99.0
    f1 = add_features(df1, created_ts=int(df1.index[0]))
    f2 = add_features(df2, created_ts=int(df2.index[0]))
    check_cols = [c for c in f1.columns if c not in ("o", "h", "l", "c")]
    a = f1[check_cols].iloc[:-15].fillna(-123.0)
    b = f2[check_cols].iloc[:-15].fillna(-123.0)
    pd.testing.assert_frame_equal(a, b)


def test_entry_signals_are_causal_for_all_strategies():
    prices = list(np.concatenate([
        np.linspace(1.0, 3.0, 60),        # pump
        np.linspace(3.0, 1.8, 30),        # dip
        np.linspace(1.8, 2.5, 60),        # reclaim
    ]))
    pool1 = _pool(prices, "A")
    prices2 = prices.copy()
    prices2[-5:] = [0.01] * 5             # future crash
    pool2 = _pool(prices2, "A")
    for name in DEFAULTS:
        if name == "trending_follow":
            continue
        strat = make_strategy(name, {"min_liq": 1000})
        s1 = strat.entries(pool1, strat.prepare(pool1))
        s2 = strat.entries(pool2, strat.prepare(pool2))
        assert (s1[:-10] == s2[:-10]).all(), f"{name} leaks future info"


def test_liquidity_gate_blocks_unknown_liquidity():
    pool = _pool([1.0] * 200, "A")
    pool.df["reserve_usd"] = np.nan   # no snapshot coverage
    strat = make_strategy("grad_momentum", {"min_liq": 1000, "min_vol5": 0})
    sig = strat.entries(pool, strat.prepare(pool))
    assert not sig.any()


def test_trending_follow_uses_event_ts():
    pool = _pool([1.0] * 100, "A")
    ts_mid = int(pool.df.index[50])
    strat = make_strategy("trending_follow", {"min_liq": 1000},
                          events={"A": ts_mid})
    sig = strat.entries(pool, strat.prepare(pool))
    idx = np.flatnonzero(sig)
    assert len(idx) == 1 and pool.df.index[idx[0]] >= ts_mid

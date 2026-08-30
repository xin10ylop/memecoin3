"""Exit-verifiability tests — the guard against the mirage that made a
losing strategy look like a +46%/trade winner."""
import pandas as pd
import pytest

from memebot.backtest.costs import CostModel
from memebot.backtest.engine import simulate_position
from memebot.strategy import ExitRules
from tests.test_engine import make_df

RULES = ExitRules(stop_frac=0.9, trail_frac=0.9, tp_levels=(),
                  max_hold_min=5, liq_drop_exit_frac=0.99)
NO_COST = CostModel(dex_fee_bps=0, adverse_bps=0, priority_fee_usd=0)


def test_exit_into_live_market_is_verified():
    df = make_df([1.0] * 40)          # continuous volume throughout
    t = simulate_position(df, 1, 25, RULES, NO_COST, "P", "X")
    assert t.verified is True


def test_exit_at_data_edge_is_not_verified():
    # data ends right after the exit: nobody proves the pool was tradable
    df = make_df([1.0] * 8)
    t = simulate_position(df, 1, 25, RULES, NO_COST, "P", "X")
    assert t.verified is False


def test_exit_into_untraded_resting_price_is_not_verified():
    df = make_df([1.0] * 40)
    v = df["vol_usd"].to_numpy().copy()
    v[5:] = 0.0                        # pool goes silent from bar 5 on
    df["vol_usd"] = v
    t = simulate_position(df, 1, 25, RULES, NO_COST, "P", "X")
    assert t.verified is False


def test_summarize_excludes_unverified(monkeypatch):
    from memebot.backtest.engine import BacktestResult
    from memebot.backtest.metrics import summarize

    good = simulate_position(make_df([1.0] * 40), 1, 25, RULES, NO_COST,
                             "GOOD", "G")
    bad = simulate_position(make_df([1.0] * 8), 1, 25, RULES, NO_COST,
                            "BAD", "B")
    assert good.verified and not bad.verified
    res = BacktestResult(trades=[good, bad],
                         equity=pd.Series([1000.0], index=[0]),
                         n_candidates=2, n_skipped_risk=0)
    s = summarize(res, n_boot=200)
    assert s["n_trades"] == 1
    assert s["n_unverified_excluded"] == 1

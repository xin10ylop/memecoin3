import numpy as np
import pandas as pd
import pytest

from memebot.backtest.costs import CostModel
from memebot.backtest.engine import RiskParams, run_backtest, simulate_position
from memebot.data.store import PoolData, PoolMeta
from memebot.strategy import ExitRules, Strategy


def make_df(prices, reserve=50_000.0, start_ts=1_700_000_000, vol=1000.0):
    n = len(prices)
    ts = [start_ts + 60 * i for i in range(n)]
    df = pd.DataFrame({
        "o": prices, "h": [p * 1.01 for p in prices],
        "l": [p * 0.99 for p in prices], "c": prices,
        "vol_usd": [vol] * n,
        "reserve_usd": [reserve] * n, "fdv_usd": [1e6] * n,
        "buys_m5": [10] * n, "sells_m5": [5] * n,
        "buyers_m5": [8] * n, "sellers_m5": [4] * n,
        "vol_h1_snap": [vol * 60] * n,
    }, index=ts)
    return df


NO_COST = CostModel(dex_fee_bps=0, adverse_bps=0, priority_fee_usd=0)


def frictionless(reserve_override=None):
    """Cost model with zero friction for arithmetic-identity tests."""
    cm = CostModel(dex_fee_bps=0, adverse_bps=0, priority_fee_usd=0)
    cm.impact_frac = lambda *a, **k: 0.0  # type: ignore
    return cm


RULES = ExitRules(stop_frac=0.2, trail_frac=0.25, tp_levels=((0.5, 0.4),),
                  max_hold_min=600, liq_drop_exit_frac=0.5)


def test_entry_fills_at_next_bar_open_price():
    df = make_df([1.0, 1.1, 1.2, 1.3, 1.4])
    t = simulate_position(df, fill_idx=1, size_usd=100, exit_rules=RULES,
                          costs=frictionless(), pool="P", symbol="X")
    assert t.entry_price == pytest.approx(df["o"].iloc[1])


def test_stop_loss_fires_and_pnl_matches():
    # price collapses 30% in one bar: low breaches the 20% stop
    df = make_df([1.0, 1.0, 0.70, 0.7, 0.7])
    t = simulate_position(df, 1, 100, RULES, frictionless(), "P", "X")
    assert t.exit_reason == "stop"
    # gap-through: open of the breach bar (0.70) is below stop (0.80),
    # so fill at the worse price = open
    assert t.fills[-1].price == pytest.approx(0.70)
    assert t.pnl_usd == pytest.approx(100 * (0.70 / 1.0 - 1.0))


def test_pessimistic_ordering_stop_before_tp():
    # single wild bar: high hits +50% TP, low hits -20% stop => stop wins
    df = make_df([1.0, 1.0, 1.0, 1.0])
    df.loc[df.index[2], "h"] = 1.6
    df.loc[df.index[2], "l"] = 0.75
    t = simulate_position(df, 1, 100, RULES, frictionless(), "P", "X")
    assert t.exit_reason == "stop"
    assert all(f.kind != "tp" for f in t.fills)


def test_tp_partial_then_trail():
    prices = [1.0, 1.0, 1.2, 1.55, 2.0, 2.0, 1.4, 1.4]
    df = make_df(prices)
    t = simulate_position(df, 1, 100, RULES, frictionless(), "P", "X")
    kinds = [f.kind for f in t.fills]
    assert "tp" in kinds
    assert t.exit_reason == "trail"
    # tp sold 40% at 1.5, trail exited the remaining 60%
    tp_fill = next(f for f in t.fills if f.kind == "tp")
    assert tp_fill.price == pytest.approx(1.5)


def test_trailing_stop_references_prior_bar_hwm():
    # hwm should NOT include the current bar's high when checking the stop
    prices = [1.0, 1.0, 3.0, 3.0]
    df = make_df(prices)
    # bar 2: huge high (3.03) and a low (2.97*0.99) that would breach a trail
    # computed from ITS OWN high but not from prior hwm (1.01)
    t = simulate_position(df, 1, 100, RULES, frictionless(), "P", "X")
    # trail from prior hwm 1.01 = 0.7575 < low 2.97 -> no trail exit on bar 2
    assert t.exit_reason != "trail" or t.fills[-1].ts != df.index[2]


def test_liquidity_rug_forces_stressed_exit():
    df = make_df([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.9])
    r = df["reserve_usd"].to_numpy().copy()
    r[6:] = 1000.0  # LP pulled
    df["reserve_usd"] = r
    df["reserve_chg_5m"] = pd.Series(r, index=df.index).pct_change(5)
    t = simulate_position(df, 1, 100, RULES, NO_COST, "P", "X")
    assert t.exit_reason == "liq_rug"


def test_data_end_dead_pool_heavy_haircut():
    # healthy pool at entry; LP pulled to $50 by the end of the data
    df = make_df([1.0, 1.0, 1.0], reserve=50_000.0)
    r = df["reserve_usd"].to_numpy().copy()
    r[-1] = 50.0
    df["reserve_usd"] = r
    t = simulate_position(df, 1, 20, RULES, NO_COST, "P", "X")
    assert t.exit_reason == "data_end"
    assert t.ret_frac < -0.5  # selling into a drained pool recovers little


def test_time_stop():
    rules = ExitRules(stop_frac=0.9, trail_frac=0.9, tp_levels=(),
                      max_hold_min=3, liq_drop_exit_frac=0.99)
    df = make_df([1.0] * 10)
    t = simulate_position(df, 1, 100, rules, frictionless(), "P", "X")
    assert t.exit_reason == "time"
    assert (t.exit_ts - t.entry_ts) / 60 == pytest.approx(3, abs=1)


# ---------------------------------------------------------------- portfolio

def _pool(prices, addr, created=1_700_000_000, reserve=50_000.0, start_ts=None):
    df = make_df(prices, reserve=reserve, start_ts=start_ts or created)
    meta = PoolMeta(address=addr, base_mint="M" + addr, symbol=addr, name=addr,
                    dex_id="pump-swap", created_ts=created,
                    first_seen_ts=created, max_reserve_usd=reserve,
                    n_bars=len(df))
    return PoolData(meta=meta, df=df)


def always_enter_bar_2(df, p):
    sig = np.zeros(len(df), dtype=bool)
    if len(sig) > 2:
        sig[2] = True
    return sig


def test_engine_no_lookahead_and_concurrency_cap():
    pools = [_pool([1.0] * 30, f"P{i}") for i in range(6)]
    strat = Strategy(name="test", params={}, exit_rules=RULES,
                     entry_fn=always_enter_bar_2)
    risk = RiskParams(starting_usd=1000, risk_per_trade_usd=25,
                      max_concurrent=2, daily_loss_limit_frac=0.5)
    res = run_backtest(pools, strat, NO_COST, risk)
    # 6 candidates, cap 2 concurrent, all positions held to time stop overlap
    assert res.n_candidates == 6
    assert len(res.trades) == 2
    assert res.n_skipped_risk >= 4
    # entries filled at bar open AFTER the signal bar (index 3)
    for t in res.trades:
        pool = next(p for p in pools if p.meta.address == t.pool)
        assert t.entry_ts == pool.df.index[3]


def test_engine_daily_loss_halt():
    # entry fills at bar 3 open (signal bar 2); bar 4 crashes 50% -> stop.
    crash = [1.0, 1.0, 1.0, 1.0, 0.5] + [0.5] * 5
    pools = [_pool(crash, f"C{i}", created=1_700_000_000 + i * 3600,
                   start_ts=1_700_000_000 + i * 3600) for i in range(20)]
    strat = Strategy(name="test", params={}, exit_rules=RULES,
                     entry_fn=always_enter_bar_2)
    risk = RiskParams(starting_usd=100, risk_per_trade_usd=25, max_concurrent=1,
                      daily_loss_limit_frac=0.10)
    res = run_backtest(pools, strat, NO_COST, risk)
    # each stop loses ~$12.5 > $10 daily limit -> halt blocks same-day entries
    assert len(res.trades) < 10
    assert res.n_skipped_risk > 0


def test_position_size_capped_by_pool_share():
    pools = [_pool([1.0] * 30, "TINY", reserve=2_000.0)]
    strat = Strategy(name="test", params={}, exit_rules=RULES,
                     entry_fn=always_enter_bar_2)
    risk = RiskParams(starting_usd=1000, risk_per_trade_usd=100,
                      max_concurrent=4, max_pool_share=0.005)
    res = run_backtest(pools, strat, NO_COST, risk)
    # 0.5% of $2k pool = $10 -> above the $5 floor, so sized down to $10
    assert len(res.trades) == 1
    assert res.trades[0].size_usd == pytest.approx(10.0)

import pytest

from memebot.backtest.costs import CostModel


def test_buy_above_sell_below_ref():
    cm = CostModel(dex_fee_bps=30, adverse_bps=30, priority_fee_usd=0.05)
    assert cm.buy_fill(1.0, 100, 50_000) > 1.0
    assert cm.sell_fill(1.0, 100, 50_000) < 1.0


def test_impact_grows_with_size_and_shrinks_with_liquidity():
    cm = CostModel()
    assert cm.impact_frac(1000, 50_000) > cm.impact_frac(100, 50_000)
    assert cm.impact_frac(100, 500_000) < cm.impact_frac(100, 50_000)


def test_impact_formula_cpamm():
    cm = CostModel()
    # q=100 into quote side Q=25_000 (reserve 50k both sides)
    # impact = q/(Q+q) = 100/25100
    assert cm.impact_frac(100, 50_000) == pytest.approx(100 / 25_100)


def test_unknown_liquidity_penalized():
    cm = CostModel()
    assert cm.impact_frac(100, None) == pytest.approx(0.10)
    assert cm.impact_frac(100, 0) == pytest.approx(0.10)


def test_stressed_exit_multiplies_impact():
    cm = CostModel(rug_exit_impact_mult=3.0)
    normal = cm.side_frac(100, 50_000)
    stressed = cm.side_frac(100, 50_000, stressed=True)
    assert stressed > normal


def test_roundtrip_cost_reasonable_for_small_clip():
    cm = CostModel(dex_fee_bps=30, adverse_bps=30)
    # $25 clip in a $50k pool should cost well under 3% round trip
    assert cm.roundtrip_frac(25, 50_000) < 0.03

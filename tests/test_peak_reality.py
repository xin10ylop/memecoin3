"""The scoring rule that ranks every strategy must not pay for wicks.

scripts/fill_outcomes arms the trailing stop on a bar's HIGH and lets it
fill inside that same bar. On a pool that traded flat for a minute with one
$10 trade printing a 5x high, that scores +348% while a real seller got -2%.
Every ranking built on those columns -- trail10 over trail30, range-only
over the filtered rules -- inherits the error, so it is pinned here.
"""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "peak_reality", os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "research", "peak_reality.py"))
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)

FLAT_WITH_WICK = [[1, 1, 1.02, .99, 1.00, 500],
                  [2, 1, 5.00, .99, 1.00, 10],
                  [3, 1, 1.02, .95, .98, 400]]
GENUINE_CLIMB = [[1, 1, 1.20, .98, 1.15, 500],
                 [2, 1.15, 2.0, 1.14, 1.95, 900],
                 [3, 1.95, 2.0, 1.5, 1.6, 600]]
RUG = [[1, 1, 1.01, .30, .35, 800], [2, .35, .36, .02, .03, 200]]


def test_shadow_rule_pays_for_an_unsellable_wick():
    assert pr.shadow_rule(FLAT_WITH_WICK, 1.0) > 3.0


def test_exec_rule_does_not_pay_for_the_wick():
    assert -0.10 < pr.exec_rule(FLAT_WITH_WICK, 1.0) < 0.0


def test_exec_rule_still_captures_a_genuine_climb():
    # closes follow the highs up, so the move was real and sellable
    assert pr.exec_rule(GENUINE_CLIMB, 1.0) > 0.6


def test_both_rules_agree_a_rug_is_a_rug():
    assert pr.shadow_rule(RUG, 1.0) < -0.05
    assert pr.exec_rule(RUG, 1.0) < -0.05

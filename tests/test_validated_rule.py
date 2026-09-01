"""The deployed defaults MUST equal the validated rule.

The validated finding (research/harvest_grid.py, docstring in scalper.py) is
range>=17.2% + activity in both minutes + acceleration in [1,10] + vol2>=0.5
SOL + clean chart (drawdown<=10%), 30-minute cap. Mid-session the clean-chart
filter was silently turned off by defaulting MAX_DRAWDOWN to 1.0, and the
validated rule survived only because an env file happened to override it -- a
restart without that file would have traded a different, unvalidated rule.

This pins the ENTRY defaults to the validated spec so that can never happen
silently: change one and a test goes red, forcing the change to be deliberate
and reviewed. The exit trail is deliberately NOT the validated 0.30 (see the
docstring); it is asserted separately so its deviation is explicit, not
accidental.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))


def _fresh_scalper():
    for k in ("MEMEBOT_MIN_ACCEL", "MEMEBOT_MAX_ACCEL", "MEMEBOT_MAX_DRAWDOWN",
              "MEMEBOT_TRAIL", "MEMEBOT_MIN_RANGE"):
        os.environ.pop(k, None)
    import importlib
    import memebot.live.scalper as sc
    return importlib.reload(sc)


def test_entry_defaults_are_the_validated_rule():
    sc = _fresh_scalper()
    assert sc.MIN_RANGE == 0.172
    assert sc.MIN_ACCEL == 1.0
    assert sc.MAX_ACCEL == 10.0
    assert sc.MAX_DRAWDOWN == 0.10   # the clean-chart filter, ON by default
    assert sc.MIN_SOL_VOL2 == 0.5
    assert sc.MIN_SAMPLES == 3
    assert sc.MAX_HOLD_MIN == 30


def test_trail_deviation_is_explicit():
    # 10%, not the validated 30% -- a deliberate, documented deviation. If
    # someone "restores" it to 0.30 or drifts it elsewhere, that is a real
    # decision and this test makes them make it on purpose.
    sc = _fresh_scalper()
    assert sc.TRAIL == 0.10

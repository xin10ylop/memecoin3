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


def _outcome_under():
    import importlib.util
    import os
    spec = importlib.util.spec_from_file_location(
        "fill_outcomes", os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "scripts", "fill_outcomes.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.outcome_under


def _panel(fwd):
    # outcome_under enters at the close of bars[1] and scores bars[2:]
    head = [[0, 1, 1, 1, 1, 100], [60, 1, 1, 1, 1, 100]]
    return head + fwd


def test_journal_exec_column_refuses_the_wick_the_trail_column_pays_for():
    """The two scorings must disagree exactly where it matters."""
    under = _outcome_under()
    # flat pool, one $10 trade prints a 5x high, then it drifts down
    fwd = [[120, 1, 1.02, .99, 1.00, 500],
           [180, 1, 5.00, .99, 1.00, 10],
           [240, 1, 1.02, .95, .98, 400],
           [300, .98, .99, .90, .92, 300]]
    bars = _panel(fwd)
    paid = under(bars, "trail", 0.10, 30)
    honest = under(bars, "exec", 0.10, 30)
    assert paid > 3.0, "the bar-high scoring should pay for the wick"
    assert honest < 0.0, "the executable scoring should not"


def test_exec_column_still_rides_a_real_move():
    under = _outcome_under()
    fwd = [[120, 1, 1.20, .98, 1.15, 500],
           [180, 1.15, 2.0, 1.14, 1.95, 900],
           [240, 1.95, 2.0, 1.5, 1.60, 600],
           [300, 1.6, 1.65, 1.5, 1.55, 400]]
    assert under(_panel(fwd), "exec", 0.10, 30) > 0.5


def test_backfill_window_starts_at_the_candidates_own_launch():
    """A backfilled row must be scored against its OWN launch window.

    Widening the backfill to pick up columns added later made every
    historical row eligible again. Unanchored, the aggregator hands back the
    most recent hour, so the entry price would come from days after the
    launch being measured.
    """
    import importlib.util
    import os
    spec = importlib.util.spec_from_file_location(
        "fill_outcomes", os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "scripts", "fill_outcomes.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    launch = 16667 * 60                # a real bar ts is divisible by 60
    det = launch + 37                  # detection lands mid-minute
    bars = [[launch - 1200 + 60 * i, 1, 1, 1, 1, 10] for i in range(20)]
    bars += [[launch + 60 * i, 2, 2, 2, 2, 10] for i in range(40)]
    win = m.window_from(bars, det)
    assert len(win) == 40, "keeps the detection minute and everything after"
    assert win[0][0] == launch, "starts at the bar detection happened in"
    assert float(win[1][4]) == 2, "entry comes from the launch, not before"


def test_http_reports_whether_it_got_an_answer():
    """A backfill must not treat 'throttled' as 'this pool is gone'.

    get_json returns None for both "no data" and "no answer", and the
    attempt counter records a permanent verdict. Without this distinction a
    rate-limited row is written off after three throttled passes -- fastest
    exactly when the API is busiest.
    """
    import sys
    import types
    sys.path.insert(0, "src")
    from memebot.data.http import HttpClient

    c = HttpClient(per_min=6000)

    class Resp:
        def __init__(self, code):
            self.status_code = code

        def json(self):
            return {"ok": True}

    c.session = types.SimpleNamespace(get=lambda *a, **k: Resp(200),
                                      headers={}, )
    assert c.get_json("http://x") == {"ok": True}
    assert c.last_error is None, "a 200 is a definitive answer"

    c.session = types.SimpleNamespace(get=lambda *a, **k: Resp(404),
                                      headers={})
    assert c.get_json("http://x") is None
    assert c.last_error is None, "a 404 is also definitive: it is not there"

    c.session = types.SimpleNamespace(get=lambda *a, **k: Resp(429),
                                      headers={})
    assert c.get_json("http://x", retries=0) is None
    assert c.last_error == "429", "throttling is NOT a verdict about the data"

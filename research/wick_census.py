#!/usr/bin/env python3
"""How much of the backtested edge is made of unsellable wicks?

scripts/fill_outcomes arms the trailing stop on a bar's HIGH and lets it
fill inside that same bar. On a pool that traded flat for a minute with one
$10 trade printing a 5x high, that scores +348% while a real seller got -2%
(pinned in tests/test_peak_reality.py). Every ranking in this project rests
on those columns, so the size of the error decides whether the edge exists.

The live ledger has 18 trades. The local panel has 877,720 minute bars over
4,326 pools, which is where a question like this should be settled.

For every pool: enter at the close of bar 2 -- the same entry the outcome
columns use -- and score the next 30 minutes two ways.

  SHADOW  fill_outcomes' rule verbatim: peak from bar highs, stop may fill
          in the bar that set it.
  EXEC    peak armed only once a bar has CLOSED, stop live from the next bar
          and filling at the open on a gap. A close is a price that survived
          a full minute, so a real seller could have met it.

If SHADOW is much larger than EXEC, the edge is an artefact of the scoring
and every rule ranked with it was ranked on prices that never existed. It
turned out to run the other way: the intra-bar fill makes SHADOW far too
PESSIMISTIC, because with a tight trail the bar that sets the peak almost
always dips below the stop within that same minute.

The script then answers the question that matters more than either number:
this rule's profit lives in a handful of trades, so how many trades does it
take before a P&L means anything at all?
"""
from __future__ import annotations

import os
import sqlite3
import statistics
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from memebot.data.gt import sanitize_bars  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") \
    else "data/panel.db"
TRAIL = float(os.environ.get("MEMEBOT_TRAIL", "0.10"))
MIN_RANGE = float(os.environ.get("MEMEBOT_MIN_RANGE", "0.172"))
COST, HORIZON = 0.016, 30
DEAD_RECOVERY = 0.10      # what a stuck position is assumed to recover
PANEL_END = None          # set at runtime; a pool cannot "die" at the edge


def _dead() -> float:
    return DEAD_RECOVERY - 1 - COST


def shadow_rule(bars, entry, died: bool):
    """scripts/fill_outcomes.outcome_under, trail branch, verbatim."""
    peak = entry
    for _, o, h, l, c, v in bars:
        hi, lo = float(h), float(l)
        peak = max(peak, hi)
        if lo <= peak * (1 - TRAIL):
            return max(peak * (1 - TRAIL), lo) / entry - 1 - COST
    return _dead() if died else float(bars[-1][4]) / entry - 1 - COST


def exec_rule(bars, entry, died: bool):
    """A stop a bot could actually have worked.

    The peak is armed only once a bar has CLOSED and the stop is live from
    the following bar, so it never reacts to a price inside the bar that
    printed it, and never trails a high that was one trade.
    """
    peak = entry
    for _, o, h, l, c, v in bars:
        stop = peak * (1 - TRAIL)
        lo, op = float(l), float(o)
        if lo <= stop:
            return (min(stop, op) if op > 0 else stop) / entry - 1 - COST
        peak = max(peak, float(c))
    return _dead() if died else float(bars[-1][4]) / entry - 1 - COST


def _trail_sweep(rows) -> None:
    """Does the choice of trail survive honest scoring?

    The deployed 10% trail was picked because the shadow columns ranked it
    top. If that ranking is an artefact of the intra-bar fill, the bot is
    running a parameter chosen by a bug.
    """
    global TRAIL
    keep = TRAIL
    print()
    print(f"{'trail':>7}{'SHADOW mean':>14}{'EXEC mean':>12}{'EXEC median':>13}")
    best_s = best_e = (None, float("-inf"))
    for t in (0.10, 0.15, 0.20, 0.30, 0.50):
        TRAIL = t
        S = [shadow_rule(f, e, d) for f, e, d in rows]
        E = [exec_rule(f, e, d) for f, e, d in rows]
        ms, me = statistics.mean(S), statistics.mean(E)
        best_s = max(best_s, (t, ms), key=lambda x: x[1])
        best_e = max(best_e, (t, me), key=lambda x: x[1])
        print(f"{t:>6.0%}{ms:>+14.1%}{me:>+12.1%}"
              f"{statistics.median(E):>+13.1%}")
    TRAIL = keep
    print(f"SHADOW picks {best_s[0]:.0%}; honest scoring picks "
          f"{best_e[0]:.0%} — the deployed trail is {keep:.0%}")


def _how_many_trades(returns) -> None:
    """How long before a live P&L is evidence rather than noise?

    This matters more than the mean. If a handful of trades carry all the
    profit, a losing ledger at small n is the expected experience of a
    winning strategy, and reacting to it destroys the strategy.
    """
    import random
    random.seed(11)
    top = sorted(returns, reverse=True)
    share = sum(top[:max(1, len(returns) // 20)]) / sum(returns) \
        if sum(returns) else float("nan")
    print()
    print(f"the best 5% of trades carry {share:.0%} of all the profit")
    print(f"{'trades':>7}{'5th pct':>10}{'median':>10}{'95th pct':>10}"
          f"{'P(shows a loss)':>17}")
    for n in (18, 30, 50, 100, 250, 500):
        means = sorted(statistics.mean(random.choices(returns, k=n))
                       for _ in range(4000))
        print(f"{n:>7}{means[200]:>+10.1%}{means[2000]:>+10.1%}"
              f"{means[3800]:>+10.1%}"
              f"{sum(m < 0 for m in means)/len(means):>17.0%}")


def main() -> int:
    global PANEL_END
    db = sqlite3.connect(DB)
    PANEL_END = db.execute("SELECT MAX(ts) FROM ohlcv").fetchone()[0]
    # Requiring a long history is survivorship bias wearing a lab coat: it
    # throws away exactly the pools that died, and an earlier run of this
    # script discarded 46% of the panel that way and reported +73%. Three
    # bars is the minimum that permits an entry, and a pool whose history
    # stops well before the panel does is scored as the death it was.
    # A pool's fate has to come from the COLLECTOR, not from how many bars
    # happen to be stored. ohlcv_state records when each pool was last
    # fetched and when its last bar arrived: a wide gap means the collector
    # asked and the pool had nothing to say, which is death. A history that
    # simply ends because collection ended is CENSORED -- outcome unknown --
    # and scoring those as anything at all is how a sample invents its own
    # answer. An earlier version of this script derived death from bar count
    # alone and marked 83% of positions dead when the true rate is 30%.
    fate = {pa: (lb, lf) for pa, lb, lf in db.execute(
        "SELECT pool_address, last_bar_ts, last_fetch_at FROM ohlcv_state "
        "WHERE last_bar_ts IS NOT NULL AND last_fetch_at IS NOT NULL")}
    pools = [r[0] for r in db.execute(
        "SELECT pool_address FROM ohlcv GROUP BY pool_address "
        "HAVING COUNT(*) >= 3")]
    print(f"pools with an entry's worth of history: {len(pools)}")
    sh, ex, gaps, thin, n_range, n_dead = [], [], [], 0, 0, 0
    rows = []                      # (fwd, entry, died) for re-scoring
    skipped = censored = 0
    for pa in pools:
        bars = sanitize_bars([list(r) for r in db.execute(
            "SELECT ts,o,h,l,c,vol_usd FROM ohlcv WHERE pool_address=? "
            "ORDER BY ts LIMIT 40", (pa,))])
        if len(bars) < 3:
            skipped += 1
            continue
        obs, fwd = bars[:2], bars[2:2 + HORIZON]
        if not fwd:
            skipped += 1
            continue
        entry = float(obs[-1][4])
        lows = [float(b[3]) for b in obs]
        highs = [float(b[2]) for b in obs]
        if entry <= 0 or min(lows) <= 0:
            skipped += 1
            continue
        if max(highs) / min(lows) - 1.0 < MIN_RANGE:
            continue                       # the live entry rule
        died = False
        if len(fwd) < HORIZON:
            lb_lf = fate.get(pa)
            if lb_lf is None:
                censored += 1
                continue
            last_bar, last_fetch = lb_lf
            if last_fetch - last_bar > 1800:
                died = True                # asked, and nothing was trading
            else:
                censored += 1              # collection ended, fate unknown
                continue
        n_range += 1
        n_dead += died
        rows.append((fwd, entry, died))
        s_r, e_r = shadow_rule(fwd, entry, died), exec_rule(fwd, entry, died)
        sh.append(s_r)
        ex.append(e_r)
        gaps.append(s_r - e_r)
        pk = max(fwd, key=lambda b: float(b[2]))
        vols = sorted(float(b[5] or 0) for b in fwd)
        if float(pk[5] or 0) < vols[len(vols) // 2]:
            thin += 1

    if n_range < 30:
        print("too few pools pass the range filter to conclude")
        return 0
    print(f"skipped as unusable: {skipped}")
    print(f"dropped as censored (collection ended, fate unknown): {censored}")
    print(f"positions left in a pool that stopped trading: {n_dead} ({n_dead/n_range:.0%})")
    print(f"pools passing range>={MIN_RANGE:.1%}: {n_range}\n")
    ms, me = statistics.mean(sh), statistics.mean(ex)
    print(f"{'':<26}{'mean':>9}{'median':>9}{'2x rate':>9}{'death':>8}")
    for lab, xs in (("SHADOW (bar highs)", sh), ("EXEC (executable)", ex)):
        print(f"{lab:<26}{statistics.mean(xs):>+9.1%}"
              f"{statistics.median(xs):>+9.1%}"
              f"{sum(x >= 1 for x in xs)/len(xs):>9.0%}"
              f"{sum(x <= -0.85 for x in xs)/len(xs):>8.0%}")
    print()
    print(f"fiction in the scoring: {ms - me:+.1%} of mean return")
    print(f"peaks printed on below-median volume: {thin}/{n_range} "
          f"({thin/n_range:.0%})")
    big = sum(g > 0.25 for g in gaps)
    print(f"pools where the scoring overstated by >25pp: {big}/{n_range} "
          f"({big/n_range:.0%})")
    print()
    _trail_sweep(rows)
    _how_many_trades(ex)
    print()
    if me > 0.02:
        print(f"VERDICT: EXEC is {me:+.1%}. An executable version of this")
        print("rule still makes money, so the edge survives honest scoring.")
    elif me > -0.02:
        print(f"VERDICT: EXEC is {me:+.1%} — a coin flip after costs. The")
        print("backtested edge was the scoring, not the market.")
    else:
        print(f"VERDICT: EXEC is {me:+.1%}. Honestly scored, this rule LOSES")
        print("money. The entire edge was an artefact of arming stops on bar")
        print("highs. No execution work saves it; the rule has to change or go.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

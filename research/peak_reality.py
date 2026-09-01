#!/usr/bin/env python3
"""Is the shadow test's edge real, or is it made of unsellable wicks?

The live ledger runs about -21% while the shadow test says the same rule is
worth +11%. The audit shows why the question is urgent: 2EoFtZ reached 5.3x
DURING THE HOLD and was closed at -26%. Either the bot is too slow to see
real peaks, or those peaks were never sellable.

The scoring in scripts/fill_outcomes.py arms the trailing stop on a bar's
HIGH and allows it to fill inside the SAME bar. On a pool that traded flat
for a minute with one $10 trade printing a 5x high, that rule scores +348%
while a real seller got -2%. So the flaw is certain; only its size in the
real data is unknown, and that is what this measures.

Three numbers per trade:

  SHADOW   scripts/fill_outcomes' exact rule -- the number the shadow test
           prints and every "trail10 beats trail30" conclusion rests on
  EXEC     the same trail, but the peak is only armed at the END of a bar
           and the stop can only fill from the NEXT bar onward, off closes.
           A close is a price that survived a full minute, so a real seller
           could have met it. This is the honest upper bound for a bot.
  actual   what the bot actually booked

SHADOW - EXEC is fiction. EXEC - actual is slowness, and slowness is fixable.
"""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from memebot.data.gt import GeckoTerminal, sanitize_bars  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else "data/scalp.db"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 25
TRAIL = float(os.environ.get("MEMEBOT_TRAIL", "0.10"))
COST = 0.016      # the same round-trip cost the shadow columns carry


def shadow_rule(bars, entry: float) -> float:
    """scripts/fill_outcomes.outcome_under, trail branch, verbatim."""
    peak = entry
    for _, o, h, l, c, v in bars:
        hi, lo = float(h), float(l)
        peak = max(peak, hi)
        if lo <= peak * (1 - TRAIL):
            return max(peak * (1 - TRAIL), lo) / entry - 1 - COST
    return float(bars[-1][4]) / entry - 1 - COST


def exec_rule(bars, entry: float) -> float:
    """A stop a bot could actually have worked.

    The peak is armed only once a bar has CLOSED, and the stop is live from
    the following bar. That removes the two credits the shadow rule takes
    for free: reacting to a price inside the bar that printed it, and
    trailing a high that may be a single trade.
    """
    peak = entry
    for _, o, h, l, c, v in bars:
        stop = peak * (1 - TRAIL)
        lo, op = float(l), float(o)
        if lo <= stop:
            # gapped through the stop -> fill at the open, not the stop
            fill = min(stop, op) if op > 0 else stop
            return fill / entry - 1 - COST
        peak = max(peak, float(c))
    return float(bars[-1][4]) / entry - 1 - COST


def main() -> int:
    d = sqlite3.connect(DB)
    trades = list(d.execute(
        "SELECT symbol, mint, entry_price, exit_price, entry_ts, exit_ts "
        f"FROM trades ORDER BY exit_ts DESC LIMIT {N}"))[::-1]
    if not trades:
        print("no closed trades")
        return 0
    gt = GeckoTerminal()
    print(f"replaying {len(trades)} trades at a {TRAIL:.0%} trail\n")
    print(f"{'trade':<8} {'peak':>6} {'pkvol$':>8} {'medvol$':>8} "
          f"{'SHADOW':>8} {'EXEC':>8} {'actual':>8}")
    rows = []
    for sym, mint, ent, ex, ets, xts in trades:
        actual = (ex / ent - 1) if ent else 0.0
        try:
            pools = gt.token_pools(mint)
            if not pools:
                print(f"{sym:<8} (no pool)")
                continue
            bars = sanitize_bars(gt.ohlcv(pools[0].address, limit=1000,
                                          before_timestamp=int(xts) + 180))
        except Exception as e:
            print(f"{sym:<8} (lookup failed: {e})")
            continue
        win = [b for b in bars if ets - 60 <= b[0] <= xts + 60]
        if len(win) < 2:
            print(f"{sym:<8} (only {len(win)} bars cover the hold)")
            continue
        pk = max(win, key=lambda b: float(b[2]))
        peak, pkvol = float(pk[2]) / ent, float(pk[5] or 0)
        vols = sorted(float(b[5] or 0) for b in win)
        medvol = vols[len(vols) // 2]
        sh, ex_r = shadow_rule(win, ent), exec_rule(win, ent)
        rows.append((peak, pkvol, medvol, sh, ex_r, actual))
        print(f"{sym:<8} {peak:>5.1f}x {pkvol:>8,.0f} {medvol:>8,.0f} "
              f"{sh:>+8.0%} {ex_r:>+8.0%} {actual:>+8.0%}")

    if len(rows) < 3:
        print("\ntoo few replays to conclude")
        return 0
    n = len(rows)
    ms = sum(r[3] for r in rows) / n
    me = sum(r[4] for r in rows) / n
    ma = sum(r[5] for r in rows) / n
    print(f"\n{'mean':<8} {'':>6} {'':>8} {'':>8} "
          f"{ms:>+8.1%} {me:>+8.1%} {ma:>+8.1%}")
    print()
    print(f"fiction  (SHADOW - EXEC):   {ms - me:+.1%}  "
          f"— credit for prices nobody could sell into")
    print(f"slowness (EXEC - actual):   {me - ma:+.1%}  "
          f"— real prices the bot did not act on")
    thin = [r for r in rows if r[1] < r[2]]
    print(f"\npeaks printed on below-median volume: {len(thin)}/{n}"
          " — a peak bar quieter than a typical bar is one trade, not a market")
    print()
    if abs(ms - me) > abs(me - ma):
        print("VERDICT: mostly FICTION. Every rule ranked on bar highs --")
        print("trail10 over trail30, range-only over the filters -- was")
        print("ranked on prices that did not exist. Re-score on EXEC before")
        print("believing any of it, including the decision to drop the gates.")
    else:
        print("VERDICT: mostly SLOWNESS. The price was really there and the")
        print("bot did not act on it. That is an engineering problem, and it")
        print("is worth fixing before judging the rule.")
    if me > 0:
        print(f"\nEXEC mean is {me:+.1%}: an executable version of this rule")
        print("is still positive, so there is something to fix toward.")
    else:
        print(f"\nEXEC mean is {me:+.1%}: even a perfect bot loses money on")
        print("this rule. No amount of execution work saves it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

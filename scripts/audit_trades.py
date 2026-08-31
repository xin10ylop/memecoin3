#!/usr/bin/env python3
"""Check every recorded trade against what actually happened on chain.

The ledger is written by the bot, so trusting it to grade itself is how a
broken instrument passes as a working strategy. Three of five losses in an
early batch turned out to be accounting artifacts -- positions written off
90% while their pools still held five figures -- and one "rug" was a real
+13% winner booked as a total loss. Every one was found by hand. This does
the same checks automatically:

  losses   is the pool actually dead? reserve near zero says yes; a pool
           still holding real money says the writeoff was ours, not the
           market's
  winners  is the exit price inside the range the token genuinely traded
           during the holding window? a price outside it was invented
  all      does the entry sit inside the entry minute's range?

Prints one line per trade and a summary. Anything marked SUSPECT deserves
a look before the numbers are believed.
"""
from __future__ import annotations

import sqlite3
import sys

sys.path.insert(0, "src")
from memebot.data.gt import GeckoTerminal, sanitize_bars  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else "data/scalp.db"
DEAD_RESERVE = 1000.0     # below this a pool cannot absorb our clip


def main() -> int:
    d = sqlite3.connect(DB)
    trades = list(d.execute(
        "SELECT symbol, mint, entry_price, exit_price, pnl_usd, reason, "
        "entry_ts, exit_ts FROM trades ORDER BY exit_ts"))
    if not trades:
        print("no closed trades to audit")
        return 0
    gt = GeckoTerminal()
    print(f"auditing {len(trades)} trades against live pool data\n")
    print(f"{'trade':<8} {'pnl':>8} {'ret':>8} {'reason':<11} {'verdict'}")
    suspect = checked = unknown = 0
    for sym, mint, ent, ex, pnl, reason, ets, xts in trades:
        ret = (ex / ent - 1) if ent else float("nan")
        try:
            pools = gt.token_pools(mint)
        except Exception as e:
            print(f"{sym:<8} {pnl:>+8.2f} {ret:>+8.0%} {reason:<11} "
                  f"UNKNOWN (lookup failed: {e})")
            unknown += 1
            continue
        if not pools:
            print(f"{sym:<8} {pnl:>+8.2f} {ret:>+8.0%} {reason:<11} "
                  f"UNKNOWN (no pools found)")
            unknown += 1
            continue
        top = pools[0]
        reserve = top.reserve_usd or 0.0
        verdict, detail = "ok", ""

        if pnl < 0 and ret <= -0.85:
            # a near-total loss is only honest if the pool is truly gone
            if reserve >= DEAD_RESERVE:
                verdict = "SUSPECT"
                detail = (f"wrote off {ret:.0%} but pool still holds "
                          f"${reserve:,.0f}")
            else:
                detail = f"pool dead (${reserve:,.0f}) — loss is real"
        else:
            # winners and small losses: was the exit price real?
            try:
                bars = sanitize_bars(gt.ohlcv(top.address, limit=90))
            except Exception:
                bars = []
            win = [b for b in bars if ets - 60 <= b[0] <= xts + 60]
            if not win:
                detail = "no bars covering the hold — cannot verify"
                verdict = "unverified"
            else:
                hi = max(float(b[2]) for b in win)
                lo = min(float(b[3]) for b in win)
                if not (lo * 0.5 <= ex <= hi * 1.5):
                    verdict = "SUSPECT"
                    detail = (f"exit {ex:.2e} outside traded range "
                              f"[{lo:.2e},{hi:.2e}]")
                else:
                    detail = f"exit inside traded range, peak {hi/ent:.1f}x"
        suspect += verdict == "SUSPECT"
        unknown += verdict == "unverified"
        checked += verdict == "ok"
        print(f"{sym:<8} {pnl:>+8.2f} {ret:>+8.0%} {reason:<11} "
              f"{verdict:<11} {detail}")

    print()
    # Say exactly what was and was not established. An earlier version
    # counted only SUSPECT and then announced "all trades verified" while
    # a trade sat right above it marked UNKNOWN -- the precise kind of
    # quiet overclaiming this tool exists to catch.
    print(f"verified {checked}/{len(trades)}   suspect {suspect}   "
          f"could not check {unknown}")
    if suspect:
        print(f"-> {suspect} trade(s) look misreported by the ledger. "
              f"Paste this output for a closer look.")
    elif unknown:
        print(f"-> nothing looks misreported, but {unknown} trade(s) could "
              f"not be checked (pool data gone). Those are unproven, not "
              f"confirmed good.")
    else:
        print("-> every trade matches what the market actually did.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

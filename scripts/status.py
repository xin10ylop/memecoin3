#!/usr/bin/env python3
"""One-glance health check: what the bot has done, against what was expected.

Prints the numbers that decide whether the strategy works, each next to its
backtested expectation, so the comparison does not depend on remembering
what the backtest said.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np

DB = sys.argv[1] if len(sys.argv) > 1 else "data/scalp.db"
# out-of-sample expectations for the deployed rule (range + volume
# acceleration + clean chart), measured on sanitized bars
EXPECT = {"2x": 0.29, "death": 0.18, "win": 0.35}


def main() -> int:
    try:
        d = sqlite3.connect(DB)
        rows = list(d.execute(
            "SELECT entry_price, exit_price, pnl_usd, reason FROM trades"))
    except sqlite3.Error as e:
        print(f"cannot read {DB}: {e}")
        return 1

    if not rows:
        print("no closed trades yet")
    else:
        r = np.array([x / e - 1 for e, x, _, _ in rows if e > 0])
        pnl = sum(t[2] for t in rows)
        print(f"trades    {len(rows)}")
        print(f"P&L       ${pnl:+.2f}    equity ${100 + pnl:.2f}")
        print(f"win rate  {(r > 0).mean():>5.0%}   (expected "
              f"{EXPECT['win']:.0%})")
        print(f"2x rate   {(r >= 1).mean():>5.0%}   (expected "
              f"{EXPECT['2x']:.0%})")
        print(f"deaths    {(r <= -0.85).mean():>5.0%}   (expected "
              f"{EXPECT['death']:.0%})")
        print(f"mean      {r.mean():>+5.1%} per trade")
        reasons: dict[str, int] = {}
        for *_, why in rows:
            reasons[why] = reasons.get(why, 0) + 1
        print("exits     " + ", ".join(f"{k} {v}" for k, v in
                                       sorted(reasons.items(),
                                              key=lambda kv: -kv[1])))
    try:
        j = d.execute("SELECT COUNT(*) FROM candidate_journal").fetchone()[0]
        o = d.execute("SELECT COUNT(*) FROM candidate_journal "
                      "WHERE outcome IS NOT NULL").fetchone()[0]
        print(f"journal   {j} candidates seen, {o} with settled outcomes")
    except sqlite3.Error:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Everything needed to judge the run, in one paste-able block.

SSH into the trading host is blocked from the analysis side, so the only
channel is copy-paste. That makes compactness a feature: this prints the
ledger, the on-chain audit, and the shadow-test comparison that decides
which filters earn their place -- in a block small enough to paste, with
every number next to what was expected of it.
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys

import numpy as np

DB = sys.argv[1] if len(sys.argv) > 1 else "data/scalp.db"
EXPECT = {"2x": 0.29, "death": 0.18, "win": 0.35, "mean": 1.24}


def main() -> int:
    d = sqlite3.connect(DB)
    print("=" * 62)
    print("LEDGER")
    print("=" * 62)
    rows = list(d.execute("SELECT entry_price, exit_price, pnl_usd, reason, "
                          "entry_ts FROM trades ORDER BY entry_ts"))
    if not rows:
        print("no closed trades yet")
    else:
        r = np.array([x / e - 1 for e, x, _, _, _ in rows if e > 0])
        pnl = sum(t[2] for t in rows)
        # Span of the trades themselves, NOT a throughput rate: six trades
        # clustered in twelve minutes once printed "25.7/hour", which is
        # not a fact about anything.
        span = (rows[-1][4] - rows[0][4]) / 3600 if len(rows) > 1 else 0
        print(f"trades {len(rows)}  (first to last: {span:.1f}h)")
        print(f"P&L    ${pnl:+.2f}   equity ${100+pnl:.2f}")
        print(f"{'':10}{'live':>8} {'expected':>10}")
        for lab, val, exp in [("win rate", (r > 0).mean(), EXPECT["win"]),
                              ("2x rate", (r >= 1).mean(), EXPECT["2x"]),
                              ("deaths", (r <= -0.85).mean(), EXPECT["death"])]:
            flag = "  <-- OFF" if abs(val - exp) > 0.15 else ""
            print(f"{lab:<10}{val:>7.0%} {exp:>9.0%}{flag}")
        print(f"{'mean':<10}{r.mean():>+7.1%} {EXPECT['mean']:>+9.0%}")
        reasons: dict[str, int] = {}
        for *_, why, _ in rows:
            reasons[why] = reasons.get(why, 0) + 1
        print("exits     " + ", ".join(f"{k} {v}" for k, v in
                                       sorted(reasons.items(),
                                              key=lambda kv: -kv[1])))
        # the tail is the whole thesis: without big winners this loses
        best = np.sort(r)[-3:][::-1]
        print("best 3    " + ", ".join(f"{x:+.0%}" for x in best))

    print()
    print("=" * 62)
    print("SHADOW TEST — what OTHER rules would have done, same coins")
    print("=" * 62)
    try:
        feeds = [r[0] or "unknown" for r in d.execute(
            "SELECT DISTINCT feed FROM candidate_journal "
            "WHERE outcome IS NOT NULL")]
    except sqlite3.Error:
        feeds = []
    # Only the current feed's candidates are comparable. Rows from the
    # polling feed were observed 4-11 minutes into a launch instead of
    # seconds, so their range and drawdown describe a different animal.
    # Strictly the real-time feed. An earlier version admitted NULL rows
    # too, which readmitted every poll-era candidate it was meant to
    # exclude -- the filter looked right and did nothing.
    has_tagged = any(f == "portal" for f in feeds)
    where = ("WHERE outcome IS NOT NULL AND feed = 'portal'"
             if has_tagged else "WHERE outcome IS NOT NULL")
    j = list(d.execute(
        "SELECT range_frac, accel, vol2, buyers_m1, buyers_m2, drawdown, "
        f"drift, outcome FROM candidate_journal {where}"))
    if len(feeds) > 1 and has_tagged:
        print(f"feeds present in the journal: {', '.join(sorted(feeds))} "
              f"-- analysing the real-time feed only, since a launch "
              f"observed minutes late is not the same observation")
    print(f"comparable candidates with a settled outcome: {len(j)}")
    if len(j) < 20:
        print("(need ~20+ before any comparison means anything)")
    else:
        import pandas as pd
        c = pd.DataFrame(j, columns=["range", "accel", "vol2", "b1", "b2",
                                     "dd", "drift", "ret"])
        c = c[c["range"] >= 0.172]
        vol = c.accel.between(1.0, 10.0, inclusive="left")
        clean = c.dd <= 0.10
        up = c.drift.between(0.10, 0.50, inclusive="left")
        bre = (c.b2 / c.b1.clip(lower=1)) >= 1.0
        print(f"{'rule':<26} {'n':>4} {'2x':>6} {'death':>7} {'mean':>9}")
        for lab, m in [("range only", pd.Series(True, index=c.index)),
                       ("+ volume", vol),
                       ("+ clean chart (LIVE)", vol & clean),
                       ("+ upward drift", vol & clean & up),
                       ("+ buyer breadth", vol & clean & bre)]:
            g = c[m]
            if len(g) < 3:
                print(f"{lab:<26} {len(g):>4}   (too few)")
                continue
            print(f"{lab:<26} {len(g):>4} {(g.ret>=1).mean():>5.0%} "
                  f"{(g.ret<=-0.85).mean():>6.0%} {g.ret.mean():>+8.1%}")
    print()
    subprocess.run([sys.executable, "scripts/audit_trades.py", DB])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

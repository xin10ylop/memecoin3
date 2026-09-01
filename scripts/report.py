#!/usr/bin/env python3
"""Everything needed to judge the run, in one paste-able block.

SSH into the trading host is blocked from the analysis side, so the only
channel is copy-paste. That makes compactness a feature: this prints the
ledger, the on-chain audit, and the shadow-test comparison that decides
which filters earn their place -- in a block small enough to paste, with
every number next to what was expected of it.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _svcenv

DB = sys.argv[1] if len(sys.argv) > 1 else "data/scalp.db"
EXPECT = {"2x": 0.29, "death": 0.18, "win": 0.35, "mean": 1.24}

# The thresholds the SERVICE is running. Hard-coding them here is how the
# shadow table came to score every rule under a 30% trail while the bot ran
# a 10% one, and to tag a rule "(LIVE)" months after it stopped being live.
try:
    _sc, _ = _svcenv.load_scalper()
    MIN_RANGE, MIN_ACCEL, TRAIL = _sc.MIN_RANGE, _sc.MIN_ACCEL, _sc.TRAIL
except Exception:
    MIN_RANGE, MIN_ACCEL, TRAIL = 0.172, 1.0, 0.10


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
    # Only real-time feeds are comparable. Rows from the polling feed were
    # observed 4-11 minutes into a launch instead of seconds, so their range
    # and drawdown describe a different animal. An earlier version admitted
    # NULL rows too, which readmitted every poll-era candidate it was meant
    # to exclude -- the filter looked right and did nothing. A later one
    # named only 'portal' and so silently dropped every 'narrow' row once
    # that second real-time feed went live.
    REALTIME = ("portal", "narrow")
    live = [f for f in REALTIME if f in feeds]
    where = ("WHERE outcome IS NOT NULL AND feed IN "
             f"({','.join(repr(f) for f in live)})" if live
             else "WHERE outcome IS NOT NULL")
    # Judge on the exit that is actually deployed. Reading 'outcome' scored
    # every rule under the old 30% trail while the bot ran a 10% one, so the
    # table described a system nobody was running.
    # Fall back if no column matches the deployed trail (a trail nobody has
    # backfilled yet must not take the whole table down with it).
    # Rank on the EXECUTABLE score. The bar-high columns arm a trail on a
    # price that may be one trade and let it fill inside the bar that
    # printed it; on the live 18 trades that overstates the mean by 47
    # points (2EoFtZ: +374% scored, -26% booked). Both are selected so the
    # gap stays visible instead of being quietly resolved in our favour.
    have = {r[1] for r in d.execute("PRAGMA table_info(candidate_journal)")}
    pct = int(round(TRAIL * 100))
    ecol, tcol = f"out_exec{pct}", f"out_trail{pct}"
    scored = ecol if ecol in have else (tcol if tcol in have else "outcome")
    basis = ("prices a seller could have met" if scored == ecol
             else "BAR HIGHS — inflated, see research/peak_reality.py")
    # PAIRED, or not at all. The backfill skips a mint whose pool has
    # vanished from the aggregator -- which is precisely the coins that
    # died -- so the exec columns fill for survivors first. Ranking exec
    # over a survivor subset while remembering trail numbers from the full
    # one would flatter exec by exactly the deaths it is missing. So every
    # row in this table carries BOTH scores or neither.
    paired = where
    if scored == ecol and tcol in have:
        paired = f"{where} AND {ecol} IS NOT NULL AND {tcol} IS NOT NULL"
    j = list(d.execute(
        "SELECT range_frac, accel, vol2, buyers_m1, buyers_m2, drawdown, "
        f"drift, {scored}, {tcol if tcol in have else 'NULL'} "
        f"FROM candidate_journal {paired}"))
    if scored == ecol:
        tot = d.execute("SELECT COUNT(*) FROM candidate_journal "
                        f"{where}").fetchone()[0]
        cov = len(j) / tot if tot else 0.0
        print(f"honest scoring covers {len(j)}/{tot} settled candidates "
              f"({cov:.0%})")
        if cov < 0.8:
            # "wait longer" and "this is as good as it gets" need different
            # responses, so say which one applies instead of leaving it to
            # be guessed at.
            gone = pending = None
            if "outcome_tries" in have:
                gone, pending = d.execute(
                    "SELECT SUM(COALESCE(outcome_tries,0) >= 3), "
                    "SUM(COALESCE(outcome_tries,0) < 3) "
                    f"FROM candidate_journal {where} "
                    f"AND {ecol} IS NULL").fetchone()
            print(f"  BELOW 80% — do not rank rules on this table yet.")
            if pending:
                print(f"  {pending} rows still to backfill: wait, then rerun.")
            if gone:
                print(f"  {gone} rows given up on (pool dropped by the "
                      f"aggregator). Those skew dead — what is left is "
                      f"optimistic by however many of them died.")
            if not pending:
                print("  nothing left to fetch; this coverage is final.")
    if len(feeds) > 1 and live:
        print(f"feeds present in the journal: {', '.join(sorted(feeds))} "
              f"-- analysing the real-time feeds ({', '.join(live)}) only, "
              f"since a launch observed minutes late is not the same "
              f"observation")
    print(f"comparable candidates with a settled outcome: {len(j)}   "
          f"({TRAIL:.0%} trail, scored on {basis})")
    if len(j) < 20:
        print("(need ~20+ before any comparison means anything)")
    else:
        import pandas as pd
        c = pd.DataFrame(j, columns=["range", "accel", "vol2", "b1", "b2",
                                     "dd", "drift", "ret", "barhigh"])
        c = c[(c["range"] >= MIN_RANGE) & c.ret.notna()]
        vol = c.accel.between(1.0, 10.0, inclusive="left")
        clean = c.dd <= 0.10
        up = c.drift.between(0.10, 0.50, inclusive="left")
        bre = (c.b2 / c.b1.clip(lower=1)) >= 1.0
        allrows = pd.Series(True, index=c.index)
        # Mark the rule the service is ACTUALLY running. This line used to
        # be pinned to '+ clean chart', which stopped being true the moment
        # the gates were turned off -- and a stale (LIVE) tag is worse than
        # none, because it is read as confirmation.
        gated = MIN_ACCEL > 0
        rules = [("range only", allrows),
                 ("+ acceleration", vol),
                 ("+ low drawdown (death filter)", clean),
                 ("+ both gates", vol & clean),
                 ("+ upward drift", vol & clean & up),
                 ("+ buyer breadth", vol & clean & bre)]
        live_label = "+ both gates" if gated else "range only"
        print(f"{'rule':<30} {'n':>4} {'2x':>6} {'death':>7} {'mean':>9}")
        for lab, m in rules:
            g = c[m]
            tag = "  <-- LIVE" if lab == live_label else ""
            if len(g) < 3:
                print(f"{lab:<30} {len(g):>4}   (too few){tag}")
                continue
            print(f"{lab:<30} {len(g):>4} {(g.ret>=1).mean():>5.0%} "
                  f"{(g.ret<=-0.85).mean():>6.0%} {g.ret.mean():>+8.1%}{tag}")

        # What do the deaths actually cost? The gates were built to dodge
        # them, so the honest question is what is left to dodge.
        base = c
        dead = base[base.ret <= -0.85]
        if len(base) >= 20:
            drag = base.ret.mean() - base[base.ret > -0.85].ret.mean()
            print()
            print(f"deaths in the traded population: {len(dead)}/{len(base)} "
                  f"({len(dead)/len(base):.0%}), dragging the mean by "
                  f"{drag:+.1%}")
            print(f"without them the mean would be "
                  f"{base[base.ret > -0.85].ret.mean():+.1%} — so deaths "
                  f"are {'the main problem' if abs(drag) > abs(base.ret.mean()) else 'not what decides this'}")
        both = c[c.barhigh.notna() & c.ret.notna()]
        if scored == ecol and len(both) >= 20:
            gap = both.barhigh.mean() - both.ret.mean()
            print(f"scoring on bar highs instead would read "
                  f"{both.barhigh.mean():+.1%} — {gap:+.1%} of credit for "
                  f"prices nobody could sell into")
    print()
    subprocess.run([sys.executable, "scripts/audit_trades.py", DB])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

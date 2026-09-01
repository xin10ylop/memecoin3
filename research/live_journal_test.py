#!/usr/bin/env python3
"""Settle it on the LIVE system's own numbers, not the panel's.

The panel says range+clean-chart on migrations is +50-66% honestly scored,
walk-forward, placebo p=0.000. The live journal, same nominal rule and
population and the same executable scoring, says -1.8%. A ~50pp gap that no
hypothesis has yet explained -- and every panel-vs-live difference (which
pools got indexed, which window the features were computed over, which week)
is a candidate.

This removes all of them by using ONLY the live journal: its own recorded
features (range_frac, drawdown, accel), its own executable outcome
(out_exec10), its own candidates. If there is an edge in what the bot
actually sees and can actually act on, it shows up here or nowhere.

Run on the trading host:  python3 research/live_journal_test.py data/scalp.db
Read COVERAGE first -- below ~80% the missing rows are disproportionately
dead pools and every number here is optimistic.
"""
from __future__ import annotations

import random
import sqlite3
import statistics as st
import sys

random.seed(29)
DB = sys.argv[1] if len(sys.argv) > 1 else "data/scalp.db"
REALTIME = ("portal", "narrow")


def ci(a, n=4000):
    if len(a) < 8:
        return (float("nan"), float("nan"))
    m = sorted(st.mean(random.choices(a, k=len(a))) for _ in range(n))
    return m[int(.025 * n)], m[int(.975 * n)]


def placebo_p(universe, mean, k, n=4000):
    if k < 5 or k >= len(universe):
        return float("nan")
    return sum(st.mean(random.sample(universe, k)) >= mean
               for _ in range(n)) / n


def main() -> int:
    d = sqlite3.connect(DB)
    feeds = ",".join(repr(f) for f in REALTIME)
    rows = list(d.execute(
        f"SELECT ts, range_frac, drawdown, accel, out_exec10 "
        f"FROM candidate_journal WHERE feed IN ({feeds}) "
        f"AND out_exec10 IS NOT NULL AND range_frac IS NOT NULL"))
    total = d.execute(
        f"SELECT COUNT(*) FROM candidate_journal WHERE feed IN ({feeds}) "
        f"AND outcome IS NOT NULL").fetchone()[0]
    if not rows:
        print("no exec-scored rows yet — let the backfill run")
        return 0
    cov = len(rows) / total if total else 0
    print(f"COVERAGE {len(rows)}/{total} ({cov:.0%})"
          + ("" if cov >= 0.8 else "  <-- BELOW 80%: missing rows skew dead, "
                                   "everything below reads optimistic"))
    sig = [r for r in rows if r[1] >= 0.172]
    sig.sort(key=lambda r: r[0])
    if len(sig) < 60:
        print(f"only {len(sig)} range-qualifying rows — too few to split")
        return 0
    h = len(sig) // 2
    train, test = sig[:h], sig[h:]
    print(f"range-qualifying: {len(sig)}   train {len(train)}  test {len(test)}"
          f"   (walk-forward by time)\n")

    RULES = {
        "range only": lambda r: True,
        "+ clean chart<=10%": lambda r: r[2] is not None and r[2] <= 0.10,
        "+ clean chart<=20%": lambda r: r[2] is not None and r[2] <= 0.20,
        "+ accel 1-10": lambda r: r[3] is not None and 1.0 <= r[3] < 10.0,
        "+ accel & clean10": lambda r: (r[3] is not None and 1.0 <= r[3] < 10.0
                                        and r[2] is not None and r[2] <= 0.10),
    }
    uni = [r[4] for r in test]
    print(f"{'rule':<22}{'train':>9}{'TEST':>9}{'test 95% CI':>22}"
          f"{'placebo':>9}{'n':>6}")
    any_real = False
    for name, f in RULES.items():
        tr = [r[4] for r in train if f(r)]
        te = [r[4] for r in test if f(r)]
        if len(te) < 10:
            print(f"{name:<22}{'(too few)':>9}")
            continue
        lo, hi = ci(te)
        pp = placebo_p(uni, st.mean(te), len(te))
        real = lo > 0 and (pp < 0.10 or name == "range only")
        any_real |= real
        print(f"{name:<22}{st.mean(tr):>+9.1%}{st.mean(te):>+9.1%}"
              f"   [{lo:+.1%},{hi:+.1%}]{pp:>9.3f}{len(te):>6}"
              + ("  <--" if real else ""))
    print()
    if not any_real:
        print("NOTHING clears zero out-of-sample on the live system's own")
        print("measurements. Whatever the panel shows, the bot cannot see it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

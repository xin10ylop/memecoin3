#!/usr/bin/env python3
"""Is a BIGGER opening range better, or is there a ceiling past which it
flips into a warning?

The entry rule treats range >= 17.2% as one undifferentiated bucket, so a
25% opener and a 400% opener are bought with equal conviction. A live trade
made that assumption look naive: a token ran 441x in the two minutes before
our entry, we bought the top of that pump, and it rugged 74 seconds later.

The hypothesis worth killing or keeping: range is informative because it
signals genuine two-sided churn, and an enormous range is not more of that
signal but a different thing entirely — a pump already spent, whose buyers
have all arrived. If so, expectancy is HUMP-SHAPED in range and the rule
should carry a ceiling as well as a floor.

Same simulation and honest accounting as harvest_grid (real deaths take the
recovery haircut, unresolved pools reported separately), at the validated
cell: observe at 1 minute, 30% trail, 30-minute cap.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "research")
from harvest_grid import boot_ci, features_at, load_bars, run_exit  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
OBS, HORIZON, STYLE = 1, 30, "trail"
# fixed cut-points so buckets mean the same thing across future re-runs,
# rather than sliding with whatever sample happens to be on disk
EDGES = [0.172, 0.30, 0.50, 1.00, 2.00, np.inf]
LABELS = ["17-30%", "30-50%", "50-100%", "100-200%", ">200%"]


def main() -> int:
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    allbars = load_bars(db)
    print(f"unbiased sample: {len(allbars)} pools")

    feats = {p: f for p, bars in allbars.items()
             if (f := features_at(bars, OBS)) is not None}
    fdf = pd.DataFrame(feats).T
    thr_t = fdf.traded_min.quantile(0.66)
    # the live rule's activity filter, held FIXED across buckets so the only
    # thing varying is range
    sel = [p for p in feats
           if feats[p]["traded_min"] >= thr_t
           and feats[p]["range_first"] >= EDGES[0]]
    print(f"qualifying on activity + range floor: {len(sel)}\n")

    rows = []
    for lo, hi, lab in zip(EDGES[:-1], EDGES[1:], LABELS):
        rets, unres, deaths = [], 0, 0
        for pool in sel:
            f = feats[pool]
            if not (lo <= f["range_first"] < hi):
                continue
            r, status = run_exit(allbars[pool], f["i"], f["t_obs"],
                                 f["entry"], HORIZON, STYLE)
            if status == "unresolved":
                unres += 1
                continue
            deaths += status == "dead"
            rets.append(r)
        if not rets:
            continue
        a = np.array(rets)
        ci_lo, ci_hi = boot_ci(a)
        rows.append({"range": lab, "n": len(a), "mean": a.mean(),
                     "ci_lo": ci_lo, "ci_hi": ci_hi, "median": np.median(a),
                     "win": (a > 0).mean(), "2x": (a >= 1.0).mean(),
                     "death": deaths / len(a), "unres": unres})

    out = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(" range      n    mean      95% CI          median   win    2x   death")
    for _, r in out.iterrows():
        print(f" {r['range']:<9} {int(r['n']):>4} {r['mean']:>+7.1%} "
              f"[{r['ci_lo']:>+6.1%},{r['ci_hi']:>+6.1%}] {r['median']:>+8.1%} "
              f"{r['win']:>5.0%} {r['2x']:>5.0%} {r['death']:>6.0%}")

    print("\nverdict:")
    if len(out) >= 3:
        top = out.iloc[-1]
        rest = out.iloc[:-1]
        w = (rest["mean"] * rest["n"]).sum() / rest["n"].sum()
        print(f"  moderate range ({LABELS[0]}..{LABELS[-2]}): {w:+.1%}/trade "
              f"on n={int(rest['n'].sum())}")
        print(f"  extreme range ({LABELS[-1]}):            "
              f"{top['mean']:+.1%}/trade on n={int(top['n'])}")
        if top["mean"] < w and top["ci_hi"] < w:
            print("  -> HUMP-SHAPED: extreme range underperforms; a CEILING "
                  "is justified.")
        elif top["mean"] > w and top["ci_lo"] > 0:
            print("  -> MONOTONIC: extreme range is the best bucket; no "
                  "ceiling, and conviction should SCALE with range.")
        else:
            print("  -> INCONCLUSIVE: buckets overlap within noise. The live "
                  "trade was an anecdote, not evidence. Keep the rule as is.")
    out.to_csv("research/results/range_shape.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

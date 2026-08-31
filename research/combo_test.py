#!/usr/bin/env python3
"""Volume, breadth, or both? Scored on identical coins.

The live journal records every feature the system computed for every
candidate -- traded or skipped -- and a companion job fills in what
happened to each. That makes the journal a shadow test: any combination
of rules can be scored on exactly the same launches, at once, with no
money and no live experiment. Changing the live rule would gain nothing
here and would cost the clean read on the current one.

Rules compared:
  volume    minute-2/minute-1 SOL volume in [1,10)      -- what trades now
  breadth   minute-2/minute-1 distinct BUYERS >= 1.0    -- the new idea
  both      volume AND breadth                          -- stricter
  either    volume OR breadth                           -- looser
  crowd     breadth AND at least 10 buyers in minute 2  -- people, not bots
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

DB = sys.argv[1] if len(sys.argv) > 1 else "data/scalp.db"
MIN_RANGE = 0.172


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main() -> int:
    db = sqlite3.connect(DB)
    df = pd.DataFrame(list(db.execute(
        "SELECT mint, range_frac, accel, vol2, buyers_m1, buyers_m2, "
        "outcome FROM candidate_journal WHERE outcome IS NOT NULL")),
        columns=["mint", "range", "accel", "vol2", "b1", "b2", "ret"])
    print(f"journal rows with a settled outcome: {len(df)}")
    df = df[df["range"] >= MIN_RANGE]
    have_b = df.dropna(subset=["b1", "b2"])
    print(f"  passing the range floor: {len(df)}")
    print(f"  with buyer counts too  : {len(have_b)}")
    if len(have_b) < 25:
        print("\nNot enough coins carry BOTH features yet. Breadth started "
              "recording at 00:40; the dataset completes itself as the "
              "night runs. Re-run this in the morning.")
        if len(df) >= 15:
            v = df[(df.accel >= 1.0) & (df.accel < 10.0)]
            print(f"\ninterim, volume rule only: n={len(v)} "
                  f"2x {(v.ret>=1).mean():.0%} death {(v.ret<=-0.85).mean():.0%} "
                  f"mean {v.ret.mean():+.1%}")
        return 0

    d = have_b.copy()
    d["b_ratio"] = d.b2 / d.b1.clip(lower=1)
    vol = (d.accel >= 1.0) & (d.accel < 10.0)
    bre = d.b_ratio >= 1.0
    crowd = bre & (d.b2 >= 10)
    rules = [("no filter (range only)", pd.Series(True, index=d.index)),
             ("volume  (live rule)", vol),
             ("breadth (new idea)", bre),
             ("both    (stricter)", vol & bre),
             ("either  (looser)", vol | bre),
             ("crowd   (>=10 buyers)", crowd)]
    print(f"\n{'rule':<24} {'n':>4} {'share':>6} {'2x':>16} {'death':>7} "
          f"{'mean':>9}")
    out = []
    for lab, m in rules:
        g = d[m]
        if len(g) < 5:
            print(f"{lab:<24} {len(g):>4}   (too few)")
            continue
        k = int((g.ret >= 1).sum())
        lo, hi = wilson(k, len(g))
        print(f"{lab:<24} {len(g):>4} {len(g)/len(d):>5.0%} "
              f"{k/len(g):>6.0%} [{lo:.0%},{hi:.0%}]  "
              f"{(g.ret<=-0.85).mean():>6.0%} {g.ret.mean():>+8.1%}")
        out.append((lab, len(g), k / len(g), (g.ret <= -0.85).mean(),
                    g.ret.mean()))

    if len(out) >= 3:
        print("\nWhat breadth adds ON TOP of the volume rule:")
        a = d[vol & bre]
        b = d[vol & ~bre]
        for nm, g in [("volume + breadth rising", a),
                      ("volume, breadth falling", b)]:
            if len(g) >= 4:
                print(f"  {nm:<26} n={len(g):>3} 2x {(g.ret>=1).mean():>4.0%} "
                      f"death {(g.ret<=-0.85).mean():>4.0%} "
                      f"mean {g.ret.mean():>+8.1%}")
        if len(a) >= 6 and len(b) >= 6:
            from scipy import stats
            ka, kb = int((a.ret >= 1).sum()), int((b.ret >= 1).sum())
            odds, p = stats.fisher_exact([[ka, len(a) - ka],
                                          [kb, len(b) - kb]])
            print(f"  doubling-rate difference: OR={odds:.2f} p={p:.4f}")
            print("  -> " + ("breadth adds real information; MIX THEM"
                             if p < 0.05 else
                             "no separation yet at this sample size"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

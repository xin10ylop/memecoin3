#!/usr/bin/env python3
"""'Already crashed? Skip it.' -- testing a trader's chart-structure rule.

Two guides describe the same setup: strong hype, rising holders, strong
volume, and a CLEAN CHART. The volume and holder halves are already built.
The chart half is a real gap, and it points at a flaw in the entry rule:
we qualify on RANGE, and a large range includes coins that spiked and
already dumped. "If a coin has been to 200k and its down to 30k its not
worth the added resistances" -- that is precisely what our rule buys.

Two features, both knowable at entry with no lookahead:
  drawdown  how far below the window's high we are entering
  drift     where the entry sits versus where the window opened

Prior work here found early RETURN predicts DEATH, which cuts against the
"staircase upward" advice, so both directions are tested rather than
assumed.
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, "research")
from full_sample_test import MIN_RANGE, entry, load_all, simulate  # noqa: E402


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main() -> int:
    db = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else "data/panel.db",
                         timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    bars = load_all(db)
    rows = []
    for p, b in bars.items():
        f = entry(b)
        if f is None or f["range"] < MIN_RANGE:
            continue
        if not (1.0 <= f["vol_ratio"] < 10.0):
            continue
        w = b.iloc[:2]
        hi = float(np.nanmax(w.h.to_numpy(float)))
        opened = float(w.c.iloc[0])
        px = f["entry_px"]
        if hi <= 0 or opened <= 0 or px <= 0:
            continue
        rows.append({"ret": simulate(b, px),
                     "drawdown": 1 - px / hi,     # 0 = entering at the high
                     "drift": px / opened - 1})   # >0 = up over the window
    df = pd.DataFrame(rows)
    print(f"pools passing range + acceleration: {len(df)}\n")

    print("1. DRAWDOWN at entry -- how far below the window's high we buy")
    print(f"   {'bucket':<16} {'n':>4} {'2x':>16} {'death':>7} {'mean':>9}")
    for lo, hi_e, lab in [(0.0, 0.10, "at the high"),
                          (0.10, 0.30, "10-30% below"),
                          (0.30, 0.60, "30-60% below"),
                          (0.60, 1.01, ">60% below")]:
        g = df[(df.drawdown >= lo) & (df.drawdown < hi_e)]
        if len(g) < 6:
            continue
        k = int((g.ret >= 1).sum())
        cl, ch = wilson(k, len(g))
        print(f"   {lab:<16} {len(g):>4} {k/len(g):>6.0%} [{cl:.0%},{ch:.0%}]  "
              f"{(g.ret<=-0.85).mean():>6.0%} {g.ret.mean():>+8.1%}")

    clean = df[df.drawdown < 0.30]
    crashed = df[df.drawdown >= 0.30]
    print(f"\n   clean chart (<30% off high): n={len(clean):>3} "
          f"2x {(clean.ret>=1).mean():.0%} death {(clean.ret<=-0.85).mean():.0%} "
          f"mean {clean.ret.mean():+.1%}")
    print(f"   already crashed (>=30%):     n={len(crashed):>3} "
          f"2x {(crashed.ret>=1).mean():.0%} "
          f"death {(crashed.ret<=-0.85).mean():.0%} "
          f"mean {crashed.ret.mean():+.1%}")
    if len(clean) >= 8 and len(crashed) >= 8:
        ka, kb = int((clean.ret >= 1).sum()), int((crashed.ret >= 1).sum())
        odds, p = stats.fisher_exact([[ka, len(clean) - ka],
                                      [kb, len(crashed) - kb]])
        print(f"   doubling rate: OR={odds:.2f} p={p:.4f}")
        kd, kc = int((clean.ret <= -0.85).sum()), int((crashed.ret <= -0.85).sum())
        odds2, p2 = stats.fisher_exact([[kd, len(clean) - kd],
                                        [kc, len(crashed) - kc]])
        print(f"   death rate:    OR={odds2:.2f} p={p2:.4f}")

    print("\n2. DRIFT -- 'staircase upward' vs prior finding that early")
    print("   gains predict death")
    print(f"   {'bucket':<16} {'n':>4} {'2x':>7} {'death':>7} {'mean':>9}")
    for lo, hi_e, lab in [(-1.0, -0.10, "down >10%"),
                          (-0.10, 0.10, "flat"),
                          (0.10, 0.50, "up 10-50%"),
                          (0.50, 1e9, "up >50%")]:
        g = df[(df.drift >= lo) & (df.drift < hi_e)]
        if len(g) < 6:
            continue
        print(f"   {lab:<16} {len(g):>4} {(g.ret>=1).mean():>6.0%} "
              f"{(g.ret<=-0.85).mean():>6.0%} {g.ret.mean():>+8.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

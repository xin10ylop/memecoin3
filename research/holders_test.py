#!/usr/bin/env python3
"""Does BREADTH -- how many distinct wallets buy -- beat dollars?

The live filter measures volume, which cannot distinguish fifty people
buying from two bots trading with each other. Traders watch holders for
exactly this reason, and the one rug examined by hand is suggestive:
F7V4a5 had a volume ratio of 1.05 (our filter bought it) and a buyer ratio
of 0.92 (breadth would have refused).

Tested on the candidates the LIVE system actually evaluated tonight, whose
outcomes are now known. Reports whether breadth adds anything BEYOND the
volume filter, since a feature that merely agrees with one already in the
rule is not worth its API calls.

Known limitation, stated rather than hidden: reaching a token's first two
minutes means paging backwards through its history, which is cheap for
tokens that died and expensive for ones that kept trading. Unreachable
tokens are counted and their outcomes compared against the reachable ones,
so the bias is measured rather than assumed.
"""
from __future__ import annotations

import sqlite3
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, "research")
from memebot.data.gt import GeckoTerminal  # noqa: E402
from memebot.data.helius import Helius  # noqa: E402

COST, DEAD_RECOVERY, TRAIL, HORIZON = 0.016, 0.10, 0.30, 30
MAX_POOLS = int(sys.argv[1]) if len(sys.argv) > 1 else 90


def outcome(bars: list, entry_i: int) -> float | None:
    """Same exit rule as everywhere else: 30% trail, 30-minute cap."""
    if len(bars) <= entry_i + 1:
        return None
    entry_px = float(bars[entry_i][4])
    if entry_px <= 0:
        return None
    fwd = bars[entry_i + 1:]
    t0 = fwd[0][0]
    peak = entry_px
    traded = [b[0] for b in fwd if (b[5] or 0) > 0]
    last = max(traded) if traded else t0
    for b in fwd:
        ts, h, low, c = b[0], float(b[2]), float(b[3]), float(b[4])
        if ts > last:
            return DEAD_RECOVERY - 1 - COST
        if (ts - t0) / 60 > HORIZON:
            return c / entry_px - 1 - COST
        peak = max(peak, h)
        if low <= peak * (1 - TRAIL):
            return max(peak * (1 - TRAIL), low) / entry_px - 1 - COST
    return DEAD_RECOVERY - 1 - COST


def main() -> int:
    d = sqlite3.connect("data/scalp.db")
    cands = pd.DataFrame(
        list(d.execute("SELECT mint, ts, range_frac, samples, accel "
                       "FROM candidate_journal WHERE range_frac >= 0.172 "
                       "AND samples >= 3 ORDER BY ts DESC")),
        columns=["mint", "ts", "range", "samples", "accel"])
    print(f"live candidates that passed range+samples: {len(cands)}")
    gt, hel = GeckoTerminal(), Helius()
    rows, unreachable = [], 0
    for _, cnd in cands.iterrows():
        if len(rows) >= MAX_POOLS:
            break
        if time.time() - cnd.ts < 40 * 60:
            continue                     # outcome not yet settled
        try:
            pools = gt.token_pools(cnd.mint)
        except Exception:
            continue
        if not pools:
            continue
        bars = gt.ohlcv(pools[0].address, limit=60)
        if len(bars) < 4:
            continue
        ret = outcome(bars, 1)           # enter at close of minute 2
        if ret is None:
            continue
        who = hel.buyers_per_minute(cnd.mint, since_ts=bars[0][0],
                                    max_pages=25)
        if len(who) < 2 or len(who[0]) == 0:
            unreachable += 1
            rows.append({"mint": cnd.mint, "ret": ret, "accel": cnd.accel,
                         "b1": None, "b2": None})
            continue
        rows.append({"mint": cnd.mint, "ret": ret, "accel": cnd.accel,
                     "b1": len(who[0]), "b2": len(who[1])})

    df = pd.DataFrame(rows)
    ok = df.dropna(subset=["b1", "b2"]).copy()
    print(f"measured: {len(df)} | breadth reachable: {len(ok)} | "
          f"unreachable: {unreachable}")
    if len(df) - len(ok) >= 5 and len(ok) >= 5:
        miss = df[df.b1.isna()]
        print(f"  bias check -- mean return reachable {ok.ret.mean():+.1%} "
              f"vs unreachable {miss.ret.mean():+.1%}")
    if len(ok) < 20:
        print("\ntoo few reachable to conclude anything. The live journal "
              "now records breadth at decision time, when history is "
              "shallow and this problem does not arise.")
        return 0

    ok["b_ratio"] = ok.b2 / ok.b1.clip(lower=1)
    ok["b_tot"] = ok.b1 + ok.b2
    print(f"\n{'feature':<22} {'group':<16} {'n':>4} {'2x':>6} {'death':>7} "
          f"{'mean':>9}")
    for lab, col, thr in [("buyer ratio >= 1.0", "b_ratio", 1.0),
                          ("total buyers >= 15", "b_tot", 15),
                          ("volume accel >= 1.0", "accel", 1.0)]:
        hi_g, lo_g = ok[ok[col] >= thr], ok[ok[col] < thr]
        for nm, g in [("passes", hi_g), ("fails", lo_g)]:
            if len(g) < 3:
                continue
            print(f"{lab:<22} {nm:<16} {len(g):>4} {(g.ret>=1).mean():>5.0%} "
                  f"{(g.ret<=-0.85).mean():>6.0%} {g.ret.mean():>+8.1%}")
        print()

    # the question that matters: does breadth add anything the volume
    # filter has not already captured?
    passed_vol = ok[ok.accel >= 1.0]
    if len(passed_vol) >= 12:
        a = passed_vol[passed_vol.b_ratio >= 1.0]
        b = passed_vol[passed_vol.b_ratio < 1.0]
        print("AMONG pools the volume filter already accepts:")
        for nm, g in [("breadth also rising", a), ("breadth falling", b)]:
            if len(g) >= 3:
                print(f"  {nm:<22} n={len(g):>3} 2x {(g.ret>=1).mean():>4.0%} "
                      f"death {(g.ret<=-0.85).mean():>4.0%} "
                      f"mean {g.ret.mean():>+8.1%}")
        if len(a) >= 5 and len(b) >= 5:
            ka, kb = int((a.ret <= -0.85).sum()), int((b.ret <= -0.85).sum())
            odds, p = stats.fisher_exact([[ka, len(a) - ka],
                                          [kb, len(b) - kb]])
            print(f"  death-rate difference: OR={odds:.2f} p={p:.4f}")
    ok.to_csv("research/results/holders_test.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

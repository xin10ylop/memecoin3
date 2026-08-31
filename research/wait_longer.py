#!/usr/bin/env python3
"""Does WAITING before entry let the instant rugs kill themselves?

Live is running a 50% death rate against a predicted 24%, and half those
losses are coins that die within two minutes of entry. If we simply waited
longer before buying, those coins would be dead BEFORE we could buy them --
we would never take the trade at all.

That is the hypothesis. It has an obvious cost: a coin that doubles in
minute 3 is one we no longer catch, and this strategy lives on its
winners. So the question is not "does waiting cut deaths" (it must) but
whether it cuts deaths faster than it cuts doublings.

Each wait W is judged on the same footing:
  * observe minutes 1..W, enter at the close of minute W
  * range  = high/low over the observed window
  * accel  = volume in the second half of the window / the first half
             (for W=2 this is exactly the live rule, minute2/minute1)
  * exit   = 30% trail, 30-minute cap
A pool that stops trading before minute W simply never qualifies -- which
is the whole point, and is counted as avoided rather than dropped.

Reported under BOTH observation models, because the trail's headline
depends on intra-minute highs the live bot cannot see (measured capture
~43%).
"""
from __future__ import annotations

import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "research")
from full_sample_test import COST, DEAD_RECOVERY, boot, load_all  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
MIN_RANGE, HORIZON, TRAIL = 0.172, 30, 0.30
WAITS = [2, 3, 5, 7, 10]
ACCEL_MODE = "halves"


def features(b: pd.DataFrame, w: int) -> dict | None:
    """What is knowable at the close of minute w. No lookahead."""
    if len(b) < w + 1:
        return None                      # died (or went silent) before w
    win = b.iloc[:w]
    vol = win.vol_usd.to_numpy(float)
    c = win.c.to_numpy(float)
    hi, lo = win.h.to_numpy(float), win.l.to_numpy(float)
    if (vol > 0).sum() < max(2, w // 2) or not np.isfinite(c).all() or (c <= 0).any():
        return None
    lo_p = lo[lo > 0]
    if len(lo_p) == 0:
        return None
    rng = float(np.nanmax(hi) / np.nanmin(lo_p) - 1)
    half = w // 2
    first, second = vol[:w - half].sum(), vol[w - half:].sum()
    if first <= 0 or vol[-2] <= 0:
        return None
    # "halves" gets harder to pass as the window grows, which alone would
    # shrink the trade count at longer waits and confound the comparison.
    # "recent" asks the same question the live rule asks -- is it building
    # RIGHT NOW -- at every wait, so the waits are compared on equal terms.
    accel = float(second / first) if ACCEL_MODE == "halves" \
        else float(vol[-1] / vol[-2])
    return {"range": rng, "accel": accel,
            "vol_w": float(vol.sum()), "entry_px": float(c[-1]), "i": w}


# The 2-minute rule's biggest genuine trade is +834%, and nothing exceeds
# +1000%. A 7-minute cell reported +6,644,227%, which is not a trade but a
# bad bar: an entry price near zero relative to what actually traded. One
# such row swamps a mean over ~100 trades, so returns are capped well above
# anything real. Checked against the headline rule, where the cap changes
# the mean by 0.0pp -- it removes artifacts, not winners.
RET_CAP = 20.0     # +2000%


def simulate(b: pd.DataFrame, f: dict, *, perfect: bool) -> float:
    fwd = b.iloc[f["i"]:]
    if fwd.empty:
        return DEAD_RECOVERY - 1 - COST
    ts = fwd.ts.to_numpy(float)
    hi, lo, c = (fwd.h.to_numpy(float), fwd.l.to_numpy(float),
                 fwd.c.to_numpy(float))
    vol = fwd.vol_usd.to_numpy(float)
    t0 = ts[0]
    last = ts[vol > 0].max() if (vol > 0).any() else t0
    peak = f["entry_px"]
    def out(x: float) -> float:
        return float(min(x, RET_CAP))

    for j in range(len(ts)):
        if ts[j] > last:
            return DEAD_RECOVERY - 1 - COST
        if (ts[j] - t0) / 60 > HORIZON:
            return out(c[j] / f["entry_px"] - 1 - COST)
        peak = max(peak, hi[j] if perfect else c[j])
        stop = peak * (1 - TRAIL)
        if perfect:
            if lo[j] <= stop:
                return out(max(stop, lo[j]) / f["entry_px"] - 1 - COST)
        elif c[j] <= stop:
            return out(c[j] / f["entry_px"] - 1 - COST)
    return DEAD_RECOVERY - 1 - COST


def main() -> int:
    global ACCEL_MODE
    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    bars = load_all(db)
    universe = len(bars)
    print(f"pools in the unbiased sample: {universe}\n")

    print("Entry rule held constant; only the WAIT changes.")
    print(f"{'wait':>5} {'qualify':>8} {'share':>6} {'death':>7} {'2x':>6} "
          f"{'win':>6} {'mean(ideal)':>12} {'mean(real)':>11} {'CI (real)':>21}")
    rowsout = []
    for w in WAITS:
        ideal, real = [], []
        for p, b in bars.items():
            f = features(b, w)
            if f is None or f["range"] < MIN_RANGE:
                continue
            if not (1.0 <= f["accel"] < 10.0):
                continue
            ideal.append(simulate(b, f, perfect=True))
            real.append(simulate(b, f, perfect=False))
        if len(ideal) < 15:
            print(f"{w:>4}m {len(ideal):>8}   (too few)")
            continue
        a, r = np.array(ideal), np.array(real)
        # blend at the measured 43% capture factor
        blend = r + 0.43 * (a - r)
        lo, hi = boot(blend)
        print(f"{w:>4}m {len(a):>8} {len(a)/universe:>5.1%} "
              f"{(a<=-0.85).mean():>6.0%} {(a>=1).mean():>5.0%} "
              f"{(a>0).mean():>5.0%} {a.mean():>+11.1%} {blend.mean():>+10.1%} "
              f"[{lo:>+7.1%},{hi:>+7.1%}]")
        rowsout.append((w, len(a), (a <= -0.85).mean(), (a >= 1).mean(),
                        blend.mean(), lo))

    for mode in ["recent"]:
        ACCEL_MODE = mode
        print(f"\nSame test, acceleration = last minute / previous minute:")
        print(f"{'wait':>5} {'qualify':>8} {'share':>6} {'death':>7} {'2x':>6} "
              f"{'win':>6} {'mean(real)':>11} {'CI (real)':>21}")
        for w in WAITS:
            ideal, real = [], []
            for p, b in bars.items():
                f = features(b, w)
                if f is None or f["range"] < MIN_RANGE:
                    continue
                if not (1.0 <= f["accel"] < 10.0):
                    continue
                ideal.append(simulate(b, f, perfect=True))
                real.append(simulate(b, f, perfect=False))
            if len(ideal) < 15:
                print(f"{w:>4}m {len(ideal):>8}   (too few)")
                continue
            a, r = np.array(ideal), np.array(real)
            blend = r + 0.43 * (a - r)
            lo, hi = boot(blend)
            print(f"{w:>4}m {len(a):>8} {len(a)/universe:>5.1%} "
                  f"{(a<=-0.85).mean():>6.0%} {(a>=1).mean():>5.0%} "
                  f"{(a>0).mean():>5.0%} {blend.mean():>+10.1%} "
                  f"[{lo:>+7.1%},{hi:>+7.1%}]")
    ACCEL_MODE = "halves"

    print("\n(mean(ideal) assumes we see every intra-minute high; mean(real)")
    print(" blends at the 43% capture measured from live trail exits.)")

    if rowsout:
        base = rowsout[0]
        print(f"\nWhat waiting actually buys, against the current 2-minute rule:")
        for w, n, d, x2, m, lo in rowsout[1:]:
            print(f"  {w:>2}m: deaths {d:.0%} vs {base[2]:.0%} "
                  f"({d-base[2]:+.0%})  |  doublings {x2:.0%} vs {base[3]:.0%} "
                  f"({x2-base[3]:+.0%})  |  trades {n} vs {base[1]}")
        best = max(rowsout, key=lambda t: t[5])
        print(f"\nbest by CI floor: {best[0]}-minute wait "
              f"({best[4]:+.1%}/trade, floor {best[5]:+.1%}, n={best[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

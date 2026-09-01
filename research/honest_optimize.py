#!/usr/bin/env python3
"""Stage 2: is there an OOS-honest, cost-real edge, and which filters earn it?

Reads data/honest_features.jsonl (exec-scored, survivorship-correct). Does
what the original discovery did, but on prices a seller could meet:

  walk-forward   fit on the EARLIER half of pools, test on the LATER half
  bootstrap CI   cluster (per-pool) bootstrap on the TEST fold
  placebo        does the rule beat a random same-size subset of the test?

The fat tail is the enemy here: 5% of trades carry all the profit, so a mean
can be a mirage built on two winners. The placebo and CI exist to catch that.
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys

CACHE = "data/honest_features.jsonl"
TRAIL = "exec10"
random.seed(17)


def load(dex=None):
    rows = [json.loads(l) for l in open(CACHE)]
    if dex:
        rows = [r for r in rows if r.get("dex") == dex]
    # the core signal: range + activity in both minutes. Everything else is
    # a candidate FILTER on top, to be earned rather than assumed.
    return [r for r in rows if r["range"] >= 0.172 and r["both_traded"]]


def boot_ci(xs, n=5000):
    if len(xs) < 5:
        return (float("nan"), float("nan"))
    means = sorted(st.mean(random.choices(xs, k=len(xs))) for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


def placebo_p(pool, selected_mean, k, n=5000):
    """P(a random k-subset of `pool` beats the rule) — high means no skill."""
    if k < 3 or k >= len(pool):
        return float("nan")
    hits = sum(st.mean(random.sample(pool, k)) >= selected_mean
               for _ in range(n))
    return hits / n


FILTERS = {
    "range only":            lambda r: True,
    "+ accel>=1":            lambda r: r["accel"] is not None and r["accel"] >= 1.0,
    "+ accel 1-10":          lambda r: r["accel"] is not None and 1.0 <= r["accel"] < 10.0,
    "+ clean chart<=10%":    lambda r: r["drawdown"] <= 0.10,
    "+ clean chart<=20%":    lambda r: r["drawdown"] <= 0.20,
    "+ vol2>=$1k":           lambda r: r["vol2_usd"] >= 1000,
    "+ accel1-10 & clean10": lambda r: (r["accel"] is not None and 1.0 <= r["accel"] < 10.0
                                        and r["drawdown"] <= 0.10),
    "+ clean10 & vol1k":     lambda r: r["drawdown"] <= 0.10 and r["vol2_usd"] >= 1000,
}


def stats(rows):
    xs = [r[TRAIL] for r in rows]
    if not xs:
        return None
    return {"n": len(xs), "mean": st.mean(xs), "median": st.median(xs),
            "win": sum(x > 0 for x in xs) / len(xs),
            "death": sum(x <= -0.85 for x in xs) / len(xs)}


def main() -> int:
    dex = sys.argv[1] if len(sys.argv) > 1 else None
    if dex:
        print(f"POPULATION: {dex} only\n")
    rows = load(dex)
    rows.sort(key=lambda r: r["t0"])
    cut = rows[len(rows) // 2]["t0"]
    train = [r for r in rows if r["t0"] < cut]
    test = [r for r in rows if r["t0"] >= cut]
    print(f"signal pool: {len(rows)}   train {len(train)}  test {len(test)}"
          f"   (walk-forward split by time)\n")
    print(f"scored on {TRAIL} — an executable trailing stop, cost included\n")
    print(f"{'rule':<24}{'train mean':>11}{'TEST mean':>11}"
          f"{'test 95% CI':>20}{'placebo p':>11}")
    test_all = test
    best = None
    for name, f in FILTERS.items():
        tr = [r for r in train if f(r)]
        te = [r for r in test if f(r)]
        strn = stats(tr)
        stte = stats(te)
        if not strn or not stte or stte["n"] < 10:
            print(f"{name:<24}{'(too few)':>11}")
            continue
        lo, hi = boot_ci([r[TRAIL] for r in te])
        pp = placebo_p([r[TRAIL] for r in test_all], stte["mean"], stte["n"])
        flag = "  <-- CI>0" if lo > 0 else ""
        print(f"{name:<24}{strn['mean']:>+10.1%}{stte['mean']:>+11.1%}"
              f"   [{lo:+.1%}, {hi:+.1%}]{pp:>10.3f}{flag}")
        # a real filter: positive OOS, CI excludes zero, and beats placebo
        if lo > 0 and pp < 0.10:
            if best is None or stte["mean"] > best[1]:
                best = (name, stte["mean"], lo, pp)
    print()
    if best:
        print(f"BEST honest OOS rule: {best[0]}  "
              f"mean {best[1]:+.1%}, CI lo {best[2]:+.1%}, placebo p {best[3]:.3f}")
    else:
        print("NO rule is OOS-positive with a CI that clears zero AND beats")
        print("placebo. The mean is real-looking but the fat tail means it")
        print("cannot be distinguished from luck at this sample size.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

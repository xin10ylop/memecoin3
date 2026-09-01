# Honest re-discovery on executable scoring

Every prior number in this project was scored on bar HIGHS — peaks a live
bot cannot sell into, which overstate this population's return by ~47pp
(`research/peak_reality.py`). This re-runs discovery on an **executable**
trailing stop (peak armed only once a bar has CLOSED, fill from the next bar)
with survivorship-correct fate, then validates walk-forward OOS with a
per-pool bootstrap CI and a placebo control.

Tooling: `research/honest_backtest.py` (extract) → `research/honest_optimize.py`.

## Result on the LIVE population (pumpswap = pump.fun migrations)

Signal = range ≥17.2% + traded in both first minutes. 991 pools, split by
time into 495 train / 496 test. Exit = 10% executable trail, 1.6% cost.

| rule | train | **TEST (OOS)** | test 95% CI | placebo p |
|---|---|---|---|---|
| range only | +36.9% | **+53.5%** | [+24%, +102%] | — |
| + acceleration 1–10 | +35.7% | +60.0% | [+13%, +146%] | 0.53 (weak) |
| **+ clean chart ≤10%** | +51.3% | **+80.8%** | [+34%, +154%] | **0.000** |

**The clean-chart filter (enter within 10% of the 2-min high) carries the
edge on migrations. Acceleration does NOT** (placebo 0.5 — indistinguishable
from random; it was carried by the harvest population, not this one).

## Robustness of range + clean-chart on pumpswap (n=621)

- **Both time-halves independently positive**: early +51% CI[+19,+92],
  late +81% CI[+35,+158]. Not a regime tailwind.
- **Survives dropping the top 3 winners**: +66% → +39.6%.
- **Median +12.2%, win rate 67%** — not a fat-tail lottery; most trades win.
- ~93 qualifying candidates/day. No scarcity.

## Why the live paper ledger was −21% and this is not a contradiction

1. The 23 live trades were taken with the clean-chart filter **OFF**
   (MEMEBOT_MAX_DRAWDOWN=1.0 for most of the run) — they do not test this
   rule. The filter is now restored to the validated default.
2. n=18–23 with a fat tail cannot contradict an n=621 result: an 18-trade
   sample sits at −20% at its 5th percentile even when the true mean is
   +36% (`research/wick_census.py` bootstrap).

## The ONE remaining risk: execution, not signal

The panel scores fills at the stop price. It cannot model slippage, latency,
or the ~43% intra-minute capture factor a 2s-polling bot suffers. So +66% is
an **upper bound on price observation** that still assumes clean fills. The
gap between it and realized P&L is pure execution, and the live paper run —
now correctly configured with clean-chart ON — is the only test of it.

## Verdict

For the first time the edge is: honestly scored, OOS-positive with a CI that
clears zero, present in both time-halves, robust to the fat tail, on the
ACTUAL live population, and with a positive median. It is not proven live —
execution is untested — but it is a real, stress-tested signal, and the live
run is now pointed at exactly the right rule to test transfer.

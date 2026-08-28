## Liquidity-floor sweep — universe widening vs edge retention (re-run on current DB, 918 pools, B tail through 15:29 UTC)

**Method (3 lines).** `load_panel(min_max_reserve=6500)` → 918 pools, features via `add_features`; entry-eligible bar = reserve≥floor ∧ fdv∈[100k,30M] ∧ vol_h1≥volfloor ∧ age 15–2880m ∧ ts≥first_seen+120s; forward 60m = close→close+60 with terminal price at data end (deaths count). Net fwd = gross − [2·(80bps + clip/(reserve/2)) + $0.20/clip] at clip=max($5, 0.0025·reserve) (constant 50bps/side impact); every CI is a 2000-draw cluster bootstrap by token (base_mint). Backtests: `run_backtest(regime_gated, min_liq=floor, CostModel(), entry_lag=2)`, `UNIVERSE_VOL_H1_MIN` monkeypatched for vol-floor variants; windows split at ts=1787860000 (A cool, snapshot coverage 0.079d≈1.9h; B hot, 0.322d≈7.7h effective — the collector ran ~6-min cadence much of B and was DOWN 12:15–15:28 UTC, so B's 16.5h wall-clock span holds only 7.7h of data; trades/day uses coverage denominators → aggressive extrapolation).

### (a)+(b) Eligible universe + cluster-bootstrapped forward 60m returns

| floor | vol_h1 | win | tokens | elig bars | tok-hrs/day | fwd60 gross [CI] | fwd60 net-of-cost [CI] |
|---|---|---|---|---|---|---|---|
| ≥8k | 10k | A | 44 | 1,064 | 224 | +5.3% [−14.3, +25.9] | +2.7% [−17.0, +21.7] |
| ≥8k | 10k | B | 245 | 3,719 | 192 | +12.5% [+4.9, +19.7] | +9.8% [+1.7, +16.7] |
| ≥10k | 10k | B | 244 | 3,714 | 192 | +12.5% [+5.0, +19.3] | +9.8% [+2.1, +17.2] |
| ≥15k | 10k | B | 243 | 3,709 | 192 | +12.4% [+5.3, +19.1] | +9.7% [+1.9, +16.8] |
| ≥25k | 10k | B | 242 | 3,652 | 189 | +11.0% [+3.5, +17.8] | +8.3% [+0.9, +15.3] |
| ≥8k | 5k | B | 283 | 3,931 | 203 | +12.4% [+5.2, +18.9] | +9.6% [+3.1, +16.5] |
| ≥15k | 5k | B | 281 | 3,913 | 202 | +12.4% [+5.3, +18.9] | +9.7% [+2.7, +16.1] |
| ≥25k | 5k | B | 280 | 3,856 | 199 | +11.0% [+4.1, +17.5] | +8.3% [+1.0, +14.8] |

Window A at every config: 44–47 tokens, gross ≈ +5–6%, net ≈ +3%, all CIs straddle 0 — per-bar edge is a hot-window (B) phenomenon only. Marginal reserve bands (B, vol 10k): [8k,10k) 2 tokens / 5 bars, [10k,15k) 2 / 5, [15k,25k) 11 / 57 — all **insufficient data** (<15 tokens).

**Why the floor barely binds** — gate attribution among age/seen-qualified bars with reserve∈[8k,25k), window B: 476 bars / 60 tokens; **84% (401) fail fdv<100k** (fresh graduates under the FDV floor), 8 more fail only vol_h1; just **67 bars / 13 tokens pass everything** (<15 → insufficient; their raw bar-mean fwd60 ≈ +94%, a couple of post-graduation moonshots). Reserve percentiles of fully-eligible bars (B): p1=21.8k, p5=29.0k, p10=32.0k, p50=84.5k; only **2.0%** of eligible bars sit below 25k (A: 0.2%). The pre-registered fdv≥100k live-parity gate, not min_liq, is the binding constraint below ~25k.

### (c) regime_gated backtests (min_cohort_mom 0.02, default exits, $1k book, max_concurrent 4)

| min_liq | vol | risk$ | win | trades | tr/day | tokens | expectancy | CI (cluster) | total pnl |
|---|---|---|---|---|---|---|---|---|---|
| 8k | 10k | 10 | A | 11 | 139 | 11 | +0.127 | insufficient (<15 tok) | +$14.0 |
| 8k | 10k | 10 | B | 118 | 366 | 115 | +0.076 | [+0.023, +0.141] | +$89.8 |
| 10k | 10k | 10 | B | 116 | 360 | 113 | +0.076 | [+0.025, +0.144] | +$88.3 |
| 15k | 10k | 10 | B | 116 | 360 | 113 | +0.076 | [+0.023, +0.138] | +$88.3 |
| 25k | 10k | 10 | B | 114 | 354 | 111 | +0.076 | [+0.024, +0.140] | +$86.2 |
| 8k | 5k | 10 | B | 125 | 388 | 122 | +0.075 | [+0.026, +0.133] | +$94.2 |
| 15k | 5k | 10 | B | 123 | 382 | 120 | +0.073 | [+0.023, +0.136] | +$90.3 |
| 25k | 5k | 10 | B | 121 | 376 | 118 | +0.073 | [+0.021, +0.135] | +$88.1 |
| 15k | 10k | 25 | B | 116 | 360 | 113 | **+0.088** | [+0.032, +0.159] | **+$254.1** |
| 25k | 10k | 25 | B | 114 | 354 | 111 | +0.087 | [+0.030, +0.155] | +$248.2 |

Window A is identical across all floors (same 11 trades / 11 tokens — insufficient): +$14.0 at vol 10k, +$1.2 at vol 5k, +$38.6 at $25 clip. Sizing: `max_pool_share=0.005` **never binds** (min eligible reserve p1≈22k → cap ≥$109 ≥ $25), so the $10 clip for low floors buys nothing and costs ~1.2pts of expectancy in pure flat-fee drag ($0.30 on 3 tx = 3% of a $10 clip vs 1.2% of $25: 0.088 vs 0.076). A $25 clip at floor 8k would behave like 15k — the eligible sets are 98% identical.

### VERDICT
- **Dead end: lowering min_liq 15k→8k (or 10k).** Widens B by 2 tokens / 10 bars / 2 trades (116→118, +1.7%) at unchanged expectancy (0.076 at all four floors) — because fdv≥100k + vol_h1≥10k already imply reserve≳25k for 98% of eligible bars. No opportunity multiplication exists on this axis.
- **Sweet spot: min_liq 15k (25k indistinguishable), risk $25, vol_h1 10k** — B: 116 trades, expectancy +0.088 [ci_lo +0.032], +$254. 25k trims per-bar gross slightly (11.0% vs 12.4%) with identical backtest results; no evidence to move off the pre-registered 15k. Do NOT pair low floors with $10 clips — flat fees eat 1.2pts.
- **Marginal candidate: vol_h1 10k→5k.** +38 eligible tokens (+15.5%) and +7 trades (+6%) in B at flat per-bar net (+9.6% vs +9.8%) and near-flat expectancy (0.075 vs 0.076, ci_lo 0.026 vs 0.023) — total B return 125×0.075=9.4R vs 116×0.076=8.8R, +7% aggregate. Real but small widening at no measured edge cost; window A on 11 trades flips +$14.0→+$1.2 (insufficient to judge). Worth carrying as a variant in paper forward, not a config change yet.
- **Insufficient data / real follow-up: the fdv<100k fresh-graduate band.** 84% of sub-25k-reserve qualified bars are blocked by the FDV floor, and the 13 tokens that do pass in [8k,25k) show ~+94% mean fwd60. That is where widening actually lives — but relaxing fdv≥100k changes the pre-registered live-parity gate: new hypothesis, needs its own pre-registration + more windows.
- Caveats: all measurable edge is window-B-only (A CIs straddle 0; A backtests = 11 tokens); regime_gated itself is NOT validated vs the random-entries placebo (research/results/REPORT.md); trades/day extrapolates from 7.7h of hot-tape coverage (collector at ~6-min cadence in B plus a 3.2h outage 12:15–15:28 UTC), so treat 350–390/day as an upper bound on rate, not a forecast.

Note: this supersedes the numbers in /home/user/memecoin3/research/mining/universe-width.md (prior iteration, pre-outage panel: 890 pools, 12 A-trades); B-window conclusions are unchanged. Artifacts: script /tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/floor_sweep2.py, results /tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/floor_sweep_results2.json, log floor_sweep2.log (same dir).
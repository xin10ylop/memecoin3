All computations complete. Assembling the report.

## Liquidity-floor sweep — universe widening vs edge retention

**Method (3 lines).** Loaded panel (`load_panel(min_max_reserve=6500)` → 890 pools), features via `add_features`; entry-eligible bar = reserve≥floor ∧ fdv∈[100k,30M] ∧ vol_h1≥volfloor ∧ age 15–2880m ∧ ts≥first_seen+120s. Forward 60m returns use next-60-bar close with terminal price at data end (deaths count); net = gross − [2·(80bps + clip/(reserve/2)) + $0.20/clip] at clip=max($5, 0.0025·reserve) (constant 50bps/side impact); all CIs are 2000-draw cluster bootstraps by token (base_mint). Backtests: `run_backtest(regime_gated, min_liq=floor, CostModel())`, `UNIVERSE_VOL_H1_MIN` monkeypatched for the 5k variant; windows split at ts=1787860000 (A: 08-27, snapshot coverage 0.079d ≈1.9h; B: 08-28, 0.315d ≈7.6h — trades/day uses these coverage denominators, so extrapolations are aggressive).

### (a)+(b) Eligible universe and forward 60m returns per floor (vol_h1≥10k unless noted)

| floor | win | tokens | elig bars | tok-hrs/day | fwd60 gross [CI] | fwd60 net-of-cost [CI] |
|---|---|---|---|---|---|---|
| ≥8k | A | 44 | 1,064 | 224 | +5.4% [−14.9, +25.7] | +2.7% [−16.7, +23.1] |
| ≥8k | B | 242 | 3,695 | 195 | +12.1% [+4.4, +19.2] | +9.4% [+1.8, +16.9] |
| ≥10k | B | 241 | 3,690 | 195 | +12.1% [+4.7, +19.1] | +9.4% [+1.8, +16.7] |
| ≥15k | B | 240 | 3,685 | 195 | +12.1% [+4.5, +19.0] | +9.4% [+1.3, +16.5] |
| ≥25k | B | 240 | 3,634 | 192 | +10.8% [+3.6, +17.5] | +8.1% [+0.9, +14.9] |
| ≥8k, vol 5k | B | 278 | 3,898 | 206 | +12.0% [+5.1, +18.6] | +9.3% [+2.3, +15.7] |
| ≥25k, vol 5k | B | 276 | 3,829 | 202 | +10.9% [+4.1, +17.6] | +8.2% [+1.6, +14.8] |

Window A across all configs: 44–47 tokens, fwd60 ≈ +5–6% gross / +3% net, CI straddles 0 — no measurable per-bar edge in the cool window; positive edge is a hot-window (B) phenomenon, matching the regime-factor finding.

**Why the floor barely moves anything** — marginal-band diagnostic (age/seen-qualified bars, both windows): reserve∈[8k,25k) has 520 bars / 68 tokens, of which **86.3% fail fdv<100k** (fresh graduates below the fdv floor), 10.6% fail vol_h1<10k; only **63 bars / 13 tokens pass all gates** (<15 → insufficient data; their bar-mean fwd60 ≈ +91% implied, driven by a couple of post-graduation moonshots). Reserve percentiles of fdv+vol-eligible bars: p1=23k, p5=30k, p10=33k, p50=116k; only **1.5%** of eligible bars sit below 25k reserve. The fdv≥100k live-parity gate, not min_liq, is the binding constraint below ~25k.

### (c) regime_gated backtests (min_cohort_mom=0.02, default exits, entry_lag=2)

| min_liq | vol | risk$ | win | trades | tr/day | tokens | expectancy | CI | total pnl |
|---|---|---|---|---|---|---|---|---|---|
| 8k | 10k | 10 | A | 12 | 152 | 12 | +0.098 | insufficient (<15 tok) | +$11.7 |
| 8k | 10k | 10 | B | 118 | 374 | 115 | +0.076 | [+0.023, +0.141] | +$89.8 |
| 10k | 10k | 10 | B | 116 | 368 | 113 | +0.076 | [+0.022, +0.146] | +$88.3 |
| 15k | 10k | 10 | B | 116 | 368 | 113 | +0.076 | [+0.023, +0.141] | +$88.3 |
| 25k | 10k | 10 | B | 114 | 362 | 111 | +0.076 | [+0.024, +0.140] | +$86.2 |
| 8k | 5k | 10 | B | 125 | 396 | 122 | +0.075 | [+0.024, +0.138] | +$94.2 |
| 25k | 5k | 10 | B | 121 | 384 | 118 | +0.073 | [+0.022, +0.135] | +$88.1 |
| 15k | 10k | 25 | B | 116 | 368 | 113 | **+0.088** | [+0.033, +0.158] | +$254.1 |
| 25k | 10k | 25 | B | 114 | 362 | 111 | +0.087 | [+0.033, +0.153] | +$248.2 |

Window A at all configs: identical 12 trades (12 tokens, insufficient), −$1.1 at vol 5k / +$11.7 at vol 10k per $10 clip. Sizing note: `max_pool_share=0.005` never binds here (min eligible reserve ≈25k → cap ≥$125), so cutting risk_per_trade to $10 buys nothing and **costs ~1.2pts of expectancy** in pure flat-fee drag ($0.30/trade on 3 tx = 3% of a $10 clip vs 1.2% of $25).

### VERDICT
- **Dead end: lowering min_liq 15k→8k.** The universe widens by ~2 tokens / 5 bars (B) because fdv≥100k+vol_h1 already implies reserve≥~25k for 98.5% of eligible bars. Trades: 116→118/window B (+1.7%), expectancy unchanged (0.076). Nothing gained, and the $10 clip it was paired with actively degrades expectancy vs $25.
- **Sweet spot: min_liq 15k (or 25k — indistinguishable), risk $25, vol_h1 10k.** 25k trims the gross per-bar edge slightly (10.8% vs 12.1%, excluding a few explosive fresh-graduate bars) but per-trade backtest results are identical within noise; keep 15k as the pre-registered value — no evidence to move it either way.
- **Marginal candidate: vol_h1 floor 10k→5k.** +36 eligible tokens (+15%), +7 trades (+6%) in B at flat expectancy (0.075 vs 0.076, ci_lo 0.024 vs 0.023) and flat net fwd60 (+9.3% vs +9.4%). Real but small widening at no measured edge cost; window A flips from +$11.7 to −$1.1 on 12 trades (insufficient to judge).
- **Insufficient data / follow-up: the fdv<100k fresh-graduate band.** The only place real widening lives is below the fdv floor (449 of 520 sub-25k-reserve bars are blocked by it); the 13 tokens that do pass in 8k–25k show huge but unquantifiable returns. Testing a lower fdv floor would be a change to the pre-registered live-parity gate — new hypothesis, needs its own pre-registration and more collection windows.
- Caveats: all edge is window-B-only (A CIs straddle 0, 12-token backtests), regime_gated remains NOT VALIDATED vs placebo per research/results/REPORT.md, and trades/day figures extrapolate from 7.6h of hot-tape coverage.

Artifacts: raw numbers in `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/floor_sweep_results.json`, script `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/floor_sweep.py`.
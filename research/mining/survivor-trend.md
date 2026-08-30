# Survivor Cohort: is there a tradable long edge in established memecoins?

**Method (3 lines).** Worked directly off raw `ohlcv` — every row there is a **real traded minute** (verified: 0 of 832,153 rows have `vol_usd<=0`), so no continuous-grid resting prices ever enter a return; cleaning dropped 286 glitch prints (>50x from centred 5-bar median) and 1,575 bars disagreeing >10x with the independent `snapshots` price feed (rebased-denomination segments), leaving **830,292 traded minutes / 5,871 pools**. Every reported return is **VERIFIED**: exit bar is a real traded bar within ±2 min of the horizon **AND** ≥10 traded minutes exist after it; failures are counted and reported, never filled. Entries are point-in-time (reserve from the last `snapshots` row at-or-before entry, ≤6h stale; age from `pool_created_at`), P&L is net via `memebot.backtest.costs.CostModel` at a $100 clip (0.8%/side + `clip/(reserve/2)` impact + $0.10/tx), CIs are 4,000-draw cluster bootstraps by `base_token_address` (and, shown alongside, by entry-hour).

## Cohort and its hard data limits

| item | value |
|---|---|
| pools in `pools` / with ≥1 traded bar | 46,501 / 5,871 |
| **point-in-time reserve exists only from** | `snapshots` min ts **1787841443** (2026-08-27T14:37Z) — nothing earlier is investable |
| entry window for 24h holds | 1787841600 → 1788003300 = **45h = 1.87 independent 24h periods** |
| survivor cohort (age≥24h, PIT reserve≥$50k, ≥10 traded min in last hour) | **101 pools / 77 tokens ever**; mean 29 qualify per hour (median 30, max 60, min 0) |
| cohort composition (representative hour, n=27) | reserve median **$1.95M** (p10 $421k, p90 $9.7M); FDV median **$711M** (p10 $20M); age median **588 days** |

**Window A (ts<1787860000) contains only the first 5 entry hours** — it is reported below but is thin by construction. Window B is everything else; there is no newer window (data ends 1788089700). This is the single biggest limitation: **~1.9 independent 24-hour periods**. Entry-hour CIs treat 41–61 *overlapping* hours as clusters and are therefore optimistically narrow; the token-clustered CI is the one to believe.

## 1. BENCHMARK FIRST — buy & hold the survivor cohort (hourly entries, equal weight)

| horizon | candidates | VERIFIED | **DISCARDED** | no vol at horizon | pool ended | tokens | NET mean, CI(token) | CI(entry-hour) | NET median | win% | gross mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 6h | 1,891 | 1,541 | **350 (18.5%)** | 334 | 16 | 59 | **−2.16%** [−4.08, −0.21] | [−3.01, −1.26] | −2.01% | 21.3 | −0.28% |
| 12h | 1,758 | 1,130 | **628 (35.7%)** | 608 | 20 | 54 | −1.47% [−5.38, +3.23] | [−2.88, −0.13] | −1.98% | 25.0 | +0.42% |
| 24h | 1,370 | 876 | **494 (36.1%)** | 477 | 17 | 40 | −4.21% [−10.33, +1.98] | [−6.31, −1.76] | −4.14% | 18.8 | −2.38% |
| 24h, reserve≥$250k | 1,064 | 737 | **327 (30.7%)** | 314 | 13 | 33 | **−4.28%** [−7.15, −2.70] | [−5.71, −2.68] | −3.71% | 19.3 | −2.51% |

Window split, 24h: A n=143, 23 tokens, **−7.98%** [−12.68, −4.94]; B n=733, 38 tokens, −3.48% [−10.80, +3.60]. At reserve≥$250k: A −8.34% [−13.21, −5.38] (22 tok), B −3.35% [−6.24, −1.55] (31 tok). At 6h: A −4.37% [−9.80, −1.00] (41 tok), B −1.74% [−3.63, +0.60] (58 tok).

**The average established token loses money over 24h.** Median is negative at every horizon and only ~19–25% of holds are profitable. Costs are not the cause — gross 24h drift is already −2.4%, and cost sensitivity is flat because these pools are deep:

| clip | mean side cost | NET mean 24h, CI(token) | NET median |
|---|---|---|---|
| $25 | 0.81% | −4.75% [−10.87, +1.64] | −4.73% |
| $100 | 0.84% | −4.21% [−10.31, +2.16] | −4.14% |
| $200 | 0.88% | −4.19% [−10.28, +2.17] | −4.06% |
| $100, cost ×2 stress | — | −6.02% [−12.11, −0.25] | — |
| $100, cost ×3 stress | — | −7.79% [−13.80, −2.12] | — |

Drift by entry block (24h hold, hourly entries bucketed to 6h):

| entry block (UTC) | n | tok | mean | median |
|---|---|---|---|---|
| 08-27 12:00 | 76 | 20 | −6.99% | −5.04% |
| 08-27 18:00 | 163 | 25 | −8.81% | −6.57% |
| 08-28 00:00 | 128 | 22 | −11.72% | −5.93% |
| 08-28 06:00 | 58 | 18 | −10.74% | −9.80% |
| 08-28 12:00 | 94 | 20 | −4.88% | −2.92% |
| 08-28 18:00 | 164 | 22 | +0.60% | −0.41% |
| 08-29 00:00 | 120 | 19 | +1.62% | −0.91% |
| 08-29 06:00 | 73 | 14 | +7.79% | −0.55% *(insufficient: <15 tokens)* |

Every block's **median** is negative. The two positive means are outlier-driven (see §4).

**The narrative's "$10M→$100M leg" is not there.** Forward 24h VERIFIED net return by entry FDV/age/reserve bucket (n=876 verified, 494 discarded):

| bucket | n | tok | mean | CI(token) | median | win% |
|---|---|---|---|---|---|---|
| FDV <$10M | 124 | 12 | — | INSUFFICIENT DATA | — | — |
| **FDV $10–100M** | 209 | **15** | **−4.41%** | [−7.4, −0.4] | **−7.72%** | 25.4 |
| FDV $100M–1B | 144 | 8 | — | INSUFFICIENT DATA | — | — |
| FDV >$1B | 399 | 5 | — | INSUFFICIENT DATA | — | — |
| age 24h–3d | 35 | 3 | — | INSUFFICIENT DATA | — | — |
| age 3–30d | 70 | 7 | — | INSUFFICIENT DATA | — | — |
| age >30d | 771 | 31 | −4.88% | [−8.6, −3.3] | −3.54% | 16.6 |
| reserve $50–250k | 139 | 9 | — | INSUFFICIENT DATA | — | — |
| reserve $250k–2M | 335 | 20 | −4.61% | [−10.4, −1.2] | −4.51% | 18.8 |
| reserve >$2M | 402 | 17 | −4.01% | [−6.4, −2.6] | −3.32% | 19.7 |

## 2. Artifact control — where the +46%/trade illusion actually lived

Identical pipeline, only the age gate moved. The gap is the difference between the mandated verified exit and the resting-price ("last close carried forward") exit.

| cohort | candidates | verified | discard% | tok | VERIFIED mean 24h | NAIVE (resting-price) mean | **gap** |
|---|---|---|---|---|---|---|---|
| age≥0h, reserve≥$50k | 1,761 | 898 | 49.0 | 43 | −3.30% [−8.9, +2.7] | **+65.6%** | **+68.9pp** |
| age≥6h, reserve≥$50k | 1,433 | 883 | 38.4 | 40 | −3.95% [−10.2, +2.3] | **+82.2%** | **+86.2pp** |
| **age≥24h, reserve≥$50k (this cohort)** | 1,370 | 876 | 36.1 | 40 | −4.21% [−10.4, +1.7] | −3.9% | **+0.3pp** |
| age≥24h, reserve≥$250k | 1,064 | 737 | 30.7 | 33 | −4.28% [−7.0, −2.7] | −3.3% | +1.0pp |

The measurement artifact is **entirely a young/thin-pool phenomenon**. Inside the survivor cohort the honest and dishonest measurements agree — and both say the drift is negative. The verification requirement still discards **36%** of candidate holds, but the discards are not adversely selected here: discarded observations' resting-price returns (mean −3.3%, median −1.9% at 24h) are no worse than kept ones (−4.2% / −4.1%), so the verified estimate is not visibly survivorship-inflated.

## 3. (a) Breakout — close > trailing-6h close-high + volume expansion, 25% trailing stop

12-variant grid (6h lookback, 6h cooldown per pool, entry at signal-bar close, stop evaluated on traded-bar closes):

| variant | signals | VERIFIED | **DISC%** | tok | NET mean | CI(token) | NET median | win% | stop-hit% |
|---|---|---|---|---|---|---|---|---|---|
| 12h, vol>1.5x, trail 25% | 113 | 85 | 24.8 | 33 | −3.13% | [−8.7, +4.5] | −3.40% | 17.6 | 22.4 |
| 12h, vol>1.5x, no stop | 113 | 81 | 28.3 | 32 | −4.82% | [−14.3, +4.0] | −3.31% | 18.5 | — |
| 12h, vol>2x, trail 25% | 85 | 66 | 22.4 | 26 | −3.04% | [−9.3, +5.7] | −3.38% | 16.7 | 21.2 |
| 12h, vol>2x, no stop | 85 | 63 | 25.9 | 25 | −4.04% | [−13.1, +6.2] | −3.24% | 17.5 | — |
| 12h, vol>3x, trail 25% | 42 | 38 | 9.5 | 18 | −2.49% | [−11.9, +10.6] | −4.26% | 15.8 | 28.9 |
| 12h, vol>3x, no stop | 42 | 36 | 14.3 | 18 | −4.03% | [−18.4, +11.6] | −3.93% | 16.7 | — |
| 24h, vol>1.5x, trail 25% | 79 | 58 | 26.6 | 27 | −2.83% | [−9.4, +5.4] | −3.89% | 20.7 | 25.9 |
| 24h, vol>1.5x, no stop | 79 | 53 | 32.9 | 24 | +4.12% | [−12.8, +35.9] | −3.57% | 20.8 | — |
| 24h, vol>2x, trail 25% | 63 | 48 | 23.8 | 21 | −1.82% | [−9.3, +8.9] | −3.50% | 20.8 | 22.9 |
| 24h, vol>2x, no stop | 63 | 46 | 27.0 | 20 | +4.85% | [−14.7, +42.6] | −3.35% | 21.7 | — |
| 24h, vol>3x, trail 25% | 37 | 30 | 18.9 | 15 | +0.99% | [−9.9, +20.4] | −3.42% | 16.7 | 26.7 |
| 24h, vol>3x, no stop | 37 | 28 | 24.3 | 14 | INSUFFICIENT DATA (<15 tokens) | | | | |

Window split for the base case (24h, vol>2x, trail 25%): A n=11, 8 tokens → insufficient; B n=37, 17 tokens, −0.67% [−9.83, +14.11].

**All 12 variants have a negative median (−3.2% to −4.3%) and a 16–22% win rate; not one CI excludes zero.** Breakouts in established tokens do not beat the cohort drift — they roughly equal it, and the drift is negative. The three positive means all come from the no-stop / high-threshold variants and are single-observation artifacts: for 24h/vol>2x/no-stop, mean +4.85% → **−7.61% dropping the single best trade** → −9.53% dropping the best three; median −3.35%.

## 4. (b) Momentum persistence — rank survivors by trailing 24h return, hold 24h

Strict daily rebalance is not testable here: the 45h entry window yields **1 usable rebalance date, 3 names, 3 tokens → INSUFFICIENT DATA**. 6-hourly rebalance: 5 usable dates, 19 signals, 13 verified, 6 discarded, 9 tokens → **INSUFFICIENT DATA**. To get any power at all I ran overlapping hourly rebalances (41 hours used, 1,209 signals, **805 verified, 404 DISCARDED = 33.4%** — 391 no-vol-at-horizon, 13 pool-ended; 40 tokens / 58 pools):

| momentum bucket | n | tok | NET mean | CI(token) | median | win% | median trailing 24h ret |
|---|---|---|---|---|---|---|---|
| **top decile (the rule asked for)** | 88 | **14** | INSUFFICIENT DATA (<15 tokens) | | | | |
| top quintile | 168 | 24 | +5.05% | [−14.9, +31.4] | **−2.43%** | 34.5 | +19.1% |
| 2nd quintile | 159 | 26 | −6.48% | [−13.5, −4.0] | −4.51% | 12.6 | +7.3% |
| mid quintile | 177 | 14 | INSUFFICIENT DATA (<15 tokens) | | | | |
| 4th quintile | 158 | 27 | −5.37% | [−10.6, −2.7] | −3.72% | 18.4 | −2.9% |
| bottom quintile | 143 | 23 | −10.82% | [−19.7, −2.0] | −5.11% | 28.0 | −14.5% |
| ALL cohort | 805 | 40 | −4.18% | [−11.0, +2.2] | −4.31% | 19.0 | +0.5% |

Paired spread (top-decile mean − cohort mean, per rebalance hour): n=40 hours, mean **+10.44pp** CI [+1.16, +21.84] — but **median +0.06pp**. Cross-sectional Spearman IC = +0.101 mean / +0.073 median over 37 hours, t=+2.71 — computed on 41 *overlapping* hours spanning 1.87 independent periods, so that t is not a test.

**The entire positive tail of this study is one token.** Ranked verified returns in the top quintile: +576%, +179%, +160%, +155%, +135% — four of the top five are the same token (`Hos282xm…`, pool `7ManjzDS3T…`). Top-quintile mean +5.05% → **+1.62% dropping the single best observation → −0.41% dropping three → −1.58% 5%-trimmed**; removing that one token alone costs **−9.39pp of the +5.05%**. The trade is *genuine*, not an artifact — it passes every check (1,418 traded minutes during the hold, 627 traded bars after exit, $1,211 of volume in the exit minute, entry reserve $82,854 → exit $234,363, 6.9x) — which is precisely the point: **a strategy whose expectancy is one 7x in 77 tokens over two days has an unmeasurable, unbankable edge, and its median trade loses 2.4–4.3%.**

## VERDICT

**No. There is no tradable long edge in the survivor cohort in this data, and the headline is the benchmark: established tokens have negative drift, so every long rule inherits it.**

- Buy-and-hold the survivor cohort is **−2.16% net / 6h [−4.08, −0.21], 59 tokens** and **−4.21% net / 24h [−10.33, +1.98], 40 tokens** (−4.28% [−7.15, −2.70] on the cleaner reserve≥$250k cohort, 33 tokens). Median negative at every horizon; 19–25% win rate; **gross** drift already negative, so this is not a cost problem.
- Breakout adds nothing: 12/12 variants negative-median, none CI-positive, and the trailing stop neither helps nor hurts significantly (it clips the right tail: +4.85% → −1.82% mean at 24h/vol>2x, both indistinguishable from zero).
- Momentum persistence **as specified (top decile, daily rebalance) is untestable here** — 1 rebalance date, 3 tokens. Forced to hourly overlapping rebalances, the top quintile's apparent +5.05% is one token; trimmed, it is −1.6% and still below zero, and monotonic ranking across quintiles does not hold (2nd quintile −6.5% is *worse* than the bottom quintile's −10.8% only in ordering, not in significance).
- Binding limitations, stated plainly: **1.87 independent 24h periods**, **77 tokens ever in the cohort**, and point-in-time reserve unavailable before 2026-08-27T14:37Z, which makes **window A only 5 entry hours** and leaves no room for a genuine out-of-sample split. Nothing here could have detected a real edge smaller than ~10%/trade, and nothing here shows one.
- **Discards are the headline number, not a footnote: 18.5% (6h), 35.7% (12h), 36.1% (24h) of candidate holds could not be exited at a price anyone could trade** — 477 of 494 at 24h because no real volume printed within ±2 min of the horizon.
- One useful positive finding for the project's process: the measurement artifact is a **young/thin-pool** phenomenon. Same pipeline, age gate off → naive +65.6% vs verified −3.30% (**+68.9pp gap**); age≥24h → naive −3.9% vs verified −4.21% (**+0.3pp gap**). Restricting to established survivors removes the illusion — and reveals that the honest answer underneath it was always negative.

**Landmine found while doing this (production is clean, but worth knowing):** `pools.pool_created_at` parses to `datetime64[us, UTC]`, so the idiom `series.astype('int64')//10**9` yields epoch **kiloseconds** — ages 1000x too large and an age filter that silently passes everything. My first pass had exactly that bug (it inflated the cohort to 383 tokens and produced the fake +68.9pp gap table above as its by-product); all numbers here are from the corrected run using `(ts - epoch).dt.total_seconds()`. `memebot.data.gt.parse_iso_ts` uses `datetime.timestamp()` and is **not** affected.

Scripts (scratch, absolute paths): `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/{core,bench,bench2,bench3,strat,mom2,bogrid,agecmp,robust,final}.py`; cleaned traded-minute panel cached at `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/panel.pkl`.
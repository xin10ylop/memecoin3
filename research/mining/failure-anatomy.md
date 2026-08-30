# AUTOPSY: why every strategy failed

**Method (3 lines).** Raw `ohlcv` rows are *only* traded minutes (837,977/837,977 have `vol_usd>0`), so I worked directly off the DB and never touched the continuous grid — the resting-price artifact cannot enter. Observation grid = snapshot times with `reserve_usd>=15k`, snapped to a real traded minute within ±2 min, ≥10 min apart, after `first_seen+120s`; guards drop 290 glitch prints (>50× off a 5-bar median) and 1,896 bars in re-based price segments (adjacent-minute jumps >30× not confirmed by the independent snapshot price feed — 343 pools affected). A horizon is VERIFIED only if a real traded minute exists within ±2 min of it AND ≥10 traded minutes follow it; "died" vs "censored" is decided by `ohlcv_state.last_fetch_at` (when we last asked GT), never by absence of bars. CIs are cluster-bootstrapped by `base_token_address`; costs = `CostModel` (0.8%/side + clip/(reserve/2) + $0.10/tx).

**Universe funnel.** 18,341 snapshot-moments at ≥$15k reserve → 7,097 pre-discovery, 1,283 spacing, **6,022 had no real trade within ±2 min (1,292 of them inside verified bar coverage — you could not even enter)** → 3,939 observations, 2,020 pools, 1,986 tokens.

## HEADLINE DISCARD LEDGER (the number that matters most)

| horizon | evaluated | VERIFIED | **DISCARDED** | quiet_no_exit | died | died_after | censored | censored_after | price_unverified | tokens verified |
|---|---|---|---|---|---|---|---|---|---|---|
| 15 min | 3,939 | 1,759 | **2,180 (55.3%)** | 53 | 150 | 99 | 1,329 | 543 | 6 | 324 |
| 1 h | 3,939 | 1,544 | **2,395 (60.8%)** | 78 | 295 | 12 | 2,004 | 3 | 3 | 212 |
| 4 h | 3,939 | 1,211 | **2,728 (69.3%)** | 173 | 229 | 4 | 2,312 | 8 | 2 | 130 |

## The panel is two disjoint universes, not one

| cohort | obs | tokens | median reserve | median age | trending-sourced | 1h determinable |
|---|---|---|---|---|---|---|
| **mature (>3h old)** | 1,436 | 154 | $762,316 | 381 days | 100% | **94.4%** |
| **young (<3h old)** | 2,503 | 1,863 | $41,910 | 15.6 min | 14% | **10.6%** |

Every strategy in `REPORT.md` traded the *young* half. That half is 89% unmeasurable at 1h.

## (1) THE DRIFT — verified forward returns, whole tradable universe

| horizon | measure | n | tokens | mean | 95% CI | median | win | mean ex-top-1% |
|---|---|---|---|---|---|---|---|---|
| 1h | gross | 1,544 | 212 | +5.64% | [+2.52, +11.65] | +0.04% | 51.6% | +2.28% |
| 1h | net $25 | 1,544 | 212 | +3.09% | [+0.04, +8.98] | **−2.38%** | 25.5% | −0.21% |
| 1h | net $50 | 1,544 | 212 | +3.41% | [+0.39, +9.28] | **−2.01%** | 26.4% | +0.12% |
| 1h | net $200 | 1,544 | 212 | +3.27% | [+0.36, +8.93] | −1.84% | 26.9% | +0.03% |
| 4h | gross | 1,211 | 130 | +10.22% | [+2.80, +26.22] | −0.03% | 49.1% | +3.03% |
| 4h | net $50 | 1,211 | 130 | +7.95% | [+0.66, +23.61] | **−2.07%** | 23.0% | +0.89% |
| 4h | net $50, token-EW | 130 | 130 | +16.59% | [−2.61, +39.33] | −2.05% | 36.9% | — |

The mean is a lottery ticket, not a drift: at 1h, dropping the **single best** observation takes +3.28%→+2.79%, dropping the top 1% takes it to **−0.00%**, the top 5% to **−3.23%**. 26% of verified holds make money.

**By window** (net $50, 1h): A (`ts<1787860000`, backfilled bars) n=227/68 tok, +3.71% [−4.66,+15.18]; B n=1,317/173 tok, +3.36% [+0.14,+9.81]. Newer windows: 08-28 +3.06% [−1.66,+11.25] (142 tok) · 08-29 +0.46% [−1.67,+5.59] (43 tok) · 08-30 +9.96% [+2.54,+23.77] (35 tok). No stable sign.

**Split by cohort — this is the whole story** (net $50):

| cohort | horizon | n | tokens | mean | CI | median | win |
|---|---|---|---|---|---|---|---|
| mature | 1h | 1,289 | 113 | **−1.57%** | [−2.93, +0.35] | −2.11% | 17.6% |
| mature | 4h | 1,094 | 93 | **−0.91%** | [−3.47, +3.02] | −2.11% | 18.4% |
| young | 1h | 255 | 119 | +28.58% | [+15.52, +42.88] | +19.11% | 70.6% |
| young | 4h | 117 | 50 | +90.78% | [+28.32, +174.34] | +38.43% | 65.8% |

**(a) price decay vs (b) costs — mature cohort, the only honestly measurable one:**

| horizon | mean gross | modeled cost | mean net | median gross | median net | net incl. observed deaths | death drag | costs as % of the loss |
|---|---|---|---|---|---|---|---|---|
| 15 min | +0.20% | 2.08% | −1.88% | +0.02% | −2.04% | −2.07% | −0.19pp | **111%** |
| 1 h | +0.52% | 2.09% | −1.57% | −0.06% | −2.11% | −2.04% | −0.47pp | **133%** |
| 4 h | +1.18% | 2.09% | −0.91% | −0.07% | −2.11% | −1.81% | −0.90pp | **230%** |

**There is no price decay to speak of.** Over 15 min to 4 h the honestly-measurable universe is a flat random walk (median gross ≈ 0.00% at every horizon). 100% of the typical loss is the cost model plus a 0.2–0.9pp death drag. The toll is the same size at 15 min as at 4 h — it is a fixed entry fee, so *trading more often is strictly worse.*

## (2) THE SURVIVORSHIP STRUCTURE

Still trading later (≥3 traded minutes in a ±15-min window; unknown = coverage-censored, excluded and counted):

| horizon | cohort | n at risk | tokens | unknown | still trading |
|---|---|---|---|---|---|
| 1h | mature | 1,343 | 126 | 93 | 96.6% |
| 1h | young | 559 | 376 | 1,944 | **47.1%** |
| 6h | young | 298 | 198 | 2,205 | **28.2%** |
| 24h | young | 78 | 45 | 2,425 | **24.4%** |

**Death hazard P(not trading 1 h later), [n at risk]:**

| age \ liquidity | 15–30k | 30–60k | 60–150k | 150–400k | >400k |
|---|---|---|---|---|---|
| **<30 min** | 0.687 [182] | **0.857 [112]** | 0.405 [37] | 0.192 [26] | 0.576 [33] |
| 30–60 min | 0.214 [14] | 0.600 [20] | 0.182 [22] | 0.174 [23] | 0.438 [16] |
| 1–3 h | 0.000 [3] | 0.000 [15] | 0.050 [20] | 0.125 [32] | 0.250 [4] |
| 3–12 h | 0.000 [10] | 0.000 [5] | 0.083 [36] | 0.258 [31] | 0.167 [12] |
| **>12 h** | 0.062 [16] | 0.091 [44] | 0.022 [184] | 0.006 [158] | **0.027 [847]** |

Age dominates, liquidity modifies. Hazard falls ~25× from (<30 min, $30–60k) to (>12 h, >$400k). At 6h the young/thin cells run 0.75–0.95.

**How much of the drift is death?** In the mature cohort, almost none: including every observed death at a forced liquidation (last real print, 3× stressed impact) moves 1h from −1.57% to −2.04% and 4h from −0.91% to −1.81%. Death is not what makes the mature universe negative — **cost is**. In the young cohort death is everything, and it is precisely what we cannot price:

Independent second channel (snapshot stream: `vol_m5>0` proves a real trade in the 5 min ending at the snapshot; coverage there is recency-driven, not fate-driven). Young cohort at +30 min: **958/2,503 (38.3%) determinable, 774 tokens — and 747 of those 958 (78.0%) had no trading at the exit.** The 22% that were tradable returned +57.5% mean [+38.97, +78.70] / +23.9% median (211 obs, 176 tokens).

| assumed recovery on a position you cannot exit | EV per young 30-min trade |
|---|---|
| 0% (you get out flat, impossible) | +12.7% |
| −20% | −2.9% |
| −50% | −26.3% |
| −90% | −57.5% |

The entire sign of the young-cohort trade rests on a number this dataset **cannot** measure — the fill you get when nobody is trading. Pricing it optimistically is exactly the +46% mirage, one level deeper.

**And verifiability itself is fate-selected in the young cohort** (1h status × attention, young):

| 1h status | n | trending *before* t0 | trending in the *next hour* | median coverage left |
|---|---|---|---|---|
| verified (ok) | 255 | **49.0%** | **47.8%** | 423 min |
| censored | 1,923 | 9.9% | 12.7% | 11 min |
| died | 285 | 11.6% | 8.1% | 395 min |

The collector re-fetches pools that stay snapshot-active, and trending pools stay snapshot-active. So the young observations we *can* verify are ~4× enriched in pools that go on to trend. The mandated (a)+(b) rule blocks untraded-price exits — it does **not** block conditioning on survival. In the young half, passing verification *is* the outcome.

## (3) WINNER ANATOMY (verified 4h, winner = net > +50%)

**Mature cohort** (clean: 87% determinable): 1,094 obs / 93 tokens, **32 winners (2.9%) across only 12 tokens** → below the 15-token bar; treat every number below as description, not evidence.

| feature @ t0 | AUC | 95% CI | median winner | median control | within age×liq cell |
|---|---|---|---|---|---|
| turnover vol_h1/reserve | **0.961** | [0.889, 0.995] | 49.1× | 0.17× | 0.799 |
| log age | **0.040** | [0.010, 0.115] | 15.5 h | 1.7 yr | 0.226 |
| turnover vol_m5/reserve | **0.940** | [0.847, 0.990] | 1.89× | 0.008× | 0.799 |
| prior 6h run | **0.887** | [0.721, 0.983] | +156% | +0.2% | 0.798 |
| log FDV | **0.149** | [0.059, 0.340] | $4.3M | $1.1B | 0.372 |
| buyers_m5 | **0.839** | [0.675, 0.951] | 129.5 | 24 | 0.701 |
| price_change_h1 | **0.811** | [0.624, 0.941] | +1578% | +5.8% | 0.625 |
| buyer share | 0.715 | [0.519, 0.841] | 0.68 | 0.52 | 0.640 |
| **prior drawdown from all-time high** | 0.686 | [0.365, 0.878] | −0.8% | −6.4% | 0.613 |
| prior 1h drawdown | 0.495 | [0.242, 0.728] | −0.8% | −0.9% | 0.512 |

15 features tested (≈0.75 false positives expected at 5%); matched analysis survived in only 2 usable age×liquidity cells (n=271, 48 tokens). **The winner signature is not a dip — it is a pool that is already exploding**: smaller, younger-within-mature, mid-cap, turning over its entire liquidity 49× per hour with 130 buyers/5min and +1,578% already on the clock. Drawdown/mean-reversion features carry no signal (CI straddles 0.5) — which is exactly why `knife_catch` and `dip_reclaim` had it backwards.

**Does the signature pay?** (mature, verified, net $50):

| horizon | bucket | n | tokens | mean | CI | median | win | ex-top-3 |
|---|---|---|---|---|---|---|---|---|
| 1h | all mature | 1,289 | 113 | −1.57% | [−2.93, +0.35] | −2.11% | 17.6% | −1.92% |
| 1h | turn ≥10× | 52 | **18** | +9.90% | [−10.32, +23.85] | +13.75% | 84.6% | +5.55% |
| 1h | turn ≥25× | 44 | **13 ✗** | +18.25% | [+2.73, +32.18] | +15.25% | 95.5% | +13.66% |
| 4h | turn ≥5× | 45 | **15** | +43.49% | [+10.78, +84.94] | — | — | +30.00% |
| 4h | turn ≥10× | 29 | **12 ✗** | +61.36% | [+9.61, +104.65] | +71.97% | 82.8% | +41.63% |
| 4h | turn ≥25× | 22 | **6 ✗** | +94.49% | [+71.25, +149.71] | +73.61% | 100% | +72.72% |

Four reasons this is not an edge: (i) **token counts fall below 15 exactly where the effect appears**; (ii) verification collapses in that bucket — the top-5%-turnover mature observations are only **34.7% determinable at 4h, with 13.9% observed deaths and 38.9% censored**, so it is measured on the surviving third, the same selection as the young cohort; (iii) including observed deaths at a forced liquidation the CI reopens: 1h top-5% turnover **+0.23% [−22.69, +17.34]** (20 tokens), 4h **+29.80% [−22.38, +72.76]** (15 tokens); (iv) per-day the sign flips — 08-27 +41.3%, 08-28 −13.0%, 08-29 −3.7%, 08-30 +29.9% — and 2 of 22 tokens carry 11.2 of the 15.9 total return units (70%).

Young-cohort anatomy is reported for completeness only (117 verified obs, 50 tokens, 45% winners — a 45% winner rate is itself proof the sample is survivor-selected): winners are higher-liquidity, higher-buyer-share, *low* prior drawdown (AUC 0.815) and *low* realized vol (0.223). Not usable.

## (4) THE COST WALL

Round-trip cost (2 sides + $0.20 flat), the per-trade gross edge you must clear:

| reserve \ clip | $25 | $50 | $100 | $200 |
|---|---|---|---|---|
| $15k | 3.07% | 3.33% | 4.47% | **7.03%** |
| $30k | 2.73% | 2.67% | 3.13% | 4.37% |
| $60k | 2.57% | 2.33% | 2.47% | 3.03% |
| $150k | 2.47% | 2.13% | 2.07% | 2.23% |
| $400k | 2.43% | 2.05% | 1.90% | 1.90% |
| $1M | 2.41% | 2.02% | 1.84% | 1.78% |

Realized on the verified panel: mean 2.23–2.61%, median 1.77–2.41%, p90 up to 4.12% ($200 clip). A forced/stressed exit (3× impact) costs 4–12% depending on liquidity. Bleed at 2.4%/trade, $25 clips on a $1,000 book: 5 trades/day = 0.30%/day, 25/day = 1.51%/day, 50/day = 3.01%/day — the shipped strategies ran 6–53 trades/day.

**Distance to the wall.** Mature universe gross drift is **+0.52%/1h vs a 2.09% wall — 1.6pp short; you need 4× the observed drift just to break even.** The young universe's 22–25% survivors clear the wall by miles, and its 75–78% no-exit cases are unpriceable. The only measured effect that clears the wall (turnover ≥10×) does so on 12–18 tokens, on a 35%-determinable subsample, with a sign that flips by day.

## VERDICT

**Long-only, this market is untradable for us, and the honest answer is "no edge here."**

1. **The measurable universe has no drift and a 2% toll.** Mature, liquid, trending-sourced pools: **−1.57%/1h trade [−2.93, +0.35], median −2.11%, 17.6% win rate, 113 tokens** — median gross return 0.00%. It is a coin flip with a 2% entry fee. Nothing in the tested feature set moves it 1.6pp.
2. **The universe the strategies actually traded cannot be measured with this data, and that — not a bad rule — is why they all failed.** Young pools: **60.8% of 1h observations discarded**, 47% not trading an hour later, **78% of determinable 30-min exits have no trade at the exit**, and verifiability is 4× enriched in pools that go on to trend. Every backtest on that population necessarily reads the winners' prices and imputes something benign for the losers. The `+46% → −22.7%` collapse was the first layer of that; conditioning on survival is the second, and the mandated (a)+(b) rule does not remove it.
3. **The one niche the anatomy points at — mature pools turning over ≥10× their liquidity in an hour, already running, with 100+ buyers/5min — is a real description of winners and an unproven trade.** 12–18 tokens, 35% determinable in exactly that bucket, CI reopens to include zero once observed deaths are added, sign flips across 4 days, 70% of P&L in 2 tokens. By this project's own rules that is **INSUFFICIENT DATA, NOT VALIDATED** — and it is the same shape of evidence that produced the last mirage.
4. **What would change the answer** is data, not a new rule: the collector must (a) keep fetching OHLCV for every pool it has ever entered on, for at least 6 h past the last observation, regardless of trending status — the current fate-correlated re-fetch priority is what makes the young cohort unmeasurable, and (b) record an actual sell quote (Jupiter) at the exit minute for dying pools, since the recovery rate on a no-exit position is the single unknown that decides the sign of the entire young-cohort trade. Until then, no long strategy on this panel can be validated, and the correct position is flat.

Working files (all absolute): `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/build_obs5.py` (panel builder with both verification channels), `snapver.py` (independent snapshot-verification channel), `an5.py`–`an13.py` (analyses), `obs6.pkl` (3,939-observation panel with all statuses/features).
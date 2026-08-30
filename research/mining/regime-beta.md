Analysis complete. Final report:

---

# Is timing the only real signal? A verified hourly meme index (data/panel.db, 2026‑08‑30)

**Method (3 lines).** Built a minute grid over the **real‑time observable era only** (08‑27 14:40 → 08‑30 12:00 UTC; 48.3% of `ohlcv` bars are pre‑discovery backfill and were dropped — including them makes the index survivorship‑biased); a pool is *qualified* at minute t if reserve ≥$25k (last snapshot ≤120 min stale), discovered ≥120 s earlier, and it printed a real bar in [t‑2, t] (causal). A pool‑return t→t+H is **VERIFIED** only if a real bar prints within ±2 min of t+H **and** the pool trades ≥10 more minutes after t+H; the index is the equal‑weighted **median** of verified returns across qualified pools, features (trailing index momentum, breadth, volume surge, launch rate) are strictly trailing and lag‑tested. CIs: token‑cluster bootstrap for pooled pool‑legs, hour‑cluster/block bootstrap for index and basket time series; costs = `memebot.backtest.costs.CostModel` (80 bps/side + clip/(reserve/2) + $0.10/tx) at a $100 clip ($25/$200 tested).

## 0. HEADLINE: what had to be thrown away

| horizon | qualified pool‑minute candidates | VERIFIED (used) | **discarded (a) no real volume at exit** | **discarded (b) pool died <10 traded min after** | total discarded |
|---|---|---|---|---|---|
| 1h | 124,901 | 85,941 (68.8%) | **37,645 (30.1%)** | **1,315 (1.1%)** | **38,960 = 31.2%** |
| 4h | 119,461 | 70,053 (58.6%) | **48,578 (40.7%)** | **830 (0.7%)** | **49,408 = 41.4%** |
| 12h | 104,840 | 50,149 (47.8%) | **54,052 (51.6%)** | **639 (0.6%)** | **54,691 = 52.2%** |

Of the (a) discards, **25.5% are provably quiet** (the collector was still polling that pool after the exit minute and no bar came) and **74.5% are simply unmeasurable** (OHLCV fetching had stopped for that pool). We cannot claim those returns were bad — only that they are not evidence.

**Universe collapse:** 2,575 pools clear the $25k gate in real time; **only 223 pools / 198 tokens ever produce a single verifiable 1‑hour forward return.** The other 2,352 pools have a median of **12 observable traded minutes each** and contribute 29,849 candidate pool‑minutes, all discarded. This is invariant to the reserve staleness cap (20 min → 221 pools; ∞ → 225 pools): OHLCV coverage, not liquidity, is binding. **The verified index is the continuously‑traded core, not the full cross‑section — disclose this wherever it is used.**

**The artifact, reproduced in this study** (identical code, verification switched off):

| measurement | verified (honest) | unverified (resting price / data edge) |
|---|---|---|
| pool‑leg mean, 1h | **+2.72%** | +6.15% |
| pool‑leg mean, 12h | **+0.02%** | +8.67% |
| hourly median‑index mean, 12h | **−0.341%** | +0.067% |
| **10‑name basket, net of costs, per hour** | **+0.30%**, cum **+18.9%** over 62 h | **+622.3%**, cum **+38,582%** |

## 1. Does the index persist? No.

Verified hourly index (H=60m): **69 hours in era, 56 defined** (13 undefined = two collector outages, 08‑27 18:00–23:59 and 08‑28 12:15–15:00, plus hours with <8 qualified pools). Mean **+0.070%/h**, block CI **[−0.08%, +0.20%]**, median +0.06%, chained over the sample **+3.81%** — gross, before any cost.

| lag | pairs | Pearson (p) | Spearman |
|---|---|---|---|
| 1h | 51 | −0.142 (0.32) | −0.043 |
| 2h | 48 | −0.099 (0.50) | −0.164 |
| 4h | 45 | −0.286 (0.06) | −0.233 |
| 6h | 43 | +0.011 (0.94) | +0.150 |
| 12h | 42 | +0.181 (0.25) | +0.067 |
| 24h | 32 | +0.079 (0.67) | +0.168 |

Per window — A (08‑27 14:40–19:46, 5 h): **insufficient**. B (→08‑29 00:00, 28 h): lag1h r=−0.111, lag4h r=−0.398 (n=11), lag12h n=7 insufficient. C (→08‑30 12:00, 36 h): lag1h r=−0.070, lag4h r=+0.036, lag12h r=+0.155 (n=22). No sign agreement across windows.

On a 15‑min grid the overlapping ACF is +0.611 at 15 min and +0.393 at 30 min — but pure mechanical overlap predicts **+0.75 and +0.50**. Observed persistence is *below* the overlap benchmark, i.e. **zero genuine memory**; by 60 min it is +0.036.

**A common factor does exist, it is just small and unpredictable.** Breadth sd = 0.205 vs 0.105 under cross‑sectional independence (**1.94×**, implied sign co‑movement ρ≈0.12); an hour fixed effect explains **4.1%** of pool log‑return variance (n=85,941). ~96% of a memecoin's hourly move is idiosyncratic.

## 2. Conditional on index state — verified forward returns

**Index level** (15‑min grid, overlapping, block CI, L=8; quintiles because only ~250 obs exist):

| state (quintile 5 = highest) | fwd 1h | fwd 4h | fwd 12h |
|---|---|---|---|
| trailing‑1h index, Q1 | +0.07% [−0.23,+0.34] | +0.19% [−0.57,+0.96] | −0.61% [−1.58,+0.26] |
| trailing‑1h index, Q5 | +0.02% [−0.51,+0.52] | **−0.50% [−1.14,−0.01]** | **−1.39% [−2.98,+0.09]** |
| trailing‑6h index, Q5 | −0.28% [−0.81,+0.09] | −0.43% [−1.33,+0.23] | **−0.47% [−1.09,−0.02]** |
| breadth Q1 / Q5 | +0.04% / −0.01% | −0.08% / −0.05% | +0.15% / −0.14% |
| volume surge Q5 | +0.19% [−0.16,+0.63] | −0.17% [−1.07,+0.98] | **−1.32% [−2.35,−0.44]** |
| new‑launch rate Q5 | +0.19% [−0.46,+0.87] | +0.14% [−0.70,+0.96] | −1.22% [−3.09,+0.36] |
| n qualified pools Q5 | +0.22% [−0.26,+0.76] | +0.02% [−0.66,+0.92] | **−1.22% [−2.36,−0.15]** |

Every CI that excludes zero at 4h/12h does so on the **negative** side, and it is always the *hot* state (high momentum, high volume, high launch rate) that mean‑reverts. There is no state in which the forward index is reliably positive.

**Pool level, verified, token‑clustered** (1h horizon: 85,941 legs / **198 tokens**; unconditional mean +2.72% CI [+0.97,+5.67], **median +0.02%**):

| decile of trailing‑1h index | n legs | n tokens | mean 1h | 95% CI (token cluster) | median |
|---|---|---|---|---|---|
| D1 (most negative) | 8,451 | 119 | +8.03% | [+0.34, +21.56] | +0.24% |
| D5 | 8,435 | 140 | +1.89% | [+0.66, +4.50] | +0.07% |
| D10 (most positive) | 8,441 | 153 | +4.03% | [+0.53, +8.22] | **−0.21%** |

| decile of volume surge | n legs | n tokens | mean 1h | 95% CI | median |
|---|---|---|---|---|---|
| D1 (quietest) | 8,599 | 75 | +0.02% | [−3.00, +3.52] | +0.07% |
| D7 | 8,610 | 138 | **+9.23%** | [+4.13, +19.33] | +0.10% |
| D10 (most extreme) | 8,579 | 73 | +2.37% | [−0.92, +7.03] | +0.01% |

Note the shape: **means of +4% to +9% sitting on medians of ±0.1%.** Non‑monotone at the top (D7 ≫ D10). At 12h the *only* CIs excluding zero are negative (trailing‑momentum D10: −5.49% [−10.83,−1.27]; volsurge D1: −4.57%). Per window, 1h verified pool legs: A **+1.34%** [−1.90,+4.98] (73 tokens), B **+5.74%** [+1.44,+14.05] (130 tokens), C **+1.33%** [+0.15,+3.82] (58 tokens).

## 3. Timing strategy — 10‑name equal‑weighted basket, net of costs

**(3a) Rebalanced hourly** (full round trip every hour; 100 random draws/hour; verified legs only):

| gate | hours on | TIM | verified legs | **discarded legs** | disc % | gross | **net** | median net | 95% CI (hour cluster) | placebo p |
|---|---|---|---|---|---|---|---|---|---|---|
| **flat** | 0 | 0.00 | 0 | 0 | — | 0 | **0.0000** | 0 | — | — |
| always‑on | 68 | 0.91 | 428 | **181** | 29.8% | +2.33% | **+0.30%** | −1.57% | [−0.90, +1.66] | 0.11 |
| idx mom >0 | 32 | 0.47 | 224 | 94 | 29.6% | +2.70% | +0.64% | −1.66% | [−1.24, +2.88] | 0.31 |
| idx mom >+0.5% | 9 | 0.13 | 55 | 32 | 36.8% | +6.41% | +4.22% | −1.00% | [+0.27, +8.48] | 0.015 |
| idx mom <0 | 29 | 0.43 | 201 | 81 | 28.8% | +1.50% | −0.50% | −1.61% | [−1.79, +1.04] | 0.86 |
| idx 6h mom >0 | 23 | 0.34 | 167 | 61 | 26.9% | +2.01% | −0.02% | −1.74% | [−1.89, +2.08] | 0.62 |
| breadth >0.55 | 27 | 0.40 | 191 | 77 | 28.8% | +3.09% | +1.02% | −1.59% | [−1.12, +3.46] | 0.18 |
| breadth >0.70 | 14 | 0.21 | 94 | 44 | 32.0% | +4.57% | +2.47% | −1.61% | [−0.46, +5.91] | 0.051 |
| volsurge >1.3 | 20 | 0.29 | 144 | 53 | 27.1% | +4.74% | +2.63% | −0.51% | [−0.23, +5.68] | 0.013 |
| **volsurge >1.6** | 12 | 0.18 | 81 | 35 | 30.4% | +6.78% | **+4.62%** | **+1.41%** | **[+0.87, +8.33]** | **0.002** |
| new launches >750/h | 33 | 0.49 | 193 | **131** | 40.3% | +3.81% | +1.72% | −1.33% | [−0.30, +3.93] | 0.014 |

**(3b) Held through each gate episode** (one round trip per episode — the cost‑fair version):

| gate | episodes | mean hold | verified legs | discarded | disc % | net | median | 95% CI |
|---|---|---|---|---|---|---|---|---|
| always‑on | **1** | 68 h | **0** | **all** | **100%** | — | — | buy‑and‑hold across the sample is **entirely unverifiable** |
| idx mom >+0.5% | 6 | 1.5 h | 36 | 20 | 36.2% | +2.82% | −1.71% | [−1.97, +10.40] |
| idx 6h >0 | 11 | 2.1 h | 71 | 38 | 35.4% | +2.93% | −1.82% | [−1.67, +8.05] |
| breadth >0.70 | 10 | 1.4 h | 67 | 30 | 30.8% | +2.32% | −1.77% | [−1.62, +7.05] |
| volsurge >1.6 | 7 | 1.7 h | 40 | 26 | 39.8% | +2.02% | −0.41% | [−1.12, +5.31] |
| volsurge >1.3 | 8 | 2.2 h | 45 | 32 | 41.8% | −0.25% | −0.43% | [−3.88, +3.19] |
| new launches >750 | 11 | 2.9 h | 67 | 39 | 37.2% | +6.62% | −1.57% | [−2.53, +20.38] |

**Not one gate keeps a CI off zero when the turnover regime changes.** volsurge>1.6 goes +4.62% [+0.87,+8.33] → +2.02% [−1.12,+5.31]; volsurge>1.3 flips sign.

**Fragility and windows.** Across all 62 tradable hours the always‑on basket means +0.30%; **minus the best hour +0.03%, minus the best two −0.18%, minus the best three −0.37%.** The entire unconditional expectancy is two hours (08‑28 04:00 +16.9%, 08‑27 15:00 +12.5%).

| gate | A (5 h) | B (28 h) | C (36 h, newest) |
|---|---|---|---|
| always‑on | +1.22% [−3.70,+7.71], 5 h | +1.42% [−1.11,+4.23], 22 h | **−0.53% [−1.80,+0.94]**, 35 h |
| idx mom >+0.5% | 2 h — insufficient | +6.66% [+0.26,+13.05], 5 h | +1.95% [−1.76,+5.66], 2 h |
| volsurge >1.6 | +3.14% [−1.67,+9.09], 4 h | **+8.61% [+0.35,+15.19]**, 4 h | +2.15% [−2.08,+8.04], 4 h |
| breadth >0.70 | 1 h — insufficient | +3.87% [−1.25,+9.65], 7 h | +0.72% [−2.31,+4.41], 6 h |
| new launches >750 | 1 h — insufficient | +3.61% [−0.32,+7.70], 12 h | **+0.06% [−1.53,+1.86]**, 20 h |

Every gate's apparent edge is a **window‑B phenomenon that decays to zero in the newest and largest window C**. Signal‑lag robustness (features at t−120 s / t−300 s, entry at t): volsurge>1.6 unchanged (+4.64%/+4.40%), so it is not lookahead — but breadth>0.70 falls +2.47% → +0.60% at a 2‑minute lag, i.e. mostly timing noise. **Configurations evaluated and logged to `research/results/registry.jsonl`: 28** (10 gates × 2 turnover regimes + 8 diversification cells). Bonferroni at α=0.05 over 10 gates requires p<0.005; only volsurge>1.6 (p=0.002) clears it, on **11–12 hour‑clusters** — by the same standard this project applies to tokens, that is **insufficient data**.

**Cost sensitivity (always‑on, N=10, 1h):** gross +2.26% is constant; net **−0.22%** at a $25 clip, **+0.23%** at $100, **+0.12%** at $200. Round‑trip drag is 2.0–2.5%. The $25 clip is *worse* because the flat $0.10/tx is 0.4%/side there.

## 4. Diversification — does a basket rescue expectancy?

Always‑on, verified legs only, net of costs, $100 clip:

| N | hold | obs | verified legs | discarded | mean | **median** | sd | mean/sd | **P(loss)** | q05 | 95% CI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1h | 8,558 | 8,558 | 0 | +0.14% | −1.82% | 0.224 | 0.006 | **78.6%** | −15.9% | [−1.24,+1.77] |
| 3 | 1h | 11,496 | 25,960 | 8,528 | −0.13% | −1.80% | 0.150 | −0.009 | 72.9% | −14.5% | [−1.31,+1.25] |
| 10 | 1h | 12,327 | 85,465 | 36,450 | +0.11% | −1.61% | 0.092 | 0.012 | 66.8% | −9.9% | [−1.08,+1.50] |
| 30 | 1h | 12,374 | 230,274 | 99,867 | +0.15% | −1.22% | 0.065 | **0.024** | 64.2% | −7.6% | [−1.04,+1.49] |
| 1 | 4h | 7,288 | 7,288 | 0 | +1.64% | −2.00% | 0.484 | 0.034 | **79.0%** | −27.5% | [−1.47,+5.74] |
| 10 | 4h | 11,531 | 73,207 | 40,842 | +1.59% | −2.28% | 0.208 | 0.077 | 66.3% | −16.3% | [−1.47,+5.32] |
| 30 | 4h | 11,731 | 194,331 | 117,424 | +1.69% | −2.21% | 0.161 | **0.105** | 66.9% | −13.2% | [−1.34,+5.21] |

Single‑name mean with a **token‑clustered** CI: 1h **+0.14% [−1.13,+2.84]** (155 tokens); 4h **+1.64% [−2.15,+9.94]** (108 tokens).

Diversification does exactly what the mathematics says and nothing more: **sd falls 2.4× (22.4%→9.2%) from N=1 to N=10, mean/sd rises 2×, P(loss) falls 78.6%→66.8%, the median rises −1.82%→−1.61% — and the mean does not move (+0.14% → +0.11%).** Baskets convert a lottery into a reliable small number; they cannot convert a zero into a positive. Even at N=30, **64% of basket‑hours lose money** and the median basket‑hour still loses 1.2%. Under the best‑looking gate (volsurge>1.6, 12 hours, 399 verified legs / **128 tokens**, leg mean +5.36% [+1.95,+10.17], leg median +0.05%, top‑1 token = 18% of total P&L, top‑3 = 40%), the N=10 basket is the only cell in this study with a positive median (+0.32%, P(loss) 46.3%, CI [+0.13,+7.74]) — on **11 hours**.

---

# VERDICT

**1. A meme beta exists; it is not timeable. No edge here.** Co‑movement is real but tiny (breadth dispersion 1.94× the independence null, ρ≈0.12, hour fixed effect R²=**4.1%**), and the verified index is flat: **+0.070%/hour, CI [−0.08%, +0.20%]**, gross, against a **2.0–2.5% round‑trip cost**. Autocorrelation at 1h/4h/12h is statistically indistinguishable from zero in every window and is *below* the mechanical overlap benchmark at short lags. Conditioning on trailing 1h/6h index return, breadth, volume surge, launch rate, or universe width produces no state with a reliably positive forward index return — the only CIs that exclude zero at 4h/12h are **negative**, and they sit in the *hot* states. Timing is not the hidden real signal; it is the same nothing measured on a different axis.

**2. Every gate that looks positive is a window‑B artifact.** All ten gates were tested in two turnover regimes; the two that clear a naive 95% bar in hourly‑rebalance mode lose it under episode‑held costs, and all of them decay to ~0 in window C (the newest 36 hours, the largest sample). volsurge>1.6 is the sole survivor of the placebo test (p=0.002, robust to a 5‑minute signal lag, mean +4.62% [+0.87,+8.33]) but rests on **11–12 hour‑clusters** — insufficient by this project's own <15‑cluster rule — and its edge is 8.6% in B vs 2.2% (CI straddling zero) in C. **Do not promote it. It is the one hypothesis worth pre‑registering and collecting more windows for; it is not a result.**

**3. Basket construction does not rescue expectancy — and was never able to.** Diversification cut dispersion 2.4× and raised mean/sd 2×, exactly as theory requires, while leaving the mean pinned at +0.1%/hour net with a CI straddling zero and the **median negative at every basket size**. The single‑name lottery problem is real (78.6% of single 1h positions lose; the mean is carried by a 3.46× tail), but averaging a zero‑mean lottery 30 ways yields a zero‑mean annuity, not an edge. Where single names failed, baskets fail more reliably.

**4. The measurement discipline is doing the work, and the discard counts are the story.** 31% of 1‑hour, 41% of 4‑hour and **52% of 12‑hour** qualified observations cannot be priced at a tradable exit; only **223 pools / 198 tokens** out of 2,575 liquidity‑qualified pools ever yield one verifiable 1‑hour return; 48% of raw bars are pre‑discovery backfill. Switching verification off in this exact pipeline turns a **+0.30%/hour** basket into **+622%/hour** and a +18.9% cumulative into **+38,582%**. Any future result on this dataset that does not print its discard count should be assumed to be that number.

Artifacts (all under `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/`): `build.py`, `res.py`, `lib.py`, `idx.py`, `feat.py`, `a1.py`, `a2.py`, `sim2.py`, `div.py`, `art.py`, `plac.py`, `lag.py`, `beta.py`; data `panel_mtx.npz`, `res_mtx.npz`, `index_min.csv`, `feats.csv`, `gate_hourly.csv`, `gate_run.csv`. 28 configurations appended to `/home/user/memecoin3/research/results/registry.jsonl`.

One incidental bug worth knowing: `pd.to_datetime(...).astype("int64")//10**9` is wrong under pandas 3.0.5 — these columns come back as `datetime64[us]`, so that idiom yields microseconds/10⁹ and silently produces epoch ≈ 1787 instead of 1.787e9. It appears in `research/` helper scripts; use `.astype("datetime64[s, UTC]").astype("int64")`. Left unfixed it disables any first‑seen/creation‑time filter (mine was a no-op until I caught it, which would have let pre-discovery backfill into the index).
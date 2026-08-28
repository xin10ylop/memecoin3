All checks complete. Compiling the report.

# Event Studies: ATTENTION events (DexScreener boosts, GT trending) — memecoin panel

**Methodology (3 lines).** Eligible universe = bars with reserve_usd≥15k, fdv∈[1e5,3e7], vol_h1_snap≥1e4 (8,062 bar-obs, 351 pools/346 mints; window A: 67 tokens, B: 289). Event entry = first eligible bar at/after event ts (≤60 min later); fill = close of next bar (timestamp-based, no same-bar leakage; horizons 15/30/60/120m computed by wall-clock ts, terminal-extended to last bar if pool data ends). Controls = eligible bars from never-evented pools, same window, age ±50%, reserve 0.5–2.0x; primary = up to 5 sampled pools/event (seed 42), robustness = 10-seed resamples + deterministic all-matched-pools variant + 1/99% winsorized; all CIs = 95% cluster bootstrap by base_mint (4,000 reps).

Window split at ts=1787860000 (A = Aug 27 cool tape, ~5.1h of collection; B = Aug 28 hot tape, ~15.6h). Median entry lag after event: 0.4–3.8 min.

## 1. Boost events (first paid-boost payment_ts)

Coverage: 37 pools mapped to a boost; only **8** had an eligible entry within 60 min (A=**2 tokens**, B=**6 tokens**). 6/8 boosts hit tokens that were already very illiquid or never passed the gates. **All 8 usable boost events are also in the trending table** (5/8 within ~1 min of a trending appearance) — the boost sample is fully confounded with trending.

| Win | H | ev tok | ctl tok (5-samp / all) | Event mean [CI] | Ctl mean [CI] | Diff (5-samp) [CI] | Diff (all-matched) [CI] | Winsor diff [CI] |
|---|---|---|---|---|---|---|---|---|
| A | 15 | 2 | 5 / 10 | −0.64 [−0.98,−0.30] | −0.28 [−0.62,+0.03] | −0.36 [−0.91,+0.20] | −0.64 [−1.21,−0.07] | −0.61 [−1.15,−0.07] |
| A | 60 | 2 | 5 / 10 | −0.85 [−0.98,−0.72] | −0.37 [−0.73,−0.00] | −0.48 [−0.89,−0.06] | −0.72 [−1.02,−0.40] | −0.72 [−1.02,−0.40] |
| A | 120 | 2 | 5 / 10 | −0.76 [−0.98,−0.54] | −0.39 [−0.78,−0.00] | −0.37 [−0.86,+0.13] | −0.56 [−1.03,−0.09] | −0.55 [−1.01,−0.10] |
| B | 15 | 6 | 25 / 168 | −0.13 [−0.60,+0.33] | −0.06 [−0.19,+0.06] | −0.07 [−0.52,+0.40] | −0.25 [−0.70,+0.21] | −0.20 [−0.64,+0.27] |
| B | 60 | 6 | 25 / 168 | −0.30 [−0.72,+0.12] | +0.12 [−0.12,+0.39] | −0.42 [−0.94,+0.07] | −0.47 [−0.92,−0.03] | −0.43 [−0.87,+0.00] |
| B | 120 | 6 | 25 / 168 | −0.27 [−0.78,+0.28] | +0.10 [−0.17,+0.43] | −0.37 [−0.99,+0.28] | −0.47 [−1.02,+0.12] | −0.43 [−0.95,+0.14] |

(H=30 similar to H=15: A diff −0.25 to −0.65, B −0.06 to −0.26 depending on spec.) 10-seed control resampling: diff negative in 9–10/10 seeds at every window×horizon.

**Assessment: INSUFFICIENT DATA — 2 tokens in A and 6 in B are both below the 15-token floor.** Every point estimate is negative (boosted tokens bleed −13% to −85% vs matched controls), but with n this small and total trending confounding, no claim survives.

## 2. First trending appearance (MIN(ts) per pool)

Coverage: 451 trending pools; **122** with eligible entry ≤60 min of first appearance (A=**31 tokens**, B=**91 tokens**; each event pool = unique mint). Truncation: fraction of events with fully-covered horizon in B: 0.56 (15m), 0.43 (30m), 0.42 (60m), 0.29 (120m) — terminal extension is doing real work at long horizons in B. 6/31 A events are left-censored (first trending poll at collector startup; may have been trending earlier).

Diff = event mean − control mean (fwd return). "Seeds" = median across 10 control resamples (count negative/10).

| Win | H | ev tok | Event mean [CI] (med) | Ctl mean (5-samp) [CI] | Diff 5-samp [CI] | Seeds (neg/10) | Diff all-matched [CI] | Winsor diff [CI] |
|---|---|---|---|---|---|---|---|---|
| A | 15 | 31 | −0.02 [−0.17,+0.13] (+0.00) | +0.15 [−0.09,+0.41] | −0.17 [−0.49,+0.11] | −0.20 (10/10) | −0.18 [−0.46,+0.08] | −0.11 [−0.31,+0.10] |
| A | 30 | 31 | −0.06 [−0.26,+0.17] (−0.02) | +0.13 [−0.10,+0.33] | −0.20 [−0.48,+0.11] | −0.23 (10/10) | −0.14 [−0.43,+0.16] | −0.14 [−0.41,+0.16] |
| A | 60 | 31 | +0.12 [−0.29,+0.76] (+0.02) | +0.16 [−0.15,+0.44] | −0.03 [−0.58,+0.71] | −0.09 (9/10) | +0.03 [−0.47,+0.72] | −0.14 [−0.48,+0.23] |
| A | 120 | 31 | −0.10 [−0.32,+0.12] (+0.00) | +0.28 [−0.11,+0.66] | −0.38 [−0.82,+0.07] | −0.44 (10/10) | −0.28 [−0.65,+0.09] | −0.26 [−0.62,+0.10] |
| B | 15 | 91 | +0.03 [−0.06,+0.13] (+0.02) | +0.11 [+0.03,+0.21] | −0.08 [−0.21,+0.05] | −0.06 (10/10) | **−0.18 [−0.36,−0.03]** | −0.12 [−0.24,+0.00] |
| B | 30 | 91 | +0.05 [−0.04,+0.15] (+0.03) | +0.13 [+0.04,+0.24] | −0.08 [−0.22,+0.06] | −0.07 (10/10) | **−0.20 [−0.39,−0.03]** | −0.13 [−0.26,+0.01] |
| B | 60 | 91 | +0.08 [−0.03,+0.19] (+0.01) | +0.14 [+0.04,+0.26] | −0.07 [−0.22,+0.09] | −0.06 (10/10) | −0.18 [−0.39,+0.01] | −0.12 [−0.26,+0.03] |
| B | 120 | 91 | +0.20 [+0.05,+0.37] (+0.03) | +0.16 [+0.05,+0.28] | **+0.05 [−0.15,+0.25]** | +0.05 (1/10) | −0.07 [−0.30,+0.16] | +0.00 [−0.18,+0.20] |

Control tokens: A 22–29, B 118–162 depending on variant.

**Strict matched-only check** (dropping events with zero matched controls — coverage is thin because trending pools are big: median entry reserve $237k in A / $160k in B; only 10/31 A and 57/91 B events had any control in-band): B diffs stay negative at 15/30/60m (−0.146 [−0.35,+0.06], −0.158 [−0.39,+0.05], −0.099 [−0.33,+0.12]); A (10 tokens, insufficient) noisy. So part of the full-sample effect is composition (trending pools sit in a reserve band the never-trending universe barely reaches), but the sign survives apples-to-apples in B.

**Interpretation.** The trending print itself is dead money: event medians ≈ 0 at all horizons while the matched eligible universe carries a fat right tail (control means +11–28%, medians +2–3%). Buying the first trending appearance forfeits that tail. The B@120m flip (+0.05, 9/10 seeds positive) suggests underperformance is concentrated in the first hour post-print; note 120m in B is 71% terminal-truncated.

**Caveats.** (i) Discovery conditioning: controls exclude any pool that *ever* trended — that removes future pre-trending run-ups from controls, which biases the measured diff toward zero, i.e. the negative finding is conservative. (ii) Controls matched on age/reserve/window only, not wall-clock minute. (iii) 6/31 A events left-censored at collector start. (iv) One 18.6x control bar verified real-looking (path-connected, survives sanitizer); winsorized spec covers it.

## VERDICT

**Composite-strategy candidates:**
- **TRENDING-FADE / NO-CHASE at 15–30m** — first-trending-appearance forward returns underperform matched controls: sign-negative in **both** windows in every spec (5-sample, 10/10 seeds, all-matched, winsorized), cluster CI excludes zero in window B (all-matched: −0.18 [−0.36,−0.03] @15m, −0.20 [−0.39,−0.03] @30m), same-sign in A. Meets the candidate rule. **Use as a negative filter in the composite: do not enter on/immediately after a first trending print; treat trending as a liquidity/exit event, not an entry trigger.** Effect size is opportunity cost (foregone right tail) more than crash risk — not a standalone short.
- **TRENDING @60m** — borderline: negative in most specs, both windows, but A flips sign in 2/4 specs and no CI excludes zero. Watch, not a candidate.

**Dead ends:**
- **TRENDING @120m** — sign flips across windows (A −0.38, B +0.05 with 9/10 seeds positive) + 71% truncation in B. Dead end.
- **BOOST events** — **insufficient data**: 2 tokens (A) / 6 tokens (B), below the 15-token floor, and 8/8 usable events are simultaneously trending pools (5/8 within ~1 min), so the effect is unidentifiable from trending. All 16 window×horizon point estimates are negative (−0.06 to −0.72 vs controls), so nothing here argues for boost-chasing either — re-run when the boost table has ≥15 eligible tokens per window.

Artifacts: eligible-bar table and per-study pickles in `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/` (`elig_table.pkl`, `final_boost.pkl`, `final_trending.pkl`; scripts `build_table2.py`, `final_study.py`, `robust.py`). Note for reuse: pools spanning >10,000 minutes skip the continuous-grid reindex in `src/memebot/data/store.py` (`MAX_GRID_ROWS`), so horizon math must be timestamp-based, not position-based (position-based first pass inflated a control outlier; corrected here).
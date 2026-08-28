All analyses complete and cross-checked. Compiling the final report.

# Round-2 Autopsies — wash-divergence, buyers-per-trade exclusion, dip-reclaim timing

**Method (3 lines).** Fresh panel reload (983 pools, `min_max_reserve=2000`, DB through ts 1787931300); entry-eligible bars = reserve≥15k ∧ fdv∈[1e5,3e7] ∧ vol_h1≥10k ∧ snapshot flow present → 8,513 bar-obs, 388 tokens (A: 1,985/67; B: 6,528/331). fwd60 = close[t+1]→close[t+61], terminal-extended (deaths count); all CIs = 95% cluster bootstrap by base_mint (4,000 draws); windows split at ts 1787860000; "net" = fwd60 after CostModel at **$200/side clip**: 80bps/side + impact 200/(reserve/2) + $0.10/side. Scripts: `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/{r2_extract,r2_stats,r2_supp,r2_forensic,r2_snapfix}.py`; tables `r2_obs.pkl`, `r2_events.pkl`.

**Panel note that matters for all replication claims:** OHLCV backfill has caught up since round 1 — window-B eligible tokens grew 81→331 *on the same wall-clock hours* (round-1's B sample was the collector's liquidity-ranked backfill priority queue, i.e. a biased subset). Round-1 effects that don't survive this completion were data artifacts, not regime change.

## 1) WASH-DIVERGENCE score

**Spec:** at bar t, cohort = all concurrently-eligible pools (cohort_n≥5; median 11, max 30). Score `wash = pctrank(vol_5m$) − pctrank(buyers_m5)` within cohort (vol_5m = trailing 5-bar OHLCV $vol; buyers from latest snapshot). Positive = volume-rank ≫ buyers-rank = wash-suspect. (Launch-cohort version is unpowered — round-1 showed 11 eligible pools total; concurrent-cohort is the tradable analogue.)

| tier | W | bars | tok | mean fwd60 [CI] | med | ew-token | net | eff vs rest [CI] | p(1s) |
|---|---|---|---|---|---|---|---|---|---|
| wash≥+0.25 | A | 274 | 29 | **+0.333 [+0.145,+0.560]** | +0.176 | +0.338 | +0.301 | **+0.323 [+0.113,+0.560]** | 0.001 |
| neutral | A | 1346 | 59 | +0.007 [−0.118,+0.136] | +0.025 | −0.004 | −0.015 | −0.168 [−0.422,+0.052] | 0.077 |
| buyer-heavy≤−0.25 | A | 287 | 34 | +0.025 [−0.304,+0.421] | −0.105 | −0.060 | −0.008 | −0.037 [−0.373,+0.382] | 0.376 |
| wash≥+0.25 | B | 1527 | 162 | +0.168 [+0.089,+0.248] | +0.097 | +0.129 | +0.138 | −0.013 [−0.170,+0.120] | 0.442 |
| neutral | B | 3166 | 268 | +0.093 [+0.015,+0.170] | +0.030 | +0.066 | +0.062 | −0.177 [−0.367,−0.021] | 0.011 |
| buyer-heavy≤−0.25 | B | 1428 | 147 | +0.379 [+0.104,+0.769] | +0.064 | +0.332 | +0.330 | +0.261 [−0.013,+0.656] | 0.033 |

Spearman(wash,fwd60): A **+0.298 [+0.115,+0.458]**; B +0.047 [−0.051,+0.145]. Decomposition: divergence *conditional on* high vol-rank (r_vol≥0.6: r_buy≤0.4 vs rest) = A +0.718 [−0.019,+1.446] (16 tok), B +0.010 [−0.131,+0.141] — in A the divergence itself carries the effect, not volume. Plain buyers-rank≥0.6: A −0.126 [−0.395,+0.121], B **+0.202 [+0.027,+0.424]**. Extreme cuts (±0.5): A cells 9/12 tokens = insufficient; B both extremes positive (smile: neutral middle worst).

**Autopsy answer:** the microstructure prior "vol-leader≠buyers-leader ⇒ wash ⇒ toxic" is **contradicted**: wash-suspect tier mean is CI-positive in BOTH windows and never underperforms. But which tail wins flips with regime (A: divergence/vol-side; B: buyer-breadth side, +20pp CI-positive), so no vs-complement effect is sign-consistent. **VERDICT: as an avoid/short flag — DEAD (the inversion). As a positive conditioner — window-inconsistent, not a candidate; carry `wash` and `pctrank(buyers_m5)` as regime-conditional composite features only.**

## 2) BUYERS-PER-TRADE >0.8 exclusion filter

Baselines: A +0.059 [−0.060,+0.181] (net +0.033); B +0.195 [+0.104,+0.304] (net +0.160).

| tier | W | bars | tok | mean [CI] | ew-token | net | eff vs rest [CI] |
|---|---|---|---|---|---|---|---|
| bpt>0.8 | A | 628 | 34 | +0.086 [−0.057,+0.262] | +0.056 | +0.062 | +0.040 [−0.127,+0.219] |
| **keep ≤0.8 (the filter)** | A | 1357 | 59 | +0.046 [−0.097,+0.175] | +0.013 | +0.020 | −0.040 [−0.225,+0.126] |
| bpt>0.8 | B | 1745 | 118 | +0.283 [+0.026,+0.629] | +0.289 | +0.240 | +0.120 [−0.132,+0.469] |
| **keep ≤0.8 (the filter)** | B | 4783 | 274 | +0.163 [+0.091,+0.240] | +0.084 | +0.130 | −0.120 [−0.461,+0.132] |

Replication split of B: **B1 (round-1 hours, now backfill-complete): bpt>0.8 effect +0.142 [−0.123,+0.479] (115 tier-tokens)** — round-1's −16.4pp [−32.4,−1.6] (48 tokens) does not survive sample completion; it was concentration + backfill-priority bias. B2 (new 4.2h): 3 tier-tokens = insufficient. The filter's remainder underperforms the unfiltered baseline in both windows (A −1.3pp, B −3.2pp gross; same net).

**VERDICT: DEAD — not an inversion candidate.** The "crowd tier is toxic in B" premise itself evaporated; excluding >0.8 removes the currently *best* B tier. Nothing to invert.

## 3) DIP-RECLAIM autopsy (pump ≥2x from launch, then dd ≤−35%)

Events on pools observed from creation (first bar ≤15min after create). Timings: `dip_trigger` = first bar with dd≤−35% (bonus counterfactual, the "falling knife"); `low_plus30` = post-dip minimum close +30min (low confirmed unbroken 30m); `reclaim` = first close-over-EMA5 cross with dd≤−17.5% (round-1 entry); `reclaim_plus60`.

| timing | W | n | tok | fwd60 [CI] | med | %>0 | winsor@300% [CI] | net$200 | fwd240 [CI] |
|---|---|---|---|---|---|---|---|---|---|
| dip_trigger | A | 26 | 25 | +0.788 [−0.096,+1.875] | −0.199 | 42% | +0.277 [−0.239,+0.867] | +0.291 | +1.766 [+0.126,+3.826] |
| **dip_trigger** | **B** | 55 | **53** | **+0.558 [+0.205,+0.947]** | **+0.260** | **56%** | **+0.481 [+0.180,+0.811]** | **+0.492** | **+0.664 [+0.184,+1.214]** |
| low_plus30 | A | 22 | 21 | −0.114 [−0.359,+0.192] | −0.075 | 36% | −0.114 [−0.348,+0.160] | −0.563 | +0.746 [−0.228,+2.110] |
| low_plus30 | B | 31 | 31 | +0.284 [−0.005,+0.614] | 0.000 | 48% | +0.255 [−0.003,+0.561] | +0.007 | +1.412 [−0.143,+4.223] |
| reclaim | A | 22 | 21 | +0.243 [−0.388,+0.996] | −0.329 | 32% | +0.096 [−0.418,+0.698] | +0.115 | +0.965 [−0.273,+2.590] |
| reclaim | B | 49 | 47 | +0.442 [+0.122,+0.783] | 0.000 | 45% | +0.424 [+0.118,+0.741] | +0.157 | +0.747 [+0.099,+1.554] |
| reclaim_plus60 | B | 20 | 20 | +0.667 [−0.169,+1.938] | +0.006 | 55% | +0.218 [−0.182,+0.704] | −0.004 | n.s. |

**Paired, same pool, dip_trigger − reclaim** (the timing question directly): B **+0.295 [+0.047,+0.583]**, winsorized **+0.209 [+0.014,+0.404]**, dip better in 71% of 47 tokens; A +0.474 [−0.232,+1.493] (same sign, n.s.). Mechanism: the EMA5 "reclaim" fires a **median 5 min** after the trigger at median dd −0.36 vs −0.44 — it is not a confirmation, it is buying the same bounce ~8–15pp higher. `low_plus30` entries sit at median dd −0.62 (the dip kept dipping; bounce spent) and net ≈ 0 or negative. Liquidity subset reserve≥10k: dip_trigger B +0.560 [+0.053,+1.129] (28 tok); A subsets 12 tok = insufficient.

**Censoring forensics (material):** 35/55 dip_trigger-B tapes end <55min post-entry. NOT rugs and NOT the collection edge: reserve at end median **$48k**, ratio-to-signal ≈1.00, only 1/35 <$3k, 33/35 pumpswap (locked LP), 3/35 near collection edge; rug-adjusting (censored ∧ reserve-collapsed → −100%) moves B mean only +0.558→+0.547. Snapshots stop *before* bars (newest-300 rotation artifact), so no independent forward price exists; bar-end = last actual trade (fetch round-robin verified: median 2.7h of confirmed zero trading post-freeze, though the final ~7h pre-now is unfetched for most). Frozen resting AMM price with intact locked reserve is exitable at $200 clip ⇒ terminal-price convention defensible; but the fully-observed-only subset (20 tok) is −0.042 [−0.437,+0.407] — the pooled positive comes from dip→bounce→goes-quiet pools, the still-trading subset keeps distributing. Round-1 `dip_reclaim` additionally died of gate-stacking (liq_stable ∧ ret_5m>−5% ∧ universe ∧ age caps → 7 OOS trades).

**VERDICT: INVERSION CANDIDATE (B-window, with stated caveat)** — drop the EMA-reclaim wait and the low+30 wait; enter at the −35%-from-high break itself (after ≥2x pump), 60min hold: B +55.8% gross / **+49.2% net** mean, median +26%, 53 tokens, CI excludes 0 gross+winsorized, survives rug-adjustment and reserve≥10k subset; paired test confirms trigger>reclaim. Window A: sign-consistent mean but CI spans 0 and median −0.20 → unproven, size to zero in cool tape. Caveat: ~2/3 of B events rely on frozen-resting-price exits; re-validate on next collection window with the collector patched to keep polling dipped pools (raise `snapshot_tracked` cap or track dippers explicitly). **(a) low+30: DEAD (net ≈0 in B, negative A). (b) EMA-reclaim: strictly dominated. (c) reclaim+60: DEAD (net −0.004).**

## Summary
- **Candidate:** dip-trigger entry (buy the −35% break post-2x-pump), B-window, net-positive at $200 clip; needs one clean OOS window + collector fix on dipped-pool tracking.
- **Dead:** wash-divergence as a wash-avoidance flag (it's positive-or-neutral everywhere — the inversion is that the prior was backwards); bpt>0.8 exclusion (round-1 negative was a backfill-incompleteness artifact — B1 re-test +0.142 [−0.12,+0.48]).
- **Insufficient:** wash-score extreme cuts in A (9–12 tok); bpt B2 fresh-hours split (3 tok); all A-window reserve≥10k dip subsets (12 tok); regime-conditional buyer-breadth rank (B-only significant, sign flips in A — re-test next window).
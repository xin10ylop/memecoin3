All computations are done. Compiling the report.

# PvP Leader Selection — does the first-45-min volume leader outperform its launch cohort?

## Methodology (3 lines)
Panel `load_panel(min_max_reserve=2000)` → 854 pools; kept the 690 pools born inside the snapshot-collection window (created_ts ≥ 1787841443−300; older pools have GT-backfilled bars but no snapshots at age 45m, hence never live-tradable). Cohorts = 30-min buckets of `pool_created_at` epoch (`created_ts//1800`); within each of the 28 buckets with ≥3 pools (680 pools, median bucket = 22 pools) every pool — including ones that died before 45m, whose volume still competes — got `share_vol` = its first-45-min Σvol_usd / bucket total, and `share_buy` = Σbuyers_m5 over unique snapshot rows in first 45m / bucket total; rank 1 = leader. Signal bar = first bar with age ≥45m (must be ≤50m), entry = NEXT-bar close, exits at entry+60m/+240m closes, terminal-extended via ts-searchsorted (robust to non-contiguous grids); windows split on signal ts vs 1787860000; diffs of means cluster-bootstrapped by base_mint (4000 reps, percentile CI).

## Sample funnel (the headline constraint)
| stage | n |
|---|---|
| pools in ≥3-pool creation buckets | 680 (28 buckets) |
| alive at age 45m with valid next-bar entry | 154 (A: 56, B: 98) |
| **entry-eligible** at signal bar (reserve≥15k, fdv 1e5–3e7, vol_h1≥10k) | **11** (A: 6, B: 5) |
| bucket leaders (rank_vol=1): 28 → alive at 45m: 10 → eligible: 4 | |

Eligibility ≠ leadership: eligible pools had vol-ranks {1:3, 2:2, 3:3, 6:1, 12:1, 13:1}. Vol-leader and buyers-leader agree in only **2/28 buckets** (volume prints ≠ buyer breadth — wash/bot volume decouples them).

## Table 1 — leader (rank 1) vs rest, mean fwd return, diff = leader−rest, cluster-bootstrap 95% CI
**PRIMARY: entry-eligible universe (the only live-tradable one)**
| ranking | win | h | leader mean (n/tok) | rest mean (n/tok) | diff [CI] |
|---|---|---|---|---|---|
| vol | A | 60m | −0.146 (2/2) | +0.254 (4/4) | −0.400 [−0.901,+0.075] |
| vol | A | 240m | −0.354 (2/2) | −0.106 (4/4) | −0.248 [−1.045,+0.597] |
| vol | B | 60m | +0.000 (1/1) | +0.102 (4/4) | −0.102 [−0.258,+0.000] |
| vol | B | 240m | +0.000 (1/1) | +0.102 (4/4) | −0.102 [−0.240,+0.000] |
| buyers | A | 60m | +0.058 (1/1) | +0.133 (5/5) | −0.076 [−0.394,+0.273] |
| buyers | A | 240m | −0.847 (1/1) | −0.057 (5/5) | −0.790 [−1.114,−0.326] |
| buyers | B | — | INSUFFICIENT (no eligible buyers-leader in B) | | |

Every leader cell has 1–2 tokens per window → **insufficient data by the ≥15-token rule**; CIs shown for completeness only.

**SECONDARY (descriptive, NOT live-tradable): all age-45 survivors**
| ranking | win | h | leader mean/med (n/tok) | rest mean/med (n/tok) | diff [CI] | winsorized[−1,4] diff [CI] |
|---|---|---|---|---|---|---|
| vol | A | 60m | −0.013/+0.171 (3/3) | +0.031/+0.003 (53/53) | −0.045 [−0.516,+0.258] | −0.045 [−0.515,+0.256] |
| vol | A | 240m | −0.152/+0.171 (3/3) | +0.173/0.000 (53/53) | −0.325 [−1.126,+0.215] | −0.300 [−1.102,+0.229] |
| vol | B | 60m | +0.300/+0.138 (7/7) | +0.197/+0.065 (91/88) | +0.103 [−0.159,+0.412] | +0.103 [−0.163,+0.406] |
| vol | B | 240m | +0.372/+0.138 (7/7) | +0.907/+0.057 (91/88) | −0.534 [−1.621,+0.293] | +0.006 [−0.375,+0.466] |
| buyers | A | 60m | −0.352/−0.154 (3/3) | +0.050/+0.003 (53/53) | −0.402 [−1.026,+0.036] | −0.402 [−1.036,+0.028] |
| buyers | A | 240m | −0.782/−0.847 (3/3) | +0.209/+0.003 (53/53) | **−0.990 [−1.349,−0.642]** | **−0.965 [−1.280,−0.629]** |
| buyers | B | 60m | +0.687/+0.372 (7/7) | +0.168/+0.065 (91/89) | +0.520 [−0.018,+1.191] | +0.520 [−0.003,+1.164] |
| buyers | B | 240m | +6.113/+0.042 (7/7) | +0.465/+0.070 (91/89) | +5.648 [−0.977,+20.190] | +0.456 [−0.848,+1.969] |

Both rankings flip sign A→B (vol: −/+ at 60m; buyers: − in A, + in B; the B-buyers +6.1 mean is one 20x outlier — winsorized it collapses to +0.46, CI spans 0). Leader group is 3/7 tokens per window — below the 15-token floor everywhere.

## Table 2 — continuous version: Spearman(share, fwd ret) among all survivors, cluster-bootstrap CI
| feature | win | fwd60 rho [CI] | fwd240 rho [CI] | n/tok |
|---|---|---|---|---|
| share_vol | A | +0.187 [−0.104,+0.461] | +0.030 [−0.260,+0.313] | 56/56 |
| share_vol | B | +0.176 [−0.009,+0.349] | **+0.251 [+0.072,+0.412]** | 98/95 |
| share_buy | A | −0.145 [−0.433,+0.171] | −0.121 [−0.403,+0.183] | 56/56 |
| share_buy | B | +0.140 [−0.074,+0.359] | +0.019 [−0.222,+0.260] | 98/95 |

## Censoring caveat (material)
Forward coverage after entry: window A median 90.5m (34/56 obs ≥60m, 21/56 ≥240m); window B median 61m (50/98 ≥60m, only **9/98 ≥240m**) — B fwd240 is mostly terminal-extended. Worse, 3 of the 5 eligible-B rows have 0–2 min of forward bars (pool tape ended at the signal; fwd≈0 is the resting-price assumption, not an observed trade path). The eligible-B leader cell is effectively n≈0 informative observations.

## VERDICT
- **"Trade only the vol leader" (rank-1 binary filter): DEAD END on current data.** Leader−rest diff is sign-INCONSISTENT across windows (negative in A, positive in B at 60m; winsorized 240m ≈ 0 in B), no CI excludes zero in the tradable universe, and every leader cell holds 1–7 tokens per window vs the 15-token floor → insufficient data even before the sign flip. Structurally the filter is also near-vacuous: the eligibility gate already removes 26 of 28 non-leader cohorts' low-volume pools, and 4 of 28 leaders were even tradable at 45m.
- **"Trade only the buyers leader": DEAD END, possibly inverted.** Sign-inconsistent (A strongly negative — fwd240 diff −0.97, CI [−1.28,−0.63], but only 3 tokens; B positive) → fails the consistency rule; the A-side hint that buyer-count leaders underperform is 3 tokens, insufficient.
- **Weak CANDIDATE (redefined, continuous): cohort volume SHARE as a monotone feature.** Spearman(share_vol, fwd) is positive in all 4 window×horizon cells, CI excludes zero in B/fwd240 (+0.251 [+0.07,+0.41]) and is same-sign in A — this technically meets the candidate rule, but B/fwd240 rests on heavily censored returns (9/98 full-horizon) and A/fwd240 is ≈0. Recommend: carry `share_vol` (or vol45 vs cohort) into the composite as a continuous score to re-test when the collector has 1–2 more weeks of data; do NOT ship rank-1-only gating.
- Side finding worth its own test later: vol-leader ≠ buyers-leader in 26/28 buckets — divergence between $-volume and buyer breadth within a cohort may itself be a wash-trading flag.

Intermediates (per-pool obs + rankings): `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/pvp_obs.csv`, `.../pvp_ranked.csv`; scripts `.../extract2.py`, `.../analyze.py`; cached panel `.../panel.pkl`.
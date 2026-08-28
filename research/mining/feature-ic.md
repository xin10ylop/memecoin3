All computations succeeded. Composing the report.

# Per-Feature Predictive Power at Entry-Eligible Bars (Spearman rank IC)

**Methodology (3 lines).** Loaded panel via `memebot.data.store.load_panel(min_max_reserve=2000)` → 837 pools; re-gridded 28 pools the loader left sparse (>10k-row span) to the continuous minute grid; features from `memebot.features.add_features` plus turnover=`vol_5m/reserve_usd`, `log(fdv)`, `reserve_usd.pct_change(30)`. Entry-eligible bars (reserve_usd≥15k, fdv∈[1e5,3e7], vol_h1_snap≥1e4, last bar excluded) sampled every 10th per pool; forward return = close[t+h]/close[t]−1 with terminal close when the series ends early (h=30/60/120). IC = pooled Spearman; 95% CI = percentile cluster bootstrap (B=1000) resampling **tokens** (base_mint, fallback pool address) with replacement, same token-resample reused across cells; windows split at ts=1787860000.

**Sample.** Window A: 221 obs / **66 tokens** (66 pools), ts 1787841480–1787852220 (~3h). Window B: 732 obs / **284 tokens** (289 pools), ts 1787875560–1787915280 (~11h). **Data-coverage caveat:** snapshots begin at ts=1787841443, so no bar before Aug 27 ~16:00 UTC can be entry-eligible — window A is effectively 3 hours of tape, and there is a ~6.5h eligibility gap (collector downtime) between the windows. Forward returns are heavily right-skewed (fwd_30: mean +18.0%, median +5.7%, min −99.98%, max +2422%) — Spearman is rank-based so outlier-robust, but the tape is unusually hot.

## IC table — Window A (cool tape, ts<1787860000; 66 tokens, 221 obs max)

| feature | IC h30 [95% CI] | IC h60 [95% CI] | IC h120 [95% CI] | n_obs | n_tok |
|---|---|---|---|---|---|
| buy_frac | +0.059 [−0.108, +0.223] | +0.074 [−0.113, +0.241] | +0.094 [−0.103, +0.280] | 221 | 66 |
| buyers_per_min | +0.128 [−0.082, +0.312] | +0.075 [−0.150, +0.291] | +0.019 [−0.225, +0.261] | 221 | 66 |
| vol_z | +0.143 [−0.026, +0.326] | +0.140 [−0.018, +0.302] | **+0.164 [+0.012, +0.324]** | 177 | 48 |
| turnover | **+0.286 [+0.063, +0.439]** | +0.239 [−0.018, +0.420] | +0.206 [−0.094, +0.431] | 221 | 66 |
| age_min | **−0.317 [−0.491, −0.105]** | **−0.258 [−0.447, −0.025]** | −0.190 [−0.400, +0.043] | 221 | 66 |
| log_fdv | −0.078 [−0.325, +0.155] | +0.024 [−0.235, +0.265] | +0.120 [−0.139, +0.363] | 221 | 66 |
| reserve_chg_5m | +0.150 [−0.095, +0.362] | +0.174 [−0.042, +0.383] | +0.154 [−0.051, +0.345] | 159 | 49 |
| reserve_chg_30m | **+0.375 [+0.147, +0.608]** | +0.207 [−0.098, +0.509] | +0.136 [−0.191, +0.475] | 62 | 34 |
| dd_from_high | **+0.364 [+0.180, +0.540]** | **+0.379 [+0.158, +0.567]** | **+0.425 [+0.191, +0.603]** | 221 | 66 |
| run_from_first | +0.162 [−0.061, +0.363] | +0.170 [−0.093, +0.401] | +0.189 [−0.091, +0.438] | 221 | 66 |
| rv_30 | −0.157 [−0.364, +0.095] | **−0.276 [−0.496, −0.004]** | **−0.330 [−0.547, −0.046]** | 196 | 56 |

## IC table — Window B (hot tape, ts≥1787860000; 284 tokens, 732 obs max)

| feature | IC h30 [95% CI] | IC h60 [95% CI] | IC h120 [95% CI] | n_obs | n_tok |
|---|---|---|---|---|---|
| buy_frac | +0.088 [−0.000, +0.182] | **+0.099 [+0.007, +0.196]** | +0.073 [−0.023, +0.177] | 732 | 284 |
| buyers_per_min | **+0.164 [+0.081, +0.251]** | **+0.170 [+0.077, +0.264]** | **+0.172 [+0.074, +0.264]** | 732 | 284 |
| vol_z | **+0.122 [+0.006, +0.224]** | +0.117 [−0.007, +0.229] | +0.088 [−0.022, +0.194] | 375 | 196 |
| turnover | **+0.218 [+0.130, +0.293]** | **+0.210 [+0.112, +0.290]** | **+0.224 [+0.123, +0.309]** | 732 | 284 |
| age_min | **−0.197 [−0.286, −0.099]** | **−0.183 [−0.279, −0.087]** | **−0.170 [−0.269, −0.066]** | 732 | 284 |
| log_fdv | −0.026 [−0.122, +0.076] | −0.009 [−0.110, +0.099] | −0.026 [−0.129, +0.089] | 732 | 284 |
| reserve_chg_5m | +0.062 [−0.037, +0.159] | +0.078 [−0.021, +0.180] | +0.064 [−0.042, +0.168] | 450 | 237 |
| reserve_chg_30m | +0.190 [−0.051, +0.434] | +0.176 [−0.076, +0.412] | +0.139 [−0.114, +0.365] | 74 | 41 |
| dd_from_high | **+0.316 [+0.234, +0.395]** | **+0.320 [+0.236, +0.403]** | **+0.299 [+0.216, +0.387]** | 732 | 284 |
| run_from_first | +0.096 [−0.015, +0.204] | +0.086 [−0.029, +0.191] | +0.093 [−0.030, +0.205] | 732 | 284 |
| rv_30 | −0.112 [−0.227, +0.004] | **−0.126 [−0.243, −0.006]** | −0.117 [−0.245, +0.012] | 550 | 259 |

(Bold = cluster-bootstrap 95% CI excludes zero. n_obs/n_tok identical across horizons within a cell because forward returns are never NaN; NaN fractions come from the feature: vol_z 42%, reserve_chg_5m 36%, reserve_chg_30m 86% — sparse asof-carried snapshots — rv_30 22%.)

## VERDICT

**Composite-strategy candidates** (sign-consistent in both windows AND CI excluding zero in ≥1 window), ranked:

1. **dd_from_high (+)** — strongest by far: IC +0.30…+0.43, all 6 CIs exclude zero, both windows, all horizons. Since dd_from_high ≤ 0, this is a near-high-water-mark momentum effect: tokens at/near their HWM outperform; deep-drawdown tokens keep dying. Full token counts (66/284).
2. **turnover = vol_5m/reserve (+)** — IC +0.21…+0.29; all 3 B-CIs exclude zero, A@30 excludes zero, sign-consistent everywhere. Hot pools relative to their liquidity keep running.
3. **age_min (−)** — IC −0.17…−0.32; excludes zero in 5/6 cells. Younger eligible pools have higher forward returns at every horizon in both windows.
4. **buyers_per_min (+)** — all 3 B-CIs exclude zero (IC ~+0.17); A same-sign at every horizon but noisy (A@120 only +0.019 — nearly flat, so treat the long horizon as B-only evidence).
5. **rv_30 (−)** — sign-consistent negative everywhere; excludes zero at A@60, A@120, B@60. High recent realized vol predicts worse forward returns — a chop/blow-off filter, not a return driver.
6. **vol_z (+)** — sign-consistent; excludes zero at A@120 and B@30, borderline elsewhere. Weaker cousin of turnover (and 42% NaN early in pool life).
7. **buy_frac (+)** — marginal candidate: sign-consistent, but only B@60 excludes zero (+0.099 [+0.007, +0.196]) and B@30 touches zero. Small standalone edge; likely subsumed by buyers_per_min/turnover.
8. **reserve_chg_30m (+)** — qualifies technically (A@30 +0.375 [+0.147, +0.608], B same-sign), but on only 62/74 obs and 34/41 tokens (≥15, so not "insufficient", yet fragile) with 86% NaN coverage. Treat as promising-unconfirmed liquidity-inflow momentum; fix snapshot-history coverage before trusting it.

**Dead ends:**
- **log_fdv** — sign flips across horizons in A, ~0 in B, every CI spans zero. Market cap level carries no rank information inside the eligible band.
- **reserve_chg_5m** — positive in all 6 cells but no CI excludes zero anywhere (5-min snapshot granularity ≈ measurement noise + heavy ties from asof-carried reserves). Fails the criterion; its 30-bar version is where the signal lives.
- **run_from_first** — positive in all 6 cells, but no CI excludes zero; largely redundant with dd_from_high, which dominates it.

**Caveats:** window A is only ~3h of tape (snapshots begin ts=1787841443, so nothing earlier is entry-eligible) and both windows sit within the same ~21h of market regime — "cross-window consistency" here is a weak out-of-sample test, not two independent regimes. IC magnitudes (0.1–0.4) are inflated by the hot tape and by terminal-price fills capturing full rug losses; expect shrinkage. Coherent composite picture: **young pool, near its high, high turnover and buyer flow, without extreme 30-min realized vol.**

Artifacts: sample builder `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/build_sample.py`, IC script `.../compute_ic.py`, full results CSV `.../ic_results.csv`, sampled dataset `.../sample.pkl`.
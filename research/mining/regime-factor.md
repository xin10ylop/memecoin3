Both robustness checks strengthen the findings. Compiling the final report.

# Regime Factor Refinement — Cohort Momentum (data/panel.db)

**Methodology (3 lines).** Loaded panel via `memebot.data.store.load_panel` (840 liq-filtered pools); factor = `cohort_momentum(pools)` (per-minute median trailing-30m return, liq≥$15k pools). Entry-eligible bars: reserve≥$15k, fdv∈[1e5,3e7], vol_h1≥$1e4; forward return = c[t+61]/c[t+1]−1 (enter next-bar close, exit 60m later, continuous minute grid). All CIs = 95% cluster bootstrap by base_mint (3,000 draws); windows A (ts<1787860000) and B reported separately; winsorized = fwd60 clipped ±100%.

**Universe actually available.** A: 303 tape minutes (~5h), factor defined 155; 1,612 eligible bars / **47 tokens**. B: 923 minutes (~15.4h), factor defined 513; 2,275 bars / **78 tokens**. Factor distribution differs violently by window — A: median +0.5%, p90 +2.8%; B: median **+10.2%**, p90 +132% (fresh-launch pools dominate the median on the hot tape). Unconditional mean fwd60: A +3.9% CI[−10.7,+18.4]; B **+14.5% CI[+3.7,+24.7]** — window B's tape is positive by itself, so all B gates must be read against that baseline.

## (1) Persistence

Spearman autocorrelation of factor (Pearson on ±50%-winsorized in parens):

| lag (min) | A (n pairs) | B (n pairs) |
|---|---|---|
| 5 | **+0.51** (+0.25, n=150) | **+0.37** (+0.33, n=456) |
| 10 | +0.16 (+0.01) | +0.08 (+0.11) |
| 15 | +0.04 (−0.11) | +0.06 (+0.14) |
| 30 | +0.20 (+0.15) | +0.06 (+0.07) |
| 60 | −0.10 (−0.10, n=95) | +0.04 (+0.07, n=419) |
| 90 | −0.24 (−0.32) | +0.05 (+0.06) |
| 120 | +0.15 (+0.09, n=35) | −0.05 (−0.11) |

State transition at +60m, thr=2%: A P(hi→hi)=0.11 vs P(lo→hi)=0.30 — but only **9 hi minutes: insufficient data**. B: P(hi→hi)=0.619 vs P(lo→hi)=0.657, base 0.635 (n=419) — **zero minute-level persistence at 1h**. **Answer: high now does NOT predict high next hour.** Memory dies within ~5–10 min; the gate's value (below) comes from slow multi-hour regime contrast, not level persistence — which argues for a sticky/hysteresis gate over level-chasing.

## (2) Threshold sweep — mean fwd60 | factor > thr (eligible bars, factor defined)

**Window A** (46 tokens baseline):

| thr | TIM | bars | tokens | mean | 95% CI | median | on−off diff [CI] |
|---|---|---|---|---|---|---|---|
| −0.02 | 1.00 | 1596 | 46 | +.039 | [−.107,+.184] | +.023 | — |
| 0.00 | 0.67 | 1070 | 38 | +.059 | [−.082,+.219] | +.025 | +.059 [−.273,+.296] |
| 0.01 | 0.19 | 297 | 27 | +.052 | [−.091,+.204] | +.007 | +.016 [−.206,+.224] |
| 0.02 | 0.10 | 156 | 19 | +.120 | [−.060,+.302] | +.004 | +.090 [−.142,+.310] |
| 0.03 | 0.04 | 64 | 19 | **+.253** | **[+.013,+.513]** | +.018 | +.223 [−.065,+.553] |
| 0.05 | 0.004 | 6 | **6 — insufficient** | +.039 | [−.384,+.409] | −.005 | ≈0 |
| 0.08 | 0.004 | 6 | **6 — insufficient** | +.039 | [−.383,+.410] | −.005 | ≈0 |

**Window B** (78 tokens baseline):

| thr | TIM | bars | tokens | mean | 95% CI | median | on−off diff [CI] |
|---|---|---|---|---|---|---|---|
| −0.02 | 0.98 | 2178 | 78 | +.145 | [+.038,+.248] | +.110 | −.037 [−.516,+.383] (off: 11 tok, insufficient) |
| 0.00 | 0.75 | 1672 | 76 | +.162 | [+.041,+.272] | +.148 | +.065 [−.041,+.177] |
| 0.01 | 0.50 | 1114 | 72 | +.207 | [+.106,+.321] | +.191 | +.122 [−.013,+.253] |
| 0.02 | 0.39 | 880 | 60 | +.219 | [+.102,+.347] | +.206 | +.121 [−.032,+.284] |
| 0.03 | 0.36 | 801 | 59 | +.214 | [+.081,+.361] | +.214 | +.106 [−.057,+.283] |
| 0.05 | 0.33 | 728 | 51 | +.213 | [+.062,+.373] | +.220 | +.101 [−.100,+.293] |
| 0.08 | 0.29 | 640 | 48 | +.213 | [+.059,+.385] | +.230 | +.095 [−.102,+.285] |

On−off diff is positive in both windows for thr 0.00–0.03; monotone improvement flattens above 0.02–0.03. Winsorized diffs: thr 0.03 → A +.167 **CI[+.015,+.315]**, B +.110 [−.034,+.257]; thr 0.02 → A +.099 [−.064,+.262], B +.117 [−.019,+.262]. Caveat: in A the gated **mean** rises while the **median falls** (+.023→+.004 at thr .02) — window-A gate profits are tail-driven (a few tokens' pumps).

## (3) Hysteresis (on@+2% / off@0%, NaN carries state) vs simple >2%

| win | gate | min-on | switches | TIM(bars) | on mean [CI] | on tok | off mean (tok) | diff [CI] | wins. diff [CI] |
|---|---|---|---|---|---|---|---|---|---|
| A | hyst | 0.23 | 9 | 0.364 | +.049 [−.075,+.184] | 27 | +.027 (47) | +.022 [−.249,+.261] | +.100 [−.070,+.290] |
| A | simple | 0.09 | 15 | 0.097 | +.120 [−.051,+.291] | 19 | +.026 (47) | +.094 [−.133,+.325] | +.103 [−.053,+.265] |
| B | hyst | 0.50 | 44 | 0.500 | **+.239 [+.136,+.353]** | 65 | +.058 (68) | **+.180 [+.025,+.352]** | **+.154 [+.019,+.307]** |
| B | simple | 0.34 | 70 | 0.387 | +.219 [+.104,+.353] | 60 | +.104 (73) | +.114 [−.036,+.272] | +.109 [−.022,+.256] |

Hysteresis wins: it is the **only** gate whose on−off diff CI excludes zero (window B, raw and winsorized), with sign-consistent (positive) diff in A; it delivers 30–280% more time-in-market than the simple cutoff and ~40% fewer regime switches (9 vs 15 in A, 44 vs 70 in B — less flip-flop cost in a live system).

## (4) Alternative breadth factors

Spearman rank correlation with cohort momentum (minutes with cm defined): `pos_frac` (fraction of eligible pools with trailing 30m ret>0, ≥3 pools; defined 155/155 A, 222/513 B): **+0.67 (A) / +0.65 (B)** — largely redundant. `cross_60m` (pools newly crossing tradable gate, trailing 60m): **−0.47 (A) / −0.27 (B)** — orthogonal-to-opposed. `elig_n` (eligible-pool count): −0.46 / −0.46.

Univariate above/below per-window median (eligible bars):

| factor | win | hi mean [CI] (tok) | lo mean (tok) | diff [CI] | wins. diff [CI] |
|---|---|---|---|---|---|
| pos_frac | A | +.074 [−.061,+.228] (38) | +.015 (46) | +.059 [−.113,+.200] | **+.080 [+.007,+.158]** |
| pos_frac | B | +.242 [+.113,+.379] (56) | +.048 (66) | **+.195 [+.065,+.338]** | **+.150 [+.045,+.259]** |
| cross_60m | A | +.040 [−.143,+.239] (42) | +.031 (39) | +.009 [−.237,+.255] | — |
| cross_60m | B | +.261 [+.109,+.428] (48) | +.061 (67) | +.200 [−.011,+.434] | — |
| elig_n | A | +.116 (45) | −.021 (43) | +.137 [−.068,+.406] | — |
| elig_n | B | +.135 (67) | +.162 (65) | **−.027** [−.179,+.145] | sign flip |

Disagreement cells (cm>2% × alt>median): pos_frac orders returns within every cm stratum in both windows — cm_hi&pf_lo: A −.039 (22 bars/19 tok) vs cm_hi&pf_hi +.146; B cm_lo&pf_hi **+.221 [+.069,+.388]** (49 tok) vs cm_lo&pf_lo +.021 — pos_frac rescues true up-tape that the launch-skewed median misses. cross_60m: best cell is cm_hi&cross_hi in both windows (A +.289 [−.004,+.619], 14 tok; B +.267 [+.099,+.459]) but flat/inverted in A's cm_lo stratum — B-only. Combined gate hyst OR pf_hi: B diff **+.186 [+.039,+.332]** raw, **+.152 [+.019,+.291]** winsorized, TIM 0.62, 74 tokens; A same-sign (+.048 raw; +.104 [−.009,+.235] winsorized, just short of zero-exclusion).

## VERDICT

**Composite-strategy candidates** (sign-consistent both windows, cluster-CI excluding zero in ≥1 window):
1. **Hysteresis cohort-momentum gate on@+2%/off@0% — the best regime specification.** Diff positive in both windows; CI excludes zero in B (raw +.180 [+.025,+.352] and winsorized); more time-in-market and fewer switches than the simple cutoff. Adopt over the plain 2% threshold.
2. **pos_frac breadth (>~0.7, i.e., per-window median)** — the statistically strongest single conditioner: winsorized diff CI excludes zero in **both** windows (+.080 A, +.150 B). Redundant with cm (ρ≈0.65) as a standalone, but adds real information in disagreement cells; **hyst-OR-pos_frac** composite is the best-performing gate in B (+.186 [+.039,+.332], 74 tokens) and same-sign in A.
3. **Simple cm>0.03** — conditional mean CI excludes zero in both windows and winsorized diff CI excludes zero in A; usable, but only 4% TIM in A and dominated by the hysteresis spec.

**Dead ends:** factor-level persistence at 60m (autocorr ≈0 beyond ~10 min in both windows — do not forecast the factor, gate on it); thresholds ≥0.05 (**insufficient data** in A: 6 tokens; no incremental edge in B); eligible-pool count `elig_n` (sign flips A vs B); `cross_60m` gate-crossing count standalone (≈0 effect in A, negatively rank-correlated with cm — B-only artifact).

**Caveats (do not over-trust):** total tape is ~20h across 2 sessions; window A high-threshold cells rest on 19 tokens and are tail-driven (gated median falls while mean rises); window B's baseline is itself +14.5%, so part of every B gate is "being in the hot session"; returns are gross of costs. No computations failed; pos_frac is undefined on 57% of B minutes (<3 eligible pools with 30m history) — treat undefined as gate-carry, not gate-off.

Analysis artifacts: `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/{build_cache.py, analyze.py, bars.pkl, factors.pkl}`.
# THE OPPORTUNITY SURFACE — verified net expectancy across (cohort × horizon)

## Method (3 lines)
1. **Raw bars only.** `ohlcv` in `panel.db` contains **zero** rows with `vol_usd<=0` — the continuous resting-price grid is manufactured by `store._load_pool_df`, not stored. I reproduced that loader's cleaning (`sanitize_bars` + `_repair_rebased_segments`) but **kept only traded minutes**, so every price on both ends of every return is a print that actually happened.
2. **Sampling** ≤1 obs/pool/clock-hour, entry bar always has real volume, and (primary sample "SNAP") the bar must have a GeckoTerminal snapshot within the preceding 600 s — so `reserve_usd`/`fdv_usd` are known **causally** and the pool was demonstrably under live observation (100 % reachable). **6,845 obs / 4,752 pools / 4,598 tokens**, 2026-08-27 14:38 → 08-30 11:25 UTC.
3. **Verification** exactly as mandated: exit = nearest real print within ±2 min of the horizon **(a)**, and ≥10 more traded minutes after it **(b)**; costs = `CostModel` (0.8 %/side + `clip/(reserve/2)` impact + $0.10/tx) at a **$50 clip**; CIs = 2,000-draw cluster bootstrap over `base_token_address`.

---

## 1. Verification ledger — the discards are the headline

| horizon | sampled | **verified** | tokens | **DISCARDED** | % | …no print at horizon | …**pool went dead** | …**coverage censored** |
|---|---|---|---|---|---|---|---|---|
| 15m | 6,845 | 2,223 | 974 | **4,622** | **67.5 %** | 73 | 916 | 3,633 |
| 1h | 6,845 | 1,412 | 320 | **5,433** | **79.4 %** | 110 | 1,117 | 4,206 |
| 4h | 6,845 | 1,005 | 168 | **5,840** | **85.3 %** | 207 | 1,214 | 4,419 |
| 12h | 6,845 | 709 | 97 | **6,136** | **89.6 %** | 182 | 1,260 | 4,694 |
| 24h | 6,845 | 506 | 50 | **6,339** | **92.6 %** | 64 | 1,281 | 4,994 |

**A second data artifact I had to handle, not previously documented:** the OHLCV fetcher rotates. Only **126 of 5,914 pools** were re-fetched within 60 min of the data edge; median fetch staleness is **1,722 min (29 h)**. So a pool's bar series usually ends because *we stopped looking*, not because it died. I classify per pool using `ohlcv_state.last_fetch_at`: **dead** = silent >60 min while we were still fetching; **censored** = series ends at the coverage edge. Censoring is **73–79 % of all discards** — this is the same "edge of our data coverage" failure mode as the original artifact, just at pool granularity.

## 2. The original artifact, re-measured on this sample (net of costs)

| horizon | naive (resting-grid / data-edge exit, n=6,845) | verified | **mirage gap** |
|---|---|---|---|
| 15m | mean **+35.4 %**, med −1.0 % | mean +30.4 %, med −1.7 % | +5 pp |
| 1h | mean **+215.4 %**, med −0.9 % | mean +26.0 %, med −2.1 % | **+189 pp** |
| 4h | mean **+220.2 %**, med −0.8 % | mean +35.8 %, med −2.1 % | **+184 pp** |
| 12h | mean **+229.6 %**, med −0.8 % | mean +29.5 %, med −2.3 % | **+200 pp** |
| 24h | mean **+230.0 %**, med −0.7 % | mean +9.1 %, med −2.5 % | **+221 pp** |

The +46 %/trade mirage reproduces cleanly. Note it is **not** a 15-minute problem — it explodes from 1 h out, exactly where pools start running past our coverage.

## 3. The discard is NOT random (this is the load-bearing caveat)

5-minute forward net return — observable for nearly every observation — split by what each observation's **1-hour** class later turned out to be:

| class at 1h | n | mean 5m | median 5m | frac >0 |
|---|---|---|---|---|
| verified | 1,388 | +0.05 % | −2.0 % | 0.169 |
| dead | 749 | **+13.7 %** | **+7.6 %** | 0.644 |
| coverage-censored | 3,266 | **+14.8 %** | **+2.8 %** | 0.589 |
| no print at horizon | 90 | −8.8 % | −2.4 % | 0.167 |

The observations we can measure and the ones we throw away differ by **~14 pp of mean return and 42 pp of win rate on a pre-horizon statistic**. The measurable subset is a biased draw. The bias does not have a clean sign — the discards were *winning* at +5 min and then either rugged or vanished from coverage — which is precisely why no estimator on the verified subset alone can be trusted.

**Dead pools are resolvable, though:** of 943 dead pools, **55 % had last-snapshot reserve <20 % of their lifetime max (liquidity pulled = rug)**, 41 % were intact-but-silent. That licenses a **dead-aware** estimator: rugged → −100 %, intact → exit at its last real print with 3× impact. Coverage-censored observations remain excluded (genuinely unknowable).

## 4. THE SURFACE — cohort × horizon, verified net (mandated) and dead-aware

`DISC` = discarded; `d_dead`/`d_cens` decompose it. `x-top3` = mean after deleting the 3 best trades. `DA` = dead-aware. <15 tokens flagged INSUFF.

| cohort | H | n_obs | n_tok | DISC | d_dead | d_cens | mean | med | cluster CI | f>0 | x-top3 | DA n | DA mean | DA med | DA CI | |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL (unconditional) | 15m | 2223 | 974 | 4622 | 916 | 3633 | +0.304 | -0.017 | [+0.152, +0.530] | 0.39 | +0.175 | 3139 | +0.038 | -0.023 | [-0.064, +0.185] | |
| ALL (unconditional) | 1h | 1412 | 320 | 5433 | 1117 | 4206 | +0.260 | -0.021 | [-0.010, +0.835] | 0.26 | +0.009 | 2529 | +0.006 | -0.037 | [-0.164, +0.274] | |
| ALL (unconditional) | 4h | 1005 | 168 | 5840 | 1214 | 4419 | +0.358 | -0.021 | [+0.005, +1.323] | 0.23 | +0.035 | 2219 | +0.075 | -0.064 | [-0.152, +0.448] | |
| ALL (unconditional) | 12h | 709 | 97 | 6136 | 1260 | 4694 | +0.295 | -0.023 | [-0.063, +1.382] | 0.20 | -0.038 | 1969 | +0.413 | -0.127 | [-0.163, +1.426] | |
| ALL (unconditional) | 24h | 506 | 50 | 6339 | 1281 | 4994 | +0.091 | -0.025 | [-0.067, +0.476] | 0.18 | -0.033 | 1787 | +0.360 | -0.168 | [-0.194, +1.555] | |
| age 0-1h | 15m | 1048 | 854 | 4318 | 895 | 3399 | **+0.637** | **+0.106** | **[+0.354, +1.057]** | 0.64 | +0.377 | 1943 | +0.063 | -0.132 | [-0.095, +0.282] | |
| age 0-1h | 1h | 313 | 211 | 5053 | 1086 | 3913 | +1.142 | -0.107 | [-0.044, +3.257] | 0.44 | +0.018 | 1399 | +0.013 | -0.682 | [-0.274, +0.479] | |
| age 0-1h | 4h | 111 | 79 | 5255 | 1171 | 4011 | +3.242 | -0.182 | [+0.209, +9.071] | 0.47 | +0.329 | 1282 | +0.136 | -0.864 | [-0.229, +0.703] | |
| age 0-1h | 12h | 47 | 34 | 5319 | 1207 | 4071 | +4.861 | -0.337 | [-0.257, +15.737] | 0.43 | -0.132 | 1254 | +0.043 | -0.918 | [-0.279, +0.536] | |
| age 0-1h | 24h | 9 | 6 | 5357 | 1224 | 4124 | +6.109 | +0.484 | [-0.500, +16.426] | 0.67 | -0.192 | 1233 | -0.101 | -0.931 | [-0.298, +0.170] | INSUFF |
| age 1-6h | 15m | 106 | 51 | 74 | 18 | 55 | -0.018 | +0.015 | [-0.086, +0.047] | 0.61 | -0.049 | 124 | -0.080 | +0.009 | [-0.159, -0.016] | |
| age 1-6h | 1h | 87 | 41 | 93 | 24 | 68 | +0.100 | +0.136 | [-0.056, +0.261] | 0.62 | +0.028 | 111 | +0.000 | +0.077 | [-0.144, +0.149] | |
| age 1-6h | 4h | 40 | 21 | 140 | 35 | 98 | +0.343 | -0.018 | [-0.240, +0.989] | 0.47 | +0.009 | 75 | +0.108 | -0.167 | [-0.266, +0.503] | |
| age 1-6h | 12h | 11 | 6 | 169 | 35 | 127 | -0.495 | -0.358 | [-0.719, -0.383] | 0.00 | -0.595 | 46 | -0.241 | -0.251 | [-0.565, +0.121] | INSUFF |
| age 1-6h | 24h | 9 | 5 | 171 | 35 | 136 | +0.876 | -0.443 | [-0.751, +2.607] | 0.44 | -0.500 | 44 | +0.051 | -0.194 | [-0.490, +0.638] | INSUFF |
| age 6-24h | 15m | 65 | 27 | 18 | 1 | 15 | +0.422 | +0.013 | [-0.007, +1.603] | 0.62 | -0.003 | 66 | +0.401 | +0.012 | [-0.042, +1.560] | |
| age 6-24h | 1h | 56 | 22 | 27 | 5 | 22 | +0.396 | +0.053 | [-0.021, +1.654] | 0.64 | +0.001 | 61 | +0.309 | +0.034 | [-0.099, +1.329] | |
| age 6-24h | 4h | 40 | 16 | 43 | 6 | 34 | +0.139 | +0.110 | [-0.070, +0.452] | 0.60 | +0.066 | 46 | +0.065 | +0.029 | [-0.139, +0.340] | |
| age 6-24h | 12h | 15 | 8 | 68 | 15 | 50 | +0.121 | -0.290 | [-0.458, +1.114] | 0.33 | -0.376 | 30 | +26.222 | -0.240 | [-0.406, +81.08] | INSUFF |
| age 6-24h | 24h | 6 | 3 | 77 | 18 | 56 | -0.607 | -0.587 | [-0.668, -0.542] | 0.00 | -0.668 | 24 | +32.476 | -0.560 | [-0.691, +95.64] | INSUFF |
| age 24-72h | 15m | 73 | 12 | 17 | 1 | 15 | -0.022 | -0.030 | [-0.041, -0.009] | 0.36 | -0.031 | 74 | -0.021 | -0.030 | [-0.039, -0.008] | INSUFF |
| age 24-72h | 1h | 70 | 11 | 20 | 1 | 18 | -0.035 | -0.049 | [-0.130, +0.006] | 0.39 | -0.052 | 71 | -0.034 | -0.047 | [-0.131, +0.005] | INSUFF |
| age 24-72h | 4h | 60 | 10 | 30 | 1 | 22 | -0.023 | -0.046 | [-0.140, +0.251] | 0.42 | -0.085 | 61 | -0.022 | -0.034 | [-0.136, +0.240] | INSUFF |
| age 24-72h | 12h | 51 | 7 | 39 | 1 | 29 | -0.062 | -0.077 | [-0.369, +0.239] | 0.47 | -0.131 | 52 | -0.060 | -0.047 | [-0.356, +0.224] | INSUFF |
| age 24-72h | 24h | 30 | 3 | 60 | 1 | 56 | -0.198 | -0.081 | [-0.717, +0.022] | 0.33 | -0.252 | 31 | -0.191 | -0.051 | [-0.683, +0.021] | INSUFF |
| age >72h (off-spec) | 15m | 931 | 85 | 195 | 1 | 149 | **-0.019** | -0.021 | **[-0.023, -0.011]** | 0.07 | -0.022 | 932 | -0.019 | -0.021 | [-0.023, -0.010] | |
| age >72h (off-spec) | 1h | 886 | 80 | 240 | 1 | 185 | **-0.021** | -0.021 | **[-0.028, -0.010]** | 0.13 | -0.024 | 887 | -0.021 | -0.021 | [-0.028, -0.011] | |
| age >72h (off-spec) | 4h | 754 | 69 | 372 | 1 | 254 | **-0.024** | -0.021 | **[-0.038, -0.015]** | 0.14 | -0.027 | 755 | -0.024 | -0.021 | [-0.039, -0.015] | |
| age >72h (off-spec) | 12h | 585 | 53 | 541 | 2 | 417 | -0.022 | -0.022 | [-0.050, +0.008] | 0.16 | -0.032 | 587 | -0.022 | -0.022 | [-0.049, +0.008] | |
| age >72h (off-spec) | 24h | 452 | 41 | 674 | 3 | 622 | -0.016 | -0.024 | [-0.073, +0.067] | 0.16 | -0.037 | 455 | -0.017 | -0.024 | [-0.075, +0.061] | |
| liq <8k (off-spec) | 15m | 200 | 165 | 768 | 308 | 439 | +0.367 | -0.011 | [+0.125, +0.748] | 0.48 | +0.161 | 508 | **-0.174** | -0.183 | **[-0.293, -0.020]** | |
| liq <8k (off-spec) | 1h | 73 | 56 | 895 | 357 | 501 | +0.141 | -0.204 | [-0.265, +0.845] | 0.23 | -0.221 | 430 | **-0.290** | -0.229 | **[-0.409, -0.131]** | |
| liq <8k (off-spec) | 4h | 22 | 21 | 946 | 388 | 523 | -0.148 | -0.482 | [-0.495, +0.385] | 0.14 | -0.482 | 410 | **-0.352** | -0.282 | **[-0.450, -0.249]** | |
| liq <8k (off-spec) | 12h | 5 | 5 | 963 | 405 | 537 | -0.136 | -0.048 | [-0.603, +0.368] | 0.20 | -0.735 | 410 | -0.366 | -0.293 | [-0.463, -0.260] | INSUFF |
| liq <8k (off-spec) | 24h | 4 | 3 | 964 | 412 | 549 | -0.183 | -0.058 | [-0.563, -0.056] | 0.00 | -0.563 | 416 | -0.370 | -0.304 | [-0.468, -0.265] | INSUFF |
| liq 8-25k | 15m | 467 | 395 | 1614 | 345 | 1260 | +0.909 | +0.011 | [+0.294, +1.843] | 0.51 | +0.326 | 812 | +0.249 | -0.224 | [-0.112, +0.787] | |
| liq 8-25k | 1h | 160 | 124 | 1921 | 425 | 1476 | +1.909 | -0.502 | [-0.365, +6.419] | 0.26 | -0.296 | 585 | +0.321 | -0.874 | [-0.347, +1.430] | |
| liq 8-25k | 4h | 61 | 50 | 2020 | 456 | 1513 | +5.234 | -0.235 | [-0.209, +16.03] | 0.33 | -0.087 | 517 | +0.648 | -0.932 | [-0.247, +2.101] | |
| liq 8-25k | 12h | 28 | 23 | 2053 | 470 | 1556 | +7.971 | -0.342 | [-0.455, +25.99] | 0.29 | -0.418 | 498 | +0.504 | -1.000 | [-0.294, +1.695] | |
| liq 8-25k | 24h | 7 | 6 | 2074 | 477 | 1591 | +3.936 | -0.518 | [-0.591, +14.41] | 0.29 | -0.632 | 484 | +0.103 | -1.000 | [-0.318, +0.807] | INSUFF |
| liq 25-100k | 15m | 376 | 224 | 1351 | 221 | 1118 | +0.185 | +0.017 | [+0.097, +0.319] | 0.53 | +0.127 | 597 | **-0.128** | -0.027 | **[-0.212, -0.043]** | |
| liq 25-100k | 1h | 201 | 75 | 1526 | 257 | 1256 | +0.202 | -0.024 | [+0.047, +0.433] | 0.32 | +0.099 | 458 | **-0.190** | -0.090 | **[-0.306, -0.080]** | |
| liq 25-100k | 4h | 130 | 39 | 1597 | 271 | 1310 | -0.047 | -0.028 | [-0.256, +0.142] | 0.18 | -0.123 | 401 | **-0.274** | -0.510 | **[-0.416, -0.136]** | |
| liq 25-100k | 12h | 69 | 19 | 1658 | 271 | 1368 | -0.087 | -0.031 | [-0.317, +0.102] | 0.13 | -0.181 | 340 | **-0.323** | -0.962 | **[-0.468, -0.175]** | |
| liq 25-100k | 24h | 46 | 9 | 1681 | 271 | 1406 | +0.871 | -0.026 | [-0.116, +3.388] | 0.20 | +0.015 | 317 | -0.201 | -1.000 | [-0.433, +0.106] | INSUFF |
| liq >100k | 15m | 1180 | 258 | 889 | 42 | 816 | +0.091 | -0.018 | **[+0.041, +0.185]** | 0.29 | +0.085 | 1222 | +0.068 | -0.018 | **[+0.028, +0.144]** | |
| liq >100k | 1h | 978 | 112 | 1091 | 78 | 973 | +0.012 | -0.020 | [-0.007, +0.052] | 0.25 | +0.009 | 1056 | +0.038 | -0.020 | [-0.000, +0.113] | |
| liq >100k | 4h | 792 | 83 | 1277 | 99 | 1073 | +0.062 | -0.020 | [-0.003, +0.224] | 0.23 | +0.033 | 891 | +0.096 | -0.019 | **[+0.018, +0.263]** | |
| liq >100k | 12h | 607 | 58 | 1462 | 114 | 1233 | -0.013 | -0.022 | [-0.062, +0.047] | 0.21 | -0.027 | 721 | +1.141 | -0.022 | [-0.002, +4.292] | |
| liq >100k | 24h | 449 | 40 | 1620 | 121 | 1448 | -0.046 | -0.023 | [-0.115, -0.007] | 0.18 | -0.057 | 570 | +1.423 | -0.021 | [-0.017, +5.881] | |
| fdv <100k | 15m | 686 | 548 | 2777 | 691 | 2053 | +0.545 | +0.028 | [+0.232, +1.073] | 0.52 | +0.266 | 1377 | -0.017 | -0.187 | [-0.180, +0.235] | |
| fdv <100k | 1h | 242 | 175 | 3221 | 830 | 2332 | +1.378 | -0.351 | [-0.189, +4.070] | 0.27 | -0.091 | 1072 | +0.079 | -0.569 | [-0.290, +0.638] | |
| fdv <100k | 4h | 86 | 71 | 3377 | 892 | 2401 | +3.658 | -0.333 | [-0.189, +11.06] | 0.29 | -0.117 | 978 | +0.215 | -0.670 | [-0.271, +0.998] | |
| fdv <100k | 12h | 33 | 27 | 3430 | 923 | 2459 | +6.699 | -0.489 | [-0.461, +22.46] | 0.27 | -0.419 | 956 | +0.126 | -0.821 | [-0.293, +0.726] | |
| fdv <100k | 24h | 11 | 9 | 3452 | 935 | 2509 | +2.438 | -0.223 | [-0.455, +8.610] | 0.18 | -0.429 | 946 | -0.087 | -0.835 | [-0.321, +0.249] | INSUFF |
| fdv 100k-1M | 15m | 342 | 245 | 1153 | 170 | 972 | **+0.482** | **+0.108** | **[+0.358, +0.633]** | 0.68 | +0.426 | 512 | +0.092 | -0.002 | [-0.007, +0.202] | |
| fdv 100k-1M | 1h | 144 | 70 | 1351 | 211 | 1130 | +0.184 | -0.024 | [+0.030, +0.357] | 0.45 | +0.074 | 355 | -0.084 | -0.143 | [-0.216, +0.051] | |
| fdv 100k-1M | 4h | 81 | 37 | 1414 | 227 | 1173 | -0.002 | -0.125 | [-0.293, +0.272] | 0.31 | -0.124 | 308 | -0.160 | -0.755 | [-0.320, -0.001] | |
| fdv 100k-1M | 12h | 35 | 18 | 1460 | 227 | 1219 | -0.120 | -0.243 | [-0.406, +0.181] | 0.26 | -0.318 | 262 | -0.203 | -1.000 | [-0.368, -0.031] | |
| fdv 100k-1M | 24h | 22 | 8 | 1473 | 228 | 1243 | +1.844 | -0.174 | [-0.218, +5.143] | 0.41 | +0.061 | 250 | -0.034 | -1.000 | [-0.318, +0.329] | INSUFF |
| fdv 1M-10M | 15m | 330 | 155 | 447 | 38 | 405 | +0.455 | +0.020 | [+0.063, +1.270] | 0.62 | +0.084 | 368 | +0.328 | +0.012 | [-0.030, +1.109] | |
| fdv 1M-10M | 1h | 225 | 68 | 552 | 55 | 490 | +0.087 | +0.025 | [+0.028, +0.165] | 0.58 | +0.073 | 280 | -0.046 | +0.001 | [-0.127, +0.029] | |
| fdv 1M-10M | 4h | 145 | 41 | 632 | 72 | 545 | +0.321 | -0.015 | [-0.008, +0.865] | 0.48 | +0.161 | 217 | +0.086 | -0.089 | [-0.177, +0.417] | |
| fdv 1M-10M | 12h | 85 | 22 | 692 | 81 | 590 | -0.097 | -0.162 | [-0.275, +0.171] | 0.33 | -0.201 | 166 | +3.142 | -0.315 | [-0.373, +11.78] | |
| fdv 1M-10M | 24h | 41 | 13 | 736 | 81 | 637 | -0.295 | -0.451 | [-0.513, +0.137] | 0.15 | -0.418 | 122 | +4.244 | -0.674 | [-0.521, +16.51] | INSUFF |
| fdv >10M | 15m | 865 | 69 | 243 | 17 | 201 | **-0.017** | -0.020 | **[-0.019, -0.009]** | 0.09 | -0.018 | 882 | -0.028 | -0.020 | [-0.046, -0.020] | |
| fdv >10M | 1h | 801 | 43 | 307 | 21 | 252 | **-0.015** | -0.021 | **[-0.020, -0.000]** | 0.13 | -0.016 | 822 | -0.031 | -0.021 | [-0.057, -0.021] | |
| fdv >10M | 4h | 693 | 41 | 415 | 23 | 298 | -0.002 | -0.020 | [-0.015, +0.039] | 0.16 | -0.007 | 716 | -0.020 | -0.021 | [-0.045, +0.007] | |
| fdv >10M | 12h | 556 | 38 | 552 | 29 | 424 | +0.000 | -0.021 | [-0.020, +0.059] | 0.18 | -0.011 | 585 | +0.383 | -0.022 | [-0.027, +1.796] | |
| fdv >10M | 24h | 432 | 28 | 676 | 37 | 603 | -0.021 | -0.020 | [-0.035, +0.000] | 0.18 | -0.027 | 469 | +0.461 | -0.020 | [-0.054, +2.631] | |
| trail down>20% | 15m | 31 | 24 | 25 | 6 | 18 | -0.048 | -0.041 | [-0.203, +0.133] | 0.42 | -0.146 | 37 | -0.085 | -0.112 | [-0.226, +0.068] | |
| trail down>20% | 1h | 29 | 23 | 27 | 8 | 19 | -0.094 | -0.053 | [-0.283, +0.095] | 0.31 | -0.197 | 37 | -0.128 | -0.140 | [-0.285, +0.029] | |
| trail down>20% | 4h | 14 | 12 | 42 | 8 | 29 | -0.009 | +0.027 | [-0.335, +0.274] | 0.57 | -0.218 | 22 | -0.098 | -0.182 | [-0.312, +0.107] | INSUFF |
| trail down>20% | 12h | 7 | 6 | 49 | 10 | 36 | +0.243 | +0.007 | [-0.388, +1.305] | 0.57 | -0.336 | 17 | -0.098 | -0.195 | [-0.402, +0.324] | INSUFF |
| trail down>20% | 24h | 7 | 6 | 49 | 10 | 39 | -0.257 | -0.563 | [-0.713, +0.588] | 0.14 | -0.726 | 17 | -0.304 | -0.235 | [-0.536, +0.014] | INSUFF |
| trail flat ±20% | 15m | 1008 | 109 | 176 | 5 | 137 | +0.008 | -0.020 | [-0.022, +0.106] | 0.12 | -0.021 | 1013 | +0.008 | -0.020 | [-0.022, +0.105] | |
| trail flat ±20% | 1h | 952 | 98 | 232 | 5 | 182 | +0.005 | -0.021 | [-0.022, +0.092] | 0.18 | -0.020 | 957 | +0.005 | -0.021 | [-0.023, +0.086] | |
| trail flat ±20% | 4h | 803 | 85 | 381 | 6 | 264 | -0.009 | -0.021 | [-0.027, +0.022] | 0.18 | -0.016 | 809 | -0.009 | -0.021 | [-0.028, +0.022] | |
| trail flat ±20% | 12h | 609 | 62 | 575 | 14 | 440 | -0.026 | -0.022 | [-0.078, +0.013] | 0.19 | -0.039 | 623 | +1.240 | -0.022 | [-0.053, +5.870] | |
| trail flat ±20% | 24h | 454 | 44 | 730 | 17 | 664 | -0.027 | -0.024 | [-0.078, +0.028] | 0.18 | -0.047 | 471 | +1.644 | -0.023 | [-0.063, +7.346] | |
| trail up>20% | 15m | 85 | 51 | 50 | 6 | 44 | +0.015 | +0.024 | [-0.023, +0.054] | 0.60 | -0.003 | 91 | -0.029 | +0.018 | [-0.092, +0.023] | |
| trail up>20% | 1h | 67 | 40 | 68 | 13 | 54 | +0.117 | +0.148 | [-0.006, +0.235] | 0.60 | +0.082 | 80 | +0.013 | +0.084 | [-0.132, +0.149] | |
| trail up>20% | 4h | 33 | 22 | 102 | 24 | 73 | +0.386 | -0.097 | [-0.150, +1.127] | 0.39 | -0.021 | 57 | +0.165 | -0.109 | [-0.251, +0.661] | |
| trail up>20% | 12h | 13 | 10 | 122 | 24 | 92 | -0.315 | -0.304 | [-0.536, -0.166] | 0.15 | -0.440 | 37 | -0.200 | -0.330 | [-0.589, +0.214] | INSUFF |
| trail up>20% | 24h | 8 | 5 | 127 | 24 | 101 | -0.394 | -0.483 | [-0.491, -0.269] | 0.12 | -0.620 | 32 | -0.202 | -0.545 | [-0.640, +0.268] | INSUFF |
| trail up>100% | 15m | 21 | 15 | 14 | 3 | 11 | -0.055 | -0.051 | [-0.186, +0.098] | 0.43 | -0.144 | 24 | -0.174 | -0.136 | [-0.379, +0.009] | |
| trail up>100% | 1h | 19 | 14 | 16 | 4 | 12 | +0.033 | -0.124 | [-0.377, +0.673] | 0.42 | -0.293 | 23 | -0.093 | -0.251 | [-0.488, +0.416] | INSUFF |
| trail up>100% | 4h | 13 | 10 | 22 | 4 | 14 | -0.325 | -0.449 | [-0.633, +0.116] | 0.31 | -0.583 | 17 | -0.411 | -0.543 | [-0.700, -0.034] | INSUFF |
| trail up>100% | 12h | 6 | 5 | 29 | 4 | 22 | +0.102 | -0.252 | [-0.491, +0.932] | 0.33 | -0.564 | 10 | -0.216 | -0.487 | [-0.694, +0.478] | INSUFF |
| trail up>100% | 24h | 6 | 4 | 29 | 4 | 24 | +1.840 | +1.335 | [-0.313, +4.065] | 0.67 | -0.115 | 10 | +0.827 | -0.126 | [-0.619, +2.695] | INSUFF |

## 5. Ranking by CI lower bound, and what survives

**Verified (mandated) estimator: 14 of 64 eligible cells (≥15 tokens) have CI_lo > 0.** Ranked, with the same cell under the dead-aware estimator:

| rank | cell | H | mean_ver | **CI_lo ver** | mean_dead-aware | **CI_lo dead-aware** | survives? |
|---|---|---|---|---|---|---|---|
| 1 | fdv 100k-1M | 15m | +0.482 | **+0.358** | +0.093 | −0.007 | ✗ |
| 2 | age 0-1h | 15m | +0.637 | **+0.354** | +0.063 | −0.095 | ✗ |
| 3 | liq 8-25k | 15m | +0.909 | **+0.294** | +0.249 | −0.112 | ✗ |
| 4 | fdv <100k | 15m | +0.545 | **+0.232** | −0.017 | −0.180 | ✗ |
| 5 | age 0-1h | 4h | +3.242 | **+0.209** | +0.136 | −0.229 | ✗ |
| 6 | ALL | 15m | +0.304 | **+0.152** | +0.038 | −0.064 | ✗ |
| 7 | liq <8k | 15m | +0.367 | **+0.125** | −0.174 | −0.293 | ✗ |
| 8 | liq 25-100k | 15m | +0.185 | **+0.097** | −0.128 | −0.212 | ✗ |
| 9 | fdv 1M-10M | 15m | +0.455 | **+0.063** | +0.328 | −0.030 | ✗ |
| 10 | liq 25-100k | 1h | +0.202 | **+0.047** | −0.190 | −0.306 | ✗ |
| 11 | **liq >100k** | **15m** | +0.091 | **+0.041** | +0.068 | **+0.028** | ✓ |
| 12 | fdv 100k-1M | 1h | +0.184 | **+0.030** | −0.084 | −0.216 | ✗ |
| 13 | fdv 1M-10M | 1h | +0.087 | **+0.028** | −0.046 | −0.127 | ✗ |
| 14 | ALL | 4h | +0.358 | **+0.005** | +0.075 | −0.152 | ✗ |

**Dead-aware: only 2 of 81 eligible cells have CI_lo > 0** — `liq >100k @15m` (+6.8 %, [+0.028,+0.144]) and `liq >100k @4h` (+9.6 %, [+0.018,+0.263]).

**Both survivors dissolve on inspection.** Splitting `liq >100k @15m` by whether the pool ever appeared in GT trending (the collector snapshots trending pools **by rank**, which is a selection on recent performance):

| subset | n | tokens | mean | median | CI | frac>0 |
|---|---|---|---|---|---|---|
| ever trending | 1,045 | 138 | **−0.006** | −0.019 | **[−0.013, +0.009]** | 0.22 |
| never trending | 135 | 120 | +0.840 | +0.180 | [+0.679, +1.014] | 0.83 |

The 1,045 trending-conditioned observations are **exactly zero after costs**. The entire positive contribution comes from 135 observations whose **median pool age is 3.0 minutes (100 % under 1 h)** — i.e. the same young-pool phenomenon, not a liquidity effect.

## 6. It is one phenomenon, and it is at minute zero

| subset | H | n | tokens | DISC | verified mean | median | CI | dead-aware mean | dead-aware CI |
|---|---|---|---|---|---|---|---|---|---|
| **age <1h** | 15m | 1,048 | 854 | 4,318 | +0.637 | +0.106 | [+0.354,+1.057] | +0.063 | [−0.095,+0.282] |
| age <1h | 1h | 313 | 211 | 5,053 | +1.142 | −0.107 | [−0.044,+3.257] | +0.013 | [−0.274,+0.479] |
| age <1h | 4h | 111 | 79 | 5,255 | +3.242 | −0.182 | [+0.209,+9.071] | +0.136 | [−0.229,+0.703] |
| **age ≥1h** | 15m | 1,175 | 159 | 304 | +0.006 | −0.020 | [−0.022,+0.088] | −0.002 | [−0.033,+0.078] |
| age ≥1h | 1h | 1,099 | 138 | 380 | +0.009 | −0.021 | [−0.020,+0.078] | −0.002 | [−0.034,+0.061] |
| age ≥1h | 4h | 894 | 107 | 585 | −0.001 | −0.021 | [−0.033,+0.054] | −0.009 | [−0.048,+0.044] |

Everything at **age ≥ 1 h is flat: mean ≈ 0, median −2.0 %, CI straddling zero at every horizon.** The mature end of the surface (`age >72h`, `fdv >10M`) is *significantly negative* at −1.5 % to −2.4 % with CI excluding zero — that is not a signal, it is the round-trip cost line with no information on top.

**The price data is not the artifact.** Cross-checking the OHLCV-derived return against the independent `snapshots.price_usd` endpoint on 1,232 dual-covered observations (951 tokens): bar gross mean +0.616 vs snapshot +0.520; medians +0.083 vs +0.082; **corr 0.895** (1 h: corr 0.931). The young-pool ramp is really in the data. What is not established is that it is *capturable*.

## 7. Robustness of the one candidate (age 0-1h @ 15m)

| stress | mean | CI | median |
|---|---|---|---|
| verified, $50 clip | +0.637 | [+0.354, +1.057] | +0.106 |
| + 1-bar entry latency | +0.271 (all-cohort) | [+0.125, +0.520] | −0.017 |
| verified, $200 clip | +0.572 | [+0.296, +0.976] | +0.076 |
| **dead-aware, $50** | +0.063 | **[−0.095, +0.282]** | −0.132 |
| **dead-aware, $200** | −0.005 | **[−0.160, +0.204]** | — |
| dead-aware, minus top-3 trades | **−0.078** | — | — |
| **breakeven**: mean the 3,399 censored obs (63.6 % of the cell) need for the cell to be zero | **−3.6 %** | | |

Window split (A: ts<1787860000 — only 5.1 h of snapshot-covered data; B: ts≥cut; C: newest 24 h):

| window | cell | H | n_ver | tok | DISC | ver mean | ver CI_lo | dead-aware mean | dead-aware CI_lo |
|---|---|---|---|---|---|---|---|---|---|
| A | age 0-1h | 15m | 104 | 73 | 178 | +1.808 | +0.115 | +0.423 | −0.274 |
| B | age 0-1h | 15m | 944 | 781 | 4,140 | +0.509 | +0.333 | +0.008 | −0.097 |
| C | age 0-1h | 15m | 351 | 322 | 1,702 | +0.884 | +0.480 | +0.802 | +0.411 |
| B | liq >100k | 15m | 1,033 | 228 | 873 | +0.098 | +0.041 | +0.075 | +0.031 |

Window C's dead-aware figure is **not evidence** — in the newest 24 h the class mix at 15m is `{censored: 1782, verified: 780, dead: 25}`: almost nothing has had time to be *observed* dying, so "dead-aware" ≈ "verified" there. Read window B, where deaths have resolved: **+0.8 %, CI [−0.097, +0.097-ish] → zero.**

## 8. Breadth check — full 22-day history (47,854 obs, optimistic costs from lifetime-max reserve)

Only **16.5 %** of these observations are at/after the pool's discovery; the rest is pre-discovery backfill we could never have traded. Restricted to reachable observations, with the dead-aware treatment: 15m +0.9 % [−0.017,+0.039]; 1h −1.7 % [−0.066,+0.045]; 4h +11.2 % [−0.055,+0.437]; 12h +30.8 % [−0.091,+1.179]; 24h +35.8 % [−0.111,+1.416]. **Every horizon's CI includes zero.** `age >72h` is −2.2 % to −5.3 % with CI excluding zero at 15m/1h/4h/24h.

---

# VERDICT

**No. There is no reachable cell on this surface with a credible, tradeable positive expectancy. The honest answer is "no edge here".**

1. **Discards dominate and are not random.** 67.5 % (15m) to 92.6 % (24h) of observations cannot be measured — 73–79 % of that because our own OHLCV fetcher rotated away (median re-fetch gap 29 h), not because pools died. The kept and discarded sets differ by ~14 pp of mean and 42 pp of win rate on a *pre-horizon* statistic (5-min return). **Any number computed on the verified subset is an estimate of a self-selected sub-population, not of the opportunity.** This is the same class of error as the original artifact, one level up.
2. **The mandated verified estimator flags 14 positive cells; 13 of them die** the moment the pools that demonstrably stopped trading are put back in at a data-derived valuation (55 % of dead pools had liquidity pulled). The 14th (`liq >100k @15m`) decomposes into 1,045 trending-conditioned observations worth **exactly zero after costs** (mean −0.6 %, CI [−0.013, +0.009]) plus 135 observations on pools with a median age of **3 minutes**.
3. **The entire surface is one phenomenon at one horizon**: pools under 1 hour old, measured 15 minutes forward. At age ≥1 h *every* cohort × horizon cell is flat-to-negative, and the mature cells (`age >72h`, `fdv >10M`) are significantly negative at ≈ −2 % — the cost line, with zero information above it. There is no liquidity band, no FDV band, no trailing-return state, and no horizon beyond 15 minutes where anything sits above costs.
4. **Even the young-pool cell is not investable.** Its median is **−13.2 %** dead-aware (only 40 % of observations positive), it turns negative when the top 3 of 1,943 trades are removed (−7.8 %), it goes to −0.5 % at a $200 clip, its CI includes zero ([−0.095, +0.282]), and the 63.6 % of the cell we never observe would only need to average **−3.6 %** to zero it out — less than two round trips of cost. It is a lottery ticket priced at whatever the tail happens to be in a 3-day sample, measured on the 36 % of tickets whose outcome we happened to witness.
5. **What would be needed to settle it:** per-pool OHLCV coverage that does not rotate — continuous fetching of a *pre-registered* watchlist of new pools for ≥2 h past entry, so that (b) is satisfiable for the pools that die as well as the ones that live. Until censoring is under 20 %, the 0-1 h × 15 m cell is unmeasurable, not promising.

**Artifacts / reproduction:** `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/` — `build_obs2.py` (observation builder), `final3.py` / `final4.py` (estimators, CIs, ranking), `MASTER.csv` (the grid above), `grid_snap.csv`, `grid_blend.csv`, `rank_verified.csv`, `rank_deadaware.csv`, `unconditional.csv`.
All analyses complete. Compiling the report.

# Exit-Machinery Plateau Search — random entries × ExitRules grid

**Methodology (3 lines):** Loaded 837 pools (287,200 min-bars) via `load_panel(min_max_reserve=2000)`; random_entries placebo (min_liq=15k, FDV 1e5–3e7, vol_h1≥1e4, age 15–720m, p=0.01/bar, seeds 0/1/2 averaged) through `run_backtest` with `RiskParams(starting_usd=1000, risk_per_trade_usd=25)` (entry_lag=2 bars, live parity), CostModel 1x; 192 ExitRules cells = stop{.10,.15,.20,.30} × trail{.15,.20,.25,.35} × tp{(0.3,40%),(0.5,40%),(1.0,50%),none} × hold{120,240,360}, all logged to registry (multiple-testing denominator: 192).
Every CI is a cluster bootstrap by base_mint. Windows: cutoff ts=1787860000 (08-27 19:46 UTC); pool-created split A=295/B=542 pools; entry-eligible universe is thin in A (292 eligible snapshot rows / 70 pools) vs B (1288 / 345).
Per-cell score = seed-averaged expectancy_ci_lo (n_boot=2000) + total_pnl; plateau = mean over the cell and its axis-neighbors; top-3 re-run per window at n_boot=5000, plus a censoring-corrected "locked bound" (see below).

## Grid results (full panel; each cell ≈ 31 trades / 30 tokens avg per seed — modest sample)

All 192 cells were profitable: pnl $131–$264, expectancy 0.18–0.32, ci_lo +0.041…+0.132 (all > 0) — confirming the edge is tape/machinery beta, not cell-specific.

**Marginal means (averaged over all other axes):**

| axis | values → mean ci_lo (mean pnl $) |
|---|---|
| stop | .10: 0.094 (194) · .15: 0.088 (192) · .20: 0.089 (194) · .30: 0.087 (193) — **inert** (trail floor `hwm×(1−trail)` ≥ stop floor at entry whenever stop ≥ trail; identical trades) |
| trail | .15: **0.101** (191) · .20: 0.095 (187) · .25: 0.087 (197) · .35: 0.075 (198) — tight trail best risk-adjusted; loose trail buys tail pnl at worse ci_lo |
| tp | none: **0.099** (229) · tp1.0/50%: 0.094 (195) · tp0.5/40%: 0.085 (180) · tp0.3/40%: 0.080 (168) — monotone: early profit-taking strictly hurts |
| hold | 120: 0.064 (160) · 240: **0.100** (208) · 360: **0.104** (211) — biggest axis; 240 ≈ 360 ≫ 120 |

**Ridge (no_tp, mean ci_lo by trail × hold):** 0.15/360=0.131, 0.15/240=0.126, 0.20/360=0.124, 0.20/240=0.119 … floor 0.35/120=0.050. Top-3 by neighborhood ci_lo (0.128/0.127/0.127): s{.10,.15,.20}/t0.15/no_tp/h360 — the latter two are mechanically identical trades. Bottom-10 all share hold=120 + trail 0.35 (nb_ci_lo 0.052–0.058) yet still positive.

**PLATEAU (neighbors also good, not a peak):** the 12-cell region **trail 0.15–0.20 × {no TP, tp1.0/50%} × hold 240–360** (any stop ≥ trail) all have nb_ci_lo ≥ 0.118; recommended: `ExitRules(stop_frac=0.15, trail_frac=0.15, tp_levels=(), max_hold_min=360)` — hold=240 and tp=(1.0,0.5) variants statistically indistinguishable.

## Top-3 configs by window (5000-boot cluster CIs, seed-averaged; per-seed in brackets)

Pool-created split (configs s0.15 and s0.20 /t0.15/no_tp/h360 are identical):

| config | window | n_trades/seed | n_tokens/seed | exp | ci per-seed (lo) | pnl/seed |
|---|---|---|---|---|---|---|
| s0.10/t.15/noTP/360 | A-pools | 7.0 [9,9,3] | 7.0 | +0.404 | [+.039,+.056,−.116] | $86 |
| | B-pools | 23.7 [26,22,23] | 23.3 | +0.277 | [+.163,+.004,+.116] | $164 |
| s0.15/t.15/noTP/360 | A-pools | 7.0 [9,9,3] | 7.0 | +0.396 | [+.028,+.052,−.166] | $85 |
| | B-pools | 23.7 | 23.3 | +0.279 | [+.182,−.007,+.108] | $166 |

Trade-entry-ts split is materially the same (A: n≈5.7/seed, exp +0.48; B: n≈25/seed, exp +0.265). **Window A: ≤9 tokens per seed, 13 unique tokens pooled — INSUFFICIENT DATA (<15 tokens), sign positive in aggregate but seed 2 has only 2–3 trades.** Window B: 23–25 tokens/seed, CI excludes zero in 2 of 3 seeds, third is borderline (−0.007/+0.004).

## Censoring audit (the honest catch)

- Window B, rec config, 3 seeds pooled: **45/75 trades (60%) exit as `data_end`**, carrying **$471.8 of $498.5 PnL (95%)**, at avg +42% after only ~52 min. Only 1/46 is at the global collection end — the rest are per-pool coverage stops caused by the collector's rotating OHLCV budget (18 calls/cycle over a 200-pool queue; each refetch backfills 1000 min), i.e. mostly **collection lag, not token death**. Resolved-only window-B trades: n=30, 25 tokens, mean +0.036, median −0.024, pnl $27 ≈ flat (itself downward-biased: it drops still-open winners).
- **Locked bound** (re-price every censored exit at the trail floor `max(stop_floor, hwm×(1−trail))` with full sell costs — assumes zero further upside on all open positions): window B pooled mark mean +0.257 CI [+0.142, +0.386] vs **locked +0.142 CI [+0.049, +0.245]**, n=77, 62 tokens — still positive, CI excludes zero. Window A locked: +0.559 CI [+0.079, +1.145] but 13 tokens (insufficient).
- Contrast config (t0.35/tp0.3/h120): locked-bound window B **−0.012 CI [−0.064, +0.045]** — off-plateau edge disappears under the censoring correction (caveat: the bound mechanically favors tight trails; the mark-based grid gives the same ordering independently).
- Full-horizon check (entries only ≥6h before global end): window B pooled mean +0.346 CI [+0.183, +0.546] (43 trades, 34 tokens) — not an end-of-sample-entry artifact.
- Cost stress, rec config (full panel, seed-avg): 1x exp 0.323 / ci_lo 0.130 · 2x 0.262 / 0.082 · 3x 0.209 / 0.037 — survives 3x costs.

## VERDICT

**Composite-strategy candidates (sign-consistent both windows; CI excludes zero in B):**
1. **Exit plateau: `stop_frac=0.15, trail_frac=0.15–0.20, tp_levels=() (or single late TP (1.0, 0.5)), max_hold_min=240–360`** — recommended cell `ExitRules(0.15, 0.15, (), 360)`. Window B: CI > 0 under both mark-based (+0.257 [0.142,0.386]) and censoring-corrected locked bound (+0.142 [0.049,0.245]), 62 tokens; window A same-sign (+0.40–0.56) but insufficient (13 tokens < 15). Robust to 3x costs and to full-horizon entry restriction. Holds in both windows *directionally*; only window B has statistical power.
2. **The load-bearing axes: hold 240 vs 120 (+0.04 ci_lo) and no-early-TP vs tp0.3 (+0.02 ci_lo, +$61 pnl)** — both monotone across the grid and consistent in both windows' sign.

**Dead ends:**
- **stop_frac tuning**: mechanically inert whenever stop ≥ trail (identical trades); stop 0.10 < trail floor changes nothing material. Stop is not a lever — the trail is the stop.
- **Early profit-taking (tp 0.3/40%, 0.5/40%)**: strictly worst tp settings on every slice.
- **Wide trail 0.35 + short hold 120**: bottom of every ranking; window-B edge vanishes entirely under the locked bound.

**Caveats:** window-A evidence is insufficient everywhere (≤13 tokens); ~60% of window-B exits are coverage-censored marks — the locked-bound CI [+0.049,+0.245] is the defensible number, and the analysis should be re-run once the collector's OHLCV rotation catches up (each refetch backfills 1000 min, so censored trades will resolve in-place). 192 configs logged to the registry for multiple-testing accounting.

**Artifacts:** grid `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/grid_full.csv` (all 192 cells, per-cell + neighborhood scores); window finals `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/final_windows.json`; script `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/exit_grid.py`; registry appended at `/home/user/memecoin3/research/results/registry.jsonl` (phase=exit_grid_random).
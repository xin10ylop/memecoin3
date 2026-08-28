All computations complete. Composing the report.

## Fat-tail exit families — regime_gated vs random control (graduated panel)

**Method (3 lines).** Loaded `load_panel("data/panel.db", min_max_reserve=2000, min_bars=5)` → 937 pools, 869 graduated (dex_id≠'pump-fun'); pools split by `meta.created_ts` at 1787860000 into A (245 pools/219 tokens) and B (624/620). Ran `run_backtest` with `regime_gated` (events `{'__cohort__': cohort_momentum(grad)}`, defaults min_liq 15k) and `random_entries` (seed 0) × 8 exit configs, `RiskParams(1000, 25)`, default `CostModel` (impact ≈ 25/(reserve/2) + 80bps + $0.10/side — all P&L net); stop_frac fixed at 0.15 for all configs so only trail/tp/hold vary. `ci_lo` = 2.5th pct of cluster bootstrap (by mint, B=3000) of mean pnl/trade; max_dd in USD from the $1000 equity curve.

Scripts/outputs: `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/tail_exits.py`, `.../tail_exits_post.py`, metrics `.../tail_exits_metrics.csv`, trades `.../tail_exits_results.pkl`.

### regime_gated — Window B (hot, ~113–116 tokens per cell)

| config | n_tr | n_tok | exp $/tr | ci_lo | total $ | median $ | top5% share | maxDD $ |
|---|---|---|---|---|---|---|---|---|
| (a) plateau s.15/t.18/h300 | 119 | 116 | **2.53** | **+0.74** | **300.8** | -0.06 | 0.75 | 26.6 |
| (b) tail t.35 h720 = h1440 | 117 | 114 | 2.16 | +0.70 | 252.8 | -0.06 | 0.73 | 24.7 |
| (b) tail t.50 h720 = h1440 | 116 | 113 | 1.98 | +0.49 | 229.4 | -0.25 | 0.80 | 24.7 |
| (c) moonbag t.50 h1440 | 116 | 113 | 1.92 | +0.47 | 222.5 | -0.25 | 0.79 | 24.7 |
| (d) trail-only t.35 h1440 | 117 | 114 | 2.41 | +0.65 | 281.8 | -0.06 | 0.80 | 24.7 |
| (d) trail-only t.50 h1440 | 116 | 113 | 2.15 | +0.39 | 249.6 | -0.25 | 0.91 | 24.7 |

### regime_gated — Window A (cool; 13–14 tokens ⇒ **insufficient data**, shown for completeness)

| config | n_tok | exp $/tr | ci_lo | total $ | median $ |
|---|---|---|---|---|---|
| (a) plateau | 14 | 17.29 | -0.25 | 242.0 | -0.26 |
| (b) t.35 h720/h1440 | 13 | -0.34 | -2.79 | -4.4 | -2.99 |
| (b) t.50 h720/h1440 | 13 | 1.19 | -2.36 | 15.5 | -2.99 |
| (c) moonbag | 13 | 2.91 | -1.55 | 37.8 | -0.89 |
| (d) t.35 | 13 | -2.04 | -6.77 | -26.5 | -3.62 |
| (d) t.50 | 13 | -0.39 | -5.99 | -5.1 | -3.62 |

### random_entries control (seed 0)

| config | win | n_tok | exp $/tr | ci_lo | total $ | median $ | top5% share |
|---|---|---|---|---|---|---|---|
| (a) plateau | B | 26 | **7.01** | +3.93 | 189.4 | +7.54 | 0.26 |
| (b) t.35 (both holds) | B | 26 | 6.43 | +3.37 | 173.7 | +3.79 | 0.27 |
| (b) t.50 (both holds) | B | 25 | 5.61 | +2.13 | 145.7 | +1.67 | 0.32 |
| (c) moonbag | B | 25 | 5.61 | +2.13 | 145.7 | +1.67 | 0.32 |
| (d) t.35 | B | 26 | 6.22 | +3.21 | 168.0 | +3.79 | 0.29 |
| (d) t.50 | B | 25 | 5.53 | +2.10 | 143.8 | +1.67 | 0.34 |
| all A cells | A | 9 | 11.6–23.0 | +0.25–+3.9 | 104–207 | — | **insufficient (<15 tokens)** |

### Why the families barely separate — censoring diagnostics (the load-bearing finding)

- **Right-censoring dominates window B**: 64–72% of trades in every config exit as `data_end` (panel collection ends ~12h into the hot window) at mean hold ~16 min; censored trades are marked at terminal close identically across configs.
- Paired on shared entries (regime B, plateau vs trail-only t.35): 102 shared trades, **pnl correlation 0.986**, totals 233.8 vs 233.4; the top winners are identical `data_end` marks (best +4.03x, censored at 11 min hold).
- max_hold 720 vs 1440 produce **bit-identical results** (time stop never binds — data ends first). Realized p95 ret in B is only 0.73–0.80x in every config: **no exit family touches the ~8x peak tail because the panel ends before tails develop**, not because exits cut them.
- Where configs do differ (the ~30% uncensored trades): wider trails convert into more 15%-stop hits (22% vs 18%) and give back trail cushion; plateau's tight 0.18 trail exits earlier at similar prices and its 300-min cap frees concurrency slots (119 vs 116 trades).

### VERDICT

- **Riding the tail does NOT beat the tight plateau on this panel.** In the only adequately-populated cell (window B, ~114 tokens), the baseline plateau has the highest expectancy ($2.53, ci_lo +0.74) and total pnl ($300.8); every tail-rider/moonbag/wide-trail variant is lower ($1.92–2.41, ci_lo +0.39–0.70) — and the ordering replicates in the random control (plateau 7.01 > all tail configs 5.53–6.43). Window-consistency untestable: window A is insufficient (9–14 tokens; regime_gated tail configs there are point-negative).
- **However, this is NOT evidence against the tail hypothesis** — it is an underpowered test: 64–72% of trades are right-censored ~16 min after entry, config pnl correlation 0.986, hold 720≡1440, and no config realizes ret > 4x. The panel currently cannot distinguish "tail-riding fails" from "tails not yet observable." **Candidate**: re-run this exact sweep once window-B pools have full lifetimes (≥2–3 more days of collection) before touching production exits.
- **Dead ends (current data)**: moonbag (c) and trail 0.50 variants — strictly dominated (lowest ci_lo, highest top-5% concentration 0.79–0.91, same maxDD). Also note: random control expectancy ≥ regime_gated in window B, so the cohort-momentum entry gate adds no measurable edge over the machinery+tape in this window — the gate, not the exits, is the weaker link.
- **Insufficient**: all window-A cells (<15 tokens); random_entries window A (9 tokens).
- **Keep for now**: baseline plateau ExitRules(0.15, 0.18, (), 300) — best or statistically tied in every populated cell, net of costs at the $25 clip.
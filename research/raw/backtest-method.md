# Backtesting Methodology for Intraday Event-Driven Strategies on New-Launch Solana Memecoin Panels

Scope assumed: minute OHLCV (+ ideally reserve/liquidity snapshots) for O(100–1000) Solana pools discovered live at/near launch, holding periods minutes–hours, event = pool launch or early-life trigger.

---

## 1. Bias Catalogue and Mitigations

### 1.1 Survivorship bias

**Why live collection mostly kills it.** The defining property of a survivorship-free panel is that *universe membership at time t is decided using only information available at t*. A live collector that subscribes to pool-creation events (Raydium/pump.fun/Meteora program logs) and then records bars for every discovered pool — **including pools that rug, drain to zero, or go silent** — satisfies this. Dead pools stay in the panel with their death observable. This is strictly better than any retrospective vendor dump, which typically only contains pools still indexed at query time.

**Where it silently re-enters:**

- **Indexing-threshold conditioning.** If discovery comes from an aggregator (DexScreener, Birdeye, GeckoTerminal) rather than raw chain events, a pool enters your panel only after crossing that vendor's liquidity/volume/holders thresholds. Your panel then over-represents tokens that achieved initial traction, and — worse — the *moment of indexing correlates with a local momentum peak* (pools get indexed because they pumped). Any "buy on discovery" backtest on such a feed is partly backtesting "buy after a pump."
  - *Mitigation:* record `t_created` (chain) and `t_discovered` (your feed) separately. Signals may only condition on data with timestamp ≥ `t_discovered + measured_feed_latency`. State explicitly that the strategy's claimed edge is over the *indexed-pool universe*, and make the live universe filter identical to the collection filter.
- **Silent gap-dropping.** If your collector drops pools that stop printing bars (no trades), you truncate exactly the left tail. *Mitigation:* forward-fill "no-trade" bars with volume=0 and last price, and mark liquidity-pull events; a held position through a rug is settled at executable value (usually ≈ −100%), never dropped.
- **Mutable metadata.** Never join on fields the indexer updates in place (current TVL, "verified", rug flags, holder counts as-of-now). Snapshot everything at collection time.

### 1.2 Look-ahead bias

**Fill discipline.** With close-labeled minute bars, a signal that uses any part of bar *t* (its close, volume, range) is computable no earlier than `close(t)`. Canonical discipline:

```
signal_time  = close(t)
earliest_fill = open(t+1)          # baseline
conservative  = open(t+1) drifted by +k·σ_1min in the adverse direction, k ≈ 0.5–1
```

Solana block time (~400 ms) is not the binding latency — **your indexer's bar-finalization lag is** (bars often finalize seconds to a minute+ after wall-clock close, and can be revised as late transactions index). *Measure it during collection*: log `wallclock_received − bar_close_label` per bar; set fill delay ≥ its p95.

**Checklist of subtle leaks:**
- Timestamp convention: verify whether the vendor labels bars by open or close time (off-by-one here is the single most common fatal leak).
- Features requiring the full bar (bar-t volume, bar-t high) are unavailable intra-bar-t.
- Stops/targets inside a bar: if a bar's range touches both stop and target, **assume stop first** (worst-case intra-bar path). If the open gaps through the stop, fill at the open, not the stop price.
- No centered/rolling windows that peek forward; no normalization by whole-sample stats (fit scalers on training folds only).
- Pool "age," "max TVL reached," lifetime labels: computable only in hindsight — features must use running versions.

### 1.3 Selection bias from the collection window

A few weeks of live data is **one draw** from a regime distribution: SOL trend, meme-cycle intensity, launchpad meta (pump.fun mechanics change), sniper/MEV-bot competition, celebrity-token episodes. Expectancy fitted in a hot window will not transfer.

*Mitigations:*
- Report regime covariates for the window: SOL return and vol, launches/day, median pool half-life, aggregate new-pool volume. Future readers (including you) need these to judge transportability.
- Evaluate a **cohort-neutral variant**: trade return minus the same-launch-hour cohort median return; if edge vanishes, you were long the meme beta of your window.
- Block-bootstrap by *day* and by *launch cohort* (see §3) so CIs reflect regime clustering, not just trade count.
- Ideally collect ≥2 disjoint windows; keep the second as a one-shot holdout (§5).

### 1.4 Backfill bias — is retro-fetching OHLCV for discovered pools OK?

Precise argument, in two halves:

**(a) The data itself is not the problem.** Solana swaps are on-chain and immutable post-finality; OHLCV is (in principle) a deterministic function of confirmed transactions. Unlike equities vendor data, there are no earnings restatements. So a backfilled bar is the *same fact* you'd have observed live — **modulo indexer repairs**: live-served bars and later-recomputed bars can differ (late-indexed txs, reorg handling, bar re-aggregation). *Mitigation:* snapshot live API responses during collection and diff against backfill; use the live snapshot for simulation when they differ.

**(b) The conditioning is the problem.** Two rules:

1. **Never simulate entries before `t_discovered`.** You could not have traded a pool you didn't know existed. Backfilled pre-discovery bars simulated as tradeable is pure look-ahead.
2. **Pre-discovery bars as *features* are OK iff discovery is unconditional; biased iff discovery is outcome-conditioned.** If you discover pools from the raw creation-event firehose, then "backfill first 10 minutes, signal at minute 11" is clean. But if you discover via a *trending/ranked* feed at time T and backfill to launch, every backfilled bar is conditioned on the event {pool survived and trended until T} — a survivorship condition baked into the features. Concretely: "pools whose first-10-min volume > X go up" may be true *only among pools that later trended*, which is not a tradeable population.

**Verdict:** backfill is acceptable for feature history when the discovery mechanism is a creation-event subscription; it is quietly poisonous when discovery is threshold- or rank-based. If stuck with a ranked feed, restrict all features to post-discovery data.

### 1.5 Wash trading / painted bars

Memecoin volume is heavily manufactured: dev self-trades, paid "volume boost" bots, bundled sniping, sandwich legs. Cong, Li, Tang & Yang, *"Crypto Wash Trading"* (Management Science, 2023) estimate wash volume >70% on unregulated venues; Solana new-pools are worse. Consequences: volume signals fire on fake prints; volume-based capacity estimates are fantasy; OHLC extremes can be painted with dust trades in thin pools.

*Mitigations:*
- **Capacity from reserves, never volume.** Use AMM pool reserve snapshots (or TVL from the pair account) for cost/size modeling (§2). Volume tells you what bots did; reserves tell you what *you* can do.
- If you collect swap-level data: per-bar **unique signer count**, top-signer volume share, and net signed flow. Flags: volume/TVL turnover ≫ 1 with |net flow| ≈ 0 and |Δprice| ≈ 0; repeated equal-size round trips; one wallet >50% of bar volume.
- Bar-level heuristic without signer data: `suspicion = volume_bar / TVL` combined with `|close−open|/(high−low)`; cap *usable* volume at `min(volume, κ·TVL)`, κ ≈ 0.5–1 per minute, for any volume-derived feature.
- Liquidity floor for tradeability: exclude bars with TVL below a floor (e.g., $10–20k) from the *tradeable* set (they can remain as features). Painted prices in near-zero-liquidity pools also corrupt price-based estimators (Roll 1984 spread, Amihud 2002 illiquidity), so those need the floor too.
- Beware **fake liquidity**: TVL spoofing / same-block liquidity pull. Conservative: use the *minimum* of TVL over the trailing few bars as executable depth.

---

## 2. Cost Modeling for Constant-Product AMMs

### 2.1 Exact swap math (implement this, not an approximation)

Pool reserves `(x, y)` = (quote, token), fee `φ` (Raydium 0.25%, pump.fun/PumpSwap ~1%/0.25%, Orca varies), `γ = 1 − φ`. Buy with quote input `Δx`:

```
Δy_out      = y · γΔx / (x + γΔx)                 # tokens received
p_mid       = x / y                               # quote per token, pre-trade
p_exec      = Δx / Δy_out = (x + γΔx) / (γ y)
slippage    = p_exec / p_mid − 1 = (1−γ)/γ + Δx/x ≈ φ + f,   f ≡ Δx / x
p_after     = (x + γΔx) / (y − Δy_out) ≈ p_mid · (1 + f)²    # marginal price impact ≈ 2f
```

**Key numbers:** trading a fraction `f` of the *input-side reserve* costs you ≈ `f` in average slippage versus mid and moves the marginal price by ≈ `2f`. With TVL `L` (both sides, quote terms), quote reserve ≈ `L/2`, so for order notional `Q`:

```
per-side cost ≈ φ + 2Q/L          (linear regime, Q ≲ 5% of L)
round trip    ≈ 2φ + 2Q_buy/L + 2Q_sell/L_at_exit ≈ 2φ + 4Q/L   (if L unchanged)
```

**Why fixed-bps understates costs in thin pools.** A "30 bps + 30 bps" assumption is off by *orders of magnitude* here: $500 into a $10k-TVL pool is `f = 10%` → ~10% slippage one side, ~20% round trip. Worse, a fixed-bps model is not just wrong on average — it *inverts the optimizer's incentives*: the thinnest pools have the wildest bars and the juiciest apparent signals, so an optimizer under fixed-bps costs will concentrate exactly where real costs are highest. The cost model is part of the objective; a convex, liquidity-aware cost term is what keeps the search honest.

### 2.2 Recommended functional form

Simulate the swap exactly using bar-time reserves; if you only have TVL, use the closed form. Full per-side cost:

```
C(Q, L, σ, s) = φ                        # pool fee
              + slip_exact(Q, L)         # from formulas above; ≈ 2Q/L small-Q
              + c_fix / Q                # priority fee + Jito tip + rent, amortized (fixed SOL per tx — dominates tiny clips)
              + k_lat · σ_1min           # latency/adverse-drift: price drifts while your tx lands; k_lat ≈ 0.5–1
              + 1{s > s*} · h_mev(s)     # sandwich haircut when slippage tolerance s is wide; ≈ s/2 expected loss to sandwichers in the worst case
              + τ_transfer               # token-2022 transfer tax if present (check mint extensions!)
```

Practical settings:
- `L` = executable depth = `min(TVL over trailing 3 bars)`, snapshotted at fill time, **not** launch-time or peak TVL. On exit after a dump, `L` is often a small fraction of entry `L` — model exit slippage with exit-time reserves; this is where memecoin PnL goes to die.
- Apply your own impact **permanently** to your fill (you trade against the curve), and assume zero rebate from mean reversion of your own impact.
- Sensitivity mandate: report headline results under 1×, 2×, 3× the cost model. A strategy that dies at 2× costs is not a strategy.
- References for CFMM math: Angeris & Chitra, *"Improved Price Oracles: Constant Function Market Makers"* (ACM AFT 2020); Milionis, Moallemi, Roughgarden & Zhang, *"Loss-Versus-Rebalancing"* (2022) for the adverse-selection view of AMM flow.

---

## 3. Statistical Validation with Small Samples

### 3.1 Expectancy with bootstrap CIs — respect the dependence structure

Trades are **not iid**: multiple trades per token share the token's fate; tokens launched in the same hour share meta/SOL beta. Two-level scheme:

1. **Cluster bootstrap over tokens** (primary): resample *tokens* with replacement (each draw brings all its trades), B = 10,000; compute mean per-trade return each time; CI = percentile `[Q_{2.5%}, Q_{97.5%}]`, or BCa (Efron & Tibshirani 1993) given heavy skew — percentile intervals under-cover with skewed payoffs.
2. **Stationary block bootstrap over calendar time** (secondary, catches cohort correlation): Politis & Romano (JASA 1994), expected block length ≈ 1 day of launch-time-ordered trades.

Report the *wider* of the two. For regression-style tests, two-way clustered SEs by token and launch-hour (Cameron, Gelbach & Miller 2011).

```
E        = (1/n) Σ R_i                       # per-trade expectancy, net of §2 costs
CI_95    = percentile/BCa interval from cluster bootstrap
p(E ≤ 0) = fraction of bootstrap means ≤ 0   # one-sided
```

### 3.2 Walk-forward by launch time

Order tokens by `t_created`; split into K sequential folds **by token, never within a token**. Fit params on folds `1..j`, test on `j+1`, roll forward; concatenate out-of-sample trades for headline stats. Add a **purge/embargo**: drop tokens launched within one max-holding-period of a fold boundary so train/test information can't overlap (López de Prado, *Advances in Financial Machine Learning*, 2018, ch. 7). With a short window, even K = 3–4 walk-forward folds beat any in-sample number; report per-fold results (consistency across folds is the point, not the pooled mean).

### 3.3 Plateau analysis, not point optimization

For each parameter grid point `θ`, compute out-of-sample metric `M(θ)`. Select and report on the **smoothed surface**:

```
M̃(θ) = median{ M(θ') : θ' ∈ neighborhood(θ) }     # e.g., ±1 grid step in each dim
θ*    = argmax M̃(θ)
```

Publish the full heatmap. Accept `θ*` only if: (i) ≥ ~50–70% of its neighbors are profitable, (ii) `M` degrades smoothly moving away, (iii) `θ*` is interior, not a grid-edge artifact. An isolated spike surrounded by losses is noise (Pardo, *The Evaluation and Optimization of Trading Strategies*, 2008). Prefer few parameters with coarse grids: each extra tuned parameter is a multiplicative trial count in §3.4.

### 3.4 Multiple-testing corrections

**Deflated Sharpe Ratio** (Bailey & López de Prado, JPM 2014). With `N` effectively-independent configurations tried, per-trial SR variance `V[SR]` (variance of SR across your trials), Euler–Mascheroni `γ_EM ≈ 0.5772`:

```
SR*  = sqrt(V[SR]) · [ (1−γ_EM)·Φ⁻¹(1 − 1/N) + γ_EM·Φ⁻¹(1 − 1/(N·e)) ]     # expected max SR under null
DSR  = Φ( (SR − SR*) · sqrt(n − 1) / sqrt(1 − γ₃·SR + ((γ₄ − 1)/4)·SR²) )
```

`n` = number of returns, `γ₃` skewness, `γ₄` kurtosis of trade returns (per-trade SR is fine; keep units consistent). Demand DSR ≥ 0.95. Note the denominator *penalizes negative skew but rewards positive skew* — lottery-like strategies get some benefit here, legitimately. `N` must count **everything you tried**, including abandoned variants (§5); if configs are correlated, estimate effective N via clustering of their return series (or conservatively use raw N).

**White's Reality Check** (Econometrica 2000) — simplified practical version:
1. Keep the per-trade (or per-day) return series of **all** `m` configs ever run, `{r_k}`.
2. Stationary-bootstrap the time index B = 2,000+ times (same resample applied to all configs, preserving cross-config correlation).
3. For each resample b: `V_b = max_k ( mean(r_k^{(b)}) − mean(r_k) )` (recentered → null of zero edge).
4. `p = (1/B) Σ 1{ V_b ≥ max_k mean(r_k) }`.

This is the p-value that *your best config* beat zero given the whole search. Hansen's SPA test (JBES 2005) is a studentized variant less distorted by including terrible configs — use it if your registry contains many deliberately bad baselines. Background: Sullivan, Timmermann & White (JF 1999); Harvey, Liu & Zhu (RFS 2016) argue for t-stat hurdles ≈ 3.0 after data mining, not 2.0.

### 3.5 Minimum trade counts

Power calculation for detecting `E > 0` at one-sided 95% with 80% power:

```
n_min ≈ ((z_{0.95} + z_{0.80}) · σ_R / E)² = (2.49 · σ_R/E)²
```

Memecoin event trades commonly have `σ_R/E ≈ 5–15` ⇒ `n_min ≈ 150–1,400`. Two sharper constraints for lottery-like payoffs:

- **Winner count binds, not trade count.** If the P&L is carried by rare wins with hit rate `h`, inference quality scales with the number of winners `n·h`; require `n·h ≥ 30–50`. At `h = 5%` that is **600–1,000 trades**. Below that, your CI is a bet on a Poisson count.
- SR standard error with higher moments (Lo, FAJ 2002; Mertens 2002): `SE(SR) = sqrt( (1 + SR²/2 − γ₃·SR + (γ₄−3)/4 · SR²) / n )` — fat tails inflate it well beyond the naive `sqrt((1+SR²/2)/n)`.

With a few hundred pools and 1–3 trades per pool, you are marginal. Design the strategy to trade *more pools with smaller size* rather than few concentrated bets — for inference, not just risk.

---

## 4. Metrics for High-Skew, Lottery-Like Distributions

Report all of the following; no single number summarizes a lottery.

```
h   = hit rate = n_win / n
W̄  = mean win, L̄ = mean |loss|
E   = h·W̄ − (1−h)·L̄                       # decomposed expectancy — report h and W̄/L̄ jointly, never h alone
PR  = W̄ / L̄                               # payoff ratio; required PR for breakeven: PR_be = (1−h)/h
PF  = Σ wins / Σ |losses|                  # profit factor; want bootstrap CI on PF too (it's a ratio — very noisy)
```

- **Median vs mean:** median trade will be negative for most viable memecoin strategies — that is expected, not disqualifying, but *report it*, plus quantiles {5, 25, 50, 75, 95, 99}. The gap `mean − median` is your skew premium and your fragility.
- **P&L concentration:** expectancy after removing top-1, top-3, top-5 trades; fraction of total P&L from the top 5% of trades. If removing 3 trades kills the strategy, your effective n is ~3, whatever the trade count says.
- **Tail dependence / effective bets:** do winners cluster? Compute within-launch-cohort correlation of trade outcomes and the effective number of independent bets `ENB = n / (1 + (n̄_c − 1)·ρ_intra)` (cluster-adjusted). Upper-tail dependence between your trade outcomes and the cohort index return tells you whether the jackpots are *your* edge or the window's meta (ties to §1.3 cohort-neutral test).
- **Risk of ruin under fractional sizing.** The rug atom at ≈ −100% breaks Gaussian Kelly. With outcome model {win multiple `b` w.p. `h`; lose fraction `a` w.p. `q`; rug (−1 + failed-exit haircut) w.p. `r`}, choose `f` maximizing expected log growth:

```
g(f) = h·ln(1 + f·b) + q·ln(1 − f·a) + r·ln(1 − f)        # r > 0 forces f* < 1 hard
f*   = argmax g(f)   (solve numerically);  trade at f = 0.25–0.5 · f*  (fractional Kelly)
```

  Then estimate ruin/drawdown by **simulation**: bootstrap per-trade returns (cluster-by-token), simulate 10⁵ equity paths at your sizing, report `P(maxDD > 50%)`, `P(equity < 0.2·start)`, time-under-water distribution. Closed-form sanity check: if per-trade log-growth has mean `g` and variance `s²`, `P(ever losing fraction 1−x of capital) ≈ x^(2g/s²)`. Enforce structural caps regardless of Kelly: per-token max exposure, per-launch-cohort max aggregate exposure (correlated rugs), and position ≤ small fraction of pool depth (§2 capacity).
- **Drawdown:** report the bootstrap *distribution* of max drawdown, not the single realized path — with n in the hundreds, realized maxDD is nearly meaningless.
- **Denomination:** report expectancy in both SOL and USD terms (a SOL-denominated edge can be a USD-flat one), and *capacity-adjusted* expectancy at 1×, 3×, 10× intended size through the §2 cost curve.

---

## 5. Honest Experiment Reports

1. **Pre-register rule families before running.** A short spec, committed to git (the commit timestamp is your notary), fixing: signal family and rationale; parameter grid (exact ranges); entry/exit/stop discipline; fill and cost model; universe filter; fold scheme; primary metric; success criteria (e.g., "OOS E > 0 at 95% cluster-bootstrap CI, DSR ≥ 0.95, survives 2× costs"). Anything outside the spec is a new registered experiment, not a tweak.
2. **Experiment registry — every run logged.** `{config_hash, param_values, data_snapshot_hash, git_sha, timestamp, n_trades, E, CI, SR, PF, maxDD}` appended automatically by the backtester (no opt-out path in the code). This registry *is* `N` for the DSR and the config set for the Reality Check. Bailey, Borwein, López de Prado & Zhu, *"Pseudo-Mathematics and Financial Charlatanism"* (Notices of the AMS, 2014): expected max in-sample Sharpe grows like `sqrt(2·ln N)` even with zero skill — undisclosed trials are the fraud mechanism.
3. **Report the distribution of all configs, not the winner.** Histogram of all trial Sharpes/expectancies with the selected config marked; per-fold walk-forward table; full parameter heatmaps (§3.3). A winner that is the right tail of a zero-centered cloud indicts itself.
4. **One-shot holdout.** Reserve the final collected week (or a second collection window) untouched until the single pre-registered final evaluation. It is spent after one look — say so in the report, and never iterate on it (López de Prado 2018, ch. 11: "backtesting is not a research tool").
5. **Negative controls in every report:** (a) permutation test — shuffle entry timestamps within token, re-run: edge should vanish; (b) placebo signal (random entries, same exit/cost machinery) to isolate exit-rule and cost artifacts; (c) gross vs net-of-cost deltas at 1×/2×/3× costs; (d) cohort-neutral variant (§1.3).
6. **Full-disclosure checklist:** universe definition and its conditioning (§1.1, §1.4); measured feed latency and fill delay used; intra-bar stop convention; bars/tokens excluded and exact reasons with counts; seed sensitivity; window regime covariates; number of researchers·months of iteration (informal N inflator — Harvey & Liu, *"Backtesting"*, JPM 2015 for haircut methodology).

---

## Key references

- White (2000), *A Reality Check for Data Snooping*, Econometrica 68(5).
- Hansen (2005), *A Test for Superior Predictive Ability*, J. Business & Economic Statistics 23(4).
- Bailey & López de Prado (2014), *The Deflated Sharpe Ratio*, J. Portfolio Management 40(5).
- Bailey, Borwein, López de Prado & Zhu (2014), *Pseudo-Mathematics and Financial Charlatanism*, Notices of the AMS 61(5).
- López de Prado (2018), *Advances in Financial Machine Learning*, Wiley — chs. 7 (purged CV), 11–14 (backtesting dangers, DSR).
- Harvey, Liu & Zhu (2016), *…and the Cross-Section of Expected Returns*, RFS 29(1); Harvey & Liu (2015), *Backtesting*, JPM 42(1).
- Sullivan, Timmermann & White (1999), *Data-Snooping, Technical Trading Rule Performance, and the Bootstrap*, J. Finance 54(5).
- Politis & Romano (1994), *The Stationary Bootstrap*, JASA 89(428); Efron & Tibshirani (1993), *An Introduction to the Bootstrap*.
- Lo (2002), *The Statistics of Sharpe Ratios*, FAJ 58(4); Mertens (2002), U. Basel working paper (SR asymptotic variance with higher moments).
- Cameron, Gelbach & Miller (2011), *Robust Inference with Multiway Clustering*, JBES 29(2).
- Pardo (2008), *The Evaluation and Optimization of Trading Strategies*, 2nd ed., Wiley (walk-forward, parameter robustness).
- Cong, Li, Tang & Yang (2023), *Crypto Wash Trading*, Management Science 69(11).
- Angeris & Chitra (2020), *Improved Price Oracles: Constant Function Market Makers*, ACM AFT; Milionis, Moallemi, Roughgarden & Zhang (2022), *Automated Market Making and Loss-Versus-Rebalancing*, arXiv:2208.06046.
- Roll (1984), *A Simple Implicit Measure of the Effective Bid-Ask Spread*, J. Finance 39(4); Amihud (2002), *Illiquidity and Stock Returns*, J. Financial Markets 5(1).
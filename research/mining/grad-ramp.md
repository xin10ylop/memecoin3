All computations complete. Compiling the final report.

**METHOD** (3 lines): Joined `pools` on `base_token_address` (pump-fun → pumpswap) for graduation events; pre-grad prices from bonding-pool `snapshots` (~3-min, drained-migration artifacts filtered at reserve≤1.5k), post-grad from pumpswap minute OHLCV indexed to first open; graduation price = first pumpswap open. Trigger trades: first bonding snapshot with `reserve_usd ≥ th` (pre-grad for graduates), entry at that snapshot's `price_usd`, forward path chains bonding snapshots → pumpswap prices (token price is continuous across migration), LOCF + terminal extension (deaths count); net = 1% curve fee/side (0.8%+$0.10 AMM exit), impact = clip/(reserve/2) per side, capped at −100%. CIs = cluster bootstrap by token (3k reps); windows split at trigger/grad ts 1787860000.

---

## 1. Graduation event set
**242 tokens** with both a pump-fun and a later pumpswap pool (window A: 19, B: 223; 0 duplicate pumpswap pools; +1 token graduated to meteora/orca-only, excluded from failure cohort). All 242 have pumpswap `pool_created_at ≥` pump-fun's. **Data-reality caveats that shape everything below:** snapshots span only ~25h (A≈5h, B≈20h); graduates' bonding pools have **zero pre-grad OHLCV** (0/242) — pre-grad price exists only via snapshots, and only **65/242** have any pre-grad snapshot (discovery-lead median **10 min**, p75 50, p90 166); pump-fun `pool_created_at` is overwritten to ≈graduation time for graduates (unusable as age).

## 2. Ramp shape
**Pre-grad ramp (bonding snapshots → first pumpswap open):** indexing at −120m is impossible (**0 tokens**); −60m n=3, −30m n=1, −15m n=5 → **insufficient (<15) at every requested offset**. Indicative 5-min-bin path (sub-threshold n): median price/grad-price = **0.60** at −10..−5m (n=12), **0.84** at −5..0m (n=13); for the 18 reserve-triggered graduates, first-ps-open/trigger-price median **1.08** (p25 0.74, p75 1.97). I.e. the measurable ramp is confined to the **final ~10 minutes, roughly +20–65%**, and trigger snapshots often catch local spikes at/above the eventual graduation price.

**Post-grad path (pumpswap 1-min closes / first open, LOCF+terminal, OHLCV-covered grads; coverage caveat 118/242):**

| H | A (n=15) med | B (n=103) med | B p25 | B p75 | B frac<0.5x |
|---|---|---|---|---|---|
| +5m | 1.05 | **1.86** | 1.06 | 19.9 | 2% |
| +15m | 1.38 | 1.21 | 0.95 | 12.9 | 23% |
| +30m | 0.38 | 1.17 | 0.04 | 4.6 | 37% |
| +60m | 0.27 | 1.09 | 0.04 | 4.0 | 42% |
| +120m | 0.32 | **1.07** | 0.04 | 4.3 | **45%** |
| +240m | 0.27 | 1.05 | 0.04 | 3.5 | 47% |

Per-token 120m trough: overall median **0.81x @ 7m**; window A median trough **0.21x @ 24m**, end 0.30x (broad post-grad dump); window B median trough 1.00x, end 1.07x but **bimodal** — 26% lose >50% within 15m while p75 sits at 4.3x by 2h (10%-trimmed mean 6.4x: lottery structure). The classic "graduation dump" is a window-A and left-quartile phenomenon, not universal.

## 3. Tradability of "buy the late curve" (reserve triggers, net of costs)
Empirical calibration first: graduates complete the curve at observed reserve ≈**6.5–9k** (max pre-grad reserve p75 6.9k, p90 8.9k; trigger→graduation median **6 min**, p75 15); `reserve_usd ≥12k` readings are stalled/spiky pools (values up to 144k are impossible for a curve) — **P(graduate | cross 12k) = 1/68**. The requested 12k/15k/18k thresholds are therefore anti-signals; 6.5k/8k added as the calibrated "late curve".

120m horizon shown (60m/240m/terminal similar; nothing flips sign). Net@$200 clip, mean [95% cluster-bootstrap CI]:

| th | win | n (g/f, cens) | P(grad) | mean gross | med gross | mean NET@200 | med NET | mean NET@500 |
|---|---|---|---|---|---|---|---|---|
| 6.5k | A | 51 (0/51, 0) | 0.00 | −22% | 0% | **−35%** [−46,−24] | −14% | −45% |
| 6.5k | B | 207 (18/189, 5) | 0.09 | −22% | −1% | **−40%** [−47,−33] | −40% | −48% |
| 8k | A | 28 (0/28, 0) | 0.00 | −24% | 0% | **−35%** [−51,−21] | −11% | −42% |
| 8k | B | 125 (12/113, 4) | 0.10 | −14% | 0% | **−30%** [−40,−20] | −11% | −36% |
| 12k | A | 9 | — | — | — | INSUFFICIENT | — | — |
| 12k | B | 59 (1/58, 3) | 0.02 | −12% | 0% | **−16%** [−27,−6] | −6% | −21% |
| 15k | B | 51 (1/50, 3) | 0.02 | −13% | 0% | **−18%** [−30,−6] | −5% | −21% |
| 18k | B | 45 (0/45, 3) | 0.00 | −16% | 0% | **−20%** [−32,−8] | −5% | −23% |

(240m/terminal at 6.5k/8k B: mean net −23%/−1% with CIs spanning zero only via one 4.3x winner; medians −40%/−11%.) **The killer:** even *conditional on graduating*, triggered entries lose — grads' 120m gross mean **0.65x, median 0.17x** (th 6.5k B) — so **no graduation probability flips the EV** (breakeven undefined). Robust to dropping the 2 corrupt pumpswap first-bars (mean net −40% → −39.9%). Cost stack at $200 clip is itself ~15–20% round trip (entry impact 6.2% at 6.5k reserve + 1%+1%/0.8% fees + exit impact); $500 clips are strictly worse everywhere. Censored-alive at data end: ≤5 per cell (counted, excluded from feature comparison only).

## 4. Graduates vs failures at trigger time (th=6.5k; 18 g / 235 f)
| feature | grad med | fail med | AUC | p |
|---|---|---|---|---|
| buyers_m5 | **100.5** | **11.0** | **0.75** | <0.001 |
| vol_m5 | 13,780 | 2,310 | 0.74 | 0.001 |
| vol_h1 | 40,141 | 4,868 | 0.73 | 0.001 |
| fdv | 23.6k | 21.7k | 0.51 | 0.93 |
| buys/sells | 1.4 | 1.5 | 0.48 | 0.79 |
| age since discovery | 0 | 0 | 0.54 | 0.39 |

Ridge logistic (log1p-std): buyers +0.30, vol_h1 +0.21, fdv +0.01 — in-sample AUC 0.75. Tiers: buyers_m5≥30 → P(grad) **14%** (n=108) vs <30 → **2%** (n=150); vol_h1≥20k → 12% vs <5k → 2%. **Flow (buyers/volume) predicts graduation; price level (fdv) and reserve height do not.** But since grads' post-entry returns are themselves negative, this classifier rescues a post-grad strategy, not a curve entry.

## VERDICT
- **DEAD END — "buy the late curve" via reserve_usd triggers on this feed:** negative EV in **both windows, all 5 thresholds, gross and net**, mean and median, all 95% CIs below zero at 60–120m; high reserve (≥12k) is an *anti-signal* (P(grad)≤2%, spike/stall artifacts). Even the graduate subset loses (median 0.17x by +2h). At curve-scale reserves ($3–9k), impact+fees (~15–20% RT at $200) exceed the entire measurable pre-grad ramp beyond the final 10 minutes.
- **CANDIDATES (new leads, not yet validated):** (1) buyers_m5/vol_m5 at the completion zone as a graduation classifier (AUC 0.75, 14% vs 2% tiers) feeding a **post-graduation** entry; (2) window-B post-grad momentum — +5m median 1.86x on OHLCV-covered grads with only 2% <0.5x — *must first control for OHLCV-coverage survivorship (118/242)*; (3) avoid/fade window-A graduations (median 0.30x @2h, n=15, borderline).
- **INSUFFICIENT DATA:** pre-grad ramp at −30/−60/−120m (n≤5, 0 tokens at −120); window A at 12k/15k/18k (n≤9); anything conditioned on pre-grad observation of graduates (65/242 observed, 18 triggered — the GT collector discovers bonding pools median ~10 min pre-graduation).
- **Structural conclusion:** the curve completes ~6 min after reaching the observable completion zone, faster than the 3-min snapshot cadence + discovery lag; this dataset kills the *GT-feed-observable* version of the strategy but cannot adjudicate a pump.fun-native (websocket/curve-account) implementation — that requires a different collector.

Scripts: `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/grad_ramp.py`
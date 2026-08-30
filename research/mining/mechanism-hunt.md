# Non-Directional & Structural Edges — Verified Assessment

**Method (3 lines).** All estimates computed directly off `data/panel.db` raw `ohlcv` (which contains **only traded minutes** — zero-volume grid rows are created by `load_panel`, not stored, so row-presence *is* the liveness test). Every window requires: (a) a real-volume bar within ±2 min of **both** entry and exit, (b) ≥10 further real-volume minutes after the exit bar, (c) a backward-only snapshot for reserve (tol 1800 s, no lookahead); everything else is **discarded and counted**. CIs are 2.5/97.5 percentile cluster bootstraps (3000 reps) resampling **tokens** (`base_token_address`, fallback pool); costs from `memebot.backtest.costs.CostModel` (0.80%/side + `clip/(reserve/2)` impact) at a $200 clip; <15 tokens is flagged INSUFFICIENT.

**Panel:** 46,803 pools, 5,968 with bars, 840,497 traded minutes, $8.40B measured volume, broad coverage ≈ 3 days (1787788800→1788092340); snapshots (reserve) exist only from 1787841443, which is why window A is thin everywhere below.

---

## HEADLINE DISCARD COUNTS (the number that killed the last strategy family)

| Study | Windows attempted | **Discarded** | Kept | Discard rate | Dominant reason |
|---|---|---|---|---|---|
| LP, reserve≥50k, 6h | 9,068 | **8,550** | 518 | 94.3% | no reserve snapshot 7,959; entry not live 280; exit not live 140; pool did not live on 9 |
| LP, reserve≥50k, 24h | 4,743 | **4,465** | 278 | 94.1% | no reserve 4,087; entry not live 262; exit not live 65; did not live on 7 |
| LP at graduation, +30m/6h | 1,249 | **1,210** | 39 | **96.9%** | **exit not live 679**; entry not live 324; no reserve 204; did not live on 3 |
| LP at graduation, +30m/24h | 1,249 | **1,242** | 7 | 99.4% | exit not live 713 |
| Cross-venue arb (co-live minutes) | 436,701 | **391,449** | 45,252 | 89.6% | no reserve on one leg 391,448; implausible >100% gap 1 |
| Reserve-decay / rug (6h) | 733 | **603** | 130 | 82.3% | no reserve at horizon 381; entry not live 146; exit not live 70 |

The graduation-LP row is the important one: **679 of 1,249 fresh pools had no tradeable print at entry+6.5h.** Those are not "missing data" — they are dead pools, and an LP in them is stuck with the whole loss. Every LP number below is therefore computed on **survivors** and is biased *favourably*.

---

## (2) LP PROVISION ON GRADUATED POOLS — the item our data can actually answer

Two different questions. **NET** = LP value vs. holding quote (USDC/SOL), i.e. `sqrt(r) − 1 + fees − costs`; this bundles a big unhedgeable directional bet. **ALPHA** = `fees + divergence-loss − costs`, the *market-making* term isolated from direction — the only non-directional quantity here.

### Core panel, memecoin base assets only (SOL/USDC/USDT/cbBTC/etc. excluded), fee = 0.25% of volume

| Cut | n | tokens | fee yield | div. loss | cost | **ALPHA** (CI95) | **NET** (CI95) | win% |
|---|---|---|---|---|---|---|---|---|
| res≥50k, 6h | 518 | 74 | +3.74% | −2.12% | 1.07% | **+0.55%** [−1.71, +3.75] | +4.95% [−0.72, +12.26] | 39% |
| res≥50k, 24h | 278 | **39** | +1.59% | −2.90% | 1.04% | **−2.35%** [−5.00, −0.32] | −3.47% [−8.99, +0.92] | 35% |
| res≥15k, 6h | 581 | 98 | +3.62% | −2.80% | 1.14% | **−0.33%** [−2.62, +2.41] | +3.51% [−1.76, +10.36] | 37% |
| res≥15k, 24h | 307 | 42 | +2.33% | −3.31% | 1.10% | **−2.08%** [−4.72, −0.27] | −0.74% [−7.05, +5.29] | 38% |
| res≥50k, 6h, MAJORS (control) | 465 | 5 ⚠️ | +0.86% | −0.00% | 1.05% | −0.19% [−0.85, −0.16] | −0.11% [−1.08, −0.06] | 24% |

Medians are worse than means everywhere (24h res50k: median NET **−2.47%**, median ALPHA **−0.88%**). The positive 6h mean is a fat right tail — a single PINK window returns +180%. **50/50 hold beats LP in every memecoin cut** (24h: hold −1.56% vs LP net −3.47%), which is just IL doing what IL does.

**Fee-tier sensitivity** (res≥50k, memecoin): at the fee LPs actually receive on PumpSwap (0.20%, since 0.05% of the 0.25% goes to the creator) 24h ALPHA = **−2.67%** [−5.22, −0.77]. It takes a **1.00%** effective LP fee before 24h ALPHA turns positive (+2.42% [−1.68, +7.25]) — and that is arithmetic on unchanged volume, which is not how fee tiers work.

### LP into a freshly graduated pool (the classic "LP the runner" play)

| Entry | Horizon | n | tokens | fee | div loss | cost | **ALPHA** (CI95) | **NET** (CI95) | hold |
|---|---|---|---|---|---|---|---|---|---|
| created+30m | 6h | 39 | **39** | +6.63% | −15.19% | 2.24% | **−10.80%** [−17.74, **−3.46**] | +16.67% [−9.05, +46.61] | +49.93% |
| created+30m | 24h | 7 | 7 ⚠️ | +11.44% | −39.32% | 1.49% | −29.36% [−60.48, −0.91] | +36.01% [−63.19, +189.60] | +165.6% |
| created+2h | 6h | 6 | 6 ⚠️ | +27.19% | −8.93% | 1.26% | +17.00% [−1.90, +39.83] | +56.79% [−6.24, +125.79] | +51.09% |

**This is the cleanest statistically significant result in the study.** 39 tokens, CI excludes zero: an LP entering a freshly graduated memecoin pool loses **−10.8% per 6 hours** versus simply holding the identical 50/50 basket. Fee income is genuinely large (+6.63% in 6h, ~24x/yr on capital) and still loses to divergence by 2.3:1. The apparent +16.67% NET is 100% directional — LP *underperforms* the hold by 33 points — and it is measured on the 3.1% of pools that survived verification.

### Is there a filterable niche? (ex-ante test)

Trailing 6h volume/TVL predicts forward volume/TVL with **corr = 0.927** (log-log, n=430, 58 tokens), so a bot *can* select on turnover ex-ante. Result (res≥50k memecoin, 6h; 319 discarded):

| Ex-ante trailing turnover quintile | n | tokens | ALPHA (CI95) | NET (CI95) |
|---|---|---|---|---|
| Q1 [0.02, 0.17] | 86 | 24 | −1.02% [−1.08, −0.99] | −1.09% [−2.04, −0.32] |
| Q2 [0.17, 0.51] | 86 | 20 | −1.00% [−1.07, −0.97] | −1.09% [−1.99, +0.46] |
| Q3 [0.51, 1.23] | 86 | 16 | −1.01% [−1.22, −0.93] | −1.87% [−4.17, −0.18] |
| Q4 [1.31, 5.31] | 86 | 20 | −1.35% [−2.41, −0.64] | −1.78% [−7.84, +2.77] |
| Q5 [5.31, **457**] | 86 | **12** ⚠️ | +6.50% [−1.94, +25.64] | +13.34% [−5.98, +45.21] |

Q1–Q4 are all significantly negative. Q5 fails the token-count bar, its CI straddles zero, its **median ALPHA is −0.29%** and only 44% of its observations are positive — the mean is carried by two pools:

> **UMIA** (pumpswap): $369.5M volume on a $230k average reserve = **1,545x daily turnover**. **PONS**: $294.4M on $164k = **2,205x**. **WHUF**: 1,560x. **NVDA**: 1,190x. Three pools ≈ $989M = **11.8% of the entire panel's $8.40B volume**, on ~$200k of liquidity each.

Real memecoins turn 5–20x/day. 1,500–2,200x is wash / volume-farming, and an LP inside a wash-traded pool is earning fees paid by an operator who controls both sides of the flow and can exit through the LP at will. **The only cell with positive point-estimate LP alpha is the wash-trading cell.**

### LP tail risk (reserve is an observed snapshot quantity, not a resting-grid price)

Pools that reached ≥$50k, verified windows (6h: n=130, 20 tokens, 603 discarded; 24h: n=74, 13 tokens ⚠️, 372 discarded): P(reserve <0.5x in 24h) = 1.4%, but **P(price <0.5x in 24h) = 10.8%** and P(price <0.3x) = 5.4%. Reserve looks stable because reserve is *measured while the pool is alive*; the deaths are in the 82% we discarded. In the kept 24h graduation sample one verified position (WOFI, r=0.0002, res₀ $882k) marks at **−100.4%**.

**VERDICT (2): NOT FEASIBLE.** Memecoin LP is a leveraged short-volatility position sold at a price that does not cover the volatility. Fee income is real and large; divergence loss plus ~1.0–2.2% round-trip conversion cost is larger. Significant negative alpha at 24h (−2.35% [−5.00, −0.32], 39 tokens) and at graduation (−10.80% [−17.74, −3.46], 39 tokens). No ex-ante-selectable subset survives. Nobody appears to have published a clean realized-return study on PumpSwap LP; ours says don't.

---

## (1) CREATOR-FEE / LAUNCHPAD REVENUE MECHANICS

**The economics.** Launch costs ~0.02 SOL. Bonding-curve trades pay ~1%; post-graduation PumpSwap swaps pay 0.25%, split **0.20% platform/LP / 0.05% creator** in the flat model. Project Ascend replaced the flat creator share with a **market-cap-tiered dynamic fee: 0.95% for tokens at $88k–$300k MC, decaying to 0.05% at $20M MC** — deliberately paying the most at the size where a bot's own token would sit. Distribution reality: **$2,138,357 to 5,640 creators** in the first week (mean $379), with the **top 25 taking $19.5k–$78.5k each** — roughly 40% of the pool to 0.44% of creators. Graduation rate: **~1.15%**.

**Who captures it.** Not the launcher-as-lottery-ticket. The economics only work if you also supply the volume the fee is levied on, which is exactly the UMIA/PONS/WHUF signature above: at 0.95% creator fee, $370M of self-generated volume on your own token returns ~$3.5M of creator fees, funded by paying ~0.25%+ per round trip on wash flow. That is a negative-sum loop unless the fee tier exceeds your own execution cost *and* real outside flow subsidises it — which is why pump.fun shipped cashback specifically to curb creator-fee extraction. A $100–1,000 account launching honest tokens faces: 98.85% of launches never graduate; median creator revenue is functionally ~$0 (mean $379 is a power-law mean); no way to buy the attention that produces the 1.15%.

**VERDICT (1): NOT FEASIBLE.** The fee schedule is real and the top of the distribution is genuinely lucrative, but it is a *distribution* business (attention/streamers/networks), not an *automation* business. The automatable version — farm your own fee by trading your own token — requires more working capital than $1,000 to move the needle, is negative-sum against a 0.25%+ toll, is actively counter-engineered by the platform, and is market manipulation. No further work warranted.

---

## (3) CROSS-VENUE / BONDING-CURVE ARBITRAGE

**Bonding curve vs AMM: structurally impossible in our data.** 85 curve/AMM pool pairs on the same mint (pump-fun, meteora-dbc, launchlab, bags-fm vs pumpswap/meteora/raydium/orca). **Overlap of their traded-minute ranges: p50 = 0, p90 = 0, max = 0 minutes. 0.0% of pairs have a single co-live minute.** Migration is atomic — the curve stops and the AMM starts. There is no two-price window to arb.

**DEX vs DEX on the same mint:** 44 mints with ≥2 pools (≥20 bars each) → 220 pairs with ≥10 co-live real-volume minutes (35 pairs discarded for <10 co-live minutes), 30 tokens.

| Statistic across pairs | median | mean | p90 |
|---|---|---|---|
| median \|log gap\| | **0.19%** | 0.43% | 0.36% |
| p99 \|gap\| within pair | 0.53% | 2.90% | 1.80% |
| fraction of minutes \|gap\|>3% | 0.00% | 3.69% | 0.20% |
| gap autocorrelation (1 min) | 0.032 | 0.100 | 0.31 |

Panel-wide \|gap\| distribution across all 45,252 priced co-live minutes: **p50 = 0.158%, p90 = 0.424%, p99 = 0.875%** — an order of magnitude below the ~2.5–3.0% two-leg cost at a $200 clip.

**Extractable P&L, cost-charged, both legs verified live:** **57 profitable minutes out of 45,252** (0.126%), **4 tokens** ⚠️, **total $505.94 across the entire 3-day panel**, median $6.18, max $43.09. And these are minute *closes* — the gap is not an executable quote, our feed is minutes stale, and the large-gap pairs are exactly the ones where one leg is a ~$11–35k satellite pool (WindChill meteora leg = $11,167 reserve) whose "price" cannot absorb $200 without becoming the price.

**Infrastructure reality.** Competing bots run self-hosted `jupiter-swap-api` at ~38 ms median route detection with 96% Jito bundle landing vs 380 ms / 24% on public RPC; arbitrage is >50% of Solana DEX volume with 90M+ confirmed arb txs through Jito in 2025. Helius free tier = **1M credits/month, 10 RPC req/s, no mainnet LaserStream** (Business/Professional only; enhanced WebSockets from the $49 Developer tier). We are 3–4 orders of magnitude off the required latency and our data feed is minute-resolution.

**VERDICT (3): NOT FEASIBLE.** $506 of gross theoretical edge across 3 days, 4 tokens, 0.13% of minutes, at a resolution 100,000x coarser than the competition, on a free RPC tier that cannot even stream mainnet transactions. The curve→AMM variant does not exist at all.

---

## (4) PREDICTION MARKETS AND OTHER VENUES

**Polymarket.** On-chain analysis of ~95M transactions (Apr 2024–Dec 2025): **0.51% of wallets earned more than $1,000 in profit.** Median arbitrage spread has compressed to ~0.3% (below gas), and mean opportunity duration fell from 12.3 s (2024) to **2.7 s (2026)**, with **73% of arb profit captured by sub-100 ms bots**. Cross-venue Kalshi↔Polymarket spreads are still occasionally fat (LA Mayoral Feb 2026: 58¢ + 35¢ = 93¢, 7.5% gross; 5–8¢ persistent on World Cup), but the binding constraints are structural, not analytical: **capital is locked until resolution** (a 3% edge over 60 days is ~21% annualised only if both legs fill), **leg risk is the #1 practical failure**, and Kalshi is a KYC'd US CFTC venue while Polymarket is a separate rails/geo problem — two funded accounts, two APIs, manual rebalancing between them.

Honest read for us: the *residual* edge is real and non-directional (negative-risk/complement arb is a genuine structural inefficiency, unlike anything in memecoins), but it is a **capital-lockup and operations business**, not a signal business. At $100–1,000, a 2% locked-for-60-days edge is $2–20 per cycle against per-leg fees, withdrawal frictions and two KYC surfaces. It scales with capital and operational reliability, both of which we lack.

**Other non-directional venues, screened out on economics rather than tested:** sandwich MEV (~$370–500M extracted on Solana over 16 months, but by **203 attackers** with validator relationships, paying only 15–20% in tips — a closed club); JIT liquidity and liquidation bots (same latency stack as (3)); perp funding/basis (needs a CEX + perp venue and margin far above $1,000 to clear fixed costs).

**VERDICT (4): NOT FEASIBLE at our capital and infrastructure; the least-hopeless of the four.** Prediction-market complement arb is the only mechanism in this report whose edge is structurally guaranteed rather than statistically hoped for. It is gated by capital lockup, two-venue operations, and KYC — not by alpha. If the account ever reaches $10k+ with reliable dual-venue funding, this is the one to revisit; below that the per-cycle dollars do not pay for the plumbing.

---

## VERDICT

**There is no edge here either.** Four mechanisms, four negatives, and this time three of them are negative *for reasons that are structural rather than statistical* — which is a stronger result than a wide confidence interval.

| # | Mechanism | Verdict | The number that decides it |
|---|---|---|---|
| 1 | Creator-fee / launchpad revenue | **NOT FEASIBLE** | 1.15% graduation; $2.14M split by 5,640 creators with 40% to the top 25; the automatable version is wash-trading your own token |
| 2 | LP on graduated memecoin pools | **NOT FEASIBLE** | ALPHA −10.80% per 6h at graduation, CI [−17.74, −3.46], **39 tokens**; −2.35% [−5.00, −0.32] at 24h on res≥50k; every ex-ante turnover quintile negative except the wash-traded one |
| 3 | Cross-venue / curve-vs-AMM arb | **NOT FEASIBLE** | 0 co-live minutes curve↔AMM (85 pairs); median cross-DEX gap 0.158% vs ~2.5–3% cost; **$506 total, 4 tokens, 3 days** |
| 4 | Prediction markets | **NOT FEASIBLE at our size** | 0.51% of Polymarket wallets ever cleared $1,000; arb windows 2.7 s; edge is real but capital-locked and ops-gated |

**The one genuinely new finding worth keeping** is not a strategy, it is a data-integrity fact: **11.8% of the panel's entire $8.40B volume sits in three ~$200k PumpSwap pools turning 1,545–2,205x per day.** Any future study that weights by volume, ranks by volume, or estimates fee income from volume is measuring those bots. That belongs in the pipeline as a hard filter (flag `24h vol/reserve > ~50x`) before it silently manufactures the next +46%.

The measurement discipline held: the two places a positive number appeared (6h LP mean +4.95%; top-turnover ALPHA +6.50%) both dissolved under the token-count bar and the median — exactly as the exit-verifiability rule was designed to make them.

**Sources:** [Pump.fun Project Ascend fee model — Blockworks](https://blockworks.com/news/pumpdotfun-fee-model) · [Creator fee sharing / $2M day one — Yahoo Finance](https://finance.yahoo.com/news/pump-fun-fee-model-hands-125849600.html) · [Creator earnings distribution — CoinMarketCap Academy](https://coinmarketcap.com/academy/article/pumpfun-creators-earn-dollar2m-in-first-day-under-new-fee-structure) · [Pump.fun fee breakdown 2026 — SolTokenCreator](https://www.soltokencreator.io/blog/pump-fun-fees-explained) · [Graduation rate 1.15% — Cryptopolitan](https://www.cryptopolitan.com/pump-fun-graduating-tokens-break-to-1-15-of-new-launches/) · [Meteora DAMM fee/volume and dynamic fees — Meteora docs](https://docs.meteora.ag/product-overview/dynamic-amm-overview/dynamic-amm-lp-fee-and-apy-calculation) · [Meteora DAMM v2 risk analysis — Hindenrank](https://hindenrank.com/blog/how-does-meteora-damm-v2-work) · [Solana arbitrage latency benchmarks — RPC Fast](https://rpcfast.com/blog/solana-arbitrage-bot-setup) · [Solana trading infrastructure 2026 — Chainstack](https://chainstack.com/solana-trading-infrastructure-2026/) · [Helius plans and limits](https://www.helius.dev/docs/billing/plans) · [Polymarket bot profitability analysis](https://1023jack.com/market/are-polymarket-trading-bots-actually-profitable-the-math-behind-2026-s-predictio/) · [Kalshi↔Polymarket arbitrage 2026](https://www.predictionhunt.com/blog/kalshi-vs-polymarket-arbitrage) · [Solana MEV extraction 2026](https://dev.to/ohmygod/solana-mev-defense-in-2026-how-sandwich-bots-extracted-500m-and-the-6-protocol-level-defenses-16d9)

**Scripts** (all read-only, `file:...?mode=ro`, `busy_timeout=60000`): `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/{lp2.py,lp_stats.py,lp_alpha.py,lp_cond.py,lp_exante.py,lp_grad.py,rug2.py,arb.py,arb2.py,arb3.py,mig.py,q5.py}`; intermediate rows at `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/lp2.json`.
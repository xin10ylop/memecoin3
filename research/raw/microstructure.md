# Solana Memecoin Microstructure & Failure Modes — Research Report

**Sourcing legend:** [S] = well-sourced (peer-reviewed/large-N study or primary data), [I] = industry report (methodology stated, not peer-reviewed), [A] = anecdotal/practitioner consensus (verify empirically before coding into a strategy).

---

## 1. Pump.fun lifecycle

### Bonding curve mechanics
- Constant-product **virtual-reserve AMM** (`x·y=k`, Uniswap-v2-style). Curve seeded with ~**30 virtual SOL** against ~1.073B virtual token reserves; buys deposit real SOL, price rises deterministically along the curve. [S — mechanics widely documented: https://crypto.news/how-meme-coins-are-made-bonding-curves-pump-fun-rug-pulls/, https://flashift.app/blog/bonding-curves-pump-fun-meme-coin-launches/, https://www.solanatracker.io/pumpfun-api]
- Fixed supply **1B tokens**: ~**800M (793.1M)** sellable on the curve, ~**200M (206.9M)** reserved to seed the DEX pool at graduation. [S — https://moby.win/learn/pumpfun/, https://bolttx.io/en/blog/pump-fun-bonding-curve-explained]
- Exact constants (virtual reserves 30 SOL / 1,073,000,191 tokens, initial price ~2.8e-8 SOL, initial mcap ~$4–5k) appear consistently in dev docs (SolanaTracker, Chainstack) but **verify against the on-chain Global config account** — pump.fun has changed parameters before. [A→S boundary]

### Graduation threshold (2025–2026)
- Curve completes at ~**85 SOL** of net real reserves ≈ **$69,000 market cap** at historical SOL prices; the threshold is **SOL-denominated**, so the USD mcap floats (reported as high as ~$100k when SOL was expensive). [S — https://flashift.app/blog/bonding-curves-pump-fun-meme-coin-launches/, https://www.soltokencreator.io/blog/pump-fun-graduation-explained; $100k figure: https://www.chaincatcher.com/en/article/2139008]
- Since **Mar 20, 2025**, graduates migrate **instantly and free** to pump.fun's own AMM **PumpSwap** (previously: Raydium, with a 6 SOL migration fee). LP from migration is deposited and **burned/locked**. [S — https://www.theblock.co/post/347360/pump-fun-launches-dex-called-pumpswap-to-instantly-migrate-graduated-tokens, https://www.blocmates.com/news-posts/pump-fun-introduces-pumpswap-a-new-dex-for-graduated-token-listings]
- **Fees:** bonding-curve trades ~1% (platform has run 1.25% periods); PumpSwap 0.25% (0.20% LP / 0.05% protocol) at launch; **May 2025**: 0.05% creator fee share; **Aug 2025 "Project Ascend"**: dynamic creator fees — **0.95%/trade below $300k mcap tapering to 0.05% above $20M**; paid creators $2.4M in first 24h. [I — https://coinmarketcap.com/academy/article/pump-token-project-ascend-launches-10x-creator-rewards, https://solanafloor.com/news/pump-funs-new-creator-fee-model-pays-2m-24-hours, https://moby.win/learn/pumpfun/]
- Safety defaults: pump.fun mints have **mint & freeze authority revoked at creation** — honeypot risk on pump.fun-native tokens is structurally low; the risk profile is distribution/rug-based, not contract-based. [S — https://www.helius.dev/docs/orb/explore-authorities]

### Graduation rates (declining over time)
| Period | Grad rate | Source |
|---|---|---|
| Lifetime through mid-2025 | **~1.4%** | [I] https://www.chaincatcher.com/en/article/2139008 |
| Best week (Nov 2024) | 1.67% | [I] https://thedefiant.io/news/defi/pump-fun-token-graduation-rate-plummets (Dune) |
| Feb–Mar 2025 | **<1%/week**, ~1,500 grads/wk | [I] same |
| Sep–Oct 2025 (Marino et al.) | **0.63%** | [S] cited in https://arxiv.org/abs/2607.02823 |
| May–Jun 2026, N=832,941 launches | **0.198%** (95% CI 0.189–0.208%) | [S] https://arxiv.org/abs/2607.02823 |
| Jun 2026 | 0.26% | [I] https://coinlaw.io/memecoin-statistics/ |

- Volume context: ~20k+ launches/day at peak, only 100–200 graduating/day. [I — https://www.odaily.news/en/post/5197733]
- **Predictors of graduation:** advertising a Telegram channel → **1.485% vs 0.166%** grad rate (8.94x lift) [S — arXiv 2607.02823]. Comment-bots and bump-bots (front-page visibility) significantly raise performance; bundle bots reduce returns and shorten the dump window. [S — https://arxiv.org/pdf/2507.01963 family / https://arxiv.org/html/2601.08641v1]

### Post-graduation price behavior
- **MELT dataset (41,470 migrated pump.fun tokens, Dec 2024–Mar 2025, 200M+ txns): 84.13% of graduates classified high-risk; ~73% of those drop below 40% of migration price within 20 minutes of migration.** First hour post-migration carries **6x** the volume of the entire pre-migration phase — this is where insiders unwind. [S — https://arxiv.org/html/2602.13480v2]
- "Many tokens see 90%+ drawdowns within minutes of migrating" — consistent with MELT but the specific phrasing is from trade press. [A/I — https://www.odaily.news/en/post/5197733]
- Solidus Labs: of ~388,000 Raydium pools examined, **~93% (361k) showed soft-rug liquidity withdrawal**; median rug take ~**$2,832**, 25% under $732, largest $1.9M. [I — https://www.soliduslabs.com/reports/solana-rug-pulls-pump-dumps-crypto-compliance]
- **>95% of Raydium rug pulls completed within 10 seconds of pool creation** (pre-funded rug bots). [I — https://cryptoslate.com/how-traders-make-over-60k-per-week-rugging-98-of-memecoins-on-pumpfun/]
- Implication for a quant system: graduation itself is a **negative-expectation event on average**; edge must come from filtering the ~15% non-high-risk cohort or trading the pre-graduation curve.

---

## 2. Scam taxonomy + detection heuristics (free data only)

All heuristics below use: Solana RPC (`getAccountInfo`, `getTokenLargestAccounts`, `getTokenSupply`, `getSignaturesForAddress`, `getTransaction`), DexScreener API (`pairs`: `liquidity.usd`, `fdv`, `volume.h24/h1/m5`, `txns.{h1,h24}.buys/sells`, `pairCreatedAt`, boosts), GeckoTerminal API (pools, `reserve_in_usd`, OHLCV), Jupiter `/quote`. Heuristic thresholds are practitioner-standard [A] unless a study is cited.

### 2.1 Honeypots (can't sell)
- **Mechanism:** on Solana, mostly via **freeze authority** (freeze buyer ATAs post-purchase) or **Token-2022 extensions** (transfer hook, transfer fee up to 100%, permanent delegate). Classic EVM-style sell-blocking code doesn't exist for vanilla SPL tokens. [S — https://www.helius.dev/docs/orb/explore-authorities]
- Prevalence is low in curated samples: 3.96% of high-performing meme coins flagged as honeypots cross-chain. [S — https://arxiv.org/pdf/2507.01963]
- **Detection:**
  1. `getAccountInfo(mint)` → parse SPL Mint: `freezeAuthority != null` ⇒ hard fail; `mintAuthority != null` ⇒ hard fail.
  2. Owner program check: mint owned by Token-2022 (`TokenzQd...`) ⇒ parse extensions; reject transfer-hook, permanent-delegate, transfer-fee > ~1%.
  3. **Jupiter sell-quote simulation:** request `/quote` token→SOL for a realistic size (e.g., $500–1,000); no route, or `outAmount` implying price impact ≫ pool depth predicts, ⇒ honeypot or fake liquidity. (CoinGecko's reference checker uses exactly this: Jupiter quote + authority audit + SPL-program verification, $1,000 test size, 10% slippage bound.) [S/I — https://www.coingecko.com/learn/build-honeypot-checker]
  4. Behavioral confirm: DexScreener `txns.h1.sells == 0` with `buys > ~20` ⇒ nobody can sell. [A]

### 2.2 Mint / freeze authority abuse
- **Mechanism:** retained `mintAuthority` → infinite dilution; retained `freezeAuthority` → selective freezing; metadata `updateAuthority` → impersonation-by-rename. Pump.fun-native tokens are safe by construction; **direct Raydium/Meteora listings are where this lives.** [S — https://www.helius.dev/docs/orb/explore-authorities]
- **Detection:** single `getAccountInfo` on the mint (bytes 0–36 encode mintAuthority option+key; freezeAuthority at offset 36+). Also check the token was created by a known launchpad program (pump.fun program `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`) vs. arbitrary deployer. Tools RugCheck.xyz / Solsniffer score exactly these fields. [A/I — https://createmycoin.app/articles/solana-rug-checker-guide, https://github.com/machenxi/rugpull-scam-token-detection]

### 2.3 LP pull vs burned LP
- **Mechanism:** deployer holds LP tokens → withdraws both sides ("soft rug"). 93% of Raydium pools showed this pattern; 90%+ of pool liquidity drained in one sweep is the signature. [I — https://www.soliduslabs.com/reports/solana-rug-pulls-pump-dumps-crypto-compliance]
- **Detection:**
  1. Find the pool's LP mint (Raydium AMM state / DexScreener `pairAddress`); `getTokenLargestAccounts(lpMint)` → if largest holder is the burn address (`1nc1nerator...`) or LP supply ≈ 0 (burned), pull risk is dead; if deployer wallet holds >10–20% of LP ⇒ high risk. Pump.fun→PumpSwap migrations burn/lock LP automatically. [A + S for migration behavior]
  2. Liquidity-vs-FDV sanity: DexScreener `liquidity.usd / fdv < ~1–2%` on a non-graduated pool ⇒ thin exit; combined with unlocked LP ⇒ near-certain soft rug. [A]
  3. Time-series: GeckoTerminal `reserve_in_usd` dropping >90% in one candle = executed rug (post-hoc label for training data). [A, matches Solidus 90% threshold]

### 2.4 Bundled supply (dev multi-wallet buys at launch)
- **Prevalence/impact:** bundle bots in ~**25%** of pump.fun projects; associated with lower returns and faster dumps [S — https://arxiv.org/html/2601.08641v1]. MELT: coordinated accounts held **36.5% of supply on average** while appearing independent. [S — https://arxiv.org/html/2602.13480v2]
- **Detection (MELT's three methods are directly reproducible):**
  1. **Same-block/same-bundle buys:** fetch the creation transaction's block; wallets buying in the creation block or same **Jito bundle ID** as the deploy ⇒ bundled. (Jito explorer exposes bundle IDs; free.) [S]
  2. **Funding-graph:** `getSignaturesForAddress` on each top-20 holder; if N wallets were funded by the same parent wallet (or fresh wallets funded minutes before launch via the same CEX hot wallet/intermediary), cluster them. [S — MELT "fund-flow relationships"]
  3. **Aggregate cluster share:** sum clustered holdings from `getTokenLargestAccounts`; reject if cluster > ~15–25% of supply, or top-10 holders (ex-curve/LP) > 30% (GoPlus/CertiK industry threshold; manipulated tokens averaged 77.85% concentration). [S — https://arxiv.org/pdf/2507.01963]

### 2.5 Sniper clusters
- **Prevalence:** sniper bots present in the **majority** of pump.fun launches [S — arXiv 2601.08641]. Cross-launch study: **1,012 persistent cohorts (2,965 wallets, 2–12 wallets each)** detected over 166,098 launches/13.4 days; sniped launches show **+16.1%** first-30-min buyer count but SOL-inflow effect indistinguishable from zero; **7% of sniped launches had zero organic buyers in 30 min** (pure bot theater). [S — https://arxiv.org/pdf/2607.02795]
- **Detection:** buyers in first N slots after pool creation (`pairCreatedAt` from DexScreener, or first signatures on the curve account); flag wallets that appear as first-window buyers across **many unrelated launches** (co-occurrence graph + union-find, per the paper); a launch where >50% of first-minute volume is from known sniper wallets who exit within minutes is exit liquidity, not demand. [S methodology / A thresholds]

### 2.6 Wash trading / volume faking
- **Prevalence:** 21.4% of pre-migration pump.fun transactions were wash trades in MELT [S]; 287/707 high-performing tokens showed wash trading, median volume inflation **1,772%** per event [S — arXiv 2507.01963]; single-token case study: >$500k fake volume in 12h from 3 wallets [I — https://bitquery.io/blog/solana-volume-numbers-are-a-lie]; VanEck's Sigel estimated 14.2% of Solana app revenue from wash trading (contested) [A/I — https://x.com/matthew_sigel/status/1853456012734591462].
- **Detection heuristics (from the papers, computable from DEX trade feeds / GeckoTerminal trades endpoint):**
  1. *Zero-risk position:* wallet buys and sells near-identical amounts same day (±2%). 
  2. *Circular volume:* ≥99% of a day's volume from the same maker set on both sides.
  3. *Repeat-offender network:* same makers across every high-volume day.
  4. Cheap proxy without wallet data: DexScreener `volume.h24 / liquidity.usd > ~50–100x` with flat price, or `txns` buys≈sells at machine-regular cadence with tiny unique-trader count. [A]

### 2.7 Slow rugs
- **Mechanism:** dev/insiders drip-sell bundled supply over hours–days instead of pulling LP; also "farmed" creator-fee tokens under Project Ascend (launch → light support → collect dynamic fees → abandon). [A — widely reported; fee-farming incentive: https://coinmarketcap.com/academy/article/pump-token-project-ascend-launches-10x-creator-rewards]
- **Detection:** track top-holder balances over time (`getTokenLargestAccounts` polled); monotonic decline of dev-cluster balance while price bleeds, sells routed through fresh intermediate wallets (1-hop funding from dev wallet); DexScreener signature: steadily negative buy/sell imbalance, liquidity flat (LP not pulled) but price −70–90% over days; creator-fee claim transactions on the pump.fun fee program without any creator buys. [A]

---

## 3. What % are scams/dead within 24h–1 week
- **98.6%** of 7M+ pump.fun tokens (≥5 trades, pre-Apr 2025) failed to hold **$1,000 liquidity** — Solidus Labs classifies these as rug/pump-and-dump-like outcomes; only ~97,000 survived the threshold. Pump.fun disputes the "fraud" framing (illiquid ≠ scam), so treat as **death rate, upper bound on scam rate**. [I — https://www.coindesk.com/business/2025/05/07/98-of-tokens-on-pump-fun-have-been-rug-pulls-or-an-act-of-fraud-new-report-says, https://www.soliduslabs.com/reports/solana-rug-pulls-pump-dumps-crypto-compliance]
- **~98–99.8% never graduate** (rates above), and non-graduates on the curve typically go inactive within hours; even among **graduates**, 84% are high-risk and ~73% of those lose >60% within 20 minutes. [S — arXiv 2607.02823, 2602.13480]
- ~93% of Raydium memecoin pools soft-rugged; >95% of those rugs execute within 10 seconds. [I — Solidus/CryptoSlate above]
- Aggregate losses: Chainalysis-tracked rug-pull losses **$2.8B in 2025**; Merkle Science: $500M lost to pump.fun-adjacent rugs in 2024. [I — https://coinlaw.io/memecoin-statistics/, https://www.coindesk.com/business/2025/05/07/98-of-tokens-on-pump-fun-have-been-rug-pulls-or-an-act-of-fraud-new-report-says]
- Only ~3% of pump.fun users have net profits >$1,000; ~50–70k DAU. [I — https://www.chaincatcher.com/en/article/2139008]

---

## 4. PvP dynamics on narrative launches (mostly [A] — no rigorous study found)
- **Attention window:** when a meme/news event breaks, hundreds of same-name tokens launch within minutes; the exploitable window is ~**30–60 minutes** of concentrated attention. Cloning tools launch a copy on pump.fun in <30 seconds. [A — https://medium.com/@jump_bit/why-token-cloning-is-the-next-big-meta-on-solana-8022722746de]
- Case pattern (Kylie Jenner X-hack, Aug 2026): original token → $1.2M mcap in minutes; copycat wave within hours, some also crossing $1M, nearly all → 0. [A/I — https://yellow.com/news/kylie-jenner-meme-coin-suspected-x-hack]
- **How the winner is decided (practitioner consensus, in rough order):**
  1. **First on-chain mover with a "clean" launch** usually anchors the Dexscreener/Photon feeds — but first-mover advantage is conditional: the first token that *doesn't* show bundled supply/dev dumping tends to win over the literal first. [A]
  2. **Dev behavior/credibility:** "dev sold" is an instant kill signal; conversely a dev holding/buying, or a known serial deployer wallet, attracts snipers. Community takeovers (CTO) can resurrect a rugged first-mover. [A]
  3. **KOL/caller entry is the usual tiebreaker:** one large caller/Telegram group consolidates flow onto one contract address; exchanges/KOLs have literally been confused about which ticker is "the" token. [A — https://cryptokolz.com/memecoin-influencers, https://www.dextools.io/tutorials/solana-memecoins-complete-guide-2026]
  4. PvP itself suppresses price: BAN example — −80% amid PvP/FUD, recovered only after ~20h of consensus formation. [A — https://www.chaincatcher.com/en/article/2153015]
- Quant-relevant: winner determination is a **coordination game resolved off-chain (X/Telegram)**; on-chain leading indicators are relative first-30-min *organic* (non-cohort) buyer counts across contenders — the sniper-cohort paper shows raw buyer counts are heavily contaminated (+130.9% naive vs +16.1% corrected), so de-bot the flow before comparing. [S — arXiv 2607.02795]

---

## 5. Sandwich/MEV exposure on Solana
- **Scale:** one dominant bot ("Vpe", ~half of all Solana sandwiches, run via DeezNode's private mempool) executed **1.55M sandwiches in 30 days** (Dec 2024–Jan 2025), 88.9% success, avg profit **0.0425 SOL (~$8.67)** per sandwich, **$13.4M/30d**, paying 34.5% of profits (22,760 SOL) as Jito tips. [I — https://www.helius.dev/blog/solana-mev-report]
- **Who gets hit:** predominantly **Raydium swaps; 16 of top-20 sandwiched tokens were pump.fun coins**; memecoin traders using Telegram bots with high slippage are the primary victims. [I — Helius report]
- **Structural facts:** Jito shut its public mempool **Mar 8, 2024**; sandwiching now requires private mempools/colluding validators — risk is reduced, not zero, and concentrated in a few operators (DeezNode validator: ~811,605 SOL delegated). Jito tips ≈ **60% of Solana's non-base fee market by Jan 2025**; 3.75M SOL tips in 2024. [I — Helius, https://www.dlnews.com/articles/defi/solana-users-use-jito-to-stop-sandwich-attacks-and-mev/, https://blog.quicknode.com/solana-mev-economics-jito-bundles-liquid-staking-guide/]
- **Retail-size exposure:** at ~$8.67 avg extraction, a $200–2,000 swap in an illiquid memecoin with 10–30% slippage tolerance is exactly the target profile; low-slippage swaps in deep pools are rarely worth attacking. [I/A]
- **Mitigations a bot should implement:**
  1. **Route via Jito-only submission / MEV-protect RPC** (transaction never touches shared mempools); tip floor ~0.0001+ SOL, scale with congestion (~$0.04+ normal conditions). [I — https://solana.com/developers/guides/advanced/mev-protection, DL News]
  2. **Tight/dynamic slippage:** Jupiter dynamic slippage (Aug 2024) sizes tolerance per token; hard-cap slippage and split large orders — slippage tolerance is the sandwicher's max take. [I — Helius]
  3. **Priority fees vs tips:** priority fee buys scheduler position, Jito tip buys bundle inclusion/privacy; during hot launches snipers paid median 1.2 SOL/tx (TRUMP launch, peaks 3.7 SOL). [I/A — https://medium.com/@shamikhzafar0/the-anatomy-of-jito-tips-who-pays-why-and-how-market-dynamics-shape-solanas-mev-economy-de2a0b09ca26]
  4. Structural: sr-AMM pools (Ellipsis "Plasma") and RFQ (JupiterZ) eliminate sandwich surface but have no liquidity for fresh memecoins. [I — Helius]

---

## Key primary sources
- arXiv 2607.02823 — survival analysis, 832,941 launches, 0.198% grad rate: https://arxiv.org/abs/2607.02823
- arXiv 2607.02795 — sniper cohorts (1,012 rings): https://arxiv.org/pdf/2607.02795
- arXiv 2602.13480 — MELT dataset, 41,470 graduates, 84% high-risk: https://arxiv.org/html/2602.13480v2
- arXiv 2507.01963 — manipulation taxonomy + wash-trade heuristics: https://arxiv.org/pdf/2507.01963
- arXiv 2601.08641 — bot taxonomy (bundle/sniper/comment/bump), 6,000 projects: https://arxiv.org/html/2601.08641v1
- Solidus Labs rug-pull report (98.6% / 93% soft rugs): https://www.soliduslabs.com/reports/solana-rug-pulls-pump-dumps-crypto-compliance (coverage: https://www.coindesk.com/business/2025/05/07/98-of-tokens-on-pump-fun-have-been-rug-pulls-or-an-act-of-fraud-new-report-says)
- Helius Solana MEV report: https://www.helius.dev/blog/solana-mev-report
- Grad-rate trend: https://thedefiant.io/news/defi/pump-fun-token-graduation-rate-plummets, https://www.theblock.co/data/on-chain-metrics/solana/pump-fun-percent-graduated-tokens-daily, https://www.chaincatcher.com/en/article/2139008
- PumpSwap migration: https://www.theblock.co/post/347360/pump-fun-launches-dex-called-pumpswap-to-instantly-migrate-graduated-tokens
- Project Ascend fees: https://coinmarketcap.com/academy/article/pump-token-project-ascend-launches-10x-creator-rewards, https://solanafloor.com/news/pump-funs-new-creator-fee-model-pays-2m-24-hours
- Honeypot checker method (Jupiter sell-quote + authorities): https://www.coingecko.com/learn/build-honeypot-checker; authorities: https://www.helius.dev/docs/orb/explore-authorities
- Wash-trade case study: https://bitquery.io/blog/solana-volume-numbers-are-a-lie
- Curve math: https://flashift.app/blog/bonding-curves-pump-fun-meme-coin-launches/, https://www.solanatracker.io/pumpfun-api

**Biggest caveats:** (1) the 98.6% "fraud" number is a liquidity-death metric, not proven intent; (2) graduation thresholds/fees have changed repeatedly — read live values from pump.fun's on-chain Global config, not blogs; (3) all §4 PvP claims and most numeric heuristic thresholds in §2 are practitioner consensus, not studied — backtest them on MELT (CC-BY, Zenodo) before trusting.
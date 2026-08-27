# Attention/Social Signal Sources for a Zero-Budget Memecoin Bot — Verified 2026-08-27

All curl tests run from this server (datacenter IP, egress via HTTPS proxy) on 2026-08-27. "VERIFIED" = live response received today.

---

## 1. DexScreener paid-promotion endpoints — VERIFIED, all free, no key

### 1a. `token-profiles/latest/v1` — VERIFIED 200
```bash
curl -s "https://api.dexscreener.com/token-profiles/latest/v1"
```
Returns array of the most recently **paid-for** Enhanced Token Info profiles: `{url, chainId, tokenAddress, icon, header, description, links[] (website/twitter/telegram), cto}`. Appearing here means someone paid DexScreener for the profile (Enhanced Token Info is a paid product). The `cto` flag marks community-takeover profiles. Live sample today included fresh Solana pump.fun tokens with full social links.

### 1b. `token-boosts/latest/v1` and `token-boosts/top/v1` — VERIFIED 200
```bash
curl -s "https://api.dexscreener.com/token-boosts/latest/v1"   # most recent boost purchases
curl -s "https://api.dexscreener.com/token-boosts/top/v1"      # ranked by active boost count
```
Same profile fields plus `amount` (boosts in this purchase) and `totalAmount` (active boosts). Observed today: tokens with `totalAmount` 10, 100, 500. Boosts are hard USD spend: packs run from ~$99 up to **$3,999 for 500 boosts** (the "Golden Ticker"), and boosts act as a multiplier on DexScreener's trending score — see [DexScreener boosting docs](https://docs.dexscreener.com/boosting), [OpenLiquid boost analysis](https://openliquid.io/blog/dexscreener-boost-feature-explained/), [tactical guide](https://medium.com/@lexlagan1337/paid-boosts-on-dexscreener-a-tactical-guide-5c14ab1cf2de).

### 1c. Per-token paid-order lookup + two bonus endpoints — VERIFIED 200
```bash
curl -s "https://api.dexscreener.com/orders/v1/solana/HavpAp4PqYUfiwyFpd9qcCKWrEVi52Z7CYJuXfQqpump"
# → {"orders":[{"type":"tokenProfile","status":"approved","paymentTimestamp":1787792547218}],
#    "boosts":[{"amount":500,"paymentTimestamp":1787794412299}]}
curl -s "https://api.dexscreener.com/ads/latest/v1"                   # paid ads: {type:"tokenAd", impressions: 10000-50000}
curl -s "https://api.dexscreener.com/community-takeovers/latest/v1"   # CTO profiles
```
`orders/v1` gives **payment timestamps** — you can compute "minutes since promoter spent money," a clean event-time feature. `ads/latest/v1` (impressions bought) was not in older docs and is live.

**Rate limits:** 60 req/min for all of the above per [DexScreener API reference](https://docs.dexscreener.com/api/reference) (pair/token price endpoints are 300 req/min). Polling `token-boosts/latest` every 5–10 s is within budget.

**Signal value / gaming risk:** This is *promoter conviction*, not organic attention — a $3,999 Golden Ticker is a costly signal (dev/marketing believes they can recoup it), but it's also the standard playbook of coordinated pump teams; the boost-farmed coins with 5–10k boosts are pure exit-liquidity funnels. Empirically boosts front-run retail flow by minutes-to-hours because DexScreener's trending bar is where retail looks. Gaming cost is real dollars (cannot be faked for free), but "gamed" here means *you are the target* — treat a boost as "marketing wallet is loaded," combine with holder-distribution safety checks, and prefer *first* boost events on young tokens over cumulative counts.
**Verdict: USE** — highest-value free attention feed; use boost `paymentTimestamp` deltas and `totalAmount` tiers (10/50/100/500) as features, never as standalone buy signals.

---

## 2. GeckoTerminal `trending_pools` — VERIFIED, free, no key

```bash
curl -s -H "Accept: application/json" \
  "https://api.geckoterminal.com/api/v2/networks/solana/trending_pools?duration=5m&page=1"
```
VERIFIED: 20 pools/page with `price_change_percentage` (m5/m15/m30/h1/h6/h24), `volume_usd`, `reserve_in_usd`, `pool_created_at`, and `transactions` per window including **`buyers`/`sellers` unique-trader counts** (e.g. `"h1":{"buys":1528,"sells":1228,"buyers":992,"sellers":783}`). `duration` accepts 5m/1h/6h/24h. `new_pools` endpoint also VERIFIED (20 newest pools).

**How trending is computed:** per [CoinGecko's trending-pools doc](https://docs.coingecko.com/reference/trending-pools-list), ranking combines (1) GeckoTerminal user engagement (web visits/clicks), (2) market activity (volume, transactions), (3) pool security checks (liquidity, honeypot). So it's **partly real eyeball data** (site engagement) — but that makes it a *lagging* attention measure: a pool trends after volume and pageviews already spiked, typically 10–60+ min behind the initial move. Keyless data is cached ~60 s; free rate limit is **30 calls/min** ([GT FAQ](https://apiguide.geckoterminal.com/faq), [CoinGecko support](https://support.coingecko.com/hc/en-us/articles/23407777579801)). No rate-limit headers returned (verified).

**Gaming risk:** volume/tx components are wash-tradeable for pennies on Solana (self-trades, multi-wallet bots); the `buyers` unique count is harder but still fakeable at ~fee-cost per wallet. The web-visit component is the least fakeable part.
**Verdict: USE, but as confirmation/feature, not discovery** — the 5m-duration list is the least stale. The real gold in this API is the `buyers` field (see §4).

---

## 3. Free / scrapeable social

| Source | Test result | Verdict |
|---|---|---|
| **Farcaster** | Public hubs on custom ports **failed from this server**: `snap.farcaster.xyz:3381` → connection reset, legacy `hoyt:2281` dead (note: this box's egress proxy may block non-443 ports; hubs also largely retired post-Snapchain). `hub-api.neynar.com` now demands API key or x402 micropayment (verified 402-style response). **BUT the client API works keyless on 443:** `curl -s "https://client.farcaster.xyz/v2/search-casts?q=solana&limit=25"` → VERIFIED full JSON casts with author `followerCount`, timestamps (also live at `client.warpcast.com`). Unofficial/undocumented — can break or get rate-limited anytime. | **USE (secondary)** — poll ticker/CA searches; crypto-native user base, decent early-signal density. Low gaming cost (bots are cheap), so weight by follower count / account age. |
| **Reddit JSON** | `https://www.reddit.com/r/CryptoMoonShots/new.json` → **403 from this datacenter IP** with default and custom UA (old.reddit too; returns block page HTML). Reddit blocks cloud IPs since the 2023-24 API lockdown. Works from residential IPs; OAuth script-app route (free, 100 QPM) still exists but requires app registration. | **SKIP from this server** (or use free OAuth app). Reddit is slow for sub-24h memecoins anyway; mostly shill spam — high gaming, low alpha. |
| **Telegram `t.me/s/<channel>`** | VERIFIED 200: `curl -s -A "Mozilla/5.0..." "https://t.me/s/pumpfunnews"` → 20 messages parsed, incl. `tgme_widget_message_views` view counts. No key, no login; works for any public channel; poll per-channel and diff message IDs. | **USE** — build a watchlist of caller channels; message-mention → CA extraction + channel view velocity. Gaming risk high (channels are paid-post machines, views botted for ~$1/1k) — treat any channel mention as "shill event," useful mainly for *timing* pumps you already validated on-chain. |
| **Google Trends (pytrends)** | **VERIFIED WORKING from this server today**: `pip install pytrends`; `interest_over_time()` for "solana", `now 1-d` → 180 rows. Unofficial; notorious for 429s at scale (keep <1 req/10s, cache aggressively, expect breakage when Google changes endpoints). | **USE only for macro regime** (memecoin-season on/off via "solana", "pump.fun" queries). Daily granularity + normalization makes it useless for individual 6-hour-lifespan tokens. Hard to game, but far too slow. |
| **Nitter (X mirror)** | 2026 state: `nitter.poast.org` dead (000), `privacyredirect` 502, `lightbrd` 403; `nitter.net` and `xcancel.com` return 200 **but 0 tweets to curl** (JS/anti-bot challenge; verified `grep -c timeline-item` = 0). Public instances have been guest-account-starved since early 2024. | **SKIP** — unreliable foundation for a bot. X data without paid API in 2026 is effectively residential-proxy scraping (ToS-violating, fragile). |
| **LunarCrush** | `api4/public/...` without key → 401 (verified). No usable free API tier in 2026 — plans are paid ([pricing](https://lunarcrush.com/pricing/), [dev pricing](https://lunarcrush.com/developers/pricing)); their data is mostly X-derived anyway. | **SKIP** (violates $0 constraint). |
| **TikTok / Instagram** | TikTok tag page → 200 but content is JS-hydrated + heavy device fingerprinting; internal APIs need signed `X-Bogus`/device params. IG → 302 to login wall (both verified). Server-side scraping requires maintained evasion libs + residential proxies. | **SKIP from a server.** Not worth it; TikTok memecoin virality usually shows up in pump.fun volume before you could scrape it anyway. |

---

## 4. On-chain attention proxies (the best "social" signal is wallets)

- **Buyer-count acceleration (GeckoTerminal `transactions.*.buyers`)** — VERIFIED free (§2). Unique buyers per 5m/15m/30m/1h lets you compute d(buyers)/dt and buyers-per-tx (crowd vs. bot ratio: `m30 buys=569, buyers=377` is organic-ish; `buys=569, buyers=12` is wash). Latency ~60 s cache. Gaming cost: nonzero (each fake buyer = wallet + rent + fees + swap fees, ~cents each, so thousands of fake buyers ≈ tens of dollars — cheap-ish but visible in size distribution). **USE — this is your primary attention proxy.** Also available per-pool: `curl -s "https://api.geckoterminal.com/api/v2/networks/solana/pools/{pool}"`.
- **Holder growth via RPC** — public `api.mainnet-beta.solana.com` is barely usable: `getTokenSupply` worked (verified), but heavy calls are throttled per-method (`getTokenLargestAccounts` → 429 "Too many requests for a specific RPC call" on first try, succeeded on retry) and `getProgramAccounts` on the token program is disabled/impractical. **Feasible only via a free-tier indexer key** (Helius free tier: `getTokenAccounts`/DAS gives holder counts; still $0). Verdict: **USE via Helius free tier if you'll accept one signup; SKIP on public RPC.** Cheap to game (dust 10k wallets for a few dollars) — filter holders below a min balance.
- **Unique-wallet inflow** — same as buyers field above (free) or via free-tier webhooks (Helius). Redundant with GT buyers; **USE GT version**.
- **KOL wallet lists — yes, public ones exist:**
  - **kolscan.io/leaderboard** — VERIFIED scrapeable with plain curl: extracted **50 unique Solana wallet addresses** today (pattern `/account/<base58>` in the HTML), e.g. `AGqjivJr1dSv73TVUvdtqAwogzmThzvYMVXjGWg2FYLm`. Named KOLs with PnL ranking. **USE** — refresh the list daily, then watch those wallets' swaps via free RPC/websocket; "2+ KOL wallets bought within 10 min" is a strong, hard-to-fake conviction signal (KOLs can rug followers, though — they get allocations; treat late KOL entries better than deployer-adjacent early ones).
  - **Dune public queries** — [Solana KOL Wallets (query 4868517)](https://dune.com/queries/4868517), [best trader address list (3832067)](https://dune.com/queries/3832067), [Top Traders 1H/7D](https://dune.com/cryp_tourist/solanatoptrades), [Smart Wallet Tracker](https://dune.com/0xqiqi/super-secret-wallet-tracker) — Dune's free tier allows manual CSV export/viewing; API export needs credits (free tier includes a small monthly allowance).
  - **gmgn.ai leaderboard API** — 403 Cloudflare from server (verified). SKIP.

---

## 5. Summary table

| Source | Reliability | Latency | Gaming cost to fake | Verdict |
|---|---|---|---|---|
| DexScreener boosts/profiles/ads/orders | High (documented, 60 rpm) | Seconds from payment | $99–$4k (real money, but *is* the promo) | **USE** (core) |
| GeckoTerminal trending_pools | High (documented, 30 rpm) | ~1–60 min behind move | Low-med (wash volume) | **USE** (confirmation) |
| GeckoTerminal `buyers` counts | High | ~60 s | Med (per-wallet cost) | **USE** (core) |
| kolscan KOL wallets + RPC watch | Med (HTML scrape) | Real-time once watching | High (real PnL history) | **USE** |
| Telegram t.me/s/ previews | Med-high | ~Real-time | Low (botted views) | **USE** (timing/shill detector) |
| Farcaster client.farcaster.xyz search | Med (unofficial) | Real-time | Low | **USE** (secondary) |
| pytrends | Low-med (429s) | Hours-days | High | **USE** (regime only) |
| Reddit JSON | Blocked from DC IP | Hours | Low | SKIP (or free OAuth) |
| Nitter/X mirrors | Dead/challenged in 2026 | — | — | **SKIP** |
| LunarCrush | Paid-only | — | — | **SKIP** |
| TikTok/IG server-side | Login/JS-walled | — | — | **SKIP** |
| Helius free-tier holder counts | High (needs signup) | ~Real-time | Low (dust wallets) | Optional |

**Environment caveat:** this box's egress proxy appears to block non-443 ports (Farcaster hub `:3381`/`:2281` connection resets may be partly local), and Reddit's 403 is datacenter-IP-based — both could differ on other hosts.

Sources: [DexScreener API reference](https://docs.dexscreener.com/api/reference) · [DexScreener boosting docs](https://docs.dexscreener.com/boosting) · [Boosting T&C](https://docs.dexscreener.com/privacy/boosting-terms-and-conditions) · [OpenLiquid boost review 2026](https://openliquid.io/blog/dexscreener-boost-feature-explained/) · [Paid Boosts tactical guide](https://medium.com/@lexlagan1337/paid-boosts-on-dexscreener-a-tactical-guide-5c14ab1cf2de) · [CoinGecko trending-pools doc](https://docs.coingecko.com/reference/trending-pools-list) · [GeckoTerminal API FAQ](https://apiguide.geckoterminal.com/faq) · [GT rate-limit support note](https://support.coingecko.com/hc/en-us/articles/23407777579801-The-rate-limit-for-the-public-GeckoTerminal-API-is-too-low-Can-I-request-a-higher-rate-limit) · [LunarCrush pricing](https://lunarcrush.com/pricing/) · [LunarCrush dev pricing](https://lunarcrush.com/developers/pricing) · [Dune Solana KOL Wallets](https://dune.com/queries/4868517) · [Dune top traders](https://dune.com/cryp_tourist/solanatoptrades) · [Dune best trader list](https://dune.com/queries/3832067) · [Dune smart wallet tracker](https://dune.com/0xqiqi/super-secret-wallet-tracker) · [KOL copy-trading overview](https://medium.com/@moiofficial/top-solana-wallets-for-copy-trading-310438afc998)
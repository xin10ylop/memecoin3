All verification done. Compiling the reference from actual observed responses.

# Free Market-Data API Reference — Solana Memecoin Bot
Verified live with curl on 2026-08-27 from a sandboxed Linux box (all responses below are real, trimmed). No API keys used anywhere.

---

## 1. GeckoTerminal API v2

Base: `https://api.geckoterminal.com/api/v2` — JSON:API format (`data[].attributes`, `relationships`, optional `included[]`). No auth.

### 1a. New pools

```
GET /networks/solana/new_pools?page={1..10}[&include=base_token,quote_token,dex]
```
- **20 pools/page, pages 1–10 only** (≈200 newest pools). `page=11` → **HTTP 401**: `{"errors":[{"status":"401","title":"Your request exceeds the allowed max number for page (10). Upgrade to Analyst plan..."}]}` (note: 401, not 400/404).
- **No server-side dex filter** — `?dex=pumpswap` is silently ignored (result still mixes `pump-fun`, `manifest`, etc.). Filter client-side on `relationships.dex.data.id`, or use the per-dex listing (§1c).
- `include=base_token` adds `included[]` token objects: `{"id":"solana_8dMPX...","type":"token","attributes":{"address":"...","name":"...","symbol":"FLOCKHOUSE","decimals":6,"image_url":null,"coingecko_coin_id":null}}`.

Real trimmed pool object (all list endpoints return this same shape):
```json
{"id":"solana_598ebE67JZU6tozRXvuaZeR7J6sp4zXmcDFDGhCKZX5S","type":"pool",
 "attributes":{
  "base_token_price_usd":"0.0000107231...","base_token_price_native_currency":"0.0000000970...",
  "quote_token_price_usd":"106.089...","base_token_price_quote_token":"0.0000000970081699",
  "address":"598ebE67...","name":"DRIP / SOL",
  "pool_created_at":"2026-08-27T14:29:02Z",
  "fdv_usd":"8180.651118","market_cap_usd":null,
  "price_change_percentage":{"m5":"-28.668","m15":"45.908","m30":"45.908","h1":"45.908","h6":"45.908","h24":"45.908"},
  "transactions":{"m5":{"buys":120,"sells":187,"buyers":103,"sellers":134},"m15":{...},"m30":{...},"h1":{...},"h6":{...},"h24":{...}},
  "volume_usd":{"m5":"12797.42","m15":"43849.36","m30":"...","h1":"...","h6":"...","h24":"..."},
  "reserve_in_usd":"5450.493"},
 "relationships":{"base_token":{"data":{"id":"solana_5EUXTS...pump","type":"token"}},
                  "quote_token":{"data":{"id":"solana_So1111...112","type":"token"}},
                  "dex":{"data":{"id":"pump-fun","type":"dex"}}}}
```
Gotchas: `market_cap_usd` is usually **null** for new memecoins (use `fdv_usd`); `reserve_in_usd` can be null; `base_token_price_native_currency` can be the literal string `"NaN"`; all numerics are strings; token mint = strip `solana_` prefix from relationship id. Pump.fun bonding-curve pools appear as dex `pump-fun`; after graduation a new pool appears under `pumpswap`.

### 1b. OHLCV

```
GET /networks/solana/pools/{poolAddr}/ohlcv/{day|hour|minute}
    ?aggregate=A&limit=N&before_timestamp=EPOCH_SECONDS&currency=usd|token&token=base|quote|<mint>
```
- **Aggregates (verified via 400 errors, which enumerate allowed values):** minute: `1, 5, 15` · hour: `1, 4, 12` · day: `1`. Bad value → `{"errors":[{"status":"400","title":"Invalid aggregate. Allowed values: 1, 5, 15"}]}`.
- **`limit` max 1000** (default 100). `limit=2000` → 400 `"Invalid limit. must be positive integer less than or equal to 1000"`.
- Rows are `[unix_ts, open, high, low, close, volume]`, **newest first**. `currency=usd` (default): prices+volume in USD; `currency=token`: prices+volume denominated in the quote token (SOL). `token=quote` flips base/quote (returns SOL priced in USD for a X/SOL pool; `meta` flips accordingly).
- **`before_timestamp` pagination works**: returns candles strictly older than the ts, newest-first. Loop: `before_timestamp = last_row[0]` until empty `ohlcv_list`.
- **Minute data reaches back to pool creation** — verified 909 one-minute bars covering the entire life of a 15h-old pumpswap pool (`5q1z6CCEQPDu3pnuhKcWLtxqyj5BkFA7KsJBKbVNvVm9`, UMIA/SOL) in one `limit=1000` call:
```json
{"data":{"type":"ohlcv_request_response","attributes":{"ohlcv_list":[
 [1787841120, 8.1276e-05, 8.1573e-05, 8.0486e-05, 8.1573e-05, 73019.25],
 ...909 rows...,
 [1787786640, 5.6873e-06, 5.8093e-06, 4.7916e-06, 5.7939e-06, 70421.38]]}},
 "meta":{"base":{"name":"Umia","symbol":"UMIA","address":"2SLGput..."},
         "quote":{"name":"Wrapped SOL","symbol":"SOL","address":"So1111...112"}}}
```
- **180-day hard cap on free tier**: `before_timestamp` older than 180d → **HTTP 401** `"You can only access data from the past 180 days with Public API"`.
- **Dead/rugged pools**: no error — you just get candles only for minutes that had ≥1 trade (no zero-filled gaps), and the series simply stops at the last trade. Verified on a pool that died 5 minutes after launch: 5 bars total (14:29→14:34), HTTP 200. An untraded window returns an empty `ohlcv_list`, still 200 with `meta`.
- Gotcha: the newest (in-progress) candle can appear **twice with the same timestamp** in one response (observed with small `limit`) — dedupe by timestamp, keep the last row.

### 1c. Trending / top pools

```
GET /networks/solana/trending_pools?page={1..10}&duration=5m|1h|6h|24h   # 400 lists allowed durations
GET /networks/solana/pools?page=N&sort=h24_volume_usd_desc|h24_tx_count_desc   # "top pools"
GET /networks/solana/dexes/{dex_id}/pools?page=N&sort=...                      # per-dex top pools
```
- Sort options verified via 400: `"Invalid sort option. Allowed values: h24_volume_usd_desc, h24_tx_count_desc"`. Same pool object shape as §1a. 20/page, 10 pages.
- `dexes/pumpswap/pools?sort=h24_volume_usd_desc` verified — this is the **correct way to get pump-swap pools** (returned UMIA/SOL, $226M 24h vol, `reserve_in_usd` 253k, tx breakdown incl. `buyers`/`sellers`).

### 1d. Dexes list

`GET /networks/solana/dexes` — one page, no pagination needed. Actual ids observed (2026-08-27):
`raydium, orca, raydium-clmm, fluxbeam, meteora, dexlab, daos-fun, pumpswap, virtuals-solana, boop-fun, saros-amm, meteora-dbc, byreal, pancakeswap-v3-solana, meteora-damm-v2, raydium-launchlab, pump-fun, saros-dlmm, wavebreak, heaven, token-mill, defituna, moonit, humidifi, zora, bags-fm, moonshot, clanker-solana, printr-v2, manifest, metadao, zerofi, easya-kickstart`
**The id is `pumpswap`, not `pump-swap`.** `pump-fun` = bonding curve, `pumpswap` = post-graduation AMM, `raydium-launchlab`/`meteora-dbc`/`boop-fun`/`moonit`/`bags-fm`/`heaven` are other launchpads.

### 1e. Rate limits (observed)

- Advertised free tier: 30 calls/min. **Observed: a small burst bucket — 4–6 rapid uncached calls then HTTP 429; refills within seconds** (a call right after a 429 can succeed). Sustained ~1 call/6s still saw intermittent 429s (shared egress IP likely shares the budget — assume worst case).
- 429 response: header `retry-after: 0` (useless), body is CoinGecko-style, **not** JSON:API: `{"status":{"error_code":429,"error_message":"You've exceeded the Rate Limit. ..."}}`. So handle both error shapes (`status` for 429, `errors[]` for 400/401).
- Cloudflare caching: identical URLs are often served `cf-cache-status: HIT` and **do not count / still work while throttled**. Cache-busting query params defeat this.
- Bot guidance: single worker, ≥2s between calls, exponential backoff (start 10–20s) on 429, reuse identical URLs where possible.

### 1f. Bonus endpoints worth using (verified)

- `GET /networks/solana/tokens/{mint}` — `price_usd, fdv_usd, total_supply, normalized_total_supply, total_reserve_in_usd, volume_usd.h24`, `launchpad_details:{graduation_percentage, completed, completed_at, migrated_destination_pool_address}`, `relationships.top_pools`.
- `GET /networks/solana/tokens/{mint}/info` — **free rug-check goldmine**: `mint_authority:"no"|"yes"`, `freeze_authority:"no"|"yes"`, `is_honeypot:"yes"|"no"|"unknown"`, `holders:{count, distribution_percentage:{top_10:"84.7035", "11_20", "21_40", rest}, last_updated}`, `gt_score` (+ per-component breakdown), `twitter_handle, telegram_handle, websites, description, gt_verified, developer_address`.
- `GET /simple/networks/solana/token_price/{mint1,mint2,...}` — bulk USD price: `{"data":{"attributes":{"token_prices":{"<mint>":"0.0000840..."}}}}`.
- `GET /search/pools?query=X&network=solana` and `GET /networks/solana/pools/multi/{addr1,addr2}` — both live.

---

## 2. DexScreener public API

Base: `https://api.dexscreener.com`. No auth. Clean JSON (numbers are numbers, not strings).

| Endpoint | Returns | Notes |
|---|---|---|
| `GET /latest/dex/pairs/solana/{pairAddr}[,{addr2}...]` | `{schemaVersion,"pairs":[...],"pair":{...}}` | multi-address works (verified 2 pairs in one call) |
| `GET /latest/dex/search?q=UMIA` | up to 30 pairs, cross-chain | ranked by relevance/volume |
| `GET /latest/dex/tokens/{mint}` | `{pairs:[...]}` all pools of a token (cap 30) | |
| `GET /token-pairs/v1/solana/{mint}` | **bare array** of pair objects | same shape, no wrapper |
| `GET /tokens/v1/solana/{mint1},{mint2}` | bare array, batch by token | |
| `GET /token-profiles/latest/v1` | 30 latest paid profiles, cross-chain | `{url, chainId, tokenAddress, icon, header, description, links}` |
| `GET /token-boosts/latest/v1` | 30 latest boosted tokens, cross-chain | ad signal — boosts = someone paid to promote |

Real pair object (pumpswap UMIA/SOL, trimmed):
```json
{"chainId":"solana","dexId":"pumpswap","url":"https://dexscreener.com/solana/5q1z6cce...",
 "pairAddress":"5q1z6CCEQPDu3pnuhKcWLtxqyj5BkFA7KsJBKbVNvVm9",
 "baseToken":{"address":"2SLGput...","name":"Umia","symbol":"UMIA"},
 "quoteToken":{"address":"So1111...112","name":"Wrapped SOL","symbol":"SOL"},
 "priceNative":"0.0000007661","priceUsd":"0.00008138",
 "txns":{"m5":{"buys":693,"sells":514},"h1":{"buys":9189,"sells":6938},"h6":{...},"h24":{"buys":141625,"sells":106435}},
 "volume":{"h24":228934122.13,"h6":92952508.23,"h1":15200116.07,"m5":1217969.52},
 "priceChange":{"m5":1.09,"h1":15.74,"h6":163,"h24":1596},
 "liquidity":{"usd":256213.77,"base":1579824682,"quote":1201.4765},
 "fdv":8138936,"marketCap":8138936,"pairCreatedAt":1787786646000}
```
Established tokens additionally carry `labels` (e.g. `["wp"]`, `["CLMM"]`) and `info`:
```json
"info":{"imageUrl":"...","websites":[{"url":"https://dogwifcoin.org","label":"Website"}],
        "socials":[{"url":"https://twitter.com/dogwifcoin","type":"twitter"},{"url":"https://t.me/dogwifcoin","type":"telegram"}]}
```
Gotchas / limits:
- `info` is **null** unless the team bought/claimed a profile — absence of socials ≠ scam, presence = someone paid (weak legitimacy signal).
- Time buckets are `m5/h1/h6/h24` only — **no m15/m30** (GeckoTerminal has those). `pairCreatedAt` is **milliseconds** (GT uses ISO-8601). `priceChange` keys are omitted (not zero) when there's no data for a bucket.
- **No OHLCV/history endpoint** at all — snapshot only. Poll and store yourself.
- Rate limits (documented): 300 req/min for pairs/search/tokens; 60 req/min for profiles/boosts. Observed: 30-call burst → all 200, no rate-limit headers exposed. dexId here is also `pumpswap`.

---

## 3. Jupiter `lite-api.jup.ag` (free tier, no key)

### Price v3
```
GET https://lite-api.jup.ag/price/v3?ids={mint1},{mint2}
```
```json
{"2SLGputEdiMT6PECgnwF4paKmWSF41aY57i9ZXCijCGC":{
   "createdAt":"2026-08-26T23:22:42Z","liquidity":128009.07,"usdPrice":8.1178e-05,
   "blockId":442123957,"decimals":6,"priceChange24h":19291.79,"launchpad":"met-dbc"},
 "So11111111111111111111111111111111111111112":{"usdPrice":106.494,"liquidity":798731665.16,...}}
```
Note: v3 returns a **flat map keyed by mint** (no `data` wrapper like the old v2). Bonus per-token fields: `liquidity` (USD), `createdAt`, `launchpad`, `priceChange24h` (%). Unknown mints are simply omitted. Served through CDN with `cache-control: max-age=5` — expect up to ~5s staleness.

### Quote (Ultra/Swap v1)
```
GET https://lite-api.jup.ag/swap/v1/quote?inputMint=...&outputMint=...&amount=RAW_UNITS&slippageBps=300
```
Verified both directions on a live pumpswap memecoin:
- SOL→UMIA, `amount=100000000` (0.1 SOL): `outAmount:"130749442264"`, `otherAmountThreshold:"126826958997"`, `priceImpactPct:"0.00263..."` (**fraction, not percent**: 0.26%), `swapMode:"ExactIn"`, `swapUsdValue:"10.647"`, `contextSlot`, `routePlan:[{"swapInfo":{"ammKey":"5q1z6CCE...","label":"Pump.fun Amm","inAmount":"100000000","outAmount":"130749442264"},"percent":100}]`.
- UMIA→SOL with that same `outAmount` back in: got `99344428` lamports (0.0993 SOL) — i.e. real round-trip cost ≈0.66% at 0.1-SOL size (impact + LP fee, both directions). Use this round-trip as an executable-spread / honeypot probe.
- `amount` is raw integer units of `inputMint` (lamports for SOL, `10^decimals` for tokens). Error on unroutable/garbage tokens is a JSON error body — treat "no route" as untradeable.
- Other useful fields: `platformFee:null`, `routePlan[].percent` (split routing), multi-hop appears as multiple `routePlan` entries.
- Rate limits: no `x-ratelimit-*` headers; 15 back-to-back quotes + 20 price calls → all 200. Jupiter documents the lite tier at ~60 req/min per IP; stay ≤1 req/s to be safe. `POST /swap/v1/swap` (build tx from a quote) lives on the same host for live execution.

---

## 4. Solana public RPC (`api.mainnet-beta.solana.com`)

JSON-RPC 2.0 over POST. Verified:

### getAccountInfo (mint, jsonParsed) — works
```json
{"method":"getAccountInfo","params":["<mint>",{"encoding":"jsonParsed"}]}
→ "value":{"data":{"parsed":{"info":{"decimals":6,"freezeAuthority":null,"isInitialized":true,
   "mintAuthority":null,"supply":"99999999077375858"},"type":"mint"},"program":"spl-token","space":82},
   "owner":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}
```
`mintAuthority:null` + `freezeAuthority:null` = renounced/none (good). `owner` distinguishes SPL Token (`Tokenkeg...`) vs Token-2022 (`TokenzQd...` — check `extensions` for transfer-fee/hook rugs there).

### getTokenSupply — works
```json
→ "value":{"amount":"99999999077375858","decimals":6,"uiAmount":99999999077.37,"uiAmountString":"..."}
```

### getTokenLargestAccounts — **BLOCKED on the public endpoint**
Every call (even the first, with headers proving it's policy not congestion):
```
HTTP 429   x-ratelimit-tier: free   x-ratelimit-method-limit: 0   retry-after: 10
{"jsonrpc":"2.0","error":{"code":429,"message":"Too many requests for a specific RPC call"},"id":1}
```
`method-limit: 0` — the method has a per-method quota of zero on the free public RPC. `solana-rpc.publicnode.com` also refuses it (`-32602 "Indexed requests require a personal token"`). **Workarounds:** (a) free-key RPC (Helius free tier serves it), or (b) GeckoTerminal `/tokens/{mint}/info` `holders.distribution_percentage.top_10` as a keyless substitute for concentration checks, or (c) `getProgramAccounts` is likewise blocked — don't bother.

### Rate limits (from live headers)
`x-ratelimit-rps-limit: 250`, `x-ratelimit-conn-limit: 40`, `x-ratelimit-connrate-limit: 40`, `x-ratelimit-pubsub-limit: 10`; 429s carry `retry-after` seconds. Officially documented public limits: 100 req/10s per IP, 40 req/10s per method. Fine for occasional mint-authority checks; not for polling.

---

## Cross-API cheat sheet for the bot

| Need | Best free source |
|---|---|
| Discover brand-new pools | GT `new_pools` (has m5/m15/m30 buckets + buyers/sellers), filter dex client-side |
| Top/trending pump-swap pools | GT `dexes/pumpswap/pools?sort=h24_volume_usd_desc`, `trending_pools?duration=5m` |
| Minute candles / backtest data | GT OHLCV only (1000×1m per call, `before_timestamp` paging, 180d cap). DexScreener has none |
| Fast snapshot polling (liquidity, m5 txns) | DexScreener (300/min ≫ GT's ~30/min) — use it as the high-frequency poller, GT for candles |
| Socials / paid-profile signal | DexScreener `info` + `token-boosts`; GT `/tokens/{mint}/info` |
| Rug checks (authorities, holders, honeypot) | RPC `getAccountInfo` (authorities) + GT `/tokens/{mint}/info` (holders top_10 %, is_honeypot) — **not** RPC largest-accounts (blocked) |
| Executable price / spread / route | Jupiter quote both directions; `priceImpactPct` is a fraction |
| Timestamps | GT: ISO-8601 UTC · DexScreener: epoch **ms** · GT OHLCV/Jupiter: epoch **s** |
| 429 handling | GT: burst bucket, `retry-after: 0`, backoff ~15s; RPC: honor `retry-after`; DexScreener/Jupiter: none observed at tested volume |
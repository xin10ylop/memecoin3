All data gathered. Composing the deliverable.

# KOL-Wallet Monitoring — Feasibility Scoping (implementation research; no trading claims)

## 1. kolscan.io leaderboard scrape (2026-08-29, via curl)

`curl -sL https://kolscan.io/leaderboard` returns 238,576 B of server-rendered HTML; wallets extracted with regex `/account/[1-9A-HJ-NP-Za-km-z]{32,44}`. **50 unique Solana wallets** on today's (daily) leaderboard. No auth, no JS rendering needed — scrape is trivially automatable (weekly refresh suggested; note leaderboard is realized-PnL-ranked, i.e., survivorship-selected). First 10 in page order:

```
CAPn1yH4oSywsxGU456jfgTrSSUidf9jgeAnHceNUJdw
87rRdssFiTJKY4MGARa4G5vQ31hmR7MxSmhzeaJ5AAxJ
Hw5UKBU5k3YudnGwaykj5E8cYUidNMPuEewRRar5Xoc7
6S8GezkxYUfZy9JPtYnanbcZTMB87Wjt1qx3c6ELajKC
4vw54BmAogeRV3vPKWyFet5yf8DTLcREzdSzx4rw9Ud9
ardinRsN1mNYVeoJWTBsWeYeXvuR9UUDGMsCDKpb6AT
CyaE1VxvBrahnPWkqm5VsdCvyS2QmNht2UFrKJHga54o
6HJetMbdHBuk3mLUainxAPpBpWzDgYbHGTS2TqDAUSX2
HYSq1KBAvqWpEv1pCbV31muKM1za5A1WSHGdiVLUoNhb
GJA1HEbxGnqBhBifH9uQauzXSB53to5rhDrzmKxhSU65
```

Full list: `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/wallets.txt`.

## 2. Public RPC budget math (api.mainnet-beta.solana.com, measured)

**Probe A** — 5 × `getSignaturesForAddress` at 1 req/s: all HTTP 200, latency 0.14–0.54 s. **Probe B** — 45 back-to-back calls (same method): first **429 at call #20** (~3.4 s in), final tally 30×200 / 15×429 over 8.0 s. The 429 response carries the actual limits:

```
retry-after: 10
x-ratelimit-tier: free
x-ratelimit-method-limit: 10        ← binding constraint (per-method bucket)
x-ratelimit-rps-limit: 250          (global, not binding)
x-ratelimit-conn-limit: 40
```

So the binding limit is **~10 calls per method per 10 s window** (token bucket with ~2× burst allowance; observed sustained throughput when hammering ≈ 3.75 ok/s, but honoring `retry-after: 10` collapses that). **Safe design rate: ≤ 1 `getSignaturesForAddress`/s, evenly paced.**

**Budget at 60 s cadence:** N wallets → N calls/min of one method. Theoretical max = 60 wallets/min at exactly 1/s with zero headroom; **practical max ≈ 40–50 wallets** with even pacing (1 call per 1.2–1.5 s) leaving retry headroom. 50 KOL wallets = 0.83 req/s — *fits, but exactly at the edge*; a naive burst-y loop (all 50 back-to-back) 429s after ~20 calls, exactly as measured. Bot's existing public-RPC usage is on *different* methods (safety gate: `getAccountInfo` + `getTokenLargestAccounts` per entry attempt; live exec: `sendTransaction`/`getSignatureStatuses`/balances — typically <10 calls/min, separate per-method buckets), so contention is via the loose global rps/conn limits only. Additional cost per detected buy: 1 `getTransaction` to extract the mint (another per-method bucket, negligible volume). **Conclusion: 50 wallets @ 60 s on public RPC is feasible but brittle — zero headroom, and any retry storm degrades cadence to ~120 s.**

## 3. Helius free tier (from helius.dev docs, fetched 2026-08-29 via `/docs/billing/llms.txt`; www.helius.dev/pricing itself timed out through the proxy)

Free plan: **$0/mo, 1M credits/month (no card), 10 req/s RPC, 2 req/s DAS/Enhanced APIs, standard WebSockets yes, Enhanced WebSockets no, webhooks: max 5, 100k addresses per webhook**. Credit costs: standard RPC calls (incl. `getSignaturesForAddress`, `getTransaction`) = 1 credit; Enhanced Transactions API = 100 credits/call; **webhook events = 1 credit/event**, webhook create/edit/delete = 100 credits; `getTransactionsForAddress`/`getTransfersByAddress` = Developer+ only. Paid tiers: $49 (10M), $499 (100M), $999/mo (200M); overage $5/M.

**Wallet-buy detection at 50 wallets, two designs:**
- **Polling** (same code path as public RPC): 50 wallets × 1,440 min/day × 1 credit = **72,000 credits/day = ~2.16M/month → exceeds free tier ~2.2×** at 60 s cadence (1M exhausted in ~14 days). Fits free tier at 3-min cadence (720k/mo) — coincidentally the panel's snapshot cadence.
- **Webhooks (recommended)**: one `enhanced` webhook, all 50 addresses (limit is 100k/webhook), `transactionTypes: ["SWAP"]`, 1 credit/event. At a generous 50–200 tx/day/wallet: 2.5k–10k events/day = **75k–300k credits/month → comfortably inside the free 1M**, with parsed swaps (token mint, direction) delivered push-style in seconds instead of ≤60 s poll latency. Requires one public HTTPS endpoint on the collector VPS. Historical backfill for offline validation (`getSignaturesForAddress` pages + `getTransaction` per sig over the panel window) also fits: ~50 wallets × ~1–2k tx ≈ 100–200k credits one-off.

## 4. Minimal integration sketch (`src/memebot/live/trader.py`)

The scan loop runs every 60 s (`config/default.yaml: scan_interval_sec: 60`; loop at trader.py:515). Three plug points, all mirroring existing patterns:

1. **Event ingestion** — new `src/memebot/data/kol.py`: `KolWatcher` (webhook receiver or paced poller thread) writing `kol_events(wallet, mint, side, ts, sig)` into a small SQLite table (panel.db or its own file). Wallet list from the kolscan scrape, refreshed weekly.
2. **Candidate injection** — a `_kol_candidates()` method modeled exactly on `_panel_candidates()` (trader.py:183–245): mints with ≥1 KOL buy in the last 10 min → resolve pool via panel.db `pools.base_token_address` (fallback `self.gt.pool()`), return `PoolStats`, merge ahead of GT candidates the way panel candidates are merged at trader.py:300–313 (dedup via `seen`, respect `WATCHLIST_MAX = 12`). Safety gate and strategy signal logic then apply unchanged via `_maybe_enter`.
3. **Feature/event feed** — mirror the trending-timestamp pattern at trader.py:257 (`self.strategy.events.setdefault(s.address, now_ts)`): record first-KOL-buy ts per pool so a strategy can consume `kol_buy_age` or a `kol_buys_10m` count exactly like `trending_follow` consumes trending events; optionally join a `kol_buys_10m` column into `_bars_with_snaps` for feature-based strategies.

**Effort:** poller MVP ~0.5–1 day (~200 LOC: scrape refresh, paced poll, mint extraction, pool resolution, events injection); webhook variant +0.5–1 day (HTTPS endpoint + dedup/state); **offline validation is the real work: 1–2 days** — Helius backfill of the 50 wallets over the panel window, then an event study of forward returns (next-bar onward, terminal extension) conditional on KOL-buy recency, cluster-bootstrapped by token, windows A and B reported separately with token counts, insufficient if <15 tokens/window.

## VERDICT

**Feasible — build the ingestion, do not wire it to entries until validated.** (a) Wallet sourcing is trivial (50 wallets today, plain curl). (b) Public RPC alone is *marginally* sufficient for 50 wallets @ 60 s (measured per-method budget ~10/10 s; 0.83 req/s needed) but has zero headroom — acceptable for a throwaway prototype only. (c) **Helius free tier via webhooks is the right architecture**: ~75k–300k of 1M monthly credits at 50 wallets, second-level latency, parsed swaps, $0. (d) Integration is a clean ~200-LOC bolt-on with two existing precedents (`_panel_candidates` merge, trending `events` feed). Total effort to a validated go/no-go: **~3–4 days**. Caveat, per prior research: copy-trading is adverse-selection-prone (leaderboard survivorship, visibility lag means entries are post-pump), so "KOL bought in last 10 min" is strictly a **candidate feature input** whose conditional forward-return distribution must clear the same cluster-bootstrap A/B bar as every other feature before it influences a single entry. No P&L edge is claimed or implied.
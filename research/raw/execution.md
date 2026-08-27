All research and live verification complete. Compiling the reference.

# Solana Trading Bot Execution Stack — Python Engineering Reference

**Verified live: 2026-08-27.** All endpoint claims below were tested with real HTTP calls or fetched from current docs, not recalled from memory. Jupiter docs now live at `https://developers.jup.ag` (old `dev.jup.ag`/`station.jup.ag` paths 301-redirect).

---

## 1. Jupiter Swap API — current state (important: it changed in 2026)

### 1.1 The lay of the land

Jupiter reorganized into **Swap V2** (`https://api.jup.ag/swap/v2`), which unifies the old Ultra API and the Metis router:

| Path | What it is | Fee | Landing |
|---|---|---|---|
| `GET /swap/v2/order` | Meta-aggregator (formerly **Ultra**): quote + fully assembled tx. Routes across Metis, JupiterZ RFQ, DFlow, OKX | Jupiter platform fee (see below) | Must submit via `POST /swap/v2/execute` (managed landing, MEV protection) |
| `GET /swap/v2/build` | Router path (Metis only): quote + **raw instructions** you assemble yourself | **No Jupiter fee** | Self-managed (your RPC) or `POST https://tx.jup.ag /submit` |
| `/swap/v1/quote` + `/swap/v1/swap` | Legacy Metis flow ("Metis Swap API is no longer actively maintained and has been superseded by Swap V2") | No Jupiter fee | Self-managed |

**Verified live today:**
- `GET https://lite-api.jup.ag/swap/v1/quote?...` → **HTTP 200**, full quote (works, no key).
- `GET https://api.jup.ag/swap/v1/quote?...` (keyless) → **HTTP 200**.
- `POST https://lite-api.jup.ag/swap/v1/swap` → **HTTP 200** with `swapTransaction` (base64 MessageV0), `lastValidBlockHeight`, `prioritizationFeeLamports: 56909`, `computeUnitLimit: 35521`, `dynamicSlippageReport`, `simulationError`.
- `GET https://api.jup.ag/swap/v2/order` (keyless, no `taker`) → **HTTP 200** quote-only (`transaction: null`, `requestId`, `router: "metis"`, `mode: "ultra"`, `feeBps: 2` on SOL→USDC).
- `GET https://lite-api.jup.ag/swap/v2/order` → **HTTP 404** ("Route not found"). **v2 is NOT on lite-api; v1 is NOT dead.** For a free-tier bot today, `lite-api.jup.ag/swap/v1/*` is still the working path; plan a migration to `/swap/v2/build` (near-identical semantics, single call) since v1 is formally deprecated.

**Fee warning for memecoins:** the `/order`+`/execute` path auto-deducts Jupiter platform fees: 2 bps SOL↔stable, 10 bps most pairs, **50 bps for tokens <24h old** — material for memecoin clips. `/swap/v1` and `/swap/v2/build` charge **zero** Jupiter fee. ([order-and-execute docs](https://developers.jup.ag/docs/swap/order-and-execute.md))

### 1.2 Auth & rate limits ([rate-limits](https://developers.jup.ag/docs/portal/rate-limits.md), [portal](https://developers.jup.ag/portal))

- Header: `x-api-key: jup_...` (keys from the portal, active ~15 s after creation).
- 60-second **sliding window** per org; on 429 wait until `x-ratelimit-reset` (no lockout beyond the window).
- Main bucket (quote/swap/price/token): Keyless **0.5 RPS (30 RPM)** · Free key **1 RPS** · Developer $25/mo **10 RPS** · Launch $100/mo **50 RPS** · Pro $500/mo **150 RPS**. `/swap/v2/execute` has its own bucket: 20/50/100 RPS.
- Practical: a single-wallet bot doing a few clips/hour lives fine on lite-api/keyless; anything polling quotes in a loop needs the $25 Developer key.

### 1.3 `/swap/v1/quote` (verified schema)

`GET https://lite-api.jup.ag/swap/v1/quote` — query params:

| Param | Type/default | Notes |
|---|---|---|
| `inputMint`, `outputMint` | required | mint addresses (SOL = `So11111111111111111111111111111111111111112`) |
| `amount` | u64, required | **raw units before decimals** (lamports for SOL) |
| `slippageBps` | u16, default 50 | min-out threshold in bps |
| `swapMode` | `ExactIn` (default) / `ExactOut` | |
| `restrictIntermediateTokens` | bool, default **true** | keep true — routes via stable intermediates, fewer weird-hop failures |
| `onlyDirectRoutes` | bool, false | single-hop only; use for brand-new tokens with one pool |
| `maxAccounts` | default 64 | lower (~40) if you append your own instructions |
| `dexes` / `excludeDexes` | csv | |
| `asLegacyTransaction` | false | leave false; you want v0 |

Response (live sample): `{"inputMint", "inAmount", "outputMint", "outAmount", "otherAmountThreshold", "swapMode", "slippageBps", "priceImpactPct", "routePlan":[{"swapInfo":{"ammKey","label","inAmount","outAmount"},"percent"}], "contextSlot", "timeTaken", "swapUsdValue"}`. `otherAmountThreshold` = enforced min-out (`outAmount` × (1 − slippage)); `priceImpactPct` is your pre-trade sanity gate.

### 1.4 `/swap/v1/swap` (verified schema)

`POST https://lite-api.jup.ag/swap/v1/swap`, JSON body:

```jsonc
{
  "quoteResponse": { /* entire /quote response verbatim */ },
  "userPublicKey": "<base58 pubkey>",
  "wrapAndUnwrapSol": true,              // default true: auto wSOL wrap/unwrap
  "dynamicComputeUnitLimit": true,       // simulates -> tight CU limit -> cheaper priority fee
  "dynamicSlippage": true,               // RTSE: server picks slippage, capped by quote's slippageBps
  "prioritizationFeeLamports": {         // EXACTLY ONE of:
    "priorityLevelWithMaxLamports": {
      "priorityLevel": "veryHigh",       // "medium" | "high" | "veryHigh" (75th/85th/95th pctile of local fee market)
      "maxLamports": 2000000,            // hard cap on total priority fee, lamports
      "global": false                    // false = local (writable-accounts) fee market — use false
    }
    // OR "jitoTipLamports": 1000000     // exact Jito tip instead of CU price
  }
  // alt: "computeUnitPriceMicroLamports": <u64> for exact CU price
  // "blockhashSlotsToExpiry": 30  — shorten tx validity for fast-fail retry loops
}
```

Response (live): `swapTransaction` (base64 **unsigned v0 VersionedTransaction**, 1 signature required), `lastValidBlockHeight`, `prioritizationFeeLamports` (actual applied, e.g. 56,909), `computeUnitLimit`, `simulationError` (null or `{"errorCode":"TRANSACTION_ERROR","error":"..."}` — **check this before sending**; our test with an unfunded wallet returned "Attempt to debit an account but found no record of a prior credit."), `dynamicSlippageReport` (`slippageBps` actually used, `simulatedIncurredSlippageBps`, `heuristicMaxSlippageBps`, `categoryName`).

**slippageBps vs dynamicSlippage:** fixed `slippageBps` is deterministic; `dynamicSlippage: true` lets Jupiter's RTSE pick (our SOL→USDC test chose 15 bps under a 100 bps request cap). For memecoins, RTSE with a generous cap (e.g. request `slippageBps=800`, let RTSE tighten) beats a hand-tuned constant. In Swap V2 `/build` this became `slippageBps=rtse`; `/order` applies RTSE automatically.

### 1.5 Swap V2 quick map (for migration)

- `GET /swap/v2/order?inputMint&outputMint&amount&taker=<pubkey>&slippageBps=...` → `{transaction, requestId, outAmount, router, feeBps, ...}`; `transaction: null` if no `taker` (quote-only), `""` if quote OK but swap can't proceed. Sign the base64 v0 tx, then `POST /swap/v2/execute {"signedTransaction": b64, "requestId": ...}` → `{status: "Success"|"Failed", signature, totalInputAmount, totalOutputAmount, ...}` — execute handles landing, retries, and reports **actual filled amounts**.
- `GET /swap/v2/build` → returns **instructions** (`computeBudgetInstructions`, `setupInstructions`, `swapInstruction`, `cleanupInstruction`, `addressesByLookupTableAddress`, `blockhashWithMetadata`) not a tx; params include `slippageBps` (int or `"rtse"`), `computeUnitPricePercentile` (`medium|high|veryHigh` or 0–10000), `tipAmount`, `blockhashSlotsToExpiry` (default 150), `forJitoBundle`. `/build` output **cannot** go to `/execute`; submit via own RPC or `tx.jup.ag` `/submit` (which requires a **minimum 0.001 SOL tip** — expensive; skip for small clips).

---

## 2. Python: solders + solana-py

**Current versions (PyPI, verified):** `solders 0.29.0` (py ≥3.10), `solana 0.40.3` (py ≥**3.11**, pins `solders>=0.28,<0.30`). Pin both: `solana==0.40.3 solders==0.29.0`. Note: in solana-py 0.40 the **sync `Client` is deprecated — `AsyncClient` is the supported client**, and `TxOpts` moved to `solana.rpc.models` (older code imports from `solana.rpc.types`).

**solders 0.29 API changes (verified by introspection):** `Keypair.to_base58_string()` is **gone** (many old tutorials use it). Surviving surface: `from_base58_string`, `from_bytes`, `from_seed`, `from_json`/`to_json` (solana-keygen JSON-array format), `to_bytes`, `secret`, `sign_message`, `pubkey`.

### 2.1 End-to-end (this exact flow was executed successfully against live endpoints)

```python
import base64, json, os, httpx
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned
from solders.signature import Signature
from solana.rpc.async_api import AsyncClient
from solana.rpc.models import TxOpts          # 0.40+; solana.rpc.types in <=0.36
from solana.rpc.commitment import Confirmed

JUP = "https://lite-api.jup.ag"               # or https://api.jup.ag + {"x-api-key": ...}
SOL = "So11111111111111111111111111111111111111112"

def load_keypair() -> Keypair:
    raw = os.environ["BOT_KEYPAIR"]           # never log this
    if raw.strip().startswith("["):           # solana-keygen JSON array
        return Keypair.from_bytes(bytes(json.loads(raw)))
    return Keypair.from_base58_string(raw)    # phantom-style base58 (64-byte secret)

async def swap(client: AsyncClient, kp: Keypair, out_mint: str, lamports_in: int):
    async with httpx.AsyncClient(timeout=15) as http:
        q = (await http.get(f"{JUP}/swap/v1/quote", params={
            "inputMint": SOL, "outputMint": out_mint, "amount": lamports_in,
            "slippageBps": 800, "restrictIntermediateTokens": True})).json()
        if "error" in q: raise RuntimeError(f"quote failed: {q}")

        s = (await http.post(f"{JUP}/swap/v1/swap", json={
            "quoteResponse": q, "userPublicKey": str(kp.pubkey()),
            "wrapAndUnwrapSol": True, "dynamicComputeUnitLimit": True,
            "dynamicSlippage": True,
            "prioritizationFeeLamports": {"priorityLevelWithMaxLamports": {
                "priorityLevel": "veryHigh", "maxLamports": 2_000_000, "global": False}},
        })).json()
    if s.get("simulationError"): raise RuntimeError(f"sim failed: {s['simulationError']}")

    # sign: constructor with (message, keypairs) SIGNS — there is no .sign() method
    unsigned = VersionedTransaction.from_bytes(base64.b64decode(s["swapTransaction"]))
    signed = VersionedTransaction(unsigned.message, [kp])
    # equivalent manual path (verified byte-identical):
    #   sig = kp.sign_message(to_bytes_versioned(unsigned.message))
    #   signed = VersionedTransaction.populate(unsigned.message, [sig])

    resp = await client.send_raw_transaction(bytes(signed), opts=TxOpts(
        skip_preflight=True,                  # see §2.2
        preflight_commitment=Confirmed,       # default is Finalized -> stale-blockhash preflight errors
        max_retries=0))                       # do your own resubmit loop (§6)
    sig: Signature = resp.value
    await client.confirm_transaction(sig, commitment=Confirmed,
        last_valid_block_height=s["lastValidBlockHeight"], sleep_seconds=0.4)
    return sig, q, s
```

### 2.2 skipPreflight considerations

- Jupiter already simulated for you (`dynamicComputeUnitLimit` / `simulationError` field) — a second preflight adds ~1 RTT of latency and, worse, solana-py's default `preflight_commitment=Finalized` makes the node simulate against a ~30-slot-old bank, producing spurious `BlockhashNotFound` for a just-built tx.
- For memecoin entries where latency = price: `skip_preflight=True` and rely on Jupiter's `simulationError` + your own confirm loop. For exits/unwinds where a revert costs only the 5000-lamport base fee + priority fee, preflight at `processed`/`confirmed` is a cheap safety net.
- With `skip_preflight=False` a failed simulation raises `solana.rpc.core.RPCException` client-side; with it skipped, failures surface only in `get_signature_statuses`/`get_transaction` `meta.err`.

### 2.3 Useful AsyncClient surface (verified signatures, [docs](https://michaelhly.com/solana-py/rpc/async_api/))

`send_raw_transaction(txn: bytes, opts)`, `send_transaction(txn: VersionedTransaction, opts)`, `confirm_transaction(tx_sig, commitment, sleep_seconds=0.5, last_valid_block_height=None)` (aborts once chain height passes `last_valid_block_height`), `get_latest_blockhash(commitment)`, `get_signature_statuses(sigs, search_transaction_history=False)`, `get_transaction(sig, encoding="json", max_supported_transaction_version=0)` (**must pass 0** or v0 txs error), `get_recent_prioritization_fees(addresses)`, `get_token_account_balance(pubkey)`. `TxOpts` fields: `skip_confirmation=True`, `skip_preflight=False`, `preflight_commitment=Finalized`, `max_retries=None`, `last_valid_block_height=None`.

---

## 3. Priority fees & Jito

### 3.1 Estimating

- **`getRecentPrioritizationFees`** ([solana.com](https://solana.com/docs/rpc/http/getrecentprioritizationfees)): per-slot samples of `prioritizationFee` in **micro-lamports per CU**; pass up to 128 addresses to get the fee market for txs write-locking those accounts (pass the pool/token accounts you'll touch). Cache covers ~150 blocks. Caveat: many slots report 0 and it reflects *minimums observed*, not what lands — take a high percentile (p75–p90) of nonzero samples, never the mean.
- **Helius `getPriorityFeeEstimate`** ([docs](https://www.helius.dev/docs/priority-fee-api)): `params:[{transaction: <b58 serialized>, options:{priorityLevel:"High"| "VeryHigh"|..., recommended:true}}]` → `{priorityFeeEstimate}` in micro-lamports/CU. Better signal than the raw RPC method; works on the free tier.
- **Simplest for a Jupiter bot:** don't estimate at all — `priorityLevelWithMaxLamports` makes Jupiter do percentile estimation on the local fee market (medium=75th, high=85th, veryHigh=95th) and the response tells you what it charged. Total priority cost = `computeUnitLimit × price`; with `dynamicComputeUnitLimit: true` the limit is tight (our test: 35,521 CU), so the same level costs far less than the default 1.4M CU limit.

### 3.2 Competitive levels for memecoin trading

Live reference point (2026-08-27): Jupiter `veryHigh` chose **56,909 lamports ≈ 0.000057 SOL ≈ $0.01** total on a liquid pair. Hot memecoin pools have their own (local) fee market: expect `veryHigh` to land 0.0005–0.005 SOL during a frenzy. Sane config for $100–1k clips: `priorityLevel: "veryHigh"`, `maxLamports: 2_000_000–5_000_000` (0.002–0.005 SOL, i.e. ≤ ~0.5% of a $100 clip worst-case, usually 10–100× less). Raise only if you see systematic non-landing while `confirm_transaction` times out.

### 3.3 Jito — overkill for $100–1k clips?

Facts ([docs.jito.wtf](https://docs.jito.wtf/lowlatencytxnsend/)): block engine `https://mainnet.block-engine.jito.wtf/api/v1/transactions` (and `/bundles`); regional endpoints (ams/dub/fra/lon/ny/slc/sg/tyo); min tip **1,000 lamports** to one of 8 tip accounts; unauthenticated limit **1 RPS/IP/region**; bundles = ≤5 txs, atomic+sequential; guidance: for `sendTransaction` split ~70% priority fee / 30% tip, for bundles only the tip matters. Live tip floor (`https://bundles.jito.wtf/api/v1/bundles/tip_floor`, fetched today): p50 = **3,763 lamports**, p75 = 20,000, p95 = 653,000, p99 = 4,440,000.

**Verdict:** for $100–1k clips, full Jito bundles are overkill — the machinery (bundle assembly, 1 RPS limit, status polling) buys atomicity/ordering you don't need for a single swap. Two cheap upgrades are *not* overkill: (a) Jupiter's `"jitoTipLamports": 100_000`–`1_000_000` (p75–p95) instead of a CU price when a token is genuinely contested — Jito's `sendTransaction` also gives revert protection (failed txs don't land, so you don't pay fees on slippage-reverts); (b) Swap V2 `/execute`, which does managed landing with MEV protection for you. Note Helius `sendBundle`/staked "sender" paths are paywalled (Business tier).

---

## 4. Key management & kill switch

- **Keyfile vs env var:** both end up plaintext-at-rest somewhere; the real rules are (1) dedicated hot wallet used **only** by the bot, (2) balance ≤ what you'd shrug off — for $100–1k clips keep ~1–5 SOL + working stables, sweep profits to a cold address automatically, (3) never in the repo. Ranked: OS keyring/KMS/HSM > root-owned `chmod 600` keyfile outside the repo (or systemd `LoadCredential=`, exposed only to the service) > env var from a `600` env-file (`EnvironmentFile=`). Plain env vars leak via `/proc/<pid>/environ`, crash dumps, and child processes — acceptable on a single-user box, use the systemd credential if you can. Accept both `solana-keygen` JSON-array and base58 formats (loader in §2.1).
- **Never log keys:** log `str(kp.pubkey())` only; never `repr` the Keypair, `kp.secret()`, or the raw env/config dict; redact env in exception reporters (Sentry `send_default_pii=False`, scrub `BOT_KEYPAIR`); don't echo the swap request body at DEBUG with the signed tx (a signed tx is broadcastable by anyone).
- **Kill switch design:** (1) a `HALT` sentinel file checked before every order (touchable by hand or by monitoring) — file, not env, so it can be flipped without restarting; (2) auto-halt triggers: daily realized loss > X%, N consecutive failed/reverted txs, wallet balance below floor, RPC/quote staleness > threshold; (3) halt = stop **new entries** but still allow exits (a bot that can't sell is worse than one that can't buy); (4) hard stop = systemd `systemctl stop` + the sentinel, and revoke/rotate the key if compromise is suspected. Keep position sizing capped in code (`min(clip, max_position - held)`) so no config typo can 10× exposure.

---

## 5. RPC options

- **Public `api.mainnet-beta.solana.com`** ([limits](https://solana.com/docs/references/clusters)): 100 req/10 s/IP, 40 req/10 s for a single method, 40 concurrent connections, 100 MB/30 s, and an explicit "not intended for production applications." It also drops/deprioritizes `sendTransaction` under load and forbids sustained polling — fine for a paper-trading prototype, not for live fills.
- **Helius free** ([pricing](https://www.helius.dev/pricing)): $0, 1M credits/mo, 10 RPS, **1 `sendTransaction`/s**, websockets included; excluded: staked connections, `sendBundle`, LaserStream gRPC. Developer $49/mo: 10M credits, 50 RPS, 5 sendTx/s. Best free default for a bot (priority-fee API included).
- **QuickNode free**: 10M credits/mo, 15 RPS; standard Solana calls 30 credits each (Solana carries a 1.5× multiplier) → ~330k calls/mo, ~8 quote-cycles/min sustained.
- **Triton One**: no free tier; usage-based with **$125 minimum deposit** — enterprise-grade, skip until you outgrow the others.
- **What breaks without paid RPC:** land rate first — free tiers lack **staked connections**, so during congestion your `sendTransaction` sits in public queues and expires (this presents as "bot works in calm markets, every tx expires during the exact memecoin frenzy you built it for"); 429s on the confirm-poll loop (each confirm poll is a `getSignatureStatuses` call — budget it); websocket subscription drops; `getProgramAccounts`/heavy scans usually blocked or truncated. A $25–50/mo tier (Jupiter Developer key + Helius Developer) is the realistic floor for live memecoin execution; keep a second provider configured as failover.

---

## 6. Failure modes

- **Blockhash expiry:** a tx is valid until `lastValidBlockHeight` (~150 blocks ≈ 60–90 s; Jupiter default `blockhashSlotsToExpiry` 150, tunable to fast-fail). Track it from the `/swap` response; `confirm_transaction(..., last_valid_block_height=h)` stops polling once `get_block_height()` passes it. Expired = **definitively not landed** (safe to rebuild & resend a fresh quote/tx); never blind-resend the *same* bytes after expiry, and never re-quote-and-resend before expiry is proven, or you can double-fill.
- **Dropped txs:** with `max_retries=0` you own resubmission: every 2–4 s resend the **identical signed bytes** (idempotent — same signature, dedup'd by the network) while polling `get_signature_statuses`, until confirmed or height > `lastValidBlockHeight`. Status `None` = not seen; `err != None` = landed-but-reverted (base + priority fee burned, no fill).
- **On-chain revert ≠ partial fill:** the classic memecoin failure is `custom program error: 0x1771` (Jupiter error 6001, `SlippageToleranceExceeded`) — the whole tx reverts, you hold your input minus fees.
- **Do Jupiter swaps partial-fill? No.** A routed swap executes atomically inside one transaction: either the full input swaps and the program enforces `out >= otherAmountThreshold`, or everything reverts. (A *split* route across AMMs still settles all-or-nothing in the one tx.) Partial fills exist only in Jupiter's Trigger/limit-order product and, differently, in RFQ — not in the swap path. What *does* vary is the actual out amount within the slippage band, so:
- **Detect actual filled amount post-hoc** — never book the quote's `outAmount`; diff token balances from confirmed tx meta:

```python
async def actual_fill(client, sig, owner: str, mint: str) -> tuple[int, object]:
    tx = (await client.get_transaction(sig, encoding="jsonParsed",
          max_supported_transaction_version=0)).value
    meta = tx.transaction.meta
    if meta.err is not None:
        return 0, meta.err                       # reverted: no fill, fees burned
    def amt(bals):                               # pre/post_token_balances
        return next((int(b.ui_token_amount.amount) for b in bals
                     if str(b.mint) == mint and str(b.owner) == owner), 0)
    delta = amt(meta.post_token_balances) - amt(meta.pre_token_balances)
    # SOL side: meta.pre_balances/post_balances index 0 (fee payer), minus meta.fee
    return delta, None
```

  (`preTokenBalances`/`postTokenBalances` in raw JSON-RPC.) On Swap V2 `/execute` this is prepackaged: the response's `totalInputAmount`/`totalOutputAmount` are the wallet-level deltas.
- **Pre-send failure:** check `/swap`'s `simulationError` (verified live: unfunded wallet → `TRANSACTION_ERROR: "Attempt to debit an account but found no record of a prior credit."`) — catches missing ATAs, insufficient SOL for rent/wrap, closed pools *before* you pay any fee.
- **Quote staleness:** memecoin pools move in ms; enforce quote→send < ~1–2 s in the bot; a stale quote is what turns into 6001 reverts. Re-quote, don't retry, after any revert.

**Sources:** [Jupiter docs index (llms.txt)](https://developers.jup.ag/docs/llms.txt) · [order-and-execute](https://developers.jup.ag/docs/swap/order-and-execute.md) · [build](https://developers.jup.ag/docs/swap/build/index.md) · [rate limits](https://developers.jup.ag/docs/portal/rate-limits.md) · [v1 quote ref](https://developers.jup.ag/docs/api-reference/swap/quote) · [v1 swap ref](https://developers.jup.ag/docs/api-reference/swap/swap) · [solders API](https://kevinheavey.github.io/solders/api_reference/transaction.html) · [solana-py AsyncClient](https://michaelhly.com/solana-py/rpc/async_api/) · [solana-py TxOpts source](https://raw.githubusercontent.com/michaelhly/solana-py/master/src/solana/rpc/models.py) · [getRecentPrioritizationFees](https://solana.com/docs/rpc/http/getrecentprioritizationfees) · [Helius priority-fee API](https://www.helius.dev/docs/priority-fee-api) · [Helius pricing](https://www.helius.dev/pricing) · [Jito low-latency send](https://docs.jito.wtf/lowlatencytxnsend/) · [Jito tip floor](https://bundles.jito.wtf/api/v1/bundles/tip_floor) · [Solana clusters/limits](https://solana.com/docs/references/clusters) · [QuickNode flat-rate RPS](https://www.quicknode.com/docs/platform/billing/flat-rate-rps) · [Triton pricing](https://triton.one/pricing) · live curl/Python verification in this session (2026-08-27).
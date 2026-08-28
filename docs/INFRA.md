# Execution & infrastructure decisions

This bot is deliberately **self-contained**: it does not use any
third-party trading platform, Telegram bot, or "sniper" service. Every
layer was chosen to protect the per-trade edge, which is the scarce
resource.

## Execution: Jupiter Swap API, direct (no middleman)

- Route: `lite-api.jup.ag /swap/v1/quote` → `/swap/v1/swap` → sign locally
  with the bot's own keypair (solders) → send via RPC. This path carries
  **zero Jupiter platform fee**; total cost per side ≈ 0.25–0.30% DEX fee
  + priority fee + our measured slippage.
- What we deliberately do NOT use, and why:
  - **Telegram trading bots (Trojan, BonkBot, Maestro, …)**: charge ~1%
    per trade. Our validated edge economics assume ~0.8%/side all-in;
    handing a bot 1%/side would consume roughly half the knife_catch
    median trade. They exist for human convenience, which an automated
    system doesn't need.
  - **Web platforms (Photon, Axiom, BullX, FOMO, …)**: same story —
    human UIs with platform fees on top of the same AMMs we reach
    directly.
  - **Block-zero sniper services**: a different game we consciously avoid.
    Research (see research/raw/microstructure.md) shows launch-block
    sniping is dominated by ~1,000 persistent wallet rings and colluding
    infrastructure; >95% of rugs execute within 10 seconds of pool
    creation. Our strategies enter minutes after launch at the earliest —
    speed-competitive with humans, not with co-located bundlers, on
    purpose.
- Slippage control: fixed `slippageBps` (dynamicSlippage off so the
  configured tolerance is authoritative), simulation checked before
  signing, short blockhash expiry so timed-out transactions die fast,
  fills confirmed by balance diff at `confirmed` commitment.

## RPC

- Paper mode: public `api.mainnet-beta.solana.com` (sufficient).
- Live mode: set `MEMEBOT_RPC_URL` to a **Helius free-tier** endpoint
  (or QuickNode/Triton). The public RPC's rate limits are the live path's
  weakest link for balance reads and confirmations. Free tier is enough
  for this bot's few transactions per hour.

## Market data

- GeckoTerminal (free) for pool discovery/OHLCV/liquidity; DexScreener
  (free) for paid-promotion attention events; Jupiter price API for held
  positions. Known limitation: ~1–3 min indexing latency. knife_catch and
  the regime machinery operate on minute-scale events, so this is
  acceptable — and the paper forward test measures exactly this
  latency's cost (live fills vs backtest assumptions).
- Upgrade path when a strategy needs sub-minute eyes (e.g. the
  graduation-ramp family that this feed provably cannot see): a
  pump.fun-native websocket (PumpPortal) or Helius webhooks. That is the
  next infra investment IF a strategy justifies it — infra follows
  validated edge here, never the reverse.

## Hosting

- Now: this cloud session (collector + two paper bots + research loop).
- Permanent: any $5 VPS or a Mac mini via `deploy/docker-compose.yml`
  (collector + trader with restart policies) or `deploy/memebot.service`
  (systemd). State is SQLite files under `data/` — copy them to migrate.

## Wallet & keys (live mode)

- Dedicated fresh hot wallet, funded only with what may be lost entirely.
- Key via `MEMEBOT_PRIVATE_KEY` env (never on disk/in git); live trading
  additionally gated behind `MEMEBOT_LIVE=YES` + config `mode: live`;
  a SOL fee reserve is enforced before every buy so exits stay payable;
  `touch data/KILL` halts entries, writing `CLOSE` in it liquidates.

## Cost ledger the edge must clear (per side, $25–200 clips)

| item | cost |
|---|---|
| DEX fee (pumpswap/raydium) | 0.25–0.30% |
| priority fee | ~$0.05–0.10 flat |
| slippage vs pool depth | clip/(reserve/2) — 0.2% at $25 in a $30k pool |
| adverse/MEV buffer | ~0.5% modeled |

knife_catch's validated +66%/trade OOS expectancy survives 3x this
ledger; that headroom — not raw speed — is the infrastructure thesis.

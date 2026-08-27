# memebot — Solana memecoin quant research + 24/7 trading system

A complete pipeline for researching, validating, and running automated
memecoin strategies on Solana: survivorship-free data collection, an
event-driven backtester with AMM-aware cost modeling, hard safety gates
against rugs/honeypots, and a restart-safe 24/7 trader that runs **paper
by default** and mirrors the exact rules that were backtested.

> **Read this first.** Memecoins are a negative-sum lottery for the average
> participant: ~98%+ of launches die, ~84% of pump.fun graduates are
> classified high-risk, and most retail wallets lose money (sources in
> `research/raw/`). Nothing in this repository is a promise of profit.
> The system's design goal is to (1) avoid the left tail with mechanical
> safety filters, (2) enforce exit discipline no human sustains, and
> (3) only ever trade rules that survived honest, cost-aware validation —
> and to tell you plainly when they don't. Trade only money you can lose
> entirely.

## Architecture

```
scripts/collect_panel.py     24/7 data collector (GeckoTerminal + DexScreener)
        │  survivorship-free launch panel: every new pool incl. ones that die,
        │  minute OHLCV, liquidity/txn snapshots, trending + paid-boost events
        ▼
data/panel.db (SQLite)
        │
        ├── research/analyze_panel.py      base rates & event studies (pre-strategy)
        │
        ├── memebot backtest|grid|walkforward
        │       src/memebot/backtest/      event-driven portfolio engine
        │       - signal at bar close -> fill at NEXT bar open
        │       - stops before TPs inside a bar (pessimistic)
        │       - CPAMM slippage: cost grows with size/liquidity
        │       - forced stressed exits on liquidity collapse
        │       - cluster bootstrap by token, leave-top-k fragility
        │       - walk-forward by launch time with embargo
        │       - experiment registry: every config tried is logged
        │
        └── memebot paper|live             src/memebot/live/trader.py
                - same strategy code, same cost model (paper)
                - safety gate: authorities revoked, no Token-2022,
                  holder concentration, Jupiter sell-quote honeypot check
                - risk: fixed sizing, concurrency cap, daily loss halt,
                  <=0.5% of pool liquidity, kill switch file
                - execution: paper (default) or Jupiter swap API (gated)
```

## Quick start

```bash
pip install -e .            # or: pip install -e '.[live,dev]'

# 1. collect data (leave running; the longer the better)
python3 scripts/collect_panel.py --hours 24 --db data/panel.db

# 2. look at base rates before fitting anything
python3 research/analyze_panel.py data/panel.db

# 3. backtest a pre-registered strategy family
memebot backtest --db data/panel.db --strategy dip_reclaim
memebot backtest --db data/panel.db --strategy random_entries   # placebo control

# 4. walk-forward validation over a parameter grid
memebot walkforward --db data/panel.db --strategy dip_reclaim \
  --param-grid '{"min_run": [0.5, 1.0], "min_dip": [0.25, 0.35, 0.5]}' \
  --exit-grid '{"trail_frac": [0.2, 0.3]}'

# 5. run the trader (PAPER by default — no keys needed)
memebot paper

# 6. live trading (only after paper works for you, only with throwaway funds)
MEMEBOT_LIVE=YES MEMEBOT_PRIVATE_KEY=<base58> memebot live
```

## Strategy families (pre-registered)

Defined in `src/memebot/strategy.py` *before* backtesting, so validation is
hypothesis-testing rather than curve-fitting:

| name | hypothesis |
|---|---|
| `grad_momentum` | young pool over liquidity/volume floor breaking its 15m high with buyer dominance continues short-term |
| `dip_reclaim` | a pool that pumped, flushed (the structural post-graduation insider unwind), and reclaims its short EMA with liquidity intact gets a second attention leg |
| `attention_cont` | 6–48h-old pool in a mcap band making new 1h highs on expanding volume continues |
| `trending_follow` | entry at first appearance in GeckoTerminal trending (public attention event) |
| `random_entries` | placebo negative control — random entries through the same liquidity gate, exits, and costs |

Exits are shared machinery: hard stop, trailing stop, TP ladder, time stop,
and forced exit on observed liquidity collapse.

## Safety gate (hard filters, all must pass before any live/paper buy)

1. market shape: age, liquidity floor, 1h volume floor, FDV band
2. mint authority revoked, freeze authority revoked, **no Token-2022**
3. top-10 holder concentration (excluding pool vault) below threshold
4. Jupiter round-trip quote: route exists, quoted loss within bounds
   (honeypot / transfer-tax detector)

## Risk containment

- fixed USD position size, capped at 0.5% of pool liquidity
- max concurrent positions, max total exposure fraction
- daily realized-loss halt (resets at UTC midnight)
- kill switch: `touch data/KILL` halts entries; writing `CLOSE` into the
  file also liquidates open positions
- live mode requires **both** `mode: live` config and `MEMEBOT_LIVE=YES`
  env; keys only via env; dedicated hot wallet with throwaway funds only

## Data collection design (why backtests here can be trusted more than most)

- **Survivorship-free by construction**: the collector snapshots GT's
  newest-pools feed continuously; pools that rug minutes later remain in
  the panel with their full price history. Backtest entries are only
  allowed after each pool's recorded discovery time.
- **Liquidity paths tracked**: every pool that ever reached $2k liquidity
  is re-snapshotted (reserve, buys/sells, unique buyers) every few minutes
  via GT's multi-pool endpoint, so the engine can simulate liquidity-
  collapse exits and size against executable depth (trailing-min reserve).
- **Attention events**: DexScreener paid boosts/profiles (timestamped
  promoter spend) and GT trending appearances are recorded for event
  studies.
- Known conditioning (documented, not hidden): the panel only contains
  pools GeckoTerminal indexes; strategies only trade pools over a
  liquidity floor, so this matches the live tradable universe.

## Cost model

Per side: DEX fee (30bps) + adverse/MEV buffer (50bps) + constant-product
price impact `q/(Q+q)` against the *trailing-min* known reserve + flat
$0.10/tx. Forced exits during liquidity collapse take 3x impact. Unknown
liquidity is punished (10% impact assumption), never rewarded. Headline
results must be reported at 1x/2x/3x cost multiples.

## Validation results

See `research/results/REPORT.md` (generated from the collected panel) for
the current evidence: base rates, per-family backtests vs the placebo
control, walk-forward out-of-sample numbers, fragility metrics, and the
go/no-go verdict per strategy. **If a strategy is not marked validated
there, do not run it live.**

## Deployment

- Docker: `docker compose -f deploy/docker-compose.yml up -d`
  (runs collector + paper trader; state in `./data`)
- systemd: `deploy/memebot.service`
- Telegram notifications: set `MEMEBOT_TG_TOKEN` / `MEMEBOT_TG_CHAT`,
  enable in config.

## Repository map

```
config/default.yaml        every tunable, documented
src/memebot/data/          GT / DexScreener / Jupiter / Solana RPC clients
src/memebot/backtest/      engine, costs, metrics, walkforward
src/memebot/strategy.py    rule families + registry
src/memebot/safety.py      rug/honeypot gate
src/memebot/risk.py        portfolio risk manager
src/memebot/execution.py   paper + Jupiter live executors
src/memebot/live/          24/7 orchestrator, state store, notifier
scripts/collect_panel.py   standalone data collector
research/raw/              6 verified research reports (APIs, microstructure,
                           strategies, execution, methodology, attention)
research/analyze_panel.py  base-rate analysis
tests/                     engine/cost/safety/feature correctness tests
```

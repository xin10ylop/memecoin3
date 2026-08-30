"""Realtime launch scalper — the validated signal, executable.

THE SIGNAL (research/harvest_grid.py, unbiased sample, out-of-sample
validated): in a pool's first ~2 minutes, if it traded in both minutes AND
the price moved at least ~17% (range, in EITHER direction — a vertical
pump predicts death, two-sided churn predicts the tail), then buying and
trailing 30% with a 30-minute cap returned:

    all trades      +41.6%  CI [+15.1%, +71.5%]   n=112
    resolved only   +46.5%  CI [+17.5%, +82.9%]
    harshest        +28.0%  CI [+0.8%,  +59.3%]
    out-of-sample   +45.0%  CI [+9.3%,  +88.0%]   (thresholds fit on the
                                                   earlier half only)
    drop top-5      +13.5%  — not carried by outliers
    win rate 30%, median negative: a fat-tail profile. Most trades lose a
    little; the mean lives in the winners. Sizing and trade count matter
    more than any single position.

WHY IT NEEDS THIS MODULE: the edge decays with latency (~+19% acted on
immediately, ~+11% at 2-3 min, ~0 by 5) and GeckoTerminal discovers pools
at a median 2.4 minutes old. So the signal is real but unreachable through
the normal feed. Helius streams creations in seconds, which is what makes
it executable at all.

Pipeline: Helius creation stream -> resolve signature to token mint ->
batch-poll Jupiter prices (one call covers every watched mint) -> compute
range/activity over the observation window -> safety gate -> paper or live
buy -> trail 30%, hard cap 30 minutes.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import numpy as np
import requests

from ..backtest.costs import CostModel
from ..config import Config, live_trading_armed
from ..data.jupiter import SOL_MINT, Jupiter
from ..data.rpc import SolanaRpc
from ..execution import PaperExecutor
from ..risk import OpenPosition, RiskManager
from ..safety import SafetyGate
from .notifier import Notifier
from .realtime import RealtimeLaunchFeed
from .state import StateStore

log = logging.getLogger(__name__)

OBS_SEC = 120          # observation window before deciding
POLL_SEC = 10          # price sampling cadence (batched across candidates)
MIN_RANGE = 0.172      # validated threshold: >=17.2% range in the window
MIN_SAMPLES = 6        # needs real activity, not two lonely prints
TRAIL = 0.30
MAX_HOLD_MIN = 30


@dataclass
class Candidate:
    mint: str
    detected_ts: float
    prices: list = field(default_factory=list)
    decided: bool = False

    @property
    def age(self) -> float:
        return time.time() - self.detected_ts

    def range_frac(self) -> float:
        p = [x for x in self.prices if x and x > 0]
        if len(p) < 2:
            return 0.0
        return max(p) / min(p) - 1.0


class RealtimeScalper:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.costs = CostModel(dex_fee_bps=cfg.costs.dex_fee_bps,
                               adverse_bps=cfg.costs.adverse_bps,
                               priority_fee_usd=cfg.costs.priority_fee_usd)
        self.jup = Jupiter(per_min=24)
        self.rpc = SolanaRpc()
        self.safety = SafetyGate(cfg, self.rpc, self.jup)
        self.risk = RiskManager(cfg)
        self.notify = Notifier(cfg.telegram.enabled)
        self.state = StateStore(cfg.live.state_db)
        self.feed = RealtimeLaunchFeed()
        self.is_live = cfg.mode == "live" and live_trading_armed()
        self.executor = PaperExecutor(self.costs)
        if self.is_live:
            from ..execution import JupiterExecutor
            self.executor = JupiterExecutor(
                self.jup, self.rpc, wallet_min_sol=cfg.live.wallet_min_sol)
        self.candidates: dict[str, Candidate] = {}
        self.positions: dict[str, OpenPosition] = self.state.load_positions()
        cash = self.state.get_kv("cash_usd")
        self.cash = float(cash) if cash is not None else cfg.capital.starting_usd
        self.sol_price = 100.0
        self._seen_sigs: set[str] = set()
        log.info("scalper up: mode=%s cash=%.2f positions=%d",
                 "LIVE" if self.is_live else "PAPER", self.cash,
                 len(self.positions))

    # ---------------------------------------------------------------- intake

    def _resolve_mint(self, sig: str) -> str | None:
        """Creation signature -> the token mint (not SOL, not the LP mint)."""
        for _ in range(6):
            res = self.rpc.call("getTransaction", [
                sig, {"encoding": "jsonParsed",
                      "maxSupportedTransactionVersion": 0}])
            if res:
                break
            time.sleep(2)
        else:
            return None
        post = (res.get("meta") or {}).get("postTokenBalances") or []
        mints = [b.get("mint") for b in post if b.get("mint")]
        cands = [m for m in dict.fromkeys(mints) if m != SOL_MINT]
        for m in cands:                      # the tradeable one is the token
            if self.jup.prices_usd([m]).get(m):
                return m
        return None

    def intake(self) -> None:
        for ev in self.feed.recent(max_age_sec=90):
            if ev.signature in self._seen_sigs:
                continue
            self._seen_sigs.add(ev.signature)
            mint = self._resolve_mint(ev.signature)
            if not mint or mint in self.candidates or mint in self.positions:
                continue
            self.candidates[mint] = Candidate(mint, ev.detected_ts)
            log.info("watching %s (detected %.0fs ago)", mint[:10],
                     time.time() - ev.detected_ts)

    # ------------------------------------------------------------- sampling

    def sample(self) -> None:
        """One batched Jupiter call prices every watched mint at once."""
        watch = [m for m, c in self.candidates.items() if not c.decided]
        if not watch:
            return
        px = self.jup.prices_usd(watch[:50])
        for m, c in self.candidates.items():
            if m in px:
                c.prices.append(px[m])

    # -------------------------------------------------------------- decision

    def decide(self) -> None:
        for mint, c in list(self.candidates.items()):
            if c.decided:
                continue
            if c.age < OBS_SEC:
                continue
            c.decided = True
            rng = c.range_frac()
            n = len([p for p in c.prices if p])
            if n < MIN_SAMPLES or rng < MIN_RANGE:
                log.info("skip %s: range %.1f%% samples %d (need >=%.1f%%, %d)",
                         mint[:10], rng * 100, n, MIN_RANGE * 100, MIN_SAMPLES)
                self.candidates.pop(mint, None)
                continue
            self._enter(mint, c)

    def _enter(self, mint: str, c: Candidate) -> None:
        now = time.time()
        equity = self.equity()
        ok, why = self.risk.can_enter(now, self.positions, equity, None)
        if not ok:
            log.info("entry blocked %s: %s", mint[:10], why)
            self.candidates.pop(mint, None)
            return
        size = self.risk.position_size(equity, None)
        # these pools are tiny (median ~$1.5k reserve): clip small or the
        # measured edge is eaten by our own impact
        size = min(size, 10.0)
        px = self.jup.prices_usd([mint]).get(mint)
        if not px:
            self.candidates.pop(mint, None)
            return
        v = self.safety.check_sellability(mint, size, self.sol_price)
        if not v.ok:
            log.info("safety reject %s: %s", mint[:10], v.reason)
            self.candidates.pop(mint, None)
            return
        rep = self.executor.buy(mint, size, px, None) if not self.is_live else \
            self.executor.buy(mint, size, px, None, self.sol_price)
        if not rep.ok or rep.tokens <= 0:
            self.candidates.pop(mint, None)
            return
        self.cash -= rep.usd
        pos = OpenPosition(pool=mint, mint=mint, symbol=mint[:6],
                           entry_ts=now, entry_price=rep.price,
                           tokens=rep.tokens, size_usd=rep.usd,
                           hwm_price=rep.price)
        self.positions[mint] = pos
        self.state.save_position(pos)
        self.state.set_kv("cash_usd", str(self.cash))
        self.candidates.pop(mint, None)
        self.notify.send(f"ENTER {mint[:8]} ${rep.usd:.0f} "
                         f"(range {c.range_frac():.0%})")

    # ----------------------------------------------------------------- exits

    def manage(self) -> None:
        if not self.positions:
            return
        px = self.jup.prices_usd([p.mint for p in self.positions.values()])
        for mint, pos in list(self.positions.items()):
            p = px.get(mint)
            held = (time.time() - pos.entry_ts) / 60
            if p is None:
                if held >= 5:
                    self._exit(pos, pos.entry_price * 0.1, "no_price")
                continue
            pos.hwm_price = max(pos.hwm_price, p)
            if p <= pos.hwm_price * (1 - TRAIL):
                self._exit(pos, p, "trail")
            elif held >= MAX_HOLD_MIN:
                self._exit(pos, p, "time")
            else:
                self.state.save_position(pos)

    def _exit(self, pos: OpenPosition, px: float, reason: str) -> None:
        rep = (self.executor.sell(pos.mint, pos.tokens, px, None, self.sol_price,
                                  sell_all=True)
               if self.is_live else
               self.executor.sell(pos.mint, pos.tokens, px, None))
        if not rep.ok:
            self.notify.send(f"⚠️ SELL FAILED {pos.symbol} ({reason})")
            return
        self.cash += rep.usd
        pnl = rep.usd - pos.size_usd
        self.positions.pop(pos.pool, None)
        self.state.delete_position(pos.pool)
        self.state.record_trade(pos, rep.price, pnl, reason)
        self.risk.record_realized(pnl, self.equity())
        self.state.set_kv("cash_usd", str(self.cash))
        self.notify.send(f"EXIT {pos.symbol} {reason} pnl ${pnl:+.2f}")

    def equity(self) -> float:
        return self.cash + sum(p.tokens * p.entry_price
                               for p in self.positions.values())

    # ------------------------------------------------------------------ loop

    def run(self) -> None:
        self.feed.start()
        self.notify.send(f"realtime scalper started "
                         f"({'LIVE' if self.is_live else 'paper'})")
        last_sample = last_beat = 0.0
        while True:
            try:
                now = time.time()
                if now - last_sample >= POLL_SEC:
                    self.intake()
                    self.sample()
                    self.decide()
                    last_sample = now
                self.manage()
                if now - last_beat >= 300:
                    s = self.state.pnl_summary()
                    log.info("heartbeat equity=%.2f watching=%d positions=%d "
                             "trades=%d pnl=%.2f", self.equity(),
                             len(self.candidates), len(self.positions),
                             s["n_trades"], s["total_pnl_usd"])
                    last_beat = now
                    px = self.jup.prices_usd([SOL_MINT])
                    if px.get(SOL_MINT):
                        self.sol_price = px[SOL_MINT]
                time.sleep(2)
            except KeyboardInterrupt:
                self.feed.stop()
                return
            except Exception:
                log.exception("scalper loop error; continuing")
                time.sleep(5)

"""24/7 trading orchestrator (paper by default).

One synchronous loop, deliberately boring for reliability:

  every tick (default 10s):
    * refresh prices of held tokens (Jupiter batch price)
    * apply exit rules (stop / trail / TP ladder / time / liquidity collapse)
  every scan interval (default 60s):
    * pull GT new_pools + trending, maintain a small watchlist
    * build minute bars + snapshot features for watchlist pools
    * evaluate the SAME strategy entry rules used in backtests
    * on signal: full safety gate -> risk manager -> execute

State survives restarts via SQLite. `touch data/KILL` halts new entries;
writing the word CLOSE into that file also liquidates open positions.
"""
from __future__ import annotations

import json
import logging
import time
from collections import deque

import numpy as np
import pandas as pd

from ..backtest.costs import CostModel
from ..config import Config, live_trading_armed
from ..data.dexscreener import DexScreener
from ..data.gt import GeckoTerminal, PoolStats
from ..data.jupiter import SOL_MINT, Jupiter
from ..data.rpc import SolanaRpc
from ..execution import ExecutionReport, JupiterExecutor, PaperExecutor
from ..risk import OpenPosition, RiskManager
from ..safety import SafetyGate
from ..strategy import ExitRules, make_strategy
from .notifier import Notifier
from .state import StateStore

log = logging.getLogger(__name__)

WATCHLIST_MAX = 8
# cover the default strategies' full lookback (age windows up to 12h) in one
# OHLCV call so live features match backtest features for young pools
BARS_PER_FETCH = 720


class LiveTrader:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.costs = CostModel(
            dex_fee_bps=cfg.costs.dex_fee_bps,
            adverse_bps=cfg.costs.adverse_bps,
            priority_fee_usd=cfg.costs.priority_fee_usd,
            rug_exit_impact_mult=cfg.costs.rug_exit_impact_mult,
        )
        self.exit_rules = ExitRules(
            stop_frac=cfg.exits.stop_frac,
            trail_frac=cfg.exits.trail_frac,
            tp_levels=tuple(tuple(x) for x in cfg.exits.tp_levels),
            max_hold_min=cfg.exits.max_hold_minutes,
            liq_drop_exit_frac=cfg.exits.liquidity_drop_exit_frac,
        )
        self.strategy = make_strategy(cfg.strategy.name,
                                      cfg.strategy.get("params").raw()
                                      if cfg.strategy.get("params") else {},
                                      self.exit_rules)
        self.gt = GeckoTerminal(per_min=cfg.live.gt_rate_per_min)
        self.jup = Jupiter()
        self.rpc = SolanaRpc()
        self.dexs = DexScreener()
        self.safety = SafetyGate(cfg, self.rpc, self.jup)
        self.risk = RiskManager(cfg)
        self.notify = Notifier(cfg.telegram.enabled)
        self.state = StateStore(cfg.live.state_db)

        self.is_live = cfg.mode == "live" and live_trading_armed()
        if cfg.mode == "live" and not live_trading_armed():
            log.warning("config mode=live but MEMEBOT_LIVE!=YES -> running PAPER")
        if self.is_live:
            self.executor = JupiterExecutor(self.jup, self.rpc)
        else:
            self.executor = PaperExecutor(self.costs)

        self.positions: dict[str, OpenPosition] = self.state.load_positions()
        cash = self.state.get_kv("cash_usd")
        self.cash = float(cash) if cash is not None else cfg.capital.starting_usd
        # rolling snapshot history per pool for feature building + liq exits
        self.snap_hist: dict[str, deque] = {}
        self.pool_stats: dict[str, PoolStats] = {}
        self.mint_by_pool: dict[str, str] = {}
        self.watchlist: list[str] = []
        self.sol_price = 100.0
        self.pool_cooldown: dict[str, float] = {}
        log.info("trader up: mode=%s positions=%d cash=%.2f",
                 "LIVE" if self.is_live else "PAPER", len(self.positions), self.cash)

    # ------------------------------------------------------------------ utils

    def equity(self, prices: dict[str, float] | None = None) -> float:
        val = 0.0
        prices = prices or {}
        for p in self.positions.values():
            px = prices.get(p.mint, p.entry_price)
            val += p.tokens * px
        return self.cash + val

    def _record_snap(self, s: PoolStats) -> None:
        self.pool_stats[s.address] = s
        if s.base_mint:
            self.mint_by_pool[s.address] = s.base_mint
        dq = self.snap_hist.setdefault(s.address, deque(maxlen=240))
        dq.append((int(time.time()), s.reserve_usd, s.fdv_usd,
                   s.buys_m5, s.sells_m5, s.buyers_m5, s.sellers_m5, s.vol_h1))

    def _snap_frame(self, pool: str) -> pd.DataFrame:
        dq = self.snap_hist.get(pool)
        if not dq:
            return pd.DataFrame()
        return pd.DataFrame(list(dq), columns=[
            "ts", "reserve_usd", "fdv_usd", "buys_m5", "sells_m5",
            "buyers_m5", "sellers_m5", "vol_h1_snap"]).drop_duplicates("ts")

    def _bars_with_snaps(self, pool: str) -> pd.DataFrame | None:
        bars = self.gt.ohlcv(pool, "minute", limit=BARS_PER_FETCH)
        if len(bars) < 30:
            return None
        df = pd.DataFrame(bars, columns=["ts", "o", "h", "l", "c", "vol_usd"])
        df = df.drop_duplicates("ts").set_index("ts").sort_index()
        snaps = self._snap_frame(pool)
        if not snaps.empty:
            df = pd.merge_asof(
                df.reset_index().sort_values("ts"),
                snaps.sort_values("ts"),
                on="ts", direction="backward", tolerance=600,
            ).set_index("ts")
        else:
            for col in ("reserve_usd", "fdv_usd", "buys_m5", "sells_m5",
                        "buyers_m5", "sellers_m5", "vol_h1_snap"):
                df[col] = np.nan
        # live fallback: current stats fill the last row so liquidity gates
        # can pass even before snapshot history accumulates
        st = self.pool_stats.get(pool)
        if st and st.reserve_usd and pd.isna(df["reserve_usd"].iloc[-1]):
            df.iloc[-1, df.columns.get_loc("reserve_usd")] = st.reserve_usd
            df.iloc[-1, df.columns.get_loc("fdv_usd")] = st.fdv_usd
        return df

    # ------------------------------------------------------------------ scan

    def scan(self) -> None:
        stats: dict[str, PoolStats] = {}
        for page in (1, 2, 3):
            for s in self.gt.new_pools(page):
                stats[s.address] = s
        for s in self.gt.trending_pools(1):
            stats[s.address] = s
        # refresh stats for held pools not in the sweep
        for pool in list(self.positions):
            if pool not in stats:
                s = self.gt.pool(pool)
                if s:
                    stats[s.address] = s
        for s in stats.values():
            self._record_snap(s)
        # candidate watchlist: market-shape pass, ranked by 1h volume
        cands = [s for s in stats.values()
                 if s.address not in self.positions
                 and self.safety.check_market(s).ok]
        cands.sort(key=lambda s: s.vol_h1 or 0, reverse=True)
        self.watchlist = [s.address for s in cands[:WATCHLIST_MAX]]

        px = self.jup.prices_usd([SOL_MINT])
        if px.get(SOL_MINT):
            self.sol_price = px[SOL_MINT]

        for pool in self.watchlist:
            if len(self.positions) >= self.cfg.capital.max_concurrent:
                break
            self._maybe_enter(pool)

    def _maybe_enter(self, pool: str) -> None:
        now = time.time()
        if self.pool_cooldown.get(pool, 0) > now:
            return
        st = self.pool_stats.get(pool)
        if not st or not st.base_mint:
            return
        df = self._bars_with_snaps(pool)
        if df is None:
            return
        fake_pool_data = _PoolShim(st, df)
        feat = self.strategy.prepare(fake_pool_data)
        sig = self.strategy.entries(fake_pool_data, feat)
        # act only if one of the last 2 CLOSED bars signalled (fresh signal)
        if len(sig) < 3 or not (sig[-3:-1].any()):
            return
        ok, why = self.risk.can_enter(now, self.positions, self.equity(),
                                      st.reserve_usd)
        if not ok:
            log.info("entry blocked %s: %s", st.symbol, why)
            return
        size = self.risk.position_size(self.equity(), st.reserve_usd)
        if size < 5:
            return
        verdict = self.safety.full_check(st, size, self.sol_price)
        if not verdict.ok:
            log.info("safety reject %s: %s", st.symbol, verdict.reason)
            self.pool_cooldown[pool] = now + 1800
            return
        ref_price = st.price_usd or float(df["c"].iloc[-1])
        rep = self._exec_buy(st, size, ref_price)
        if not rep.ok or rep.tokens <= 0:
            log.warning("buy failed %s: %s", st.symbol, rep.detail)
            return
        self.cash -= rep.usd
        pos = OpenPosition(pool=pool, mint=st.base_mint, symbol=st.symbol,
                           entry_ts=now, entry_price=rep.price,
                           tokens=rep.tokens, size_usd=rep.usd,
                           hwm_price=rep.price)
        self.positions[pool] = pos
        self.state.save_position(pos)
        self.state.set_kv("cash_usd", str(self.cash))
        self.notify.send(f"ENTER {st.symbol} ${rep.usd:.0f} @ {rep.price:.8f} "
                         f"({'LIVE' if self.is_live else 'paper'})")

    def _exec_buy(self, st: PoolStats, size: float, ref_price: float) -> ExecutionReport:
        if self.is_live:
            return self.executor.buy(st.base_mint, size, ref_price,
                                     st.reserve_usd, self.sol_price)
        return self.executor.buy(st.base_mint, size, ref_price, st.reserve_usd)

    # ------------------------------------------------------------------ exits

    def manage_positions(self) -> None:
        if not self.positions:
            return
        mints = [p.mint for p in self.positions.values()]
        prices = self.jup.prices_usd(mints)
        er = self.exit_rules
        for pool, pos in list(self.positions.items()):
            px = prices.get(pos.mint)
            if px is None:
                continue
            pos.hwm_price = max(pos.hwm_price, px)
            held_min = (time.time() - pos.entry_ts) / 60.0
            st = self.pool_stats.get(pool)
            reserve = st.reserve_usd if st else None

            # liquidity collapse check from snapshot history
            liq_rug = False
            snaps = self._snap_frame(pool)
            if len(snaps) >= 2:
                recent = snaps[snaps["ts"] >= time.time() - 360]
                r = recent["reserve_usd"].dropna()
                if len(r) >= 2 and r.iloc[0] > 0 \
                        and r.iloc[-1] / r.iloc[0] - 1 <= -er.liq_drop_exit_frac:
                    liq_rug = True

            eff_stop = max(pos.entry_price * (1 - er.stop_frac),
                           pos.hwm_price * (1 - er.trail_frac))
            reason = None
            frac = 1.0
            stressed = False
            if liq_rug:
                reason, stressed = "liq_rug", True
            elif px <= eff_stop:
                reason = "stop" if pos.hwm_price * (1 - er.trail_frac) \
                                   <= pos.entry_price * (1 - er.stop_frac) else "trail"
            elif held_min >= er.max_hold_min:
                reason = "time"
            else:
                for k, (gain, sell_frac) in enumerate(er.tp_levels):
                    if k in pos.tp_taken:
                        continue
                    if px >= pos.entry_price * (1 + gain):
                        reason, frac = "tp", sell_frac
                        pos.tp_taken.append(k)
                        break
            if reason is None:
                self.state.save_position(pos)
                continue
            self._exec_exit(pool, pos, px, reserve, frac, reason, stressed)

    def _exec_exit(self, pool: str, pos: OpenPosition, px: float,
                   reserve: float | None, frac: float, reason: str,
                   stressed: bool) -> None:
        qty = pos.tokens * frac
        if self.is_live:
            rep = self.executor.sell(pos.mint, qty, px, reserve,
                                     self.sol_price, stressed=stressed)
        else:
            rep = self.executor.sell(pos.mint, qty, px, reserve, stressed)
        if not rep.ok:
            log.warning("sell failed %s (%s): %s", pos.symbol, reason, rep.detail)
            if reason in ("stop", "trail", "liq_rug"):
                # critical exit failed -> retry next tick, notify loudly
                self.notify.send(f"⚠️ SELL FAILED {pos.symbol} ({reason})")
            return
        self.cash += rep.usd
        cost_basis = pos.size_usd * frac
        pnl = rep.usd - cost_basis
        if frac >= 0.999:
            self.positions.pop(pool, None)
            self.state.delete_position(pool)
            self.state.record_trade(pos, rep.price, pnl, reason)
            self.risk.record_realized(pnl, self.equity())
            self.pool_cooldown[pool] = time.time() + 3600
        else:
            pos.tokens -= qty
            pos.size_usd -= cost_basis
            self.state.save_position(pos)
            self.state.record_trade(pos, rep.price, pnl, f"{reason}_partial")
            self.risk.record_realized(pnl, self.equity())
        self.state.set_kv("cash_usd", str(self.cash))
        self.notify.send(f"EXIT {pos.symbol} {reason} pnl ${pnl:+.2f}")

    # ------------------------------------------------------------------ loop

    def run(self) -> None:
        cfg = self.cfg.live
        last_scan = 0.0
        last_heartbeat = 0.0
        self.notify.send(f"memebot started ({'LIVE' if self.is_live else 'paper'}), "
                         f"strategy={self.strategy.name}")
        while True:
            try:
                now = time.time()
                kill = self._kill_mode()
                if kill == "CLOSE" and self.positions:
                    log.warning("KILL CLOSE: liquidating all positions")
                    prices = self.jup.prices_usd(
                        [p.mint for p in self.positions.values()])
                    for pool, pos in list(self.positions.items()):
                        px = prices.get(pos.mint, pos.entry_price)
                        self._exec_exit(pool, pos, px, None, 1.0, "kill", False)
                self.manage_positions()
                if now - last_scan >= cfg.scan_interval_sec and kill is None:
                    self.scan()
                    last_scan = now
                if now - last_heartbeat >= 300:
                    eq = self.equity(self.jup.prices_usd(
                        [p.mint for p in self.positions.values()])
                        if self.positions else {})
                    self.state.snapshot_equity(eq, self.cash, len(self.positions))
                    log.info("heartbeat equity=%.2f cash=%.2f pos=%d watch=%d",
                             eq, self.cash, len(self.positions), len(self.watchlist))
                    last_heartbeat = now
            except KeyboardInterrupt:
                log.info("interrupted; exiting")
                return
            except Exception:
                log.exception("main loop error; continuing")
                time.sleep(10)
            time.sleep(cfg.tick_interval_sec)

    def _kill_mode(self) -> str | None:
        import os
        if not os.path.exists(self.cfg.live.kill_file):
            return None
        try:
            with open(self.cfg.live.kill_file) as fh:
                content = fh.read().strip().upper()
            return "CLOSE" if "CLOSE" in content else "HALT"
        except OSError:
            return "HALT"


class _PoolShim:
    """Adapts live (stats, bars) to the PoolData interface strategies expect."""

    def __init__(self, st: PoolStats, df: pd.DataFrame):
        self.meta = st           # PoolStats has .address/.created_ts/.symbol
        self.df = df

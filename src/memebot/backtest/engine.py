"""Event-driven portfolio backtester over a panel of pool minute-bars.

Discipline:
  * signal evaluated at bar close i -> entry fill at bar open i+1
  * intrabar exit ordering is pessimistic: stops fill before take-profits
  * trailing stop references the high-water mark up to the PREVIOUS bar
  * liquidity-collapse (observed reserve -X% in 5m) forces a stressed exit
  * a pool whose data ends while holding is closed at the last bar close —
    with stressed costs if the pool's last known liquidity died
  * fixed USD position sizing => portfolio sim with concurrency caps and a
    daily-loss halt is exact (positions don't interact beyond the caps)

Costs come from CostModel and are applied per side; flat priority fee per tx.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..data.store import PoolData
from ..features import liquidity_at
from ..strategy import ExitRules, Strategy
from .costs import CostModel


@dataclass
class RiskParams:
    starting_usd: float = 1000.0
    risk_per_trade_usd: float = 25.0
    max_concurrent: int = 4
    daily_loss_limit_frac: float = 0.10
    max_pool_share: float = 0.005
    cooldown_min: int = 60          # per-pool cooldown after an exit


@dataclass
class Fill:
    ts: int
    price: float
    usd: float
    kind: str          # entry | tp | stop | trail | time | liq_rug | data_end


@dataclass
class Trade:
    pool: str
    symbol: str | None
    entry_ts: int
    exit_ts: int
    entry_price: float
    size_usd: float
    pnl_usd: float
    ret_frac: float
    exit_reason: str
    n_tx: int
    fills: list[Fill] = field(default_factory=list)


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity: pd.Series               # equity sampled at trade exits
    n_candidates: int
    n_skipped_risk: int
    params: dict = field(default_factory=dict)

    def trades_df(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "pool": t.pool, "symbol": t.symbol, "entry_ts": t.entry_ts,
            "exit_ts": t.exit_ts, "hold_min": (t.exit_ts - t.entry_ts) / 60,
            "size_usd": t.size_usd, "pnl_usd": t.pnl_usd, "ret": t.ret_frac,
            "reason": t.exit_reason,
        } for t in self.trades])


def simulate_position(df: pd.DataFrame, fill_idx: int, size_usd: float,
                      exit_rules: ExitRules, costs: CostModel,
                      pool: str, symbol: str | None) -> Trade | None:
    """Walk one position from its fill bar to exit. Deterministic, no lookahead."""
    n = len(df)
    if fill_idx >= n:
        return None
    o = df["o"].to_numpy(dtype=float)
    h = df["h"].to_numpy(dtype=float)
    lo = df["l"].to_numpy(dtype=float)
    cl = df["c"].to_numpy(dtype=float)
    ts = df.index.to_numpy()
    reserve = (df["reserve_usd"].to_numpy(dtype=float)
               if "reserve_usd" in df.columns else np.full(n, np.nan))
    res_chg = (df["reserve_chg_5m"].to_numpy(dtype=float)
               if "reserve_chg_5m" in df.columns else np.full(n, np.nan))

    liq0 = liquidity_at(df, fill_idx)
    entry_price = costs.buy_fill(o[fill_idx], size_usd, liq0)
    if not np.isfinite(entry_price) or entry_price <= 0:
        return None
    tokens = size_usd / entry_price
    fills = [Fill(int(ts[fill_idx]), entry_price, -size_usd, "entry")]
    n_tx = 1
    proceeds = 0.0
    remaining = 1.0                      # fraction of original tokens still held
    hwm = entry_price                    # high-water mark up to previous bar
    stop_price = entry_price * (1.0 - exit_rules.stop_frac)
    tp_hit = [False] * len(exit_rules.tp_levels)
    exit_reason = None

    def known_liq(j: int) -> float | None:
        s = reserve[: j + 1]
        s = s[np.isfinite(s)]
        return float(s[-1]) if len(s) else None

    def sell(j: int, frac: float, ref_price: float, kind: str,
             stressed: bool = False) -> None:
        nonlocal proceeds, remaining, n_tx
        qty = tokens * frac
        usd_ref = qty * ref_price
        price = costs.sell_fill(ref_price, usd_ref, known_liq(j), stressed)
        proceeds += qty * price
        remaining -= frac
        n_tx += 1
        fills.append(Fill(int(ts[j]), price, qty * price, kind))

    j = fill_idx
    while j < n and remaining > 1e-9:
        # 1) liquidity collapse observed at this bar -> stressed full exit
        if np.isfinite(res_chg[j]) and res_chg[j] <= -exit_rules.liq_drop_exit_frac:
            sell(j, remaining, cl[j], "liq_rug", stressed=True)
            exit_reason = "liq_rug"
            break
        # 2) time stop
        if (ts[j] - ts[fill_idx]) / 60.0 >= exit_rules.max_hold_min:
            sell(j, remaining, o[j], "time")
            exit_reason = "time"
            break
        # 3) protective stop (hard stop or trail) — pessimistic: before TPs
        eff_stop = max(stop_price, hwm * (1.0 - exit_rules.trail_frac))
        if lo[j] <= eff_stop:
            fill_ref = min(o[j], eff_stop)   # gap-through fills worse
            kind = "stop" if eff_stop == stop_price else "trail"
            sell(j, remaining, fill_ref, kind)
            exit_reason = kind
            break
        # 4) take-profit ladder
        for k, (gain, frac_of_orig) in enumerate(exit_rules.tp_levels):
            if tp_hit[k] or remaining <= 1e-9:
                continue
            level = entry_price * (1.0 + gain)
            if h[j] >= level:
                f = min(frac_of_orig, remaining)
                # pessimistic: fill exactly at the level, never credit a
                # gap-up open beyond it
                sell(j, f, level, "tp")
                tp_hit[k] = True
        # 5) advance high-water mark AFTER the bar is processed
        hwm = max(hwm, h[j])
        j += 1

    if remaining > 1e-9:
        # data ended while holding
        last = n - 1
        lastliq = known_liq(last)
        dead = (lastliq is not None and lastliq < 1000)
        sell(last, remaining, cl[last], "data_end", stressed=dead)
        exit_reason = exit_reason or "data_end"

    exit_ts = int(fills[-1].ts)
    flat_fees = costs.priority_fee_usd * n_tx
    pnl = proceeds - size_usd - flat_fees
    return Trade(pool=pool, symbol=symbol, entry_ts=int(ts[fill_idx]),
                 exit_ts=exit_ts, entry_price=entry_price, size_usd=size_usd,
                 pnl_usd=pnl, ret_frac=pnl / size_usd, exit_reason=exit_reason,
                 n_tx=n_tx, fills=fills)


def run_backtest(pools: list[PoolData], strategy: Strategy, costs: CostModel,
                 risk: RiskParams) -> BacktestResult:
    # 1) collect candidate entries across the panel
    candidates: list[tuple[int, PoolData, pd.DataFrame, int]] = []
    prepared: dict[str, pd.DataFrame] = {}
    for pool in pools:
        df = strategy.prepare(pool)
        prepared[pool.meta.address] = df
        sig = strategy.entries(pool, df)
        idxs = np.flatnonzero(sig)
        ts = df.index.to_numpy()
        for i in idxs:
            fill_idx = int(i) + 1
            if fill_idx >= len(df):
                continue
            candidates.append((int(ts[fill_idx]), pool, df, fill_idx))
    candidates.sort(key=lambda x: x[0])

    # 2) chronological portfolio pass with caps
    open_until: list[tuple[int, str]] = []       # (exit_ts, pool)
    pool_cooldown_until: dict[str, int] = {}
    realized: list[tuple[int, float]] = []       # (exit_ts, pnl)
    trades: list[Trade] = []
    n_skipped = 0

    def realized_today(now_ts: int) -> float:
        day = now_ts - now_ts % 86400
        return sum(p for (t, p) in realized if day <= t <= now_ts)

    for fill_ts, pool, df, fill_idx in candidates:
        addr = pool.meta.address
        open_until = [(e, a) for (e, a) in open_until if e > fill_ts]
        if any(a == addr for (_, a) in open_until):
            continue                                # already in this pool
        if pool_cooldown_until.get(addr, 0) > fill_ts:
            continue
        if len(open_until) >= risk.max_concurrent:
            n_skipped += 1
            continue
        if realized_today(fill_ts) <= -risk.daily_loss_limit_frac * risk.starting_usd:
            n_skipped += 1
            continue
        liq = liquidity_at(df, fill_idx)
        size = risk.risk_per_trade_usd
        if liq is not None and size > risk.max_pool_share * liq:
            size = risk.max_pool_share * liq
            if size < 5.0:
                n_skipped += 1
                continue
        trade = simulate_position(df, fill_idx, size, strategy.exit_rules, costs,
                                  addr, pool.meta.symbol)
        if trade is None:
            continue
        trades.append(trade)
        open_until.append((trade.exit_ts, addr))
        pool_cooldown_until[addr] = trade.exit_ts + risk.cooldown_min * 60
        realized.append((trade.exit_ts, trade.pnl_usd))
        realized.sort()

    trades.sort(key=lambda t: t.exit_ts)
    eq = risk.starting_usd + np.cumsum([t.pnl_usd for t in trades]) \
        if trades else np.array([risk.starting_usd])
    idx = [t.exit_ts for t in trades] if trades else [0]
    equity = pd.Series(eq, index=idx, dtype=float)
    return BacktestResult(trades=trades, equity=equity,
                          n_candidates=len(candidates), n_skipped_risk=n_skipped,
                          params={"strategy": strategy.name, **strategy.params})

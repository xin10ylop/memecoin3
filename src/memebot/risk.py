"""Portfolio risk manager for live/paper trading. Mirrors backtest RiskParams
so live behavior matches what was backtested."""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

from .config import Config

log = logging.getLogger(__name__)


@dataclass
class OpenPosition:
    pool: str
    mint: str
    symbol: str | None
    entry_ts: float
    entry_price: float
    tokens: float
    size_usd: float
    hwm_price: float
    tp_taken: list = field(default_factory=list)


class RiskManager:
    def __init__(self, cfg: Config):
        self.cap = cfg.capital
        self.kill_file = cfg.live.kill_file
        self.day_start = self._utc_day(time.time())
        self.realized_today = 0.0
        self.halted_reason: str | None = None

    @staticmethod
    def _utc_day(ts: float) -> int:
        return int(ts) - int(ts) % 86400

    def roll_day(self, now: float) -> None:
        day = self._utc_day(now)
        if day != self.day_start:
            self.day_start = day
            self.realized_today = 0.0
            if self.halted_reason == "daily_loss":
                self.halted_reason = None
                log.info("daily loss halt reset (new UTC day)")

    def record_realized(self, pnl_usd: float, equity_usd: float) -> None:
        self.realized_today += pnl_usd
        limit = self.cap.daily_loss_limit_frac * max(equity_usd, 1.0)
        if self.realized_today <= -limit:
            self.halted_reason = "daily_loss"
            log.warning("DAILY LOSS LIMIT hit (%.2f); halting new entries",
                        self.realized_today)

    def kill_switch_active(self) -> bool:
        return os.path.exists(self.kill_file)

    def can_enter(self, now: float, open_positions: dict[str, OpenPosition],
                  equity_usd: float, pool_liquidity_usd: float | None) -> tuple[bool, str]:
        self.roll_day(now)
        if self.kill_switch_active():
            return False, "kill switch active"
        if self.halted_reason:
            return False, f"halted: {self.halted_reason}"
        if len(open_positions) >= self.cap.max_concurrent:
            return False, "max concurrent positions"
        deployed = sum(p.size_usd for p in open_positions.values())
        if deployed + self.position_size(equity_usd, pool_liquidity_usd) \
                > self.cap.max_exposure_frac * equity_usd:
            return False, "max exposure"
        return True, "ok"

    def position_size(self, equity_usd: float,
                      pool_liquidity_usd: float | None) -> float:
        size = min(self.cap.risk_per_trade_usd, 0.25 * equity_usd)
        if pool_liquidity_usd:
            size = min(size, self.cap.max_pool_share * pool_liquidity_usd)
        return max(0.0, size)

"""Execution cost model shared by backtest and paper trading.

Constant-product AMM math: pool with quote-side reserve Q (USD value) and
base reserve B, spot p0 = Q/B.

  Buy spending q USD:  tokens out t = B*q/(Q+q)  -> avg price = p0*(1+q/Q)
  Sell tokens worth v: avg price received ~= p0*(1-v/Q)

GeckoTerminal `reserve_in_usd` is BOTH sides, so Q ~= reserve/2.
Per-side proportional cost = dex fee + price impact + adverse-selection
buffer, plus a flat priority-fee in USD per transaction.

This deliberately over- rather than under-estimates costs for small clips in
liquid pools, and grows costs correctly as position/liquidity rises — the
regime that kills naive memecoin backtests.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostModel:
    dex_fee_bps: float = 30.0        # per side
    adverse_bps: float = 50.0        # per side latency/adverse/MEV buffer
    priority_fee_usd: float = 0.10   # per transaction
    rug_exit_impact_mult: float = 3.0
    mult: float = 1.0                # stress multiplier: report at 1x/2x/3x

    def impact_frac(self, trade_usd: float, reserve_usd: float | None) -> float:
        """Proportional price impact for one side."""
        if not reserve_usd or reserve_usd <= 0:
            return 0.10  # unknown liquidity: assume very thin
        q = reserve_usd / 2.0
        return min(0.50, trade_usd / (q + trade_usd))

    def side_frac(self, trade_usd: float, reserve_usd: float | None,
                  stressed: bool = False) -> float:
        """Total proportional cost for one side (fees + impact + buffer)."""
        imp = self.impact_frac(trade_usd, reserve_usd)
        if stressed:
            imp = min(0.90, imp * self.rug_exit_impact_mult)
        return min(0.95, self.mult * ((self.dex_fee_bps + self.adverse_bps)
                                      / 10_000.0 + imp))

    @property
    def flat_fee_usd(self) -> float:
        return self.mult * self.priority_fee_usd

    def buy_fill(self, ref_price: float, trade_usd: float,
                 reserve_usd: float | None) -> float:
        """Effective per-token price paid when buying at reference price."""
        return ref_price * (1.0 + self.side_frac(trade_usd, reserve_usd))

    def sell_fill(self, ref_price: float, trade_usd: float,
                  reserve_usd: float | None, stressed: bool = False) -> float:
        """Effective per-token price received when selling at reference price."""
        return ref_price * (1.0 - self.side_frac(trade_usd, reserve_usd, stressed))

    def roundtrip_frac(self, trade_usd: float, reserve_usd: float | None) -> float:
        """Total proportional cost of buy+sell (excl. flat fees)."""
        return 2.0 * self.side_frac(trade_usd, reserve_usd)

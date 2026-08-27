"""Jupiter aggregator API (lite-api.jup.ag: free tier, no key).

Used for: USD prices of held tokens, quote-based sellability checks
(honeypot detection), and building live swap transactions.
"""
from __future__ import annotations

import logging
from typing import Any

from .http import HttpClient

log = logging.getLogger(__name__)

BASE = "https://lite-api.jup.ag"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


class Jupiter:
    # keyless lite-api budget is ~30 RPM (60s sliding window); stay under it
    def __init__(self, per_min: float = 24.0):
        self.http = HttpClient(per_min=per_min)

    def prices_usd(self, mints: list[str]) -> dict[str, float]:
        """Batch USD prices; unknown mints omitted from result."""
        out: dict[str, float] = {}
        for i in range(0, len(mints), 50):
            chunk = mints[i:i + 50]
            data = self.http.get_json(f"{BASE}/price/v3", {"ids": ",".join(chunk)})
            if not isinstance(data, dict):
                continue
            for mint, info in data.items():
                p = (info or {}).get("usdPrice")
                if p is not None:
                    out[mint] = float(p)
        return out

    def quote(self, input_mint: str, output_mint: str, amount: int,
              slippage_bps: int = 300) -> dict | None:
        """Raw units in `amount` (lamports / token base units)."""
        return self.http.get_json(f"{BASE}/swap/v1/quote", {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": slippage_bps,
        })

    def roundtrip_loss_frac(self, mint: str, sol_lamports: int = 100_000_000) -> float | None:
        """Quote SOL->token->SOL; return fraction lost (0.02 = 2%).

        A quoted round-trip loss far above pool fees+impact indicates
        transfer taxes / honeypot mechanics. None = no route (also fatal).
        """
        q1 = self.quote(SOL_MINT, mint, sol_lamports)
        out1 = int((q1 or {}).get("outAmount") or 0)
        if out1 <= 0:
            return None
        q2 = self.quote(mint, SOL_MINT, out1)
        out2 = int((q2 or {}).get("outAmount") or 0)
        if out2 <= 0:
            return None
        return 1.0 - out2 / sol_lamports

    def sell_impact_frac(self, mint: str, token_amount: int) -> float | None:
        """Price impact of selling `token_amount` base units into SOL."""
        q = self.quote(mint, SOL_MINT, token_amount)
        if not q:
            return None
        try:
            return abs(float(q.get("priceImpactPct") or 0.0))
        except (TypeError, ValueError):
            return None

    def build_swap_tx(self, quote_response: dict, user_pubkey: str,
                      priority_lamports: int = 1_000_000) -> str | None:
        """Returns base64 unsigned VersionedTransaction (live mode only).

        dynamicSlippage lets Jupiter pick effective slippage capped by the
        quote's slippageBps; the response's simulationError is checked so a
        transaction that already fails simulation is never signed."""
        data = self.http.post_json(f"{BASE}/swap/v1/swap", {
            "quoteResponse": quote_response,
            "userPublicKey": user_pubkey,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "dynamicSlippage": True,
            "prioritizationFeeLamports": {
                "priorityLevelWithMaxLamports": {
                    "priorityLevel": "high",
                    "maxLamports": priority_lamports,
                    "global": False,
                }
            },
        })
        if not data:
            return None
        sim_err = data.get("simulationError")
        if sim_err:
            log.warning("swap simulation error, refusing to sign: %s", sim_err)
            return None
        return data.get("swapTransaction")

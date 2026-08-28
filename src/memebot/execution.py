"""Order execution: paper (default) and live via Jupiter.

Paper fills use the SAME CostModel as the backtester, so paper results stay
comparable to backtests. Live execution is hard-gated behind BOTH
`mode: live` in config AND env MEMEBOT_LIVE=YES, and lazily imports solders
so the base install never needs signing libraries.
"""
from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass

from .backtest.costs import CostModel
from .config import env, live_trading_armed
from .data.jupiter import SOL_MINT, Jupiter
from .data.rpc import SolanaRpc

log = logging.getLogger(__name__)


@dataclass
class ExecutionReport:
    ok: bool
    side: str                  # buy | sell
    mint: str
    tokens: float              # ui amount filled
    usd: float                 # usd spent (buy) or received (sell)
    price: float               # effective usd per token
    detail: str = ""
    tx_sig: str | None = None


class PaperExecutor:
    """Fills at reference price adjusted by the shared cost model."""

    def __init__(self, costs: CostModel):
        self.costs = costs

    def buy(self, mint: str, usd: float, ref_price: float,
            reserve_usd: float | None) -> ExecutionReport:
        price = self.costs.buy_fill(ref_price, usd, reserve_usd)
        tokens = usd / price if price > 0 else 0.0
        return ExecutionReport(True, "buy", mint, tokens,
                               usd + self.costs.priority_fee_usd, price, "paper")

    def sell(self, mint: str, tokens: float, ref_price: float,
             reserve_usd: float | None, stressed: bool = False) -> ExecutionReport:
        usd_ref = tokens * ref_price
        price = self.costs.sell_fill(ref_price, usd_ref, reserve_usd, stressed)
        usd = max(0.0, tokens * price - self.costs.priority_fee_usd)
        return ExecutionReport(True, "sell", mint, tokens, usd, price, "paper")


class JupiterExecutor:
    """Live executor. Requires:
       * env MEMEBOT_LIVE=YES  (explicit arm switch)
       * env MEMEBOT_PRIVATE_KEY (base58 keypair)
       * optional MEMEBOT_RPC_URL (strongly recommended: a private RPC)
    Never logs key material. Confirms fills by post-tx balance diff at the
    same commitment level as tx confirmation; aborts rather than trade on
    unreadable balances; treats confirmation timeouts as UNKNOWN and
    re-checks balances before declaring failure (a timed-out tx can land)."""

    def __init__(self, jup: Jupiter, rpc: SolanaRpc,
                 slippage_bps: int = 300, priority_lamports: int = 1_000_000,
                 wallet_min_sol: float = 0.05):
        if not live_trading_armed():
            raise RuntimeError("live executor requires MEMEBOT_LIVE=YES")
        key = env("MEMEBOT_PRIVATE_KEY")
        if not key:
            raise RuntimeError("MEMEBOT_PRIVATE_KEY not set")
        try:
            from solders.keypair import Keypair  # lazy: [live] extra
        except ImportError as e:
            raise RuntimeError("pip install 'memebot[live]' for live mode") from e
        self._keypair = Keypair.from_base58_string(key)
        self.pubkey = str(self._keypair.pubkey())
        self.jup = jup
        self.rpc = rpc
        self.slippage_bps = slippage_bps
        self.priority_lamports = priority_lamports
        self.wallet_min_sol = wallet_min_sol
        log.info("live executor armed for wallet %s...%s",
                 self.pubkey[:4], self.pubkey[-4:])

    # -- internals -----------------------------------------------------------

    def _sign_and_send(self, swap_tx_b64: str) -> str | None:
        from solders.transaction import VersionedTransaction
        raw = base64.b64decode(swap_tx_b64)
        tx = VersionedTransaction.from_bytes(raw)
        signed = VersionedTransaction(tx.message, [self._keypair])
        b64 = base64.b64encode(bytes(signed)).decode()
        res = self.rpc.call("sendTransaction", [
            b64, {"encoding": "base64", "skipPreflight": False,
                  "maxRetries": 3},
        ])
        return res if isinstance(res, str) else None

    def _confirm(self, sig: str, timeout_s: float = 45.0) -> str:
        """Returns 'landed', 'failed', or 'unknown' (timeout — may still land)."""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            res = self.rpc.call("getSignatureStatuses", [[sig]])
            st = ((res or {}).get("value") or [None])[0]
            if st:
                if st.get("err"):
                    log.warning("tx %s failed: %s", sig, st["err"])
                    return "failed"
                if st.get("confirmationStatus") in ("confirmed", "finalized"):
                    return "landed"
            time.sleep(2)
        log.warning("tx %s not confirmed in %.0fs (may still land)", sig, timeout_s)
        return "unknown"

    def _swap(self, input_mint: str, output_mint: str,
              amount_raw: int) -> tuple[str | None, str]:
        quote = self.jup.quote(input_mint, output_mint, amount_raw,
                               self.slippage_bps)
        if not quote or not quote.get("outAmount"):
            return None, "failed"
        tx = self.jup.build_swap_tx(quote, self.pubkey, self.priority_lamports)
        if not tx:
            return None, "failed"
        sig = self._sign_and_send(tx)
        if not sig:
            return None, "failed"
        return sig, self._confirm(sig)

    def _read_token(self, mint: str, retries: int = 4) -> int | None:
        for _ in range(retries):
            v = self.rpc.token_balance(self.pubkey, mint)
            if v is not None:
                return v
            time.sleep(3)
        return None

    def _read_sol(self, retries: int = 4) -> int | None:
        for _ in range(retries):
            v = self.rpc.sol_balance_lamports(self.pubkey)
            if v is not None:
                return v
            time.sleep(3)
        return None

    # -- public --------------------------------------------------------------

    def buy(self, mint: str, usd: float, ref_price: float,
            reserve_usd: float | None, sol_price_usd: float,
            token_decimals: int = 6) -> ExecutionReport:
        lamports = int(usd / max(sol_price_usd, 1e-9) * 1e9)
        sol_before = self._read_sol()
        before = self._read_token(mint)
        if before is None or sol_before is None:
            return ExecutionReport(False, "buy", mint, 0, 0, 0,
                                   "balance unreadable — refusing to trade")
        # never spend into the fee reserve: exits must always be payable
        if sol_before - lamports < self.wallet_min_sol * 1e9:
            return ExecutionReport(False, "buy", mint, 0, 0, 0,
                                   "would breach wallet SOL fee reserve")
        sig, status = self._swap(SOL_MINT, mint, lamports)
        if status == "failed":
            return ExecutionReport(False, "buy", mint, 0, 0, 0, "swap failed")
        # 'landed' or 'unknown': the balance diff is the ground truth either
        # way (an unknown tx that landed shows up here; one that expired
        # doesn't)
        if status == "unknown":
            time.sleep(10)
        after = self._read_token(mint)
        if after is None:
            return ExecutionReport(False, "buy", mint, 0, 0, 0,
                                   "POST-BUY BALANCE UNREADABLE — possible "
                                   "orphan position, reconcile manually",
                                   sig)
        got_raw = max(0, after - before)
        tokens = got_raw / 10 ** token_decimals
        price = usd / tokens if tokens > 0 else 0.0
        return ExecutionReport(tokens > 0, "buy", mint, tokens, usd, price,
                               f"live:{status}", sig)

    def sell(self, mint: str, tokens: float, ref_price: float,
             reserve_usd: float | None, sol_price_usd: float,
             token_decimals: int = 6, stressed: bool = False,
             sell_all: bool = False) -> ExecutionReport:
        if sell_all:
            # sell the actual on-chain balance — float reconstruction of raw
            # units can exceed the true balance and fail simulation forever
            live_raw = self._read_token(mint)
            if live_raw is None:
                return ExecutionReport(False, "sell", mint, 0, 0, 0,
                                       "balance unreadable — refusing to trade")
            amount_raw = live_raw
        else:
            amount_raw = int(tokens * 10 ** token_decimals)
        if amount_raw <= 0:
            # nothing on chain to sell: the position is already flat
            return ExecutionReport(True, "sell", mint, tokens, 0.0, 0.0,
                                   "no balance on chain (already flat)")
        before = self._read_sol()
        if before is None:
            return ExecutionReport(False, "sell", mint, 0, 0, 0,
                                   "balance unreadable — refusing to trade")
        sig, status = self._swap(mint, SOL_MINT, amount_raw)
        if status == "failed":
            return ExecutionReport(False, "sell", mint, 0, 0, 0, "swap failed")
        if status == "unknown":
            time.sleep(10)
        after = self._read_sol()
        sold_tokens = amount_raw / 10 ** token_decimals
        if after is None:
            # tx (probably) landed but proceeds unreadable: book a
            # conservative estimate rather than the whole wallet or zero
            est = max(0.0, sold_tokens * ref_price * 0.95)
            log.error("post-sell SOL balance unreadable; booking estimate "
                      "$%.2f for %s", est, mint)
            return ExecutionReport(True, "sell", mint, sold_tokens, est,
                                   ref_price * 0.95,
                                   "proceeds estimated (rpc failure)", sig)
        delta = after - before
        if status == "unknown" and delta <= 0:
            # timed out AND no proceeds visible: genuinely unknown — report
            # failure but with a marker so the caller re-reads balances
            # before retrying (sell_all retries are safe by construction)
            return ExecutionReport(False, "sell", mint, 0, 0, 0,
                                   "unconfirmed — recheck before retry", sig)
        usd = max(0.0, delta) / 1e9 * sol_price_usd
        price = usd / sold_tokens if sold_tokens > 0 else 0.0
        # a confirmed sell with ~zero net proceeds (fees ate a dust exit)
        # still closes the position: ok reflects execution, not P&L
        return ExecutionReport(True, "sell", mint, sold_tokens, usd, price,
                               f"live:{status}", sig)

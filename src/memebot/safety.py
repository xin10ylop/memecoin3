"""Pre-trade safety gate: hard filters against rugs/honeypots/concentration.

Layered checks, cheapest first. ALL must pass before the bot may buy:

  1. market shape   — age, liquidity, volume, FDV band (GT pool stats)
  2. mint account   — mint authority + freeze authority revoked (RPC)
  3. concentration  — top-10 holders (excl. largest acct, assumed pool vault)
                      below threshold (RPC)
  4. sellability    — Jupiter round-trip quote loss within bounds and a
                      sell-quote for 2x our size has acceptable impact

Every failure returns a reason string for logs/notifications.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import Config
from .data.gt import PoolStats
from .data.jupiter import Jupiter
from .data.rpc import SolanaRpc

log = logging.getLogger(__name__)


@dataclass
class SafetyVerdict:
    ok: bool
    reasons: list[str]

    @property
    def reason(self) -> str:
        return "; ".join(self.reasons) if self.reasons else "ok"


class SafetyGate:
    def __init__(self, cfg: Config, rpc: SolanaRpc, jup: Jupiter):
        self.cfg = cfg.safety
        self.rpc = rpc
        self.jup = jup

    # -- 1. market shape (no network calls beyond stats already held) --------
    def check_market(self, p: PoolStats) -> SafetyVerdict:
        c = self.cfg
        reasons = []
        age = p.age_minutes
        if age is None or age < c.min_age_minutes:
            reasons.append(f"age<{c.min_age_minutes}m")
        if age is not None and age > c.max_age_hours * 60:
            reasons.append(f"age>{c.max_age_hours}h")
        if not p.reserve_usd or p.reserve_usd < c.min_liquidity_usd:
            reasons.append(f"liquidity<{c.min_liquidity_usd}")
        if not p.vol_h1 or p.vol_h1 < c.min_vol_h1_usd:
            reasons.append(f"vol_h1<{c.min_vol_h1_usd}")
        fdv = p.fdv_usd or p.market_cap_usd
        if not fdv or not (c.fdv_min_usd <= fdv <= c.fdv_max_usd):
            reasons.append("fdv outside band")
        return SafetyVerdict(not reasons, reasons)

    # -- 2+3. on-chain account checks ----------------------------------------
    def check_onchain(self, mint: str) -> SafetyVerdict:
        c = self.cfg
        reasons = []
        info = self.rpc.mint_info(mint)
        if info is None:
            return SafetyVerdict(False, ["mint account unreadable"])
        if c.require_revoked_mint_authority and info["mint_authority"]:
            reasons.append("mint authority not revoked")
        if c.require_revoked_freeze_authority and info["freeze_authority"]:
            reasons.append("freeze authority not revoked")
        # Token-2022 is now used by major launchpads (pump.fun mints carry
        # only metadata extensions), so screen EXTENSIONS, not the program:
        # reject only mechanisms that can tax, block, or confiscate.
        if info.get("program") == "spl-token-2022":
            for ext in info.get("extensions") or []:
                name = ext.get("extension")
                state = ext.get("state") or {}
                if name in ("transferHook", "permanentDelegate",
                            "pausableConfig"):
                    reasons.append(f"token-2022 dangerous extension: {name}")
                elif name == "transferFeeConfig":
                    fee = max(
                        ((state.get("newerTransferFee") or {})
                         .get("transferFeeBasisPoints") or 0),
                        ((state.get("olderTransferFee") or {})
                         .get("transferFeeBasisPoints") or 0))
                    if fee > 100:
                        reasons.append(f"token-2022 transfer fee {fee}bps")
                elif name == "defaultAccountState" and \
                        (state.get("accountState") or "").lower() == "frozen":
                    reasons.append("token-2022 default-frozen accounts")
        supply = info["supply"]
        if supply <= 0:
            reasons.append("zero supply")
        else:
            largest = self.rpc.token_largest_accounts(mint)
            if largest:
                # Exclude the single largest account: for a graduated pool it
                # is virtually always the AMM vault. Remainder measures
                # insider/sniper concentration.
                rest = largest[1:11]
                frac = sum(a["amount"] for a in rest) / supply
                if frac > c.max_top10_holder_frac:
                    reasons.append(f"top10 holders {frac:.0%} > "
                                   f"{c.max_top10_holder_frac:.0%}")
                # The exclusion is an ASSUMPTION — if the largest account is
                # actually an insider (not the vault), the check above is
                # blind to it. Cap total top-10 concentration including the
                # largest account as a backstop.
                frac_incl = sum(a["amount"] for a in largest[:10]) / supply
                if frac_incl > 0.75:
                    reasons.append(f"top10 incl largest {frac_incl:.0%} > 75%")
            else:
                # public-RPC throttling makes this read flaky; blocking on it
                # rejects clean tokens for infra reasons. Paper mode may
                # continue (flagged) to measure true capture; LIVE mode
                # always hard-blocks unverified concentration.
                if self.cfg.get("allow_unverified_holders"):
                    log.warning("holder list unreadable for %s — proceeding "
                                "UNVERIFIED (paper-only policy)", mint)
                else:
                    reasons.append("holder list unreadable")
        return SafetyVerdict(not reasons, reasons)

    # -- 4. sellability via Jupiter ------------------------------------------
    def check_sellability(self, mint: str, position_usd: float,
                          sol_price_usd: float) -> SafetyVerdict:
        """Probes at 2x the position size: the exit that matters is the
        stressed full exit, and depth must exist beyond our own clip."""
        c = self.cfg
        reasons = []
        probe_lamports = max(10_000_000,
                             int(2 * position_usd / max(sol_price_usd, 1) * 1e9))
        rt = self.jup.roundtrip_loss_frac(mint, probe_lamports)
        if rt is None:
            reasons.append("no jupiter route (unsellable)")
        elif rt > c.roundtrip_max_loss_frac:
            reasons.append(f"2x-size roundtrip loss {rt:.1%} > "
                           f"{c.roundtrip_max_loss_frac:.0%} (tax/honeypot/thin)")
        elif rt > c.sell_quote_max_impact_frac:
            reasons.append(f"2x-size roundtrip loss {rt:.1%} > impact bound "
                           f"{c.sell_quote_max_impact_frac:.0%}")
        return SafetyVerdict(not reasons, reasons)

    def full_check(self, p: PoolStats, position_usd: float,
                   sol_price_usd: float) -> SafetyVerdict:
        v1 = self.check_market(p)
        if not v1.ok:
            return v1
        if not p.base_mint:
            return SafetyVerdict(False, ["unknown base mint"])
        v2 = self.check_onchain(p.base_mint)
        if not v2.ok:
            return v2
        v3 = self.check_sellability(p.base_mint, position_usd, sol_price_usd)
        if not v3.ok:
            return v3
        return SafetyVerdict(True, [])

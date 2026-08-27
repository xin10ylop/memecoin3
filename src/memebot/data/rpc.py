"""Solana JSON-RPC helpers for on-chain safety checks.

Uses the public mainnet endpoint by default (heavily rate limited, fine for
occasional safety checks). Set MEMEBOT_RPC_URL for a private RPC.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from .http import HttpClient

log = logging.getLogger(__name__)

DEFAULT_RPC = "https://api.mainnet-beta.solana.com"


class SolanaRpc:
    def __init__(self, url: str | None = None, per_min: float = 30.0):
        self.url = url or os.environ.get("MEMEBOT_RPC_URL") or DEFAULT_RPC
        self.http = HttpClient(per_min=per_min)
        self._id = 0

    def call(self, method: str, params: list) -> Any | None:
        self._id += 1
        data = self.http.post_json(self.url, {
            "jsonrpc": "2.0", "id": self._id, "method": method, "params": params,
        })
        if data is None:
            return None
        if "error" in data:
            log.warning("rpc %s error: %s", method, data["error"])
            return None
        return data.get("result")

    # ---- token safety primitives -------------------------------------------

    def mint_info(self, mint: str) -> dict | None:
        """Returns {mint_authority, freeze_authority, supply, decimals} or None."""
        res = self.call("getAccountInfo", [mint, {"encoding": "jsonParsed"}])
        info = ((((res or {}).get("value") or {}).get("data") or {})
                .get("parsed") or {}).get("info")
        if not info:
            return None
        return {
            "mint_authority": info.get("mintAuthority"),
            "freeze_authority": info.get("freezeAuthority"),
            "supply": int(info.get("supply") or 0),
            "decimals": int(info.get("decimals") or 0),
        }

    def token_largest_accounts(self, mint: str) -> list[dict]:
        """[{address, amount(int), uiAmount}] descending."""
        res = self.call("getTokenLargestAccounts", [mint])
        out = []
        for v in (res or {}).get("value") or []:
            try:
                out.append({"address": v["address"], "amount": int(v["amount"]),
                            "ui_amount": v.get("uiAmount")})
            except (KeyError, TypeError, ValueError):
                continue
        return out

    def token_supply(self, mint: str) -> int | None:
        res = self.call("getTokenSupply", [mint])
        try:
            return int(res["value"]["amount"])
        except (KeyError, TypeError, ValueError):
            return None

    def sol_balance_lamports(self, pubkey: str) -> int | None:
        res = self.call("getBalance", [pubkey])
        try:
            return int(res["value"])
        except (KeyError, TypeError, ValueError):
            return None

    def token_balance(self, owner: str, mint: str) -> int:
        """Sum of base units across the owner's token accounts for mint."""
        res = self.call("getTokenAccountsByOwner",
                        [owner, {"mint": mint}, {"encoding": "jsonParsed"}])
        total = 0
        for acc in (res or {}).get("value") or []:
            try:
                amt = acc["account"]["data"]["parsed"]["info"]["tokenAmount"]["amount"]
                total += int(amt)
            except (KeyError, TypeError, ValueError):
                continue
        return total

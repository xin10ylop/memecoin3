"""DexScreener public API (free; ~300 req/min for pair endpoints).

Used for: cross-checking liquidity/volume, socials/profile presence, and the
paid-promotion feeds (token-profiles, token-boosts) as attention proxies.
"""
from __future__ import annotations

from typing import Any

from .http import HttpClient

BASE = "https://api.dexscreener.com"


class DexScreener:
    def __init__(self, per_min: float = 120.0):
        self.http = HttpClient(per_min=per_min)

    def token_pairs(self, mint: str) -> list[dict]:
        data = self.http.get_json(f"{BASE}/token-pairs/v1/solana/{mint}")
        return data if isinstance(data, list) else []

    def pair(self, pair_address: str) -> dict | None:
        data = self.http.get_json(f"{BASE}/latest/dex/pairs/solana/{pair_address}")
        pairs = (data or {}).get("pairs") or []
        return pairs[0] if pairs else None

    def latest_token_profiles(self) -> list[dict]:
        data = self.http.get_json(f"{BASE}/token-profiles/latest/v1")
        return data if isinstance(data, list) else []

    def latest_boosts(self) -> list[dict]:
        data = self.http.get_json(f"{BASE}/token-boosts/latest/v1")
        return data if isinstance(data, list) else []

    @staticmethod
    def best_solana_pair(pairs: list[dict]) -> dict | None:
        """Highest-liquidity Solana pair for a token."""
        sol = [p for p in pairs if p.get("chainId") == "solana"]
        if not sol:
            return None
        return max(sol, key=lambda p: ((p.get("liquidity") or {}).get("usd") or 0))

    @staticmethod
    def has_socials(pair: dict) -> bool:
        info = pair.get("info") or {}
        return bool(info.get("socials") or info.get("websites"))

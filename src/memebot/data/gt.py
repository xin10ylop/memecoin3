"""GeckoTerminal API v2 client (free, no key; ~30 calls/min).

Endpoints used:
  /networks/solana/new_pools            newest indexed pools (pages 1..10)
  /networks/solana/trending_pools       trending by recent activity
  /networks/solana/pools/{addr}         single pool live stats
  /networks/solana/pools/{addr}/ohlcv/{tf}   minute/hour/day bars
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .http import HttpClient

BASE = "https://api.geckoterminal.com/api/v2"


def _f(x: Any) -> float | None:
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


def parse_iso_ts(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


@dataclass
class PoolStats:
    address: str
    base_mint: str | None
    symbol: str | None
    name: str | None
    dex_id: str | None
    created_ts: int | None
    price_usd: float | None
    reserve_usd: float | None
    fdv_usd: float | None
    market_cap_usd: float | None
    vol_m5: float | None
    vol_h1: float | None
    vol_h24: float | None
    buys_m5: int | None
    sells_m5: int | None
    buyers_m5: int | None
    sellers_m5: int | None
    price_change_m5: float | None
    price_change_h1: float | None
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def age_minutes(self) -> float | None:
        if self.created_ts is None:
            return None
        return (datetime.now(timezone.utc).timestamp() - self.created_ts) / 60.0


def _parse_pool(item: dict, tokens: dict[str, dict]) -> PoolStats:
    a = item.get("attributes", {}) or {}
    rel = item.get("relationships", {}) or {}
    bt_id = (((rel.get("base_token") or {}).get("data") or {}).get("id")) or ""
    base_mint = bt_id.split("_", 1)[1] if "_" in bt_id else None
    tok = tokens.get(bt_id, {})
    vol = a.get("volume_usd") or {}
    tx = (a.get("transactions") or {}).get("m5") or {}
    pc = a.get("price_change_percentage") or {}
    return PoolStats(
        address=a.get("address"),
        base_mint=base_mint,
        symbol=tok.get("symbol"),
        name=tok.get("name"),
        dex_id=(((rel.get("dex") or {}).get("data") or {}).get("id")),
        created_ts=parse_iso_ts(a.get("pool_created_at")),
        price_usd=_f(a.get("base_token_price_usd")),
        reserve_usd=_f(a.get("reserve_in_usd")),
        fdv_usd=_f(a.get("fdv_usd")),
        market_cap_usd=_f(a.get("market_cap_usd")),
        vol_m5=_f(vol.get("m5")),
        vol_h1=_f(vol.get("h1")),
        vol_h24=_f(vol.get("h24")),
        buys_m5=tx.get("buys"),
        sells_m5=tx.get("sells"),
        buyers_m5=tx.get("buyers"),
        sellers_m5=tx.get("sellers"),
        price_change_m5=_f(pc.get("m5")),
        price_change_h1=_f(pc.get("h1")),
        raw=a,
    )


class GeckoTerminal:
    def __init__(self, per_min: float = 25.0):
        self.http = HttpClient(per_min=per_min)

    def _pools_call(self, path: str, params: dict | None = None) -> list[PoolStats]:
        params = dict(params or {})
        params.setdefault("include", "base_token")
        data = self.http.get_json(f"{BASE}{path}", params)
        if not data or "data" not in data:
            return []
        tokens = {inc["id"]: inc.get("attributes", {})
                  for inc in (data.get("included") or []) if inc.get("type") == "token"}
        out = []
        for item in data["data"]:
            p = _parse_pool(item, tokens)
            if p.address:
                out.append(p)
        return out

    def new_pools(self, page: int = 1) -> list[PoolStats]:
        return self._pools_call("/networks/solana/new_pools", {"page": page})

    def trending_pools(self, page: int = 1) -> list[PoolStats]:
        return self._pools_call("/networks/solana/trending_pools", {"page": page})

    def pool(self, address: str) -> PoolStats | None:
        got = self._pools_call(f"/networks/solana/pools/{address}")
        return got[0] if got else None

    def ohlcv(self, address: str, timeframe: str = "minute", aggregate: int = 1,
              limit: int = 1000, before_timestamp: int | None = None) -> list[list]:
        """Returns bars [[ts,o,h,l,c,vol_usd], ...] oldest->newest."""
        params: dict = {"aggregate": aggregate, "limit": limit,
                        "currency": "usd", "token": "base"}
        if before_timestamp:
            params["before_timestamp"] = before_timestamp
        data = self.http.get_json(
            f"{BASE}/networks/solana/pools/{address}/ohlcv/{timeframe}", params)
        bars = (((data or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
        return sorted((b for b in bars if isinstance(b, list) and len(b) >= 6),
                      key=lambda b: b[0])

    def token_pools(self, mint: str) -> list[PoolStats]:
        """Every pool trading this token, best-capitalised first.

        A token minutes old typically lives in more than one pool (a bonding
        curve and a fresh AMM). An aggregator can quote a sell through the
        empty one and report a near-total loss on a token whose real pool is
        healthy — so an implausible price must be checked against the pools
        that actually exist before it is allowed to close a position.
        """
        pools = self._pools_call(f"/networks/solana/tokens/{mint}/pools")
        return sorted(pools, key=lambda p: p.reserve_usd or 0.0, reverse=True)

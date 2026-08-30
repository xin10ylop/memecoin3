"""Helius parsed-transaction access: real per-minute swap VOLUME.

The scalper first approximated a launch's momentum by counting
transactions, because counting signatures is cheap. Measured against the
quantity the backtest actually validated -- minute-2/minute-1 USD volume --
that proxy holds up badly: rank correlation +0.21, and the two rules agree
on 63% of pools against a ~56% chance baseline. Similar thresholds, almost
unrelated selections. A filter that picks different launches than the one
that was validated is simply a different filter.

Helius returns swaps already parsed, with timestamps and SOL amounts, so
the validated quantity can be measured directly instead of proxied.
"""
from __future__ import annotations

import logging
import os
import re

from .http import HttpClient

log = logging.getLogger(__name__)

BASE = "https://api.helius.xyz/v0"


def api_key_from_rpc_url(url: str | None = None) -> str | None:
    """The RPC URL already carries the key; no second secret to configure."""
    u = url or os.environ.get("MEMEBOT_RPC_URL") or ""
    m = re.search(r"api-key=([\w-]+)", u)
    return m.group(1) if m else None


class Helius:
    def __init__(self, api_key: str | None = None, per_min: float = 120.0):
        self.key = api_key or api_key_from_rpc_url()
        self.http = HttpClient(per_min=per_min)

    @property
    def available(self) -> bool:
        return bool(self.key)

    def transactions(self, address: str, limit: int = 100,
                     before: str | None = None) -> list:
        if not self.key:
            return []
        params = {"api-key": self.key, "limit": int(limit)}
        if before:
            params["before"] = before
        out = self.http.get_json(f"{BASE}/addresses/{address}/transactions",
                                 params=params)
        return out if isinstance(out, list) else []

    def swap_volume_per_minute(self, address: str,
                               since_ts: float | None = None,
                               max_pages: int = 12) -> list[float]:
        """SOL volume per minute since the first swap seen, oldest first.

        Paging matters more than it looks. At 100 transactions per page a
        BUSY launch -- hundreds of swaps in its first two minutes -- is
        exactly the one a short window fails to reach back through, so a
        low page cap silently blinds the filter to the most active
        launches, which are the ones most worth judging. Live journalling
        caught this: 16 of 21 range-qualifying candidates returned no
        opinion at 3 pages.

        Each swap is valued at its largest native transfer, which is the
        SOL leg of the trade; summing every transfer would double-count
        routing hops and fees. SOL rather than USD is deliberate -- the
        ratio is taken over two adjacent minutes, so the SOL price cancels
        and no price lookup can go stale between them.
        """
        txs, before = [], None
        for _ in range(max_pages):
            page = self.transactions(address, limit=100, before=before)
            if not page:
                break
            txs.extend(page)
            before = page[-1].get("signature")
            oldest = min((t.get("timestamp") or 0) for t in page)
            if since_ts is not None and oldest <= since_ts + 20:
                break                      # reached the launch, stop paging
        swaps = [t for t in txs
                 if t.get("type") == "SWAP" and t.get("timestamp")]
        if not swaps:
            return []
        times = [t["timestamp"] for t in swaps]
        # Same discipline as the signature counter: if the window never
        # reached the launch, the first bucket is a partial minute and any
        # ratio from it is fiction. No opinion beats a wrong one.
        truncated = since_ts is not None and min(times) > since_ts + 20
        t0 = min(times)
        buckets: dict[int, float] = {}
        for t in swaps:
            lamports = max((n.get("amount") or 0)
                           for n in (t.get("nativeTransfers") or [])) \
                if t.get("nativeTransfers") else 0
            idx = int((t["timestamp"] - t0) // 60)
            buckets[idx] = buckets.get(idx, 0.0) + lamports / 1e9
        out = [buckets.get(i, 0.0) for i in range(max(buckets) + 1)]
        if truncated:
            # The window missed the start, so bucket 0 holds only PART of
            # minute one and the ratio built on it is overstated. That is
            # still enough to reject: the true first minute can only be
            # larger, so a ratio already below the floor is genuinely
            # below it. Only an apparent PASS is unsafe, and that is
            # withheld.
            if len(out) >= 2 and out[0] > 0 and out[1] / out[0] < 1.0:
                return out
            return []
        return out

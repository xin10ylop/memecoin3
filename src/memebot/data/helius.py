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
import time
import re

from .http import HttpClient

log = logging.getLogger(__name__)

BASE = "https://api.helius.xyz/v0"


def api_key_from_rpc_url(url: str | None = None) -> str | None:
    """The RPC URL already carries the key; no second secret to configure."""
    u = url or os.environ.get("MEMEBOT_RPC_URL") or ""
    m = re.search(r"api-key=([\w-]+)", u)
    return m.group(1) if m else None


# A hard ceiling on billed calls, enforced here rather than trusted to
# callers. A websocket firehose consumed a million credits in under a day
# and nothing in the code objected, because nothing was counting. Expected
# steady-state use is roughly 20 calls an hour, so this leaves ~10x headroom
# and still bounds a runaway to a few thousand a day instead of millions.
MAX_CALLS_PER_HOUR = int(os.environ.get("MEMEBOT_HELIUS_HOURLY_CAP", "200"))


class Helius:
    def __init__(self, api_key: str | None = None, per_min: float = 120.0):
        self.key = api_key or api_key_from_rpc_url()
        self.http = HttpClient(per_min=per_min)
        self._calls: list[float] = []
        self._warned = False

    def _budget_ok(self) -> bool:
        """False once the hourly cap is spent, so a bug cannot bankrupt the
        key. Refusing to answer is always safer than answering expensively:
        a missing acceleration reading skips a candidate, it never invents
        one."""
        now = time.time()
        self._calls = [t for t in self._calls if now - t < 3600]
        if len(self._calls) >= MAX_CALLS_PER_HOUR:
            if not self._warned:
                log.error("Helius hourly cap reached (%d calls) — skipping "
                          "paid lookups until the window clears. Raise "
                          "MEMEBOT_HELIUS_HOURLY_CAP only if this is "
                          "expected.", MAX_CALLS_PER_HOUR)
                self._warned = True
            return False
        self._warned = False
        self._calls.append(now)
        return True

    @property
    def available(self) -> bool:
        return bool(self.key)

    def transactions(self, address: str, limit: int = 100,
                     before: str | None = None) -> list:
        if not self.key or not self._budget_ok():
            return []
        params = {"api-key": self.key, "limit": int(limit)}
        if before:
            params["before"] = before
        out = self.http.get_json(f"{BASE}/addresses/{address}/transactions",
                                 params=params)
        return out if isinstance(out, list) else []

    def swaps_since(self, address: str, since_ts: float | None = None,
                    max_pages: int = 6) -> tuple[list, bool]:
        """Page back to the launch once, returning (swaps, truncated).

        Volume and buyer breadth both need the same transactions, and each
        used to page for them separately -- up to 24 HTTP calls to answer
        one question about one candidate, blocking the trading loop while
        new launches expired unseen. Fetch once, derive both.
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
                break
        swaps = [t for t in txs
                 if t.get("type") == "SWAP" and t.get("timestamp")]
        if not swaps:
            return [], False
        truncated = (since_ts is not None
                     and min(t["timestamp"] for t in swaps) > since_ts + 20)
        return swaps, truncated

    @staticmethod
    def volume_buckets(swaps: list, anchor_ts: float | None = None,
                       min_buckets: int = 0) -> list[float]:
        """SOL per minute, oldest minute first.

        anchor_ts fixes where minute one BEGINS. Without it the first bucket
        starts at whichever swap happened to be fetched first, which is not
        the same window the backtest measured: bars are fixed minute
        windows, and a minute with no trades is zero volume, not absent
        data.

        That distinction decided real trades. A launch that traded hard in
        its first minute and went silent in its second returned a SINGLE
        bucket, so the ratio could not be computed and the candidate was
        skipped as "no opinion" -- when the honest reading is a ratio of
        zero: all the buyers left. Anchoring on detection and padding to
        min_buckets turns that silence back into the evidence it is.
        """
        if not swaps:
            return []
        times = [t["timestamp"] for t in swaps]
        t0 = anchor_ts if anchor_ts is not None else min(times)
        buckets: dict[int, float] = {}
        for t in swaps:
            idx = int((t["timestamp"] - t0) // 60)
            if idx < 0:
                continue            # predates the window we are measuring
            lamports = max((n.get("amount") or 0)
                           for n in (t.get("nativeTransfers") or [])) \
                if t.get("nativeTransfers") else 0
            buckets[idx] = buckets.get(idx, 0.0) + lamports / 1e9
        high = max(max(buckets) + 1 if buckets else 0, min_buckets)
        return [buckets.get(i, 0.0) for i in range(high)]

    @staticmethod
    def buyer_buckets(swaps: list, mint: str,
                      anchor_ts: float | None = None,
                      min_buckets: int = 0) -> list[int]:
        """Distinct buyer wallets per minute, on the same fixed windows."""
        if not swaps:
            return []
        times = [t["timestamp"] for t in swaps]
        t0 = anchor_ts if anchor_ts is not None else min(times)
        buckets: dict[int, set] = {}
        for t in swaps:
            idx = int((t["timestamp"] - t0) // 60)
            if idx < 0:
                continue
            who = buckets.setdefault(idx, set())
            for tr in (t.get("tokenTransfers") or []):
                if tr.get("mint") == mint and tr.get("toUserAccount"):
                    who.add(tr["toUserAccount"])
        high = max(max(buckets) + 1 if buckets else 0, min_buckets)
        return [len(buckets.get(i, set())) for i in range(high)]

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

    def buyers_per_minute(self, address: str, since_ts: float | None = None,
                          max_pages: int = 12) -> list[set]:
        """Distinct BUYER wallets per minute since the first swap, oldest first.

        Volume answers how many dollars arrived; it cannot tell fifty
        people buying from two bots trading with each other. Breadth is the
        harder quantity to fake, and it is free here -- every parsed swap
        already carries its wallet, so this reuses the call the volume
        feature makes.

        A buyer is a wallet that RECEIVED the token in the swap; the wallet
        sending SOL and receiving nothing is a seller.
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
                break
        swaps = [t for t in txs
                 if t.get("type") == "SWAP" and t.get("timestamp")]
        if not swaps:
            return []
        times = [t["timestamp"] for t in swaps]
        if since_ts is not None and min(times) > since_ts + 20:
            return []
        t0 = min(times)
        buckets: dict[int, set] = {}
        for t in swaps:
            idx = int((t["timestamp"] - t0) // 60)
            who = buckets.setdefault(idx, set())
            for tr in (t.get("tokenTransfers") or []):
                if tr.get("mint") == address and tr.get("toUserAccount"):
                    who.add(tr["toUserAccount"])
        return [buckets.get(i, set()) for i in range(max(buckets) + 1)]

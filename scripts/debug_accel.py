#!/usr/bin/env python3
"""Trace the acceleration path end to end on live candidates.

330 portal candidates produced zero acceleration readings, with the credit
cap untouched, the journal healthy and the key working. That rules out
every cheap explanation, so this instruments each step and prints where the
value is lost instead of inferring it.
"""
from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, "src")
from memebot.data.helius import Helius, api_key_from_rpc_url  # noqa: E402
from memebot.live.portalfeed import PortalLaunchFeed  # noqa: E402

import asyncio  # noqa: E402


def main() -> int:
    print("1. KEY")
    key = api_key_from_rpc_url()
    print(f"   parsed from MEMEBOT_RPC_URL: {'yes' if key else 'NO'}")
    h = Helius()
    print(f"   Helius.available: {h.available}")
    if not h.available:
        print("   -> acceleration always returns None. This is the cause.")
        return 1

    print("\n2. CATCH A LIVE MIGRATION (up to 90s)")
    feed = PortalLaunchFeed()
    feed.start()
    deadline = time.time() + 90
    while time.time() < deadline and not feed.events:
        time.sleep(2)
    if not feed.events:
        print("   no migration seen in 90s — try again")
        return 1
    ev = list(feed.events)[0]
    mint, since = ev.mint, ev.detected_ts
    print(f"   mint {mint}")

    print("\n3. WAIT 2 MINUTES, as the scalper does before deciding")
    time.sleep(125)

    print("\n4. FETCH SWAPS (what acceleration() calls)")
    t0 = time.time()
    swaps, truncated = h.swaps_since(mint, since_ts=since)
    print(f"   swaps returned : {len(swaps)}")
    print(f"   truncated      : {truncated}")
    print(f"   took           : {time.time()-t0:.1f}s")
    if swaps:
        ts = [s['timestamp'] for s in swaps]
        print(f"   oldest swap is {since - min(ts):.0f}s BEFORE detection")
        print(f"   newest swap is {max(ts) - since:.0f}s after detection")
    if truncated:
        print("   -> TRUNCATED: the window never reached the launch, so the")
        print("      guard withholds a reading. With detection at MIGRATION,")
        print("      the mint already has a long bonding-curve history, and")
        print("      6 pages of 100 cannot page back through it.")

    print("\n5. BUCKETS")
    v = h.volume_buckets(swaps)
    print(f"   volume per minute: {[round(x,3) for x in v[:6]]}")
    if len(v) >= 2 and v[0] > 0:
        print(f"   ratio v[1]/v[0] = {v[1]/v[0]:.2f}")
    else:
        print("   -> fewer than 2 buckets or an empty first minute:")
        print("      acceleration returns None here.")

    print("\n6. WHAT THE SCALPER WOULD RECORD")
    final = None
    if not truncated and len(v) >= 2 and v[0] > 0:
        final = v[1] / v[0]
    print(f"   accel = {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

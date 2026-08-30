"""The acceleration filter — the guard against buying the graveyard.

range>=17.2% alone measures -11.3%/trade on the full sample; requiring the
second minute to trade at least as much as the first turns it positive.
These lock the bucketing and the ratio, since an off-by-one in the minute
boundaries would silently disable the only filter that made the rule work.
"""
from memebot.data.rpc import SolanaRpc


class FakeRpc(SolanaRpc):
    def __init__(self, times):
        self._times = times

    def call(self, method, params):
        assert method == "getSignaturesForAddress"
        return [{"blockTime": t} for t in self._times]


def test_counts_bucket_by_minute_from_first_signature():
    # 3 in the first minute, 2 in the second, 1 in the third
    t = 1_700_000_000
    r = FakeRpc([t, t + 10, t + 59, t + 61, t + 119, t + 130])
    assert r.activity_per_minute("M") == [3, 2, 1]


def test_accelerating_and_dying_launches_are_distinguished():
    t = 1_700_000_000
    dying = FakeRpc([t, t + 1, t + 2, t + 3, t + 70])        # 4 then 1
    building = FakeRpc([t, t + 30, t + 61, t + 70, t + 80])  # 2 then 3
    d, b = dying.activity_per_minute("M"), building.activity_per_minute("M")
    assert d[1] / d[0] < 1.0
    assert b[1] / b[0] > 1.0


def test_no_signatures_yields_no_opinion():
    assert FakeRpc([]).activity_per_minute("M") == []


def test_out_of_order_signatures_still_bucket_correctly():
    # RPC returns newest-first; the counter must not depend on order
    t = 1_700_000_000
    r = FakeRpc([t + 130, t + 10, t + 61, t, t + 119, t + 59])
    assert r.activity_per_minute("M") == [3, 2, 1]


def test_silent_minute_counts_as_zero_not_missing():
    # a gap minute must not shift later minutes left, which would turn a
    # dead launch into an accelerating one
    t = 1_700_000_000
    r = FakeRpc([t, t + 5, t + 125])         # minute 1: 2, minute 2: 0, minute 3: 1
    assert r.activity_per_minute("M") == [2, 0, 1]


def test_frenzy_is_rejected_by_the_ceiling():
    """A 10x second minute must NOT pass: return is non-monotonic in
    acceleration and the extreme bucket is the worst one."""
    from memebot.live.scalper import MAX_ACCEL, MIN_ACCEL
    assert MIN_ACCEL <= 1.0 < MAX_ACCEL
    for ratio, ok in [(0.5, False), (1.0, True), (2.0, True),
                      (9.9, True), (10.0, False), (50.0, False)]:
        assert (MIN_ACCEL <= ratio < MAX_ACCEL) is ok


def test_truncated_history_yields_no_opinion_not_a_wrong_ratio():
    """If the signature window does not reach the launch, the first bucket
    is a partial minute and any ratio from it is fiction."""
    t = 1_700_000_000
    r = FakeRpc([t + 300, t + 360])          # history starts 5 min late
    assert r.activity_per_minute("M", since_ts=t) == []
    # ...but a window that does reach it is fine
    assert r.activity_per_minute("M", since_ts=t + 295) == [1, 1]


def test_truncated_window_can_still_reject_but_never_accept():
    """A window that missed the launch undercounts minute one, so the
    ratio is overstated. An overstated ratio BELOW the floor is decisive;
    one above it is not, and must be withheld."""
    from memebot.data.helius import Helius

    class FakeHelius(Helius):
        def __init__(self, txs):
            self.key = "k"
            self._txs = txs

        def transactions(self, address, limit=100, before=None):
            return self._txs if before is None else []

    t = 1_700_000_000
    def swap(ts, lamports):
        return {"type": "SWAP", "timestamp": ts, "signature": f"s{ts}",
                "nativeTransfers": [{"amount": lamports}]}

    # history starts 5 min late: truncated. Falling volume -> still rejectable
    falling = FakeHelius([swap(t + 300, 10_000), swap(t + 370, 1_000)])
    out = falling.swap_volume_per_minute("M", since_ts=t)
    assert out and out[1] / out[0] < 1.0

    # truncated but apparently RISING -> unsafe, withhold
    rising = FakeHelius([swap(t + 300, 1_000), swap(t + 370, 10_000)])
    assert rising.swap_volume_per_minute("M", since_ts=t) == []


def test_unroutable_token_with_a_live_pool_is_not_marked_to_zero():
    """An aggregator that cannot route a token has not proved it worthless.
    A live pool overrides the quote; a dead one does not."""
    from memebot.data.gt import PoolStats

    def pool(reserve, vol5, price):
        return PoolStats(address="p", base_mint="m", symbol="S", name="N",
                         dex_id="d", created_ts=0, price_usd=price,
                         reserve_usd=reserve, fdv_usd=None,
                         market_cap_usd=None, vol_m5=vol5, vol_h1=None,
                         vol_h24=None, buys_m5=None, sells_m5=None,
                         buyers_m5=None, sellers_m5=None,
                         price_change_m5=None, price_change_h1=None)

    class Fake:
        def __init__(self, pools):
            self._p = pools

        def token_pools(self, mint):
            return self._p

    class Scalp:
        pool_alive_price = None

    from memebot.live.scalper import RealtimeScalper
    obj = RealtimeScalper.__new__(RealtimeScalper)
    obj._pool_cache = {}

    obj.gt = Fake([pool(26_000, 5_000, 9.17e-05)])
    assert obj.pool_alive_price("m") == 9.17e-05          # alive -> use it

    obj._pool_cache.clear()
    obj.gt = Fake([pool(0.0, 0.0, 4.6e-08)])
    assert obj.pool_alive_price("m") is None              # dead -> real loss

    # A quiet pool with real reserves is still sellable: an AMM fills a
    # \$10 order whether or not anyone traded in the last five minutes.
    obj._pool_cache.clear()
    obj.gt = Fake([pool(23_670, 0.0, 1.53e-05)])
    assert obj.pool_alive_price("m") == 1.53e-05

    obj._pool_cache.clear()
    obj.gt = Fake([pool(200, 0.0, 1.0e-05)])              # too thin to trust
    assert obj.pool_alive_price("m") is None

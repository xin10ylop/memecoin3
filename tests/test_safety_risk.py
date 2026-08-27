import time
from types import SimpleNamespace

from memebot.config import load
from memebot.data.gt import PoolStats
from memebot.risk import OpenPosition, RiskManager
from memebot.safety import SafetyGate


class FakeRpc:
    def __init__(self, mint_auth=None, freeze_auth=None, supply=10_000,
                 largest=None):
        self._info = {"mint_authority": mint_auth, "freeze_authority": freeze_auth,
                      "supply": supply, "decimals": 6}
        self._largest = largest or []

    def mint_info(self, mint):
        return self._info

    def token_largest_accounts(self, mint):
        return self._largest


class FakeJup:
    def __init__(self, rt_loss=0.02):
        self._rt = rt_loss

    def roundtrip_loss_frac(self, mint, lamports):
        return self._rt


def make_stats(**kw):
    base = dict(address="POOL", base_mint="MINT", symbol="X", name="X",
                dex_id="pump-swap", created_ts=int(time.time()) - 7200,
                price_usd=0.001, reserve_usd=50_000, fdv_usd=1_000_000,
                market_cap_usd=1_000_000, vol_m5=5_000, vol_h1=60_000,
                vol_h24=100_000, buys_m5=20, sells_m5=10, buyers_m5=15,
                sellers_m5=8, price_change_m5=1.0, price_change_h1=5.0)
    base.update(kw)
    return PoolStats(**base)


def gate(rpc=None, jup=None):
    cfg = load()
    return SafetyGate(cfg, rpc or FakeRpc(), jup or FakeJup())


def test_market_check_passes_good_pool():
    assert gate().check_market(make_stats()).ok


def test_market_check_rejects_young_thin_pools():
    g = gate()
    assert not g.check_market(make_stats(created_ts=int(time.time()) - 60)).ok
    assert not g.check_market(make_stats(reserve_usd=500)).ok
    assert not g.check_market(make_stats(fdv_usd=5_000, market_cap_usd=5_000)).ok


def test_onchain_rejects_active_authorities():
    g = gate(rpc=FakeRpc(mint_auth="somebody"))
    assert not g.check_onchain("MINT").ok
    g = gate(rpc=FakeRpc(freeze_auth="somebody"))
    assert not g.check_onchain("MINT").ok


def test_onchain_rejects_concentration_excluding_pool_vault():
    largest = ([{"address": "vault", "amount": 5_000, "ui_amount": 5000}] +
               [{"address": f"w{i}", "amount": 500, "ui_amount": 500}
                for i in range(10)])
    g = gate(rpc=FakeRpc(largest=largest))          # rest = 5000/10000 = 50%
    assert not g.check_onchain("MINT").ok
    largest2 = ([{"address": "vault", "amount": 8_000, "ui_amount": 8000}] +
                [{"address": f"w{i}", "amount": 100, "ui_amount": 100}
                 for i in range(10)])                # rest = 1000/10000 = 10%
    g2 = gate(rpc=FakeRpc(largest=largest2))
    assert g2.check_onchain("MINT").ok


def test_sellability_rejects_honeypot():
    g = gate(jup=FakeJup(rt_loss=0.6))
    assert not g.check_sellability("MINT", 50, 100).ok
    g2 = gate(jup=FakeJup(rt_loss=None))
    assert not g2.check_sellability("MINT", 50, 100).ok
    g3 = gate(jup=FakeJup(rt_loss=0.03))
    assert g3.check_sellability("MINT", 50, 100).ok


# ------------------------------------------------------------------ risk

def test_risk_daily_halt_and_reset():
    cfg = load()
    rm = RiskManager(cfg)
    now = time.time()
    rm.record_realized(-1000.0, 1000.0)
    ok, why = rm.can_enter(now, {}, 1000.0, 50_000)
    assert not ok and "halted" in why
    rm.roll_day(now + 86400 * 2)
    ok, _ = rm.can_enter(now + 86400 * 2, {}, 1000.0, 50_000)
    assert ok


def test_risk_concurrency_and_sizing():
    cfg = load()
    rm = RiskManager(cfg)
    pos = {f"p{i}": OpenPosition(pool=f"p{i}", mint="m", symbol="s",
                                 entry_ts=0, entry_price=1, tokens=1,
                                 size_usd=25, hwm_price=1)
           for i in range(cfg.capital.max_concurrent)}
    ok, why = rm.can_enter(time.time(), pos, 1000.0, 50_000)
    assert not ok and "concurrent" in why
    # sizing respects pool share cap
    assert rm.position_size(1000.0, 1_000.0) <= 0.005 * 1_000.0 + 1e-9

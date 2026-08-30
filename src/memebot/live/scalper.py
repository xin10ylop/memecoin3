"""Realtime launch scalper — the validated signal, executable.

THE SIGNAL (research/harvest_grid.py, unbiased sample, out-of-sample
validated): in a pool's first ~2 minutes, if it traded in both minutes AND
the price moved at least ~17% (range, in EITHER direction — a vertical
pump predicts death, two-sided churn predicts the tail), then buying and
trailing 30% with a 30-minute cap returned:

    all trades      +41.6%  CI [+15.1%, +71.5%]   n=112
    resolved only   +46.5%  CI [+17.5%, +82.9%]
    harshest        +28.0%  CI [+0.8%,  +59.3%]
    out-of-sample   +45.0%  CI [+9.3%,  +88.0%]   (thresholds fit on the
                                                   earlier half only)
    drop top-5      +13.5%  — not carried by outliers
    win rate 30%, median negative: a fat-tail profile. Most trades lose a
    little; the mean lives in the winners. Sizing and trade count matter
    more than any single position.

WHY IT NEEDS THIS MODULE: the edge decays with latency (~+19% acted on
immediately, ~+11% at 2-3 min, ~0 by 5) and GeckoTerminal discovers pools
at a median 2.4 minutes old. So the signal is real but unreachable through
the normal feed. Helius streams creations in seconds, which is what makes
it executable at all.

Pipeline: Helius creation stream -> resolve signature to token mint ->
batch-poll Jupiter prices (one call covers every watched mint) -> compute
range/activity over the observation window -> safety gate -> paper or live
buy -> trail 30%, hard cap 30 minutes.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import numpy as np
import requests

from ..backtest.costs import CostModel
from ..config import Config, live_trading_armed
from ..data.jupiter import SOL_MINT, Jupiter
from ..data.gt import GeckoTerminal
from ..data.helius import Helius
from ..data.rpc import SolanaRpc
from ..execution import PaperExecutor
from ..risk import OpenPosition, RiskManager
from ..safety import SafetyGate
from .notifier import Notifier
from .realtime import RealtimeLaunchFeed
from .state import StateStore

log = logging.getLogger(__name__)

OBS_SEC = 120          # observation window before deciding
POLL_SEC = 10          # price sampling cadence (batched across candidates)
MIN_RANGE = 0.172      # validated threshold: >=17.2% range in the window
# Range alone is NOT tradable. Tested on every harvested pool with nothing
# excluded for dying young, range>=17.2% returns -11.3% per trade
# CI[-25.2%,+4.2%]: the rule buys the graveyard, and the graveyard was
# invisible to earlier backtests because a pool that stops trading after
# two minutes leaves too few bars to score.
# What separates the doomed from the living is not how far price moved but
# whether trading is still BUILDING. Median second minute, as a fraction of
# the first: 0.12 for pools that die, 1.20 for pools still alive ten
# minutes later. Requiring acceleration turns the same rule into +37.0%
# per trade CI[+6.9%,+70.1%] (n=130), holds up out-of-sample (+19.3% on the
# later half) and beats a same-size random subset of that period at p=0.012.
MIN_ACCEL = 1.0        # minute-2 activity must at least match minute-1
# ...but not by too much. Return is NOT monotonic in acceleration -- rank
# correlation is -0.17 and the >5x bucket earns +5.2% against +75.8% for
# 1.5-2.5x. A second minute trading ten times the first is a frenzy at its
# peak, not demand building, and it is the last buyer who pays for it.
# Adopted as PROVISIONAL: every ceiling tested (3x, 5x, 10x) beat no
# ceiling both in and out of sample, so the effect is a plateau rather than
# a spike at one lucky cut point -- but each OOS floor still spans zero at
# n<=60. The loosest cut is used deliberately: it excludes only the extreme
# and adds the fewest degrees of freedom to overfit.
MAX_ACCEL = 10.0       # above this the launch is a frenzy, not a trend
# A separate question from alpha: can the pool be TRADED at all? A live
# entry fired on a pool whose first two minutes carried one dollar of
# volume -- its "range" was a stale resting price moving on nothing, and
# its acceleration ratio was two tiny numbers divided by each other. The
# backtest cannot object because such a pool costs nothing to hold in a
# spreadsheet. Real money cannot get in or out of it. This floor is set
# low deliberately: it excludes the untradeable, not the merely small,
# since volume LEVEL was tested as an alpha filter and did not help.
MIN_SOL_VOL2 = 0.5     # total SOL swapped in the first two minutes
MIN_SAMPLES = 3        # matches the backtest's "traded in >=2 minutes";
                       # Jupiter's batch price call intermittently omits
                       # brand-new mints, so demanding 6 samples was
                       # rejecting QUALIFYING signals (28.8% range, 27.5%
                       # range) for our feed's reliability, not the token's
TRAIL = 0.30
MAX_HOLD_MIN = 30
# Fills are priced from Jupiter quotes, which already contain the real
# slippage for our size. Passing an unknown reserve made the cost model
# charge its punitive 10%/side "thin pool" default ON TOP of that — about
# 18pp of phantom cost per round trip, which is why -30% trail exits were
# booking as -36%. A large notional reserve makes that model a no-op and
# leaves only the flat fee, so paper P&L reflects executable prices.
QUOTE_RESERVE = 1e9


# Calibrated from a live post-mortem worth recording. A position was marked
# down 99.8% in one poll; a GeckoTerminal snapshot still showed the pool
# healthy, so the mark looked like an aggregator routing our sell through a
# dead pool. The minute bars proved the opposite: the rug happened DURING
# that minute, the quote was right, and the GT snapshot was the stale one.
# The lesson is not to distrust quotes — it is that a lagging source must
# never overrule a real-time one, and that a real loss must never be
# explained away as an instrument fault.
# So the guard stays, but only where hesitating is nearly free: at a 95%+
# wipeout one extra poll costs pennies of an already-dead position, while a
# genuinely phantom zero would cost the whole clip. Ordinary sharp drops
# (a -60% leg down is normal here) exit immediately, as they must.
CRASH_FRAC = 0.95          # only a near-total wipeout awaits confirmation
CONFIRM_POLLS = 2          # consecutive readings required


@dataclass
class Candidate:
    mint: str
    detected_ts: float
    prices: list = field(default_factory=list)
    decided: bool = False

    @property
    def age(self) -> float:
        return time.time() - self.detected_ts

    def range_frac(self) -> float:
        p = [x for x in self.prices if x and x > 0]
        if len(p) < 2:
            return 0.0
        return max(p) / min(p) - 1.0


class RealtimeScalper:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.costs = CostModel(dex_fee_bps=cfg.costs.dex_fee_bps,
                               adverse_bps=cfg.costs.adverse_bps,
                               priority_fee_usd=cfg.costs.priority_fee_usd)
        self.jup = Jupiter(per_min=24)
        self.rpc = SolanaRpc()
        self.helius = Helius()
        self.gt = GeckoTerminal()
        self.safety = SafetyGate(cfg, self.rpc, self.jup)
        self.risk = RiskManager(cfg)
        self.notify = Notifier(cfg.telegram.enabled)
        self.state = StateStore(cfg.live.state_db)
        self.feed = RealtimeLaunchFeed()
        self.is_live = cfg.mode == "live" and live_trading_armed()
        self.executor = PaperExecutor(self.costs)
        if self.is_live:
            from ..execution import JupiterExecutor
            self.executor = JupiterExecutor(
                self.jup, self.rpc, wallet_min_sol=cfg.live.wallet_min_sol)
        self.candidates: dict[str, Candidate] = {}
        self.positions: dict[str, OpenPosition] = self.state.load_positions()
        cash = self.state.get_kv("cash_usd")
        self.cash = float(cash) if cash is not None else cfg.capital.starting_usd
        self.sol_price = 100.0
        self._seen_sigs: set[str] = set()
        self._crash_count: dict[str, int] = {}
        self._last_vol2: float | None = None
        log.info("scalper up: mode=%s cash=%.2f positions=%d",
                 "LIVE" if self.is_live else "PAPER", self.cash,
                 len(self.positions))

    # ---------------------------------------------------------------- intake

    def _resolve_mint(self, sig: str) -> str | None:
        """Creation signature -> the token mint (not SOL, not the LP mint)."""
        for _ in range(6):
            res = self.rpc.call("getTransaction", [
                sig, {"encoding": "jsonParsed",
                      "maxSupportedTransactionVersion": 0}])
            if res:
                break
            time.sleep(2)
        else:
            return None
        post = (res.get("meta") or {}).get("postTokenBalances") or []
        mints = [b.get("mint") for b in post if b.get("mint")]
        cands = [m for m in dict.fromkeys(mints) if m != SOL_MINT]
        for m in cands:                      # the tradeable one is the token
            if self.jup.prices_usd([m]).get(m):
                return m
        return None

    def intake(self) -> None:
        for ev in self.feed.recent(max_age_sec=90):
            if ev.signature in self._seen_sigs:
                continue
            self._seen_sigs.add(ev.signature)
            mint = self._resolve_mint(ev.signature)
            if not mint or mint in self.candidates or mint in self.positions:
                continue
            self.candidates[mint] = Candidate(mint, ev.detected_ts)
            log.info("watching %s (detected %.0fs ago)", mint[:10],
                     time.time() - ev.detected_ts)

    # ------------------------------------------------------------- sampling

    def sample(self) -> None:
        """One batched Jupiter call prices every watched mint at once."""
        watch = [m for m, c in self.candidates.items() if not c.decided]
        if not watch:
            return
        px = self.jup.prices_usd(watch[:50])
        for m, c in self.candidates.items():
            if m in px:
                c.prices.append(px[m])

    # -------------------------------------------------------------- decision

    def decide(self) -> None:
        for mint, c in list(self.candidates.items()):
            if c.decided:
                continue
            if c.age < OBS_SEC:
                continue
            c.decided = True
            rng = c.range_frac()
            n = len([p for p in c.prices if p])
            accel = self.acceleration(mint, c.detected_ts) if (
                n >= MIN_SAMPLES and rng >= MIN_RANGE) else None
            vol2 = self._last_vol2
            ok = (n >= MIN_SAMPLES and rng >= MIN_RANGE and accel is not None
                  and MIN_ACCEL <= accel < MAX_ACCEL
                  and (vol2 is None or vol2 >= MIN_SOL_VOL2))
            self._journal(mint, rng, n, accel, ok)
            if not ok:
                log.info("skip %s: range %.1f%% samples %d accel %s "
                         "(need >=%.1f%%, %d, >=%.1f)",
                         mint[:10], rng * 100, n,
                         f"{accel:.2f}" if accel is not None else "n/a",
                         MIN_RANGE * 100, MIN_SAMPLES, MIN_ACCEL)
                self.candidates.pop(mint, None)
                continue
            self._enter(mint, c)

    def _enter(self, mint: str, c: Candidate) -> None:
        now = time.time()
        equity = self.equity()
        ok, why = self.risk.can_enter(now, self.positions, equity, None)
        if not ok:
            log.info("entry blocked %s: %s", mint[:10], why)
            self.candidates.pop(mint, None)
            return
        size = self.risk.position_size(equity, None)
        # these pools are tiny (median ~$1.5k reserve): clip small or the
        # measured edge is eaten by our own impact
        size = min(size, 10.0)
        px = self.jup.prices_usd([mint]).get(mint)
        if not px:
            self.candidates.pop(mint, None)
            return
        # price the fill from a real BUY quote — it embeds the true slippage
        # for our size, so the cost model must not charge impact again
        bp = self.quote_buy_price(mint, size)
        if bp and (bp / px > 3 or bp / px < 0.33):
            log.info("skip %s: entry price unreliable (index %.3e vs quote "
                     "%.3e)", mint[:10], px, bp)
            self.candidates.pop(mint, None)
            return
        px = bp or px
        v = self.safety.check_sellability(mint, size, self.sol_price)
        if not v.ok:
            log.info("safety reject %s: %s", mint[:10], v.reason)
            self.candidates.pop(mint, None)
            return
        rep = (self.executor.buy(mint, size, px, QUOTE_RESERVE)
               if not self.is_live else
               self.executor.buy(mint, size, px, QUOTE_RESERVE, self.sol_price))
        if not rep.ok or rep.tokens <= 0:
            self.candidates.pop(mint, None)
            return
        self.cash -= rep.usd
        pos = OpenPosition(pool=mint, mint=mint, symbol=mint[:6],
                           entry_ts=now, entry_price=rep.price,
                           tokens=rep.tokens, size_usd=rep.usd,
                           hwm_price=rep.price)
        self.positions[mint] = pos
        self.state.save_position(pos)
        self.state.set_kv("cash_usd", str(self.cash))
        self.candidates.pop(mint, None)
        self.notify.send(f"ENTER {mint[:8]} ${rep.usd:.0f} "
                         f"(range {c.range_frac():.0%})")

    # ----------------------------------------------------------------- exits

    def manage(self) -> None:
        if not self.positions:
            return
        px = self.jup.prices_usd([p.mint for p in self.positions.values()])
        for mint, pos in list(self.positions.items()):
            p = px.get(mint)
            held = (time.time() - pos.entry_ts) / 60
            if p is None:
                # the index feed dropping a token is NOT proof it died —
                # confirm against an executable quote before writing off 90%
                qp = self.quote_price(pos.mint, pos.tokens, pos.decimals)
                if qp:
                    # The confirmation guard belongs on EVERY exit path, not
                    # just the index-price one. A live position was closed
                    # here at 2.2e-07 while its token traded at 9.2e-05 in a
                    # \$26k pool -- a +13% winner booked as a total loss
                    # because a single quote on a two-minute-old token
                    # routed somewhere thin. One reading may not close a
                    # position; a real collapse survives the next poll.
                    ref = min(pos.entry_price, pos.hwm_price)
                    if qp < ref * (1 - CRASH_FRAC):
                        # An aggregator that cannot ROUTE a token is not the
                        # same as a token that is worthless. 2KKwjF quoted
                        # 2.2e-07 while its pool held \$26k and traded at
                        # 9.2e-05; Jupiter had no index price for it at all.
                        # A real seller can go straight to the pool. So
                        # before booking a wipeout, ask whether the pool is
                        # alive RIGHT NOW -- current reserve and current
                        # volume, not a stale snapshot, which is the
                        # distinction that made the F7V4a5 rug look fake.
                        alive = self.pool_alive_price(pos.mint)
                        if alive:
                            log.warning("%s: quote %.3e unroutable but pool "
                                        "is alive at %.3e — marking to pool",
                                        pos.symbol, qp, alive)
                            qp = alive
                    if qp < ref * (1 - CRASH_FRAC):
                        k = self._crash_count.get(pos.mint, 0) + 1
                        self._crash_count[pos.mint] = k
                        if k < CONFIRM_POLLS:
                            log.warning("%s: quote implies %.0f%% wipeout "
                                        "(%.3e vs %.3e) — awaiting "
                                        "confirmation %d/%d", pos.symbol,
                                        100 * (1 - qp / ref), qp, ref, k,
                                        CONFIRM_POLLS)
                            self.state.save_position(pos)
                            continue
                    else:
                        self._crash_count.pop(pos.mint, None)
                    pos.hwm_price = max(pos.hwm_price, qp)
                    if qp <= pos.hwm_price * (1 - TRAIL) or held >= MAX_HOLD_MIN:
                        self._exit(pos, qp, "quote_exit")
                    else:
                        self.state.save_position(pos)
                elif held >= 10:
                    self._exit(pos, pos.entry_price * 0.1, "no_route")
                continue
            # the index price only SCREENS; every exit is confirmed against
            # an executable quote so one bad index tick cannot dump a position
            if p <= pos.hwm_price * (1 - TRAIL) or held >= MAX_HOLD_MIN:
                qp = self.quote_price(pos.mint, pos.tokens, pos.decimals)
                real = qp if qp else p
                # An implausible collapse must be CONFIRMED before it can
                # close a position — routing through a dead pool looks
                # identical to a rug for exactly one reading.
                ref = min(pos.entry_price, pos.hwm_price)
                if real < ref * (1 - CRASH_FRAC):
                    n = self._crash_count.get(pos.mint, 0) + 1
                    self._crash_count[pos.mint] = n
                    if n < CONFIRM_POLLS:
                        log.warning("%s: implausible %.0f%% drop (%.3e vs "
                                    "%.3e) — awaiting confirmation %d/%d",
                                    pos.symbol, 100 * (1 - real / ref), real,
                                    ref, n, CONFIRM_POLLS)
                        self.state.save_position(pos)
                        continue
                else:
                    self._crash_count.pop(pos.mint, None)
                pos.hwm_price = max(pos.hwm_price, real)
                if held >= MAX_HOLD_MIN:
                    self._exit(pos, real, "time")
                elif real <= pos.hwm_price * (1 - TRAIL):
                    self._exit(pos, real, "trail")
                else:
                    self.state.save_position(pos)
            else:
                self._crash_count.pop(pos.mint, None)
                pos.hwm_price = max(pos.hwm_price, p)
                self.state.save_position(pos)

    def _exit(self, pos: OpenPosition, px: float, reason: str) -> None:
        rep = (self.executor.sell(pos.mint, pos.tokens, px, QUOTE_RESERVE,
                                  self.sol_price, sell_all=True)
               if self.is_live else
               self.executor.sell(pos.mint, pos.tokens, px, QUOTE_RESERVE))
        if not rep.ok:
            self.notify.send(f"⚠️ SELL FAILED {pos.symbol} ({reason})")
            return
        self.cash += rep.usd
        pnl = rep.usd - pos.size_usd
        self.positions.pop(pos.pool, None)
        self.state.delete_position(pos.pool)
        self.state.record_trade(pos, rep.price, pnl, reason)
        self.risk.record_realized(pnl, self.equity())
        self.state.set_kv("cash_usd", str(self.cash))
        self.notify.send(f"EXIT {pos.symbol} {reason} pnl ${pnl:+.2f}")

    def quote_price(self, mint: str, tokens: float,
                    decimals: int = 6) -> float | None:
        """The price we could ACTUALLY SELL AT, from a Jupiter quote.

        Jupiter's index price is unreliable for tokens minutes old — it can
        price a different venue than the one holding the liquidity. A live
        position was marked down 87% and exited on a phantom crash while the
        real market price sat ABOVE our entry. A quote cannot lie that way:
        it is what a real sell would return, right now.
        """
        raw = int(max(tokens, 0) * 10 ** decimals)
        if raw <= 0:
            return None
        q = self.jup.quote(mint, SOL_MINT, raw, slippage_bps=1000)
        out = int((q or {}).get("outAmount") or 0)
        if out <= 0:
            return None
        return (out / 1e9 * self.sol_price) / tokens

    def _journal(self, mint: str, rng: float, n: int,
                 accel: float | None, taken: bool) -> None:
        """Record EVERY candidate and the features it was judged on.

        Thresholds validated on historical bars had to be ported onto a
        different live measurement, and the port was wrong -- the backtest
        used minute-2/minute-1 USD volume, the scalper counts transactions,
        and the 1.0 threshold moved across unexamined. Mapping one onto the
        other is a workaround; the real fix is a dataset of the feature the
        LIVE system actually computes, paired with the outcome that
        followed. Skipped candidates are the important half: without them
        there is no way to ask what a different threshold would have earned.
        """
        try:
            self.state.db.execute(
                "INSERT OR REPLACE INTO candidate_journal "
                "(mint, ts, range_frac, samples, accel, taken) "
                "VALUES (?,?,?,?,?,?)",
                (mint, time.time(), float(rng), int(n),
                 float(accel) if accel is not None else None, int(taken)))
            self.state.db.commit()
        except Exception as e:                       # journalling is never
            log.debug("journal write failed: %s", e)  # allowed to block a trade

    def pool_alive_price(self, mint: str) -> float | None:
        """Current price from the token's best pool, if that pool is
        demonstrably still trading. Returns None when nothing is alive, so
        a genuine rug still books as a loss."""
        try:
            pools = self.gt.token_pools(mint)
        except Exception as e:
            log.debug("pool lookup failed for %s: %s", mint[:10], e)
            return None
        for p in pools[:3]:
            reserve = p.reserve_usd or 0.0
            vol5 = p.vol_m5 or 0.0
            if reserve >= 500 and vol5 > 0 and (p.price_usd or 0) > 0:
                return float(p.price_usd)
        return None

    def acceleration(self, mint: str, since_ts: float | None = None) -> float | None:
        """minute-2 volume / minute-1 volume -- the VALIDATED quantity.

        A launch whose second minute trades less than its first has already
        spent its buyers; one still building has ongoing demand.

        This began as a transaction COUNT, because counting signatures is
        cheap. Measured against the volume ratio the backtest validated,
        that proxy ranked at +0.21 and picked the same launches only 63% of
        the time against a 56% chance baseline -- a different filter
        wearing the same threshold. On the one live rug in the ledger it
        scored 3.94 (buy) where real volume scored 0.20 (reject).
        So volume is now measured directly from parsed swaps, and the
        counter is kept only as a fallback when Helius is unavailable.
        """
        if self.helius.available:
            try:
                v = self.helius.swap_volume_per_minute(mint, since_ts=since_ts)
            except Exception as e:
                log.warning("volume lookup failed for %s: %s", mint[:10], e)
                v = []
            if len(v) >= 2 and v[0] > 0:
                self._last_vol2 = float(v[0] + v[1])
                return v[1] / v[0]
            self._last_vol2 = None
            return None
        try:
            a = self.rpc.activity_per_minute(mint, since_ts=since_ts)
        except Exception as e:                       # never block on RPC
            log.warning("activity lookup failed for %s: %s", mint[:10], e)
            return None
        if len(a) < 2 or a[0] <= 0:
            return None
        return a[1] / a[0]

    def quote_buy_price(self, mint: str, usd: float) -> float | None:
        """The price we would ACTUALLY PAY, from a real buy quote."""
        lamports = int(usd / max(self.sol_price, 1e-9) * 1e9)
        if lamports <= 0:
            return None
        q = self.jup.quote(SOL_MINT, mint, lamports, slippage_bps=1000)
        out = int((q or {}).get("outAmount") or 0)
        if out <= 0:
            return None
        tokens = out / 1e6          # pump.fun mints are 6-decimal
        return usd / tokens if tokens > 0 else None

    def equity(self) -> float:
        return self.cash + sum(p.tokens * p.entry_price
                               for p in self.positions.values())

    # ------------------------------------------------------------------ loop

    def run(self) -> None:
        self.feed.start()
        self.notify.send(f"realtime scalper started "
                         f"({'LIVE' if self.is_live else 'paper'})")
        last_sample = last_beat = 0.0
        while True:
            try:
                now = time.time()
                if now - last_sample >= POLL_SEC:
                    self.intake()
                    self.sample()
                    self.decide()
                    last_sample = now
                self.manage()
                if now - last_beat >= 300:
                    s = self.state.pnl_summary()
                    log.info("heartbeat equity=%.2f watching=%d positions=%d "
                             "trades=%d pnl=%.2f", self.equity(),
                             len(self.candidates), len(self.positions),
                             s["n_trades"], s["total_pnl_usd"])
                    last_beat = now
                    px = self.jup.prices_usd([SOL_MINT])
                    if px.get(SOL_MINT):
                        self.sol_price = px[SOL_MINT]
                time.sleep(2)
            except KeyboardInterrupt:
                self.feed.stop()
                return
            except Exception:
                log.exception("scalper loop error; continuing")
                time.sleep(5)

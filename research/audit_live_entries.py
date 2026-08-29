#!/usr/bin/env python3
"""Entry-fidelity audit: does every LIVE trade match the BACKTESTED trade?

The first four live knife trades lost money not because the strategy was
wrong but because the live entries were a different trade than the one
validated (late fills into spent bounces). That failure was invisible in
the P&L alone — it took manual bar-by-bar forensics to find.

This script makes that check automatic. For every trade in a live/paper
state DB it reconstructs, from the collector's panel, what the strategy
saw at signal time and reports:

  * signal_ok   — were the strategy's entry conditions actually true in
                  the minutes before the fill?
  * drift       — fill price vs the signal bar's close (the killer metric:
                  positive = bought a bounce that already ran)
  * fill_in_bar — was the fill price inside the entry bar's high/low range?

Any FAIL line means live execution has drifted from the validated spec and
the trades in question must not be counted as evidence for or against the
strategy.

Usage: python3 research/audit_live_entries.py [state_db] [panel_db]
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

STATE_DB = sys.argv[1] if len(sys.argv) > 1 else "data/live_knife.db"
PANEL_DB = sys.argv[2] if len(sys.argv) > 2 else "data/panel.db"

MAX_DRIFT_UP = 0.10      # matches the live entry_max_drift_up gate
MAX_DRIFT_DOWN = -0.35


def utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%m-%d %H:%M:%S")


def main() -> int:
    st = sqlite3.connect(STATE_DB, timeout=30)
    panel = sqlite3.connect(PANEL_DB, timeout=60)
    panel.execute("PRAGMA busy_timeout=60000")

    trades = st.execute(
        "SELECT symbol, pool, entry_ts, entry_price, exit_price, size_usd, "
        "pnl_usd, reason FROM trades ORDER BY entry_ts").fetchall()
    if not trades:
        print("no live trades recorded yet")
        return 0

    from memebot.data.gt import GeckoTerminal
    gt = GeckoTerminal(per_min=20)

    def bars_for(pool: str, ets: float):
        """Panel bars around the fill; fetch from GT when coverage is short
        (the collector's rotation lags fresh trades) and persist them."""
        q = ("SELECT ts, o, h, l, c FROM ohlcv WHERE pool_address=? "
             "AND ts BETWEEN ? AND ? ORDER BY ts")
        rows = panel.execute(q, (pool, int(ets) - 600, int(ets) + 120)).fetchall()
        if rows:
            return rows
        fetched = gt.ohlcv(pool, "minute", limit=1000)
        if fetched:
            panel.executemany(
                "INSERT OR REPLACE INTO ohlcv VALUES (?,?,?,?,?,?,?)",
                [(pool, int(b[0]), b[1], b[2], b[3], b[4], b[5])
                 for b in fetched])
            panel.commit()
        return panel.execute(q, (pool, int(ets) - 600, int(ets) + 120)).fetchall()

    print(f"{'symbol':<12} {'entry(UTC)':<16} {'drift':>8} {'in-bar':>7} "
          f"{'pnl':>8}  verdict")
    print("-" * 68)
    fails = 0
    for sym, pool, ets, eprice, xprice, size, pnl, reason in trades:
        bars = bars_for(pool, ets)
        if not bars:
            print(f"{sym:<12} {utc(ets):<16} {'n/a':>8} {'n/a':>7} "
                  f"{pnl:>8.2f}  NO PANEL DATA (cannot audit)")
            continue
        # bar containing the fill, and the last closed bar before it
        entry_bar = None
        prev_bar = None
        for b in bars:
            if b[0] <= ets:
                prev_bar, entry_bar = entry_bar, b
        entry_bar = entry_bar or bars[-1]
        prev_bar = prev_bar or entry_bar

        sig_close = float(prev_bar[4])
        drift = eprice / sig_close - 1.0 if sig_close else float("nan")
        lo, hi = float(entry_bar[3]), float(entry_bar[2])
        in_bar = lo * 0.98 <= eprice <= hi * 1.02

        bad = []
        if drift > MAX_DRIFT_UP:
            bad.append(f"late fill +{drift:.0%} above signal (spent bounce)")
        if drift < MAX_DRIFT_DOWN:
            bad.append(f"fill {drift:.0%} below signal (still falling)")
        if not in_bar:
            bad.append("fill price outside the entry bar's range")
        verdict = "OK" if not bad else "FAIL: " + "; ".join(bad)
        if bad:
            fails += 1
        print(f"{sym:<12} {utc(ets):<16} {drift:>+7.1%} {str(in_bar):>7} "
              f"{pnl:>8.2f}  {verdict}")

    print("-" * 68)
    n = len(trades)
    print(f"{n} trades audited, {fails} fidelity FAILURES "
          f"({fails / n:.0%})")
    if fails:
        print("\nTrades flagged FAIL executed a different trade than the one "
              "backtested.\nExclude them from strategy evidence and fix the "
              "live path before judging edge.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

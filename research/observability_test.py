#!/usr/bin/env python3
"""Is the backtest edge real, or an artifact of pricing dead pools?

The panel reindexes bars to a continuous minute grid: minutes with no
trades carry the resting AMM price at zero volume. That is the right
convention for holding through quiet periods, but it means a trade can
"exit" at a price nobody actually traded at. If the measured edge lives
disproportionately in those trades, the strategy is a mirage.

Test: split every backtested trade by how much REAL trading happened
during the hold (fraction of minutes with volume > 0) and compare
expectancy across the tiers. A genuine edge survives in the
fully-observed tier; an artifact concentrates in the quiet one.

Usage: python3 research/observability_test.py [db]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from memebot.backtest.costs import CostModel                    # noqa: E402
from memebot.backtest.engine import RiskParams, run_backtest    # noqa: E402
from memebot.backtest.metrics import _cluster_bootstrap_means   # noqa: E402
from memebot.data.store import (cohort_gate, cohort_momentum,   # noqa: E402
                                load_panel)
from memebot.strategy import ExitRules, make_strategy           # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
EXITS = ExitRules(stop_frac=0.35, trail_frac=0.90, tp_levels=(),
                  max_hold_min=60, liq_drop_exit_frac=0.5)
RISK = RiskParams(starting_usd=1000, risk_per_trade_usd=25)


def observability(pools, trades) -> pd.DataFrame:
    by_addr = {p.meta.address: p for p in pools}
    rows = []
    for t in trades:
        p = by_addr.get(t.pool)
        if p is None:
            continue
        df = p.df
        seg = df[(df.index >= t.entry_ts) & (df.index <= t.exit_ts)]
        if len(seg) == 0:
            continue
        traded = float((seg["vol_usd"].fillna(0) > 0).mean())
        # was there real trading at the exit minute itself?
        tail = df[(df.index >= t.exit_ts - 120) & (df.index <= t.exit_ts)]
        exit_live = bool((tail["vol_usd"].fillna(0) > 0).any())
        # did the pool keep trading well past our exit? (not the data edge)
        after = df[df.index > t.exit_ts]
        after_live = float((after["vol_usd"].fillna(0) > 0).sum()) if len(after) else 0.0
        rows.append({"pool": t.pool, "mint": t.mint or t.pool, "ret": t.ret_frac,
                     "pnl": t.pnl_usd, "traded_frac": traded,
                     "exit_live": exit_live, "bars_after": after_live,
                     "hold_min": (t.exit_ts - t.entry_ts) / 60,
                     "reason": t.exit_reason})
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame, label: str) -> dict:
    if df.empty:
        return {"tier": label, "n": 0}
    rets = df["ret"].to_numpy()
    boot = _cluster_bootstrap_means(rets, df["mint"].to_numpy(), n_boot=4000)
    return {
        "tier": label, "n": len(df), "tokens": df["mint"].nunique(),
        "mean_ret": float(rets.mean()),
        "ci_lo": float(np.quantile(boot, 0.025)),
        "ci_hi": float(np.quantile(boot, 0.975)),
        "median": float(np.median(rets)),
        "win_rate": float((df["pnl"] > 0).mean()),
        "total_pnl": float(df["pnl"].sum()),
    }


def main() -> int:
    pools = load_panel(DB, min_max_reserve=2000.0)
    cohort = cohort_momentum(pools)
    gate = cohort_gate(cohort)
    print(f"panel: {len(pools)} pools\n")

    for name, params, events in [
        ("knife_catch", {"use_regime": 0}, {"__cohort_gate__": gate}),
        ("random_entries", {"seed": 0}, {}),
    ]:
        strat = make_strategy(name, params, EXITS, events=events)
        res = run_backtest(pools, strat, CostModel(), RISK)
        df = observability(pools, res.trades)
        if df.empty:
            print(f"=== {name}: no trades\n")
            continue
        print(f"=== {name}: {len(df)} trades")
        tiers = [
            ("ALL", df),
            ("fully-observed (>=80% minutes traded, exit live, "
             "pool alive after)",
             df[(df.traded_frac >= 0.8) & df.exit_live & (df.bars_after > 10)]),
            ("partly quiet (30-80% traded)",
             df[(df.traded_frac >= 0.3) & (df.traded_frac < 0.8)]),
            ("mostly dead (<30% minutes traded)", df[df.traded_frac < 0.3]),
        ]
        out = [summarize(d, t) for t, d in tiers]
        print(pd.DataFrame(out).to_string(index=False,
                                          float_format=lambda x: f"{x:.3f}"))
        share = df[df.traded_frac < 0.3]["pnl"].sum() / df["pnl"].sum() \
            if df["pnl"].sum() else float("nan")
        print(f"  share of total P&L from mostly-dead-pool trades: {share:.0%}")
        print(f"  median minutes-traded fraction: {df.traded_frac.median():.2f}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Full validation pipeline -> research/results/REPORT.md

Pre-registered protocol (committed before results were seen):
  1. Base rates (analyze_panel.py output is a prerequisite context).
  2. Every strategy family at tuned defaults, 1x costs, vs the
     random_entries placebo (3 seeds).
  3. Coarse pre-registered grids per family -> full grid report (every
     config logged to the experiment registry).
  4. Anchored walk-forward by launch time (3 folds, embargo) for each
     family with enough trades.
  5. Cost stress: winning configs re-run at 2x and 3x cost multiples.
  6. Verdict per family. "VALIDATED" requires ALL of:
       - walk-forward OOS cluster-bootstrap CI low > 0
       - OOS expectancy > placebo mean + its CI width
       - still profitable at 2x costs
       - profitable after removing top-3 trades
       - >= 30 OOS trades across >= 20 distinct tokens
     Anything less is reported as NOT validated. No exceptions.

Usage: python3 research/run_validation.py [db_path]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from memebot.backtest.costs import CostModel                     # noqa: E402
from memebot.backtest.engine import RiskParams, run_backtest     # noqa: E402
from memebot.backtest.metrics import log_registry, summarize, summary_table  # noqa: E402
from memebot.backtest.walkforward import (                       # noqa: E402
    GridSpec, eval_config, grid_report, walk_forward)
from memebot.data.store import (boost_first_seen, cohort_gate,   # noqa: E402
                                cohort_momentum, load_panel,
                                trending_first_seen)
from memebot.strategy import ExitRules, make_strategy            # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)

COSTS = CostModel()
RISK = RiskParams(starting_usd=1000, risk_per_trade_usd=25, max_concurrent=4,
                  daily_loss_limit_frac=0.10, max_pool_share=0.005)

# exit-opt mining plateau: tight trail, no early TP, patient hold
EXIT_DEFAULT = {"stop_frac": 0.15, "trail_frac": 0.18,
                "tp_levels": (), "max_hold_min": 300,
                "liq_drop_exit_frac": 0.5}

# --- pre-registered grids (coarse, few params, interior optima expected) ---
GRIDS: dict[str, dict] = {
    "grad_momentum": {
        "param_grid": {"min_age_min": [15, 30], "min_vol5": [1000, 3000],
                       "min_liq": [15000, 30000]},
        "exit_grid": {"trail_frac": [0.2, 0.3]},
    },
    "dip_reclaim": {
        "param_grid": {"min_run": [0.5, 1.0], "min_dip": [0.25, 0.35, 0.5]},
        "exit_grid": {"trail_frac": [0.2, 0.3]},
    },
    "trending_follow": {
        "param_grid": {"min_liq": [15000, 30000]},
        "exit_grid": {"trail_frac": [0.25]},
    },
    # E/F pre-registered 2026-08-28 AFTER observing window 2 — results on
    # data up to then are EXPLORATORY; confirmation needs later windows.
    "regime_gated": {
        "param_grid": {"min_cohort_mom": [0.0, 0.02, 0.05]},
        "exit_grid": {"trail_frac": [0.2, 0.3]},
    },
    "boost_follow": {
        "param_grid": {"min_liq": [15000]},
        "exit_grid": {"trail_frac": [0.25]},
    },
    # G composite_v2 (pre-registered 2026-08-28 from the mining pass; data
    # through then is its DESIGN sample — exploratory until later windows)
    "composite_v2": {
        "param_grid": {"max_dd": [0.12, 0.25], "min_turnover": [0.02, 0.08],
                       "max_rv30": [0.08, 99.0]},
        "exit_grid": {"trail_frac": [0.15, 0.2]},
    },
    # H knife_catch (pre-registered 2026-08-28 from the failure-autopsy
    # inversion; hot-window evidence only — exploratory until a clean
    # forward window). Exit grid includes the pure timed hold that was
    # actually tested (stop/trail effectively off) and a protected variant.
    "knife_catch": {
        "param_grid": {"min_dip": [0.30, 0.35, 0.45], "use_regime": [0, 1]},
        "exit_grid": {"stop_frac": [0.90, 0.35], "trail_frac": [0.90],
                      "max_hold_min": [60, 120]},
    },
}


def defaults_pass(pools, events_by_family) -> list[dict]:
    rows = []
    for name in ("grad_momentum", "dip_reclaim", "attention_cont",
                 "trending_follow", "regime_gated", "boost_follow",
                 "composite_v2", "knife_catch"):
        strat = make_strategy(name, {}, ExitRules(**EXIT_DEFAULT),
                              events=events_by_family.get(name, {}))
        res = run_backtest(pools, strat, COSTS, RISK)
        s = summarize(res, label=name)
        log_registry({"phase": "defaults", **{k: s.get(k) for k in
                     ("label", "n_trades", "expectancy_ret", "total_pnl_usd")}})
        rows.append(s)
    for seed in (0, 1, 2):
        strat = make_strategy("random_entries", {"seed": seed},
                              ExitRules(**EXIT_DEFAULT))
        res = run_backtest(pools, strat, COSTS, RISK)
        s = summarize(res, label=f"placebo_seed{seed}")
        log_registry({"phase": "defaults", **{k: s.get(k) for k in
                     ("label", "n_trades", "expectancy_ret", "total_pnl_usd")}})
        rows.append(s)
    return rows


def cost_stress(pools, name, params, exit_params, events) -> list[dict]:
    rows = []
    for mult in (1.0, 2.0, 3.0):
        costs = CostModel(mult=mult)
        strat = make_strategy(name, params, ExitRules(**{**EXIT_DEFAULT,
                                                         **exit_params}),
                              events=events)
        res = run_backtest(pools, strat, costs, RISK)
        rows.append(summarize(res, label=f"{name}@{mult:.0f}x"))
    return rows


def verdict(pooled: dict | None, placebo_hi: float,
            stress: list[dict]) -> tuple[bool, list[str]]:
    """All criteria evaluated on the POOLED out-of-sample trades (never
    per-fold means) and on OOS-only cost stress."""
    reasons = []
    if not pooled or pooled.get("n_trades", 0) == 0:
        return False, ["no pooled out-of-sample trades"]
    if pooled["n_trades"] < 30:
        reasons.append(f"only {pooled['n_trades']} OOS trades (<30)")
    if pooled.get("n_tokens", 0) < 20:
        reasons.append(f"only {pooled.get('n_tokens', 0)} OOS tokens (<20)")
    if (pooled.get("expectancy_ci_lo") or -1) <= 0:
        reasons.append("pooled OOS cluster-bootstrap CI includes <= 0")
    if pooled.get("expectancy_ret", 0) <= placebo_hi:
        reasons.append(f"does not beat placebo upper CI ({placebo_hi:.4f})")
    two_x = next((s for s in stress if s["label"].endswith("@2x")), None)
    if not two_x or (two_x.get("total_pnl_usd") or 0) <= 0:
        reasons.append("dies at 2x costs (OOS)")
    if pooled["n_trades"] > 3 and (pooled.get("pnl_minus_top3") or 0) <= 0:
        reasons.append("pooled OOS P&L carried entirely by top-3 trades")
    return (not reasons), reasons


def _snapshot_windows(db_path: str, gap_min: int = 30) -> str:
    """Human-readable list of contiguous snapshot-coverage windows."""
    import sqlite3
    from datetime import datetime, timezone
    db = sqlite3.connect(db_path)
    try:
        ts = [r[0] for r in db.execute(
            "SELECT DISTINCT ts FROM snapshots ORDER BY ts")]
    finally:
        db.close()
    if not ts:
        return "none"
    def fmt(t):
        return datetime.fromtimestamp(t, timezone.utc).strftime("%m-%d %H:%M")
    windows = []
    start = prev = ts[0]
    for t in ts[1:]:
        if t - prev > gap_min * 60:
            windows.append(f"{fmt(start)}..{fmt(prev)}")
            start = t
        prev = t
    windows.append(f"{fmt(start)}..{fmt(prev)}")
    return "; ".join(windows)


def main() -> int:
    # min_bars stays at the survivorship-safe floor: bar count is a lifetime
    # outcome and must not condition panel membership
    pools = load_panel(DB, min_max_reserve=2000.0, min_bars=5)
    events = trending_first_seen(DB)
    boosts = boost_first_seen(DB)
    cohort = cohort_momentum(pools)
    gate = cohort_gate(cohort, on=0.02, off=0.0)
    events_by_family = {
        "trending_follow": events,
        "boost_follow": boosts,
        "regime_gated": {"__cohort__": cohort},
        "composite_v2": {**events, "__cohort_gate__": gate},
        "knife_catch": {"__cohort_gate__": gate},
    }
    print(f"panel: {len(pools)} pools; trending events: {len(events)}; "
          f"boost events: {len(boosts)}; cohort minutes: {len(cohort)}")
    if len(pools) < 20:
        print("PANEL TOO SMALL for validation — collect longer.")
        return 1

    from datetime import datetime, timezone
    snap_windows = _snapshot_windows(DB)
    lines = ["# Strategy validation report", "",
             f"generated: {datetime.now(timezone.utc).isoformat()}",
             f"panel: {len(pools)} pools (>= $2k max reserve, >= 5 minute-bars), "
             f"{len(events)} trending events",
             f"snapshot-covered collection windows (UTC): {snap_windows}",
             "",
             "> Entries are only permitted on bars with fresh snapshot",
             "> coverage (liquidity/FDV/volume verified), i.e. inside the",
             "> collection windows above. Verdicts tighten or flip as the",
             "> collector accumulates more windows — re-run this script to",
             "> regenerate. NOT VALIDATED on a thin panel means 'not enough",
             "> evidence yet', never 'edge confirmed'.", ""]

    # 2. defaults vs placebo
    d = defaults_pass(pools, events_by_family)
    ddf = summary_table(d)
    ddf.to_csv(OUT / "defaults_vs_placebo.csv", index=False)
    lines += ["## Defaults vs placebo (1x costs)", "```",
              ddf.to_string(index=False), "```", ""]
    placebo_rows = [r for r in d if r["label"].startswith("placebo")
                    and r.get("n_trades", 0) > 0]
    placebo_mean = (float(np.mean([r["expectancy_ret"] for r in placebo_rows]))
                    if placebo_rows else 0.0)
    # bar to beat: placebo upper CI (protocol: mean + CI width), averaged
    # over seeds; 0 when the placebo never trades
    placebo_hi = (float(np.mean([r.get("expectancy_ci_hi", 0) or 0
                                 for r in placebo_rows]))
                  if placebo_rows else 0.0)
    lines.append(f"placebo mean expectancy: {placebo_mean:.4f}; "
                 f"upper-CI bar to beat: {placebo_hi:.4f}")
    strat_best = max((r.get("expectancy_ret") or -9e9 for r in d
                      if not r["label"].startswith("placebo")
                      and r.get("n_trades", 0) > 0), default=None)
    if strat_best is not None and placebo_rows and strat_best <= placebo_mean:
        lines += ["",
                  "> **Interpretation:** the RANDOM-ENTRY placebo matches or",
                  "> beats every strategy's expectancy in this window. The",
                  "> measured returns are therefore window beta captured by",
                  "> the shared exit machinery (asymmetric stops/trails on a",
                  "> hot tape), NOT entry-signal edge. No entry signal has",
                  "> demonstrated value beyond random timing yet."]
    lines.append("")

    # 3-5. per-family grid + walk-forward + stress
    verdicts = {}
    for name, g in GRIDS.items():
        ev = events_by_family.get(name, {})
        grid = GridSpec(strategy=name, param_grid=g["param_grid"],
                        exit_grid=g["exit_grid"], events=ev)
        gr = grid_report(pools, grid, COSTS, RISK)
        gr.to_csv(OUT / f"grid_{name}.csv", index=False)
        lines += [f"## {name} — full grid (every config tried)", "```",
                  gr.to_string(index=False), "```", ""]

        wf = walk_forward(pools, grid, COSTS, RISK, n_folds=3, min_trades=15)
        (OUT / f"walkforward_{name}.json").write_text(
            json.dumps(wf, indent=2, default=str))
        oos = wf["oos"]
        pooled = wf.get("oos_pooled")
        lines += [f"### {name} — walk-forward OOS (per fold + pooled)", "```",
                  summary_table(oos + ([pooled] if pooled else []))
                  .to_string(index=False) if oos else "no folds",
                  "```", ""]

        picks = [p for p in wf["picks"] if p]
        oos_addrs = set(wf.get("oos_pool_addresses") or [])
        oos_only = [p for p in pools if p.meta.address in oos_addrs]
        if picks and oos_only:
            last = picks[-1]
            stress = cost_stress(oos_only, name, last["params"],
                                 last["exit_params"], ev)
            lines += [f"### {name} — cost stress (OOS pools only, last pick)",
                      "```", summary_table(stress).to_string(index=False),
                      "```", ""]
        else:
            stress = []
        ok, reasons = verdict(pooled, placebo_hi, stress)
        verdicts[name] = (ok, reasons)
        lines += [f"### {name} — VERDICT: "
                  f"{'VALIDATED' if ok else 'NOT VALIDATED'}"]
        for r in reasons:
            lines.append(f"- {r}")
        lines.append("")

    lines += ["## Summary", ""]
    for name, (ok, reasons) in verdicts.items():
        lines.append(f"- **{name}**: {'VALIDATED' if ok else 'NOT validated'}"
                     + ("" if ok else f" ({'; '.join(reasons)})"))
    lines += ["", "> A strategy not marked VALIDATED must not be run live.",
              "> Paper-trade validated strategies first; live only with",
              "> throwaway funds and the risk caps in config/default.yaml."]

    (OUT / "REPORT.md").write_text("\n".join(lines))
    print("\n".join(lines[-12:]))
    print(f"\nreport -> {OUT / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

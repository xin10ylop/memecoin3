"""Walk-forward validation + parameter plateau analysis.

Folds are split by POOL LAUNCH TIME (not trade time) so a token never
contributes to both train and test. Selection metric on train requires a
minimum trade count; ties broken toward more trades (plateau preference).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..data.store import PoolData
from ..strategy import ExitRules, make_strategy
from .costs import CostModel
from .engine import RiskParams, run_backtest
from .metrics import log_registry, summarize

__all__ = ["GridSpec", "grid_report", "walk_forward", "eval_config",
           "select_best", "split_by_launch"]


@dataclass
class GridSpec:
    strategy: str
    param_grid: dict[str, list]          # entry-rule params
    exit_grid: dict[str, list]           # ExitRules params
    events: dict | None = None


def _configs(grid: GridSpec):
    p_keys = sorted(grid.param_grid)
    e_keys = sorted(grid.exit_grid)
    for p_vals in itertools.product(*(grid.param_grid[k] for k in p_keys)):
        for e_vals in itertools.product(*(grid.exit_grid[k] for k in e_keys)):
            yield dict(zip(p_keys, p_vals)), dict(zip(e_keys, e_vals))


def split_by_launch(pools: list[PoolData], n_folds: int) -> list[list[PoolData]]:
    # pools with unknown creation time cannot be placed in a launch-time
    # fold without leaking; exclude them from walk-forward entirely
    keyed = sorted((p for p in pools if p.meta.created_ts),
                   key=lambda p: p.meta.created_ts)
    edges = np.linspace(0, len(keyed), n_folds + 1).astype(int)
    return [keyed[edges[i]:edges[i + 1]] for i in range(n_folds)]


def eval_config(pools: list[PoolData], grid: GridSpec, params: dict,
                exit_params: dict, costs: CostModel, risk: RiskParams,
                label: str = "") -> dict:
    strat = make_strategy(grid.strategy, params, ExitRules(**exit_params),
                          events=grid.events)
    res = run_backtest(pools, strat, costs, risk)
    s = summarize(res, label=label)
    s["params"] = params
    s["exit_params"] = exit_params
    log_registry({"strategy": grid.strategy, "label": label, "params": params,
                  "exit_params": exit_params,
                  **{k: s.get(k) for k in ("n_trades", "expectancy_ret",
                                           "expectancy_ci_lo", "total_pnl_usd",
                                           "win_rate", "profit_factor")}})
    return s


def grid_report(pools: list[PoolData], grid: GridSpec, costs: CostModel,
                risk: RiskParams) -> pd.DataFrame:
    """Evaluate EVERY config on the full panel — for plateau/sensitivity
    analysis and honest reporting of all configs tried (not just winners)."""
    rows = []
    for params, exit_params in _configs(grid):
        s = eval_config(pools, grid, params, exit_params, costs, risk)
        row = {**{f"p_{k}": v for k, v in params.items()},
               **{f"x_{k}": v for k, v in exit_params.items()}}
        row.update({k: s.get(k) for k in
                    ("n_trades", "total_pnl_usd", "expectancy_ret",
                     "expectancy_ci_lo", "p_positive", "win_rate",
                     "profit_factor", "max_dd_frac")})
        rows.append(row)
    return pd.DataFrame(rows)


def select_best(train_rows: list[dict], min_trades: int = 20) -> dict | None:
    """Pick config by expectancy among those with enough trades; prefer the
    LOWER CI bound (robustness) over the point estimate."""
    ok = [r for r in train_rows if r.get("n_trades", 0) >= min_trades]
    if not ok:
        return None
    return max(ok, key=lambda r: (r.get("expectancy_ci_lo") or -9e9,
                                  r.get("n_trades", 0)))


def walk_forward(pools: list[PoolData], grid: GridSpec, costs: CostModel,
                 risk: RiskParams, n_folds: int = 3,
                 min_trades: int = 20) -> dict:
    """Anchored walk-forward: train on folds[0..i], test on fold[i+1]."""
    folds = split_by_launch(pools, n_folds)
    # embargo: keep a train pool's trades from bleeding into the test
    # period via a boundary launch. Capped at 90 min: realized holds run
    # 15-60 min, and an embargo of the full max_hold ceiling would consume
    # the entire test fold on a short collection window. (Regime overlap
    # between folds on a short panel is a documented limitation either way.)
    embargo_sec = min(max(grid.exit_grid.get("max_hold_min", [360])) * 60, 5400)
    oos_summaries = []
    picks = []
    pooled_trades = []
    oos_pools: list[PoolData] = []
    for i in range(n_folds - 1):
        train = [p for f in folds[: i + 1] for p in f]
        if not train or not folds[i + 1]:
            picks.append(None)
            continue
        boundary = max(p.meta.created_ts for p in train)
        test = [p for p in folds[i + 1]
                if (p.meta.created_ts or 0) >= boundary + embargo_sec]
        if not test:
            picks.append(None)
            continue
        train_rows = []
        for params, exit_params in _configs(grid):
            s = eval_config(train, grid, params, exit_params, costs, risk)
            train_rows.append(s)
        best = select_best(train_rows, min_trades=min_trades)
        if best is None:
            picks.append(None)
            continue
        picks.append({"fold": i + 1, "params": best["params"],
                      "exit_params": best["exit_params"],
                      "train_expectancy": best["expectancy_ret"],
                      "train_n": best["n_trades"]})
        strat = make_strategy(grid.strategy, best["params"],
                              ExitRules(**best["exit_params"]),
                              events=grid.events)
        res = run_backtest(test, strat, costs, risk)
        oos_summaries.append(summarize(res, label=f"oos_fold_{i + 1}"))
        pooled_trades.extend(res.trades)
        oos_pools.extend(test)
    # pooled OOS: statistics over the CONCATENATED out-of-sample trades —
    # per-fold means weight a 1-trade fold like a 100-trade fold
    pooled = None
    if pooled_trades:
        import pandas as pd

        from .engine import BacktestResult
        pooled_trades.sort(key=lambda t: t.exit_ts)
        eq = risk.starting_usd + np.cumsum([t.pnl_usd for t in pooled_trades])
        pooled_res = BacktestResult(
            trades=pooled_trades,
            equity=pd.Series(
                np.concatenate([[risk.starting_usd], eq]),
                index=[pooled_trades[0].entry_ts]
                      + [t.exit_ts for t in pooled_trades], dtype=float),
            n_candidates=sum(s.get("n_candidates", 0) for s in oos_summaries),
            n_skipped_risk=sum(s.get("n_skipped_risk", 0) for s in oos_summaries),
        )
        pooled = summarize(pooled_res, label="oos_pooled")
    return {"picks": picks, "oos": oos_summaries, "oos_pooled": pooled,
            "oos_pool_addresses": [p.meta.address for p in oos_pools]}

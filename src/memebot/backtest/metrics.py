"""Performance metrics honest about small, fat-tailed, clustered samples.

Trades are NOT iid: multiple trades on one token share its fate. All CIs use
a cluster bootstrap over TOKENS (each draw brings all of a token's trades).
Fragility is quantified by leave-top-k-out expectancy and P&L concentration.
Every summarize() caller should also log_registry() so the number of
configurations ever tried is on the record (multiple-testing honesty).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .engine import BacktestResult


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def _cluster_bootstrap_means(rets: np.ndarray, clusters: np.ndarray,
                             n_boot: int = 5000, seed: int = 7) -> np.ndarray:
    """Bootstrap distribution of mean per-trade return, resampling clusters."""
    uniq = np.unique(clusters)
    by_cluster = [rets[clusters == c] for c in uniq]
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    k = len(by_cluster)
    for b in range(n_boot):
        idx = rng.integers(0, k, size=k)
        sample = np.concatenate([by_cluster[i] for i in idx])
        means[b] = sample.mean()
    return means


def leave_top_k(pnl: np.ndarray, k: int) -> float:
    """Total P&L after removing the k best trades."""
    if len(pnl) <= k:
        return float("nan")
    order = np.sort(pnl)
    return float(order[:-k].sum()) if k > 0 else float(pnl.sum())


def summarize(result: BacktestResult, label: str = "",
              n_boot: int = 5000) -> dict:
    tdf = result.trades_df()
    if tdf.empty:
        return {"label": label, "n_trades": 0,
                "n_candidates": result.n_candidates}
    rets = tdf["ret"].to_numpy()
    pnl = tdf["pnl_usd"].to_numpy()
    pools = tdf["pool"].to_numpy()
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]

    boot = _cluster_bootstrap_means(rets, pools, n_boot=n_boot)
    lo, hi = float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))
    p_pos = float((boot > 0).mean())

    total = float(pnl.sum())
    top5_share = float(np.sort(pnl)[-max(1, int(np.ceil(len(pnl) * 0.05))):].sum()
                       / total) if total > 0 else float("nan")
    span_days = max(1e-9, (tdf["exit_ts"].max() - tdf["entry_ts"].min()) / 86400)
    return {
        "label": label,
        "n_trades": int(len(tdf)),
        "n_tokens": int(len(np.unique(pools))),
        "n_candidates": result.n_candidates,
        "n_skipped_risk": result.n_skipped_risk,
        "total_pnl_usd": total,
        "expectancy_ret": float(rets.mean()),
        "expectancy_ci_lo": lo,
        "expectancy_ci_hi": hi,
        "p_positive": p_pos,
        "median_ret": float(np.median(rets)),
        "win_rate": float((pnl > 0).mean()),
        "profit_factor": float(wins.sum() / -losses.sum())
                          if losses.sum() < 0 else float("inf"),
        "avg_win_ret": float(rets[pnl > 0].mean()) if len(wins) else float("nan"),
        "avg_loss_ret": float(rets[pnl <= 0].mean()) if len(losses) else float("nan"),
        "pnl_minus_top1": leave_top_k(pnl, 1),
        "pnl_minus_top3": leave_top_k(pnl, 3),
        "pnl_minus_top5": leave_top_k(pnl, 5),
        "top5pct_pnl_share": top5_share,
        "max_dd_frac": max_drawdown(result.equity),
        "avg_hold_min": float(tdf["hold_min"].mean()),
        "trades_per_day": float(len(tdf) / span_days),
        "exit_reasons": tdf["reason"].value_counts().to_dict(),
    }


def summary_table(summaries: list[dict]) -> pd.DataFrame:
    cols = ["label", "n_trades", "n_tokens", "total_pnl_usd", "expectancy_ret",
            "expectancy_ci_lo", "expectancy_ci_hi", "p_positive", "win_rate",
            "profit_factor", "median_ret", "pnl_minus_top3",
            "top5pct_pnl_share", "max_dd_frac", "avg_hold_min",
            "trades_per_day"]
    df = pd.DataFrame(summaries)
    return df[[c for c in cols if c in df.columns]]


REGISTRY_PATH = Path("research/results/registry.jsonl")


def log_registry(record: dict, path: Path | None = None) -> None:
    """Append every evaluated configuration to the experiment registry.

    The registry is the denominator for multiple-testing corrections: the
    number of configs ever tried, including losers, must be on record.
    """
    p = path or REGISTRY_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": time.time(), **record}
    with open(p, "a") as fh:
        fh.write(json.dumps(rec, default=str) + "\n")

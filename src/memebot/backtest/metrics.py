"""Performance metrics with small-sample honesty (bootstrap CIs, PSR-style)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import BacktestResult


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def bootstrap_ci(x: np.ndarray, stat=np.mean, n_boot: int = 5000,
                 alpha: float = 0.05, seed: int = 7) -> tuple[float, float]:
    if len(x) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    stats = stat(x[idx], axis=1)
    return (float(np.quantile(stats, alpha / 2)),
            float(np.quantile(stats, 1 - alpha / 2)))


def prob_positive_expectancy(rets: np.ndarray, n_boot: int = 5000,
                             seed: int = 7) -> float:
    """Bootstrap probability that true mean return per trade > 0."""
    if len(rets) < 5:
        return float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(rets), size=(n_boot, len(rets)))
    return float((rets[idx].mean(axis=1) > 0).mean())


def summarize(result: BacktestResult, label: str = "") -> dict:
    tdf = result.trades_df()
    if tdf.empty:
        return {"label": label, "n_trades": 0, "n_candidates": result.n_candidates}
    rets = tdf["ret"].to_numpy()
    pnl = tdf["pnl_usd"].to_numpy()
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]
    lo, hi = bootstrap_ci(rets)
    span_days = max(1e-9, (tdf["exit_ts"].max() - tdf["entry_ts"].min()) / 86400)
    return {
        "label": label,
        "n_trades": int(len(tdf)),
        "n_candidates": result.n_candidates,
        "n_skipped_risk": result.n_skipped_risk,
        "total_pnl_usd": float(pnl.sum()),
        "expectancy_ret": float(rets.mean()),
        "expectancy_ci_lo": lo,
        "expectancy_ci_hi": hi,
        "p_positive": prob_positive_expectancy(rets),
        "median_ret": float(np.median(rets)),
        "win_rate": float((pnl > 0).mean()),
        "profit_factor": float(wins.sum() / -losses.sum()) if losses.sum() < 0 else float("inf"),
        "avg_win_ret": float(rets[pnl > 0].mean()) if len(wins) else float("nan"),
        "avg_loss_ret": float(rets[pnl <= 0].mean()) if len(losses) else float("nan"),
        "max_dd_frac": max_drawdown(result.equity),
        "avg_hold_min": float(tdf["hold_min"].mean()),
        "trades_per_day": float(len(tdf) / span_days),
        "exit_reasons": tdf["reason"].value_counts().to_dict(),
    }


def summary_table(summaries: list[dict]) -> pd.DataFrame:
    cols = ["label", "n_trades", "total_pnl_usd", "expectancy_ret",
            "expectancy_ci_lo", "expectancy_ci_hi", "p_positive", "win_rate",
            "profit_factor", "median_ret", "max_dd_frac", "avg_hold_min",
            "trades_per_day"]
    df = pd.DataFrame(summaries)
    return df[[c for c in cols if c in df.columns]]

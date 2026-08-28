#!/usr/bin/env python3
"""Base-rate analysis of the launch panel (run BEFORE strategy fitting).

Answers the structural questions that bound what any long-only strategy can
achieve on this market:
  * outcome distribution: peak multiple vs first indexed price, final vs first
  * survival: fraction of pools above their first price after N minutes
  * time-to-peak distribution (how long does momentum persist?)
  * conditional slices by liquidity band and dex
  * post-threshold event study: given a pool crossed $15k liquidity + $10k/h
    volume (the bot's minimum tradable gate), what do forward returns from
    THAT moment look like? (this is the actual opportunity set)

Writes research/results/base_rates.md + csvs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from memebot.data.store import load_panel, panel_summary  # noqa: E402

DB = sys.argv[1] if len(sys.argv) > 1 else "data/panel.db"
OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)

HORIZONS_MIN = [5, 15, 30, 60, 120, 240, 480]


def survival_from_index(df: pd.DataFrame, i0: int) -> dict:
    """Forward gross returns from bar i0's close at fixed horizons.

    Pools whose data ends before a horizon contribute their TERMINAL price
    (last close) at that horizon — dropping them would resurrect
    survivorship bias exactly where death matters most."""
    c = df["c"].to_numpy(dtype=float)
    ts = df.index.to_numpy()
    t0, p0 = ts[i0], c[i0]
    out = {}
    for h in HORIZONS_MIN:
        j = np.searchsorted(ts, t0 + h * 60, side="left")
        out[f"fwd_{h}m"] = c[min(j, len(c) - 1)] / p0
    seg = c[i0:]
    out["fwd_peak"] = seg.max() / p0
    out["fwd_trough"] = seg.min() / p0
    ts_seg = ts[i0:]
    out["min_to_peak"] = (ts_seg[np.argmax(seg)] - t0) / 60
    return out


def main() -> int:
    pools = load_panel(DB, min_max_reserve=2000.0, min_bars=30)
    print(f"panel pools loaded: {len(pools)}")
    summ = panel_summary(pools)
    summ.to_csv(OUT / "panel_summary.csv", index=False)

    # ---- unconditional outcomes (from first indexed bar) -------------------
    rows = []
    for p in pools:
        df = p.df
        if len(df) < 30:
            continue
        r = survival_from_index(df, 0)
        r.update(address=p.meta.address, dex=p.meta.dex_id,
                 max_reserve=p.meta.max_reserve_usd, bars=len(df))
        rows.append(r)
    uncond = pd.DataFrame(rows)
    uncond.to_csv(OUT / "unconditional_outcomes.csv", index=False)

    # ---- conditional: first time pool qualifies for the tradable gate ------
    gate_rows = []
    for p in pools:
        df = p.df
        if "reserve_usd" not in df.columns:
            continue
        liq_ok = df["reserve_usd"].fillna(0) >= 15_000
        vol_1h = df["vol_usd"].rolling(60, min_periods=10).sum()
        vol_ok = vol_1h >= 10_000
        qual = (liq_ok & vol_ok).to_numpy()
        idx = np.flatnonzero(qual)
        if len(idx) == 0 or idx[0] >= len(df) - 15:
            continue
        r = survival_from_index(df, int(idx[0]))
        r.update(address=p.meta.address, dex=p.meta.dex_id,
                 qual_age_min=float((df.index[idx[0]] - df.index[0]) / 60),
                 reserve_at_qual=float(df["reserve_usd"].iloc[idx[0]]))
        gate_rows.append(r)
    cond = pd.DataFrame(gate_rows)
    cond.to_csv(OUT / "post_gate_outcomes.csv", index=False)

    # ---- report ------------------------------------------------------------
    def q(s, name):
        s = s.dropna()
        if s.empty:
            return f"{name}: n=0"
        return (f"{name}: n={len(s)} mean={s.mean():.3f} p25={s.quantile(.25):.3f} "
                f"med={s.median():.3f} p75={s.quantile(.75):.3f} "
                f"p95={s.quantile(.95):.3f} frac>1: {(s > 1).mean():.1%}")

    lines = ["# Panel base rates", "",
             f"pools: {len(pools)}  (indexed by GT with >= $2k max reserve, >=30 bars)",
             "", "## Unconditional (from first indexed bar)"]
    if uncond.empty:
        lines.append("- no pools with enough bars yet")
    else:
        for h in HORIZONS_MIN:
            lines.append("- " + q(uncond[f"fwd_{h}m"], f"gross fwd {h}m"))
        lines.append("- " + q(uncond["fwd_peak"], "peak multiple"))
        lines.append("- " + q(uncond["min_to_peak"], "minutes to peak"))
    lines += ["", "## Conditional on crossing tradable gate "
                  "($15k liq & $10k/h vol)"]
    if not cond.empty:
        for h in HORIZONS_MIN:
            lines.append("- " + q(cond[f"fwd_{h}m"], f"gross fwd {h}m"))
        lines.append("- " + q(cond["fwd_peak"], "peak multiple after gate"))
        lines.append("- " + q(cond["min_to_peak"], "minutes to peak after gate"))
        lines.append("- " + q(cond["qual_age_min"], "age at gate (min)"))
    else:
        lines.append("- no pools crossed the gate yet")
    lines += ["", "## By dex (final/first, unconditional)"]
    if not uncond.empty:
        for dex, grp in uncond.groupby("dex", dropna=False):
            lines.append("- " + q(grp["fwd_480m"], f"{dex} fwd 8h"))
    report = "\n".join(lines)
    (OUT / "base_rates.md").write_text(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

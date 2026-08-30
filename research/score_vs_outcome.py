#!/usr/bin/env python3
"""Did blind meme judgment predict what actually happened?

Joins three independent scorers' blind ratings (ticker + name only, no
charts, no outcomes) to the realised fate of each launch. Two questions:

  1. Do the scorers AGREE with each other? If meme sense is systematic,
     independent raters converge; if it is personal intuition, they do
     not — and then it cannot be automated at all.
  2. Do the scores PREDICT outcomes — did it run, did it survive, did it
     attract volume?

Bootstrap CIs throughout; the sample is small and the honest answer may
well be "no signal", which is a result, not a failure.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

R = Path("research/results")
scores = json.loads((R / "scores_raw.json").read_text())
truth = pd.DataFrame(json.loads((R / "scoring_truth.json").read_text()))
names = {d["id"]: d for d in json.loads((R / "scoring_input.json").read_text())}

DIMS = ["meme_quality", "narrative_live", "name_craft", "would_buy"]
frames = []
for i, s in enumerate(scores):
    df = pd.DataFrame(s)[["id"] + DIMS].copy()
    df["scorer"] = i
    frames.append(df)
long = pd.concat(frames)

print("=== 1. DO INDEPENDENT SCORERS AGREE? ===")
for d in DIMS:
    w = long.pivot_table(index="id", columns="scorer", values=d)
    corrs = [w[a].corr(w[b], method="spearman")
             for a in w.columns for b in w.columns if a < b]
    print(f"  {d:16s} pairwise spearman: "
          f"{', '.join(f'{c:+.2f}' for c in corrs)}  mean {np.mean(corrs):+.2f}")

cons = long.groupby("id")[DIMS].mean().reset_index()
m = cons.merge(truth, on="id")
m["doubled"] = (m.peak_mult >= 2).astype(int)
m["survived_1h"] = (m.life_min >= 60).astype(int)
m["log_vol"] = np.log10(m.total_vol.clip(lower=1))
print(f"\nmatched launches: {len(m)}  "
      f"({m.doubled.mean():.0%} doubled, {m.survived_1h.mean():.0%} lived >=1h)")


def boot_corr(x, y, n=4000, seed=5):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        idx = rng.integers(0, len(x), len(x))
        s = pd.Series(x[idx]).corr(pd.Series(y[idx]), method="spearman")
        if np.isfinite(s):
            out.append(s)
    return np.quantile(out, [0.025, 0.975]) if out else (np.nan, np.nan)


print("\n=== 2. DO SCORES PREDICT OUTCOMES? (consensus of 3 scorers) ===")
rows = []
for d in DIMS:
    for tgt in ["peak_mult", "life_min", "log_vol", "doubled"]:
        x = m[d].to_numpy(dtype=float)
        y = m[tgt].to_numpy(dtype=float)
        ic = pd.Series(x).corr(pd.Series(y), method="spearman")
        lo, hi = boot_corr(x, y)
        rows.append({"score": d, "outcome": tgt, "spearman": ic,
                     "ci_lo": lo, "ci_hi": hi,
                     "signif": "YES" if (lo > 0 or hi < 0) else ""})
print(pd.DataFrame(rows).to_string(index=False,
                                   float_format=lambda v: f"{v:+.3f}"))

print("\n=== 3. THE TRADER'S TEST: top-scored vs the rest (would_buy) ===")
for thr in [3, 4, 5]:
    top = m[m.would_buy >= thr]
    rest = m[m.would_buy < thr]
    if len(top) < 3:
        print(f"  would_buy >= {thr}: only {len(top)} launches — too few")
        continue
    print(f"  would_buy >= {thr}: n={len(top):3d} | doubled {top.doubled.mean():.0%} "
          f"vs {rest.doubled.mean():.0%} | median peak {top.peak_mult.median():.2f} "
          f"vs {rest.peak_mult.median():.2f} | median life {top.life_min.median():.0f}m "
          f"vs {rest.life_min.median():.0f}m")

print("\n=== 4. WHAT THE SCORERS LIKED, AND WHAT HAPPENED ===")
top = m.sort_values("would_buy", ascending=False).head(8)
for _, r in top.iterrows():
    nm = names.get(r.id, {})
    print(f"  {nm.get('symbol','?'):14s} {str(nm.get('name',''))[:26]:26s} "
          f"score {r.would_buy:.1f} -> peak {r.peak_mult:.2f}x life "
          f"{r.life_min:5.0f}m vol ${r.total_vol:,.0f}")
print("\n  --- and the biggest actual runners ---")
for _, r in m.sort_values("peak_mult", ascending=False).head(6).iterrows():
    nm = names.get(r.id, {})
    print(f"  {nm.get('symbol','?'):14s} {str(nm.get('name',''))[:26]:26s} "
          f"score {r.would_buy:.1f} -> peak {r.peak_mult:.2f}x life "
          f"{r.life_min:5.0f}m")

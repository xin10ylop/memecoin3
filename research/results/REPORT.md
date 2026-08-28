# Strategy validation report

generated: 2026-08-28T04:16:29.577458+00:00
panel: 99 pools (>= $2k max reserve, >= 5 minute-bars), 277 trending events
snapshot-covered collection windows (UTC): 08-27 14:37..08-27 17:27; 08-28 00:05..08-28 04:15

> Entries are only permitted on bars with fresh snapshot
> coverage (liquidity/FDV/volume verified), i.e. inside the
> collection windows above. Verdicts tighten or flip as the
> collector accumulates more windows — re-run this script to
> regenerate. NOT VALIDATED on a thin panel means 'not enough
> evidence yet', never 'edge confirmed'.

## Defaults vs placebo (1x costs)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
  grad_momentum         1       1.0       8.825254        0.353010          0.353010          0.353010         1.0       1.0            inf    0.353010             NaN                1.0          0.0          32.0            45.0
    dip_reclaim         1       1.0       6.281306        0.251252          0.251252          0.251252         1.0       1.0            inf    0.251252             NaN                1.0          0.0           1.0          1440.0
 attention_cont         0       NaN            NaN             NaN               NaN               NaN         NaN       NaN            NaN         NaN             NaN                NaN          NaN           NaN             NaN
trending_follow         0       NaN            NaN             NaN               NaN               NaN         NaN       NaN            NaN         NaN             NaN                NaN          NaN           NaN             NaN
  placebo_seed0         0       NaN            NaN             NaN               NaN               NaN         NaN       NaN            NaN         NaN             NaN                NaN          NaN           NaN             NaN
  placebo_seed1         0       NaN            NaN             NaN               NaN               NaN         NaN       NaN            NaN         NaN             NaN                NaN          NaN           NaN             NaN
  placebo_seed2         0       NaN            NaN             NaN               NaN               NaN         NaN       NaN            NaN         NaN             NaN                NaN          NaN           NaN             NaN
```

placebo mean expectancy: 0.0000; upper-CI bar to beat: 0.0000

## grad_momentum — full grid (every config tried)
```
 p_min_age_min  p_min_liq  p_min_vol5  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
            15      15000        1000           0.2         1       8.825254         0.35301           0.35301         1.0       1.0            inf          0.0
            15      15000        1000           0.3         1       8.825254         0.35301           0.35301         1.0       1.0            inf          0.0
            15      15000        3000           0.2         1       8.825254         0.35301           0.35301         1.0       1.0            inf          0.0
            15      15000        3000           0.3         1       8.825254         0.35301           0.35301         1.0       1.0            inf          0.0
            15      30000        1000           0.2         1       8.825254         0.35301           0.35301         1.0       1.0            inf          0.0
            15      30000        1000           0.3         1       8.825254         0.35301           0.35301         1.0       1.0            inf          0.0
            15      30000        3000           0.2         1       8.825254         0.35301           0.35301         1.0       1.0            inf          0.0
            15      30000        3000           0.3         1       8.825254         0.35301           0.35301         1.0       1.0            inf          0.0
            30      15000        1000           0.2         0            NaN             NaN               NaN         NaN       NaN            NaN          NaN
            30      15000        1000           0.3         0            NaN             NaN               NaN         NaN       NaN            NaN          NaN
            30      15000        3000           0.2         0            NaN             NaN               NaN         NaN       NaN            NaN          NaN
            30      15000        3000           0.3         0            NaN             NaN               NaN         NaN       NaN            NaN          NaN
            30      30000        1000           0.2         0            NaN             NaN               NaN         NaN       NaN            NaN          NaN
            30      30000        1000           0.3         0            NaN             NaN               NaN         NaN       NaN            NaN          NaN
            30      30000        3000           0.2         0            NaN             NaN               NaN         NaN       NaN            NaN          NaN
            30      30000        3000           0.3         0            NaN             NaN               NaN         NaN       NaN            NaN          NaN
```

### grad_momentum — walk-forward OOS (per fold + pooled)
```
no folds
```

### grad_momentum — VERDICT: NOT VALIDATED
- no pooled out-of-sample trades

## dip_reclaim — full grid (every config tried)
```
 p_min_dip  p_min_run  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
      0.25        0.5           0.2         1       6.281306        0.251252          0.251252         1.0       1.0            inf          0.0
      0.25        0.5           0.3         1       6.281306        0.251252          0.251252         1.0       1.0            inf          0.0
      0.25        1.0           0.2         1       6.281306        0.251252          0.251252         1.0       1.0            inf          0.0
      0.25        1.0           0.3         1       6.281306        0.251252          0.251252         1.0       1.0            inf          0.0
      0.35        0.5           0.2         1       6.281306        0.251252          0.251252         1.0       1.0            inf          0.0
      0.35        0.5           0.3         1       6.281306        0.251252          0.251252         1.0       1.0            inf          0.0
      0.35        1.0           0.2         1       6.281306        0.251252          0.251252         1.0       1.0            inf          0.0
      0.35        1.0           0.3         1       6.281306        0.251252          0.251252         1.0       1.0            inf          0.0
      0.50        0.5           0.2         1       6.281306        0.251252          0.251252         1.0       1.0            inf          0.0
      0.50        0.5           0.3         1       6.281306        0.251252          0.251252         1.0       1.0            inf          0.0
      0.50        1.0           0.2         1       6.281306        0.251252          0.251252         1.0       1.0            inf          0.0
      0.50        1.0           0.3         1       6.281306        0.251252          0.251252         1.0       1.0            inf          0.0
```

### dip_reclaim — walk-forward OOS (per fold + pooled)
```
no folds
```

### dip_reclaim — VERDICT: NOT VALIDATED
- no pooled out-of-sample trades

## trending_follow — full grid (every config tried)
```
 p_min_liq  x_trail_frac  n_trades total_pnl_usd expectancy_ret expectancy_ci_lo p_positive win_rate profit_factor max_dd_frac
     15000          0.25         0          None           None             None       None     None          None        None
     30000          0.25         0          None           None             None       None     None          None        None
```

### trending_follow — walk-forward OOS (per fold + pooled)
```
no folds
```

### trending_follow — VERDICT: NOT VALIDATED
- no pooled out-of-sample trades

## Summary

- **grad_momentum**: NOT validated (no pooled out-of-sample trades)
- **dip_reclaim**: NOT validated (no pooled out-of-sample trades)
- **trending_follow**: NOT validated (no pooled out-of-sample trades)

> A strategy not marked VALIDATED must not be run live.
> Paper-trade validated strategies first; live only with
> throwaway funds and the risk caps in config/default.yaml.
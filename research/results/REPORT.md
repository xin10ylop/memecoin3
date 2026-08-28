# Strategy validation report

generated: 2026-08-28T10:22:38.672082+00:00
panel: 739 pools (>= $2k max reserve, >= 5 minute-bars), 426 trending events
snapshot-covered collection windows (UTC): 08-27 14:37..08-27 17:27; 08-28 00:05..08-28 10:19

> Entries are only permitted on bars with fresh snapshot
> coverage (liquidity/FDV/volume verified), i.e. inside the
> collection windows above. Verdicts tighten or flip as the
> collector accumulates more windows — re-run this script to
> regenerate. NOT VALIDATED on a thin panel means 'not enough
> evidence yet', never 'edge confirmed'.

## Defaults vs placebo (1x costs)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
  grad_momentum        85        85     473.191353        0.222678          0.125166          0.327748      1.0000  0.635294       6.173582    0.033999      330.078725           0.440616    -0.010520     26.788235      105.608283
    dip_reclaim        28        23      74.022302        0.105746         -0.054081          0.289777      0.9016  0.392857       2.008109   -0.097933      -11.170710           0.822239    -0.020307     15.392857       36.000000
 attention_cont         8         7      57.338569        0.286693          0.029613          0.598858      0.9856  0.625000       9.044354    0.114731       -1.391251           0.355601    -0.004055    147.750000       13.457944
trending_follow        47        46     131.010945        0.111499          0.005003          0.240547      0.9808  0.489362       2.637976   -0.012872       39.050276           0.701931    -0.025613     38.042553       58.852174
   regime_gated       105       103     358.185649        0.136452          0.050656          0.239290      0.9998  0.552381       3.515228    0.023700      177.789817           0.744392    -0.020690     25.800000      139.098436
   boost_follow         8         8     -16.685944       -0.083430         -0.184599          0.042737      0.1024  0.250000       0.331813   -0.170773      -24.679476                NaN    -0.016686      6.000000       11.851852
  placebo_seed0        34        34     270.021199        0.317672          0.188074          0.457519      1.0000  0.735294      13.552586    0.345551      177.562605           0.265524    -0.005251     45.205882       44.958678
  placebo_seed1        30        30     197.501859        0.263336          0.042389          0.514956      0.9938  0.500000       5.031088   -0.001786       51.356130           0.530006    -0.010538     57.166667       38.918919
  placebo_seed2        25        25     129.207439        0.206732          0.073572          0.358126      0.9996  0.640000       5.993137    0.124151       62.806496           0.377759    -0.010656     32.800000       35.053554
```

placebo mean expectancy: 0.2626; upper-CI bar to beat: 0.4435

## grad_momentum — full grid (every config tried)
```
 p_min_age_min  p_min_liq  p_min_vol5  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
            15      15000        1000           0.2        98     521.761499        0.212964          0.128664      1.0000  0.642857       7.475211    -0.011559
            15      15000        1000           0.3        98     484.735393        0.197851          0.115730      1.0000  0.622449       6.163781    -0.012896
            15      15000        3000           0.2        85     492.345690        0.231692          0.132556      1.0000  0.635294       6.392731    -0.011260
            15      15000        3000           0.3        85     450.639731        0.212066          0.115620      1.0000  0.611765       5.563354    -0.011762
            15      30000        1000           0.2        95     399.083045        0.168035          0.088532      1.0000  0.610526       5.368948    -0.011559
            15      30000        1000           0.3        95     369.056669        0.155392          0.078350      1.0000  0.589474       4.526944    -0.012896
            15      30000        3000           0.2        82     372.747427        0.181828          0.089923      1.0000  0.597561       4.765701    -0.013202
            15      30000        3000           0.3        82     335.189000        0.163507          0.073212      1.0000  0.573171       4.066943    -0.013684
            30      15000        1000           0.2        32     260.523411        0.325654          0.151617      1.0000  0.718750      16.467676    -0.004719
            30      15000        1000           0.3        32     230.272612        0.287841          0.115292      1.0000  0.625000       8.467156    -0.005576
            30      15000        3000           0.2        30     258.176455        0.344235          0.158188      1.0000  0.733333      16.831864    -0.004301
            30      15000        3000           0.3        30     227.925657        0.303901          0.119085      1.0000  0.633333       8.521711    -0.005576
            30      30000        1000           0.2        31     248.398797        0.320515          0.144423      1.0000  0.709677      15.747819    -0.006464
            30      30000        1000           0.3        31     220.964087        0.285115          0.108978      0.9998  0.612903       8.165304    -0.008198
            30      30000        3000           0.2        29     246.051841        0.339382          0.148528      1.0000  0.724138      16.088360    -0.006051
            30      30000        3000           0.3        29     218.617132        0.301541          0.111292      1.0000  0.620690       8.214523    -0.007779
```

### grad_momentum — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_2         4         4      13.499782        0.134998         -0.054565          0.358322      0.8724       0.5       5.948131    0.071235       -2.186595           0.898134     -0.00216           2.0       85.970149
oos_pooled         4         4      13.499782        0.134998         -0.054565          0.358322      0.8724       0.5       5.948131    0.071235       -2.186595           0.898134     -0.00216           2.0       85.970149
```

### grad_momentum — cost stress (OOS pools only, last pick)
```
           label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
grad_momentum@1x         4         4      13.499782        0.134998         -0.054565          0.358322      0.8724       0.5       5.948131    0.071235       -2.186595           0.898134    -0.002160           2.0       85.970149
grad_momentum@2x         4         4      10.655969        0.106560         -0.079091          0.326339      0.8092       0.5       3.694594    0.044246       -2.814387           1.056501    -0.002783           2.0       85.970149
grad_momentum@3x         4         4       7.846662        0.078467         -0.103322          0.294685      0.7876       0.5       2.518880    0.017603       -3.433769           1.325439    -0.003398           2.0       85.970149
```

### grad_momentum — VERDICT: NOT VALIDATED
- only 4 OOS trades (<30)
- only 4 OOS tokens (<20)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.4435)
- pooled OOS P&L carried entirely by top-3 trades

## dip_reclaim — full grid (every config tried)
```
 p_min_dip  p_min_run  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
      0.25        0.5           0.2        41      66.748223        0.065120         -0.038649      0.8744  0.365854       1.674614    -0.025039
      0.25        0.5           0.3        41      90.926073        0.088708         -0.042766      0.8954  0.365854       1.775080    -0.024469
      0.25        1.0           0.2        35      48.462761        0.055386         -0.058740      0.8202  0.342857       1.571803    -0.030573
      0.25        1.0           0.3        35      74.602931        0.085260         -0.057720      0.8558  0.342857       1.737466    -0.034953
      0.35        0.5           0.2        32      78.580440        0.098226         -0.025803      0.9418  0.437500       2.114337    -0.018723
      0.35        0.5           0.3        32     102.697272        0.128372         -0.022735      0.9432  0.406250       2.247403    -0.015967
      0.35        1.0           0.2        28      62.956086        0.089937         -0.043178      0.9026  0.428571       2.004461    -0.018047
      0.35        1.0           0.3        28      87.072917        0.124390         -0.048041      0.9154  0.392857       2.168958    -0.020246
      0.50        0.5           0.2        21      22.300177        0.042477         -0.088799      0.7024  0.380952       1.423478    -0.029945
      0.50        0.5           0.3        21      24.132243        0.045966         -0.104480      0.6804  0.285714       1.404668    -0.022549
      0.50        1.0           0.2        20      27.691453        0.055383         -0.077287      0.7608  0.400000       1.585836    -0.029945
      0.50        1.0           0.3        20      29.523519        0.059047         -0.091742      0.7376  0.300000       1.544279    -0.022549
```

### dip_reclaim — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_2         5         5      14.512157        0.116097          -0.19178          0.606294      0.6758       0.4       2.098473   -0.097998      -10.761268           1.841721    -0.013211           2.2       69.902913
oos_pooled         5         5      14.512157        0.116097          -0.19178          0.606294      0.6758       0.4       2.098473   -0.097998      -10.761268           1.841721    -0.013211           2.2       69.902913
```

### dip_reclaim — cost stress (OOS pools only, last pick)
```
         label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
dip_reclaim@1x         5         5      14.512157        0.116097         -0.191780          0.606294      0.6758       0.4       2.098473   -0.097998      -10.761268           1.841721    -0.013211           2.2       69.902913
dip_reclaim@2x         5         5       9.377107        0.075017         -0.224237          0.570001      0.6750       0.4       1.568066   -0.199381      -11.522535           2.727304    -0.016507           2.2       69.902913
dip_reclaim@3x         5         5       4.338790        0.034710         -0.266307          0.523953      0.5490       0.2       1.215893   -0.244399      -13.620338           5.631926    -0.019730           2.2       69.902913
```

### dip_reclaim — VERDICT: NOT VALIDATED
- only 5 OOS trades (<30)
- only 5 OOS tokens (<20)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.4435)
- pooled OOS P&L carried entirely by top-3 trades

## trending_follow — full grid (every config tried)
```
 p_min_liq  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
     15000          0.25        49     126.518274        0.103280         -0.000891      0.9734  0.489796       2.490320    -0.025712
     30000          0.25        47     131.010945        0.111499          0.005003      0.9808  0.489362       2.637976    -0.025613
```

### trending_follow — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_2        20        20     -22.753936       -0.045508         -0.099811          0.011703      0.0578      0.35       0.386839   -0.024176      -34.233539                NaN    -0.023323           4.6      154.010695
oos_pooled        20        20     -22.753936       -0.045508         -0.099811          0.011703      0.0578      0.35       0.386839   -0.024176      -34.233539                NaN    -0.023323           4.6      154.010695
```

### trending_follow — cost stress (OOS pools only, last pick)
```
             label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
trending_follow@1x        20        20     -22.753936       -0.045508         -0.099811          0.011703      0.0578      0.35       0.386839   -0.024176      -34.233539                NaN    -0.023323           4.6      154.010695
trending_follow@2x        20        20     -36.301352       -0.072603         -0.126778         -0.015448      0.0072      0.25       0.217203   -0.048530      -45.735921                NaN    -0.036301           4.6      154.010695
trending_follow@3x        20        20     -49.667483       -0.099335         -0.154767         -0.042485      0.0008      0.10       0.131074   -0.073007      -57.077593                NaN    -0.049667           4.6      154.010695
```

### trending_follow — VERDICT: NOT VALIDATED
- only 20 OOS trades (<30)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.4435)
- dies at 2x costs (OOS)
- pooled OOS P&L carried entirely by top-3 trades

## regime_gated — full grid (every config tried)
```
 p_min_cohort_mom  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
             0.00           0.2       120     462.583911        0.154195          0.068710      1.0000  0.558333       4.191619    -0.018516
             0.00           0.3       114     391.227361        0.137273          0.053229      0.9996  0.552632       3.594391    -0.016915
             0.02           0.2       106     381.911120        0.144117          0.057735      1.0000  0.547170       3.935863    -0.019104
             0.02           0.3       105     328.051951        0.124972          0.045731      0.9994  0.571429       3.205982    -0.018784
             0.05           0.2        98     356.946787        0.145693          0.058801      1.0000  0.561224       4.242143    -0.012705
             0.05           0.3       101     349.365721        0.138363          0.051663      1.0000  0.584158       3.798766    -0.018206
```

### regime_gated — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        20        20     179.425627        0.358851          0.057621          0.750685      0.9974  0.600000       8.262866    0.073841       28.174511           0.428454    -0.010889     64.950000       59.751037
oos_fold_2        54        53     159.165153        0.117900          0.020130          0.244910      0.9944  0.574074       3.534987    0.024672       48.998563           0.692153    -0.013669      5.870370      405.000000
oos_pooled        74        73     338.590781        0.183022          0.067655          0.322274      1.0000  0.581081       4.869968    0.026237      145.147666           0.639717    -0.012095     21.837838      177.896494
```

### regime_gated — cost stress (OOS pools only, last pick)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
regime_gated@1x        75        74     318.949095        0.170106          0.062676          0.294248      1.0000  0.586667       4.788353    0.030253      145.967662           0.613282    -0.015759     20.573333       185.56701
regime_gated@2x        75        74     246.248901        0.131333          0.025789          0.253752      0.9956  0.506667       3.248503    0.000375       78.633337           0.768209    -0.035526     20.573333       185.56701
regime_gated@3x        75        74     174.525987        0.093081         -0.010127          0.214040      0.9542  0.346667       2.164739   -0.038025       12.190565           1.047604    -0.059947     20.573333       185.56701
```

### regime_gated — VERDICT: NOT VALIDATED
- does not beat placebo upper CI (0.4435)

## boost_follow — full grid (every config tried)
```
 p_min_liq  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
     15000          0.25         8     -16.685944        -0.08343         -0.184599      0.1024      0.25       0.331813    -0.016686
```

### boost_follow — walk-forward OOS (per fold + pooled)
```
no folds
```

### boost_follow — VERDICT: NOT VALIDATED
- no pooled out-of-sample trades

## Summary

- **grad_momentum**: NOT validated (only 4 OOS trades (<30); only 4 OOS tokens (<20); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.4435); pooled OOS P&L carried entirely by top-3 trades)
- **dip_reclaim**: NOT validated (only 5 OOS trades (<30); only 5 OOS tokens (<20); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.4435); pooled OOS P&L carried entirely by top-3 trades)
- **trending_follow**: NOT validated (only 20 OOS trades (<30); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.4435); dies at 2x costs (OOS); pooled OOS P&L carried entirely by top-3 trades)
- **regime_gated**: NOT validated (does not beat placebo upper CI (0.4435))
- **boost_follow**: NOT validated (no pooled out-of-sample trades)

> A strategy not marked VALIDATED must not be run live.
> Paper-trade validated strategies first; live only with
> throwaway funds and the risk caps in config/default.yaml.
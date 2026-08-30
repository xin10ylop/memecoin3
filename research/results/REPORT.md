# Strategy validation report

generated: 2026-08-30T05:23:20.787905+00:00
panel: 4053 pools (>= $2k max reserve, >= 5 minute-bars), 1244 trending events
snapshot-covered collection windows (UTC): 08-27 14:37..08-27 17:27; 08-28 00:05..08-28 12:15; 08-28 15:28..08-30 05:14

> Entries are only permitted on bars with fresh snapshot
> coverage (liquidity/FDV/volume verified), i.e. inside the
> collection windows above. Verdicts tighten or flip as the
> collector accumulates more windows — re-run this script to
> regenerate. NOT VALIDATED on a thin panel means 'not enough
> evidence yet', never 'edge confirmed'.

## Defaults vs placebo (1x costs)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
  grad_momentum        40        40      79.096975        0.079097         -0.087048          0.302624      0.7586  0.225000       1.681671   -0.165388      -68.351228           1.587525    -0.009879      6.900000       15.686275
    dip_reclaim        32        26      -8.546617       -0.010683         -0.085453          0.085491      0.3822  0.343750       0.886137   -0.124403      -52.802326                NaN    -0.028105      4.406250       14.213448
 attention_cont         5         4      61.194037        0.489552          0.133035          0.827980      1.0000  0.800000      21.962485    0.753990        0.945287           0.342415    -0.005623    193.600000        3.873050
trending_follow        31        31      56.762573        0.073242         -0.098539          0.338594      0.6962  0.193548       1.693212   -0.165195      -70.486929           1.883211    -0.041972     28.322581       12.163488
   regime_gated        34        33      26.276900        0.030914         -0.100219          0.257084      0.5972  0.235294       1.298265   -0.149788      -70.404979           3.338485    -0.013230     16.205882       13.772152
   boost_follow        13        13      -2.590109       -0.007970         -0.116887          0.127864      0.4240  0.307692       0.916074   -0.118321      -28.833167                NaN    -0.014948      3.000000        6.196624
   composite_v2         8         8      -6.157873       -0.030789         -0.143827          0.108118      0.3110  0.250000       0.697919   -0.130079      -18.960265                NaN    -0.006731      9.125000        5.059289
    knife_catch       135       132     484.278978        0.143335          0.028674          0.279980      0.9962  0.370370       2.595794   -0.106327      186.015493           0.989997    -0.023726      1.785185       52.597403
  placebo_seed0        14        13      58.790014        0.167971         -0.022874          0.393461      0.9542  0.500000       3.450378   -0.020989       -4.712594           0.368154    -0.009958     25.785714        6.808511
  placebo_seed1        16        16      50.091891        0.125230         -0.076627          0.435279      0.8016  0.437500       2.728683   -0.049971      -22.161360           1.024658    -0.021084      3.500000        7.775903
  placebo_seed2         7         6      -4.423758       -0.025279         -0.143594          0.149970      0.3594  0.428571       0.732762   -0.165356      -16.553654                NaN    -0.019644      6.428571        3.782364
```

placebo mean expectancy: 0.0893; upper-CI bar to beat: 0.3262

## grad_momentum — full grid (every config tried)
```
 p_min_age_min  p_min_liq  p_min_vol5  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
            15      15000        1000           0.2        36      29.812085        0.033125         -0.098148      0.6424  0.277778       1.258547    -0.013142
            15      15000        1000           0.3        33     -21.650452       -0.026243         -0.146677      0.3334  0.181818       0.830857    -0.014684
            15      15000        3000           0.2        37      20.739521        0.022421         -0.105076      0.5840  0.270270       1.164517    -0.014451
            15      15000        3000           0.3        36     -22.200742       -0.024667         -0.141079      0.3334  0.194444       0.840269    -0.014945
            15      30000        1000           0.2        29       0.984677        0.001358         -0.146711      0.4578  0.241379       1.009498    -0.016928
            15      30000        1000           0.3        27     -28.219582       -0.041807         -0.179096      0.2816  0.148148       0.747003    -0.022946
            15      30000        3000           0.2        29      -5.107226       -0.007044         -0.157292      0.4230  0.206897       0.953385    -0.017928
            15      30000        3000           0.3        28     -34.178519       -0.048826         -0.180179      0.2516  0.142857       0.709119    -0.024233
            30      15000        1000           0.2        11      62.462956        0.227138         -0.033889      0.9358  0.636364       5.927228    -0.010918
            30      15000        1000           0.3        11      34.135265        0.124128         -0.121637      0.7636  0.272727       2.282346    -0.019011
            30      15000        3000           0.2        11      62.462956        0.227138         -0.033889      0.9358  0.636364       5.927228    -0.007908
            30      15000        3000           0.3        11      34.135265        0.124128         -0.121637      0.7636  0.272727       2.282346    -0.014823
            30      30000        1000           0.2        10      50.338342        0.201353         -0.063380      0.8412  0.600000       4.970809    -0.007935
            30      30000        1000           0.3        10      24.826740        0.099307         -0.149193      0.6946  0.200000       1.932656    -0.014841
            30      30000        3000           0.2        10      50.338342        0.201353         -0.063380      0.8412  0.600000       4.970809    -0.007949
            30      30000        3000           0.3        10      24.826740        0.099307         -0.149193      0.6946  0.200000       1.932656    -0.014869
```

### grad_momentum — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1         7         7     -32.739566       -0.187083         -0.210142         -0.158497      0.0000  0.000000       0.000000   -0.215222      -21.561337                NaN    -0.019317      0.428571        8.102894
oos_fold_2         7         7       4.136498        0.023637         -0.197481          0.412014      0.5736  0.142857       1.169230   -0.214592      -21.536496           6.909116    -0.016051      3.428571       10.059880
oos_pooled        14        14     -28.603068       -0.081723         -0.197865          0.122800      0.2210  0.071429       0.499794   -0.214907      -54.276062                NaN    -0.019317      1.928571        8.445748
```

### grad_momentum — cost stress (OOS pools only, last pick)
```
           label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
grad_momentum@1x        16        16     -15.596071       -0.038990         -0.161563          0.187402      0.2686    0.0625       0.718150   -0.165715      -52.428169                NaN    -0.016283          1.75        9.434889
grad_momentum@2x        16        16     -24.018153       -0.060045         -0.178905          0.160292      0.2684    0.0625       0.613987   -0.181430      -58.010130                NaN    -0.025834          1.75        9.434889
grad_momentum@3x        16        16     -35.242257       -0.088106         -0.197893          0.122525      0.2684    0.0625       0.510103   -0.197217      -64.375106                NaN    -0.080556          1.50        9.434889
```

### grad_momentum — VERDICT: NOT VALIDATED
- only 14 OOS trades (<30)
- only 14 OOS tokens (<20)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.3262)
- dies at 2x costs (OOS)
- pooled OOS P&L carried entirely by top-3 trades

## dip_reclaim — full grid (every config tried)
```
 p_min_dip  p_min_run  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
      0.25        0.5           0.2        49     -59.555260       -0.048617         -0.112775      0.0904  0.285714       0.601375    -0.026582
      0.25        0.5           0.3        48     -61.538840       -0.051282         -0.143499      0.1602  0.208333       0.661589    -0.030637
      0.25        1.0           0.2        44     -54.740699       -0.049764         -0.118869      0.0994  0.272727       0.595102    -0.039431
      0.25        1.0           0.3        43     -50.291829       -0.046783         -0.145334      0.2038  0.209302       0.691011    -0.045486
      0.35        0.5           0.2        33      -8.040224       -0.009746         -0.100095      0.4110  0.333333       0.917823    -0.018723
      0.35        0.5           0.3        33       9.292856        0.011264         -0.114562      0.5274  0.303030       1.083319    -0.018763
      0.35        1.0           0.2        31     -11.778435       -0.015198         -0.110092      0.3688  0.322581       0.872595    -0.019058
      0.35        1.0           0.3        31       6.847237        0.008835         -0.126105      0.5070  0.290323       1.064510    -0.024681
      0.50        0.5           0.2        20     -13.427855       -0.026856         -0.134549      0.3042  0.350000       0.782526    -0.030398
      0.50        0.5           0.3        20      -7.240715       -0.014481         -0.149737      0.3974  0.250000       0.895052    -0.031242
      0.50        1.0           0.2        19      -8.036579       -0.016919         -0.124522      0.3614  0.368421       0.857389    -0.029945
      0.50        1.0           0.3        19      -1.849439       -0.003894         -0.140112      0.4392  0.263158       0.970922    -0.026039
```

### dip_reclaim — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1         4         4       6.235735        0.062357         -0.215402          0.340117      0.6836  0.500000       1.578986    0.046241       -5.385751           1.492915    -0.005861          1.25       11.925466
oos_fold_2         5         4     -25.019781       -0.200158         -0.215445         -0.188392      0.0000  0.000000       0.000000   -0.203983      -10.772260                NaN    -0.025395          4.40       14.428858
oos_pooled         9         8     -18.784046       -0.083485         -0.208397          0.089519      0.1354  0.222222       0.475158   -0.203983      -31.693606                NaN    -0.022140          3.00        9.678865
```

### dip_reclaim — cost stress (OOS pools only, last pick)
```
         label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
dip_reclaim@1x         9         8     -16.306258       -0.072472         -0.165701          0.061359      0.1224  0.222222       0.437248   -0.165751      -24.879678                NaN    -0.018680      2.333333        9.678865
dip_reclaim@2x         9         8     -20.786828       -0.092386         -0.181728          0.035881      0.0774  0.222222       0.345820   -0.181502      -27.259356                NaN    -0.022989      2.111111        9.678865
dip_reclaim@3x         9         8     -25.202599       -0.112012         -0.197593          0.010865      0.0394  0.222222       0.270296   -0.197253      -29.639034                NaN    -0.029191      2.111111        9.678865
```

### dip_reclaim — VERDICT: NOT VALIDATED
- only 9 OOS trades (<30)
- only 8 OOS tokens (<20)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.3262)
- dies at 2x costs (OOS)
- pooled OOS P&L carried entirely by top-3 trades

## trending_follow — full grid (every config tried)
```
 p_min_liq  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
     15000          0.25        33      -9.225035       -0.011182         -0.139494      0.4214  0.242424       0.921797    -0.052228
     30000          0.25        27      14.300861        0.021186         -0.135400      0.5600  0.259259       1.152106    -0.041450
```

### trending_follow — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1         5         5     -20.016129       -0.160129         -0.215833         -0.082151         0.0       0.0            0.0   -0.215386      -10.797215                NaN    -0.020176      1.000000        6.005004
oos_fold_2         7         7     -33.022567       -0.188700         -0.215247         -0.151734         0.0       0.0            0.0   -0.215093      -21.527424                NaN    -0.027079      2.285714        9.473684
oos_pooled        12        12     -53.038695       -0.176796         -0.208413         -0.139986         0.0       0.0            0.0   -0.215107      -46.618627                NaN    -0.027211      1.750000        6.906475
```

### trending_follow — cost stress (OOS pools only, last pick)
```
             label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
trending_follow@1x        11        11     -39.005183       -0.141837         -0.162946         -0.114520         0.0       0.0            0.0   -0.165614      -32.585115                NaN    -0.020412      1.909091        6.330935
trending_follow@2x        11        11     -44.215661       -0.160784         -0.179609         -0.134932         0.0       0.0            0.0   -0.181229      -35.995715                NaN    -0.038450      1.909091        6.330935
trending_follow@3x        11        11     -49.396769       -0.179625         -0.196476         -0.155503         0.0       0.0            0.0   -0.196843      -39.398327                NaN    -0.096131      1.909091        6.330935
```

### trending_follow — VERDICT: NOT VALIDATED
- only 12 OOS trades (<30)
- only 12 OOS tokens (<20)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.3262)
- dies at 2x costs (OOS)
- pooled OOS P&L carried entirely by top-3 trades

## regime_gated — full grid (every config tried)
```
 p_min_cohort_mom  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
             0.00           0.2        50      25.317603        0.020254         -0.083569      0.6154  0.240000       1.172139    -0.015890
             0.00           0.3        41      -6.327091       -0.006173         -0.130640      0.4346  0.170732       0.958996    -0.021601
             0.02           0.2        31       5.100468        0.006581         -0.108660      0.4954  0.290323       1.058538    -0.018105
             0.02           0.3        27     -22.831180       -0.033824         -0.144703      0.2746  0.222222       0.765996    -0.022289
             0.05           0.2        29      12.463981        0.017192         -0.108620      0.5478  0.344828       1.150159    -0.014774
             0.05           0.3        26      33.345337        0.051301         -0.106526      0.6872  0.307692       1.384460    -0.017751
```

### regime_gated — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1         2         2       -2.66186       -0.053237         -0.215585          0.109110      0.2338  0.500000       0.506114   -0.053237             NaN                NaN    -0.017004      1.000000        2.550930
oos_fold_2         9         9       -8.42106       -0.037427         -0.171281          0.128723      0.3100  0.222222       0.686767   -0.122318      -26.193522                NaN    -0.021317      1.444444       12.558140
oos_pooled        11        11      -11.08292       -0.040302         -0.154417          0.098799      0.2662  0.272727       0.656598   -0.122318      -32.273923                NaN    -0.027982      1.363636        6.633166
```

### regime_gated — cost stress (OOS pools only, last pick)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
regime_gated@1x        13        13     -18.736608       -0.057651         -0.141481          0.043663      0.1150  0.230769       0.487535   -0.165749      -36.561729                NaN    -0.018087      1.153846        7.839196
regime_gated@2x        13        13     -25.879733       -0.079630         -0.161283          0.017447      0.0488  0.230769       0.373617   -0.181499      -41.316180                NaN    -0.040755      1.153846        7.839196
regime_gated@3x        14        14     -40.823285       -0.116638         -0.194330         -0.027333      0.0064  0.214286       0.242712   -0.198332      -53.907179                NaN    -0.094364      0.857143        8.442211
```

### regime_gated — VERDICT: NOT VALIDATED
- only 11 OOS trades (<30)
- only 11 OOS tokens (<20)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.3262)
- dies at 2x costs (OOS)
- pooled OOS P&L carried entirely by top-3 trades

## boost_follow — full grid (every config tried)
```
 p_min_liq  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
     15000          0.25        12     -17.001682       -0.056672         -0.168578      0.1986      0.25       0.558526    -0.020141
```

### boost_follow — walk-forward OOS (per fold + pooled)
```
no folds
```

### boost_follow — VERDICT: NOT VALIDATED
- no pooled out-of-sample trades

## composite_v2 — full grid (every config tried)
```
 p_max_dd  p_max_rv30  p_min_turnover  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
     0.12        0.08            0.02          0.15         9      24.256111        0.107805         -0.126400      0.7598  0.333333       2.140895    -0.012499
     0.12        0.08            0.02          0.20         7      -6.134616       -0.035055         -0.197049      0.3308  0.285714       0.737169    -0.013921
     0.12        0.08            0.08          0.15         7       3.232173        0.018470         -0.152056      0.6168  0.285714       1.184461    -0.012499
     0.12        0.08            0.08          0.20         6      -1.134604       -0.007564         -0.194051      0.4274  0.333333       0.938137    -0.013921
     0.12       99.00            0.02          0.15        26      30.562685        0.047020         -0.062713      0.7774  0.346154       1.510263    -0.016403
     0.12       99.00            0.02          0.20        23       6.896405        0.011994         -0.085872      0.5868  0.391304       1.104759    -0.011631
     0.12       99.00            0.08          0.15        24       9.538747        0.015898         -0.075521      0.6206  0.333333       1.169857    -0.016403
     0.12       99.00            0.08          0.20        22      11.896417        0.021630         -0.081946      0.6552  0.409091       1.195565    -0.011631
     0.25        0.08            0.02          0.15         9      27.439064        0.121951         -0.095643      0.8188  0.333333       2.517845    -0.012499
     0.25        0.08            0.02          0.20         7      -3.138639       -0.017935         -0.174503      0.3822  0.285714       0.845726    -0.013921
     0.25        0.08            0.08          0.15         8       2.676756        0.013384         -0.133807      0.5652  0.250000       1.148070    -0.012499
     0.25        0.08            0.08          0.20         7      -3.138639       -0.017935         -0.174503      0.3822  0.285714       0.845726    -0.013921
     0.25       99.00            0.02          0.15        27      28.306200        0.041935         -0.062369      0.7644  0.333333       1.455432    -0.019794
     0.25       99.00            0.02          0.20        23      12.890329        0.022418         -0.077547      0.6586  0.391304       1.207050    -0.011626
     0.25       99.00            0.08          0.15        26       3.543892        0.005452         -0.078945      0.5398  0.307692       1.057019    -0.019794
     0.25       99.00            0.08          0.20        23      12.890329        0.022418         -0.077547      0.6586  0.391304       1.207050    -0.011626
```

### composite_v2 — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1         2         2      -9.217069       -0.184341         -0.215439         -0.153244         0.0       0.0            0.0   -0.184341             NaN                NaN    -0.008737      0.500000       23.801653
oos_fold_2         6         6     -19.909834       -0.132732         -0.158536         -0.100460         0.0       0.0            0.0   -0.142827      -12.459074                NaN    -0.010085      1.166667        9.919633
oos_pooled         8         8     -29.126903       -0.145635         -0.175665         -0.116043         0.0       0.0            0.0   -0.159497      -21.676143                NaN    -0.009714      1.000000        8.700906
```

### composite_v2 — cost stress (OOS pools only, last pick)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
composite_v2@1x         8         8     -26.557398       -0.132787         -0.157703         -0.107362         0.0       0.0            0.0   -0.142827      -19.606027                NaN    -0.009618           1.0        8.700906
composite_v2@2x         8         8     -30.697903       -0.153490         -0.174900         -0.131045         0.0       0.0            0.0   -0.163113      -21.834980                NaN    -0.019997           1.0        8.700906
composite_v2@3x         8         8     -34.803166       -0.174016         -0.192050         -0.154245         0.0       0.0            0.0   -0.183229      -24.055430                NaN    -0.035104           1.0        8.700906
```

### composite_v2 — VERDICT: NOT VALIDATED
- only 8 OOS trades (<30)
- only 8 OOS tokens (<20)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.3262)
- dies at 2x costs (OOS)
- pooled OOS P&L carried entirely by top-3 trades

## knife_catch — full grid (every config tried)
```
 p_min_dip  p_use_regime  x_max_hold_min  x_stop_frac  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
      0.30             0              60         0.90           0.9        48    -356.095337       -0.297182         -0.450813      0.0014  0.208333       0.272459    -0.080839
      0.30             0              60         0.35           0.9        83    -393.101546       -0.189699         -0.264792      0.0004  0.084337       0.273002    -0.040359
      0.30             0             120         0.90           0.9        42    -256.029889       -0.244336         -0.465473      0.0354  0.190476       0.444265    -0.076065
      0.30             0             120         0.35           0.9        82    -353.346565       -0.172619         -0.268038      0.0044  0.073171       0.337245    -0.038966
      0.30             1              60         0.90           0.9        30    -202.979095       -0.271336         -0.445252      0.0068  0.166667       0.286830    -0.046659
      0.30             1              60         0.35           0.9        45    -207.286595       -0.184720         -0.280542      0.0022  0.066667       0.269589    -0.036387
      0.30             1             120         0.90           0.9        26    -177.639885       -0.274097         -0.514000      0.0360  0.115385       0.375562    -0.048391
      0.30             1             120         0.35           0.9        44    -168.624439       -0.153770         -0.276516      0.0330  0.068182       0.387854    -0.036387
      0.35             0              60         0.90           0.9        52    -388.613398       -0.299336         -0.456912      0.0004  0.211538       0.276452    -0.089919
      0.35             0              60         0.35           0.9        82    -412.068038       -0.201264         -0.280688      0.0002  0.073171       0.249240    -0.039097
      0.35             0             120         0.90           0.9        43    -256.999621       -0.239556         -0.456190      0.0372  0.186047       0.438727    -0.073800
      0.35             0             120         0.35           0.9        81    -365.143057       -0.180576         -0.278455      0.0052  0.061728       0.324445    -0.038576
      0.35             1              60         0.90           0.9        32    -256.644396       -0.321459         -0.479444      0.0006  0.125000       0.227673    -0.063431
      0.35             1              60         0.35           0.9        44    -231.390494       -0.210831         -0.309806      0.0012  0.045455       0.224710    -0.036837
      0.35             1             120         0.90           0.9        26    -138.947936       -0.214571         -0.466934      0.0810  0.115385       0.474676    -0.058126
      0.35             1             120         0.35           0.9        44    -196.053470       -0.178706         -0.307641      0.0196  0.045455       0.343109    -0.036517
      0.45             0              60         0.90           0.9        51    -329.477442       -0.258824         -0.398910      0.0024  0.215686       0.289352    -0.072400
      0.45             0              60         0.35           0.9        74    -373.021313       -0.201916         -0.281747      0.0010  0.067568       0.225667    -0.065613
      0.45             0             120         0.90           0.9        41    -182.554215       -0.178612         -0.415902      0.1004  0.195122       0.551046    -0.085231
      0.45             0             120         0.35           0.9        74    -362.964621       -0.196480         -0.283877      0.0020  0.054054       0.247747    -0.066783
      0.45             1              60         0.90           0.9        26    -187.462142       -0.289208         -0.452118      0.0072  0.153846       0.228171    -0.046642
      0.45             1              60         0.35           0.9        35    -196.736282       -0.225439         -0.333486      0.0032  0.057143       0.202480    -0.028640
      0.45             1             120         0.90           0.9        23    -152.723648       -0.266516         -0.484240      0.0324  0.086957       0.343221    -0.045035
      0.45             1             120         0.35           0.9        35    -200.879136       -0.230174         -0.336332      0.0028  0.028571       0.188224    -0.028640
```

### knife_catch — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        25        25    -197.410258       -0.316693         -0.390748         -0.248386         0.0   0.04000       0.004270   -0.364091     -196.715700                NaN    -0.087883      1.960000       29.654036
oos_fold_2        16        16     -89.543646       -0.223859         -0.306556         -0.130078         0.0   0.06250       0.061789   -0.353099      -93.905428                NaN    -0.021114     14.250000       25.207877
oos_pooled        41        41    -286.953904       -0.280465         -0.335972         -0.220612         0.0   0.04878       0.022961   -0.363919     -292.930940                NaN    -0.087883      6.756098       24.932432
```

### knife_catch — cost stress (OOS pools only, last pick)
```
         label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
knife_catch@1x        42        42    -359.131368       -0.342528         -0.362814         -0.312675         0.0   0.02381       0.005567   -0.364086     -353.564923                NaN    -0.093792      6.404762       25.846154
knife_catch@2x        42        42    -381.981206       -0.364774         -0.381581         -0.342086         0.0   0.00000       0.000000   -0.378204     -370.927461                NaN    -0.103898      6.404762       25.846154
knife_catch@3x        42        42    -404.623048       -0.386801         -0.401987         -0.369694         0.0   0.00000       0.000000   -0.392306     -388.201183                NaN    -0.114257      6.404762       25.846154
```

### knife_catch — VERDICT: NOT VALIDATED
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.3262)
- dies at 2x costs (OOS)
- pooled OOS P&L carried entirely by top-3 trades

## Summary

- **grad_momentum**: NOT validated (only 14 OOS trades (<30); only 14 OOS tokens (<20); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.3262); dies at 2x costs (OOS); pooled OOS P&L carried entirely by top-3 trades)
- **dip_reclaim**: NOT validated (only 9 OOS trades (<30); only 8 OOS tokens (<20); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.3262); dies at 2x costs (OOS); pooled OOS P&L carried entirely by top-3 trades)
- **trending_follow**: NOT validated (only 12 OOS trades (<30); only 12 OOS tokens (<20); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.3262); dies at 2x costs (OOS); pooled OOS P&L carried entirely by top-3 trades)
- **regime_gated**: NOT validated (only 11 OOS trades (<30); only 11 OOS tokens (<20); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.3262); dies at 2x costs (OOS); pooled OOS P&L carried entirely by top-3 trades)
- **boost_follow**: NOT validated (no pooled out-of-sample trades)
- **composite_v2**: NOT validated (only 8 OOS trades (<30); only 8 OOS tokens (<20); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.3262); dies at 2x costs (OOS); pooled OOS P&L carried entirely by top-3 trades)
- **knife_catch**: NOT validated (pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.3262); dies at 2x costs (OOS); pooled OOS P&L carried entirely by top-3 trades)

> A strategy not marked VALIDATED must not be run live.
> Paper-trade validated strategies first; live only with
> throwaway funds and the risk caps in config/default.yaml.
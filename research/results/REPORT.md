# Strategy validation report

generated: 2026-08-28T11:52:59.993501+00:00
panel: 907 pools (>= $2k max reserve, >= 5 minute-bars), 465 trending events
snapshot-covered collection windows (UTC): 08-27 14:37..08-27 17:27; 08-28 00:05..08-28 11:49

> Entries are only permitted on bars with fresh snapshot
> coverage (liquidity/FDV/volume verified), i.e. inside the
> collection windows above. Verdicts tighten or flip as the
> collector accumulates more windows — re-run this script to
> regenerate. NOT VALIDATED on a thin panel means 'not enough
> evidence yet', never 'edge confirmed'.

## Defaults vs placebo (1x costs)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
  grad_momentum       107       107     807.591398        0.301903          0.155284          0.486985      1.0000  0.579439       8.719915    0.028950      478.609109           0.592581    -0.007242     21.476636      122.675159
    dip_reclaim        32        27     135.141910        0.155917         -0.063825          0.484267      0.8878  0.437500       2.924516   -0.057324      -23.997649           1.005727    -0.028105      4.875000       38.336106
 attention_cont         8         7      62.497263        0.312486          0.067031          0.613613      0.9938  0.625000      13.124672    0.148061        2.248512           0.335275    -0.002883    123.375000       13.457944
trending_follow        61        60     221.854692        0.145478          0.004024          0.328081      0.9802  0.360656       3.477805   -0.020820       26.487252           0.973696    -0.033198     28.557377       70.895884
   regime_gated       128       125     522.544890        0.163295          0.053785          0.310140      1.0000  0.507812       4.689749    0.001510      188.982792           0.822297    -0.019733     21.835938      156.734694
   boost_follow        11        11      -2.104615       -0.007653         -0.092422          0.086031      0.4186  0.363636       0.889807   -0.027334      -17.070448                NaN    -0.012080      6.454545       13.069307
   composite_v2        42        42     334.852242        0.318907          0.117265          0.648495      1.0000  0.761905      26.150868    0.068099      133.702524           0.600712    -0.003460     23.238095       53.006135
  placebo_seed0        36        35     293.573853        0.326193          0.173923          0.510168      1.0000  0.666667      11.409657    0.242880      181.370054           0.301057    -0.007127     40.833333       43.709949
  placebo_seed1        34        34     260.206604        0.306125          0.066553          0.593597      0.9964  0.500000       6.930572   -0.001786       71.183878           0.500991    -0.014583     41.117647       40.396040
  placebo_seed2        26        26     164.897347        0.253688          0.099656          0.426778      1.0000  0.615385       8.849365    0.119908       75.334357           0.412968    -0.008188     31.115385       34.160584
```

placebo mean expectancy: 0.2953; upper-CI bar to beat: 0.5102

## grad_momentum — full grid (every config tried)
```
 p_min_age_min  p_min_liq  p_min_vol5  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
            15      15000        1000           0.2       120     532.276522        0.177426          0.106612         1.0  0.625000       5.917703    -0.011536
            15      15000        1000           0.3       120     489.668886        0.163223          0.094911         1.0  0.600000       4.960176    -0.012870
            15      15000        3000           0.2       106     501.467744        0.189233          0.111297         1.0  0.613208       5.215555    -0.011240
            15      15000        3000           0.3       106     454.180255        0.171389          0.094856         1.0  0.584906       4.533708    -0.012461
            15      30000        1000           0.2       115     420.379946        0.146219          0.080098         1.0  0.608696       4.884424    -0.011536
            15      30000        1000           0.3       115     384.772040        0.133834          0.068892         1.0  0.582609       4.112201    -0.012874
            15      30000        3000           0.2       101     392.651359        0.155505          0.081642         1.0  0.594059       4.388972    -0.013178
            15      30000        3000           0.3       101     349.511402        0.138420          0.067308         1.0  0.564356       3.724489    -0.013659
            30      15000        1000           0.2        33     259.847639        0.314967          0.142997         1.0  0.696970      15.832452    -0.004719
            30      15000        1000           0.3        33     229.596840        0.278299          0.108296         1.0  0.606061       8.285589    -0.005576
            30      15000        3000           0.2        31     257.500683        0.332259          0.148451         1.0  0.709677      16.162112    -0.004301
            30      15000        3000           0.3        31     227.249884        0.293226          0.110316         1.0  0.612903       8.335814    -0.005576
            30      30000        1000           0.2        32     247.723025        0.309654          0.136320         1.0  0.687500      15.140363    -0.007004
            30      30000        1000           0.3        32     220.288315        0.275360          0.104644         1.0  0.593750       7.990210    -0.008748
            30      30000        3000           0.2        30     245.376069        0.327168          0.142742         1.0  0.700000      15.448193    -0.006591
            30      30000        3000           0.3        30     217.941359        0.290588          0.107401         1.0  0.600000       8.035327    -0.008331
```

### grad_momentum — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        17        17     122.403040        0.288007          0.089934          0.549483      0.9996  0.705882      11.559092    0.115306       44.426365           0.378903    -0.005240     50.529412       72.426036
oos_fold_2         3         3       2.885991        0.038480         -0.027031          0.164137      0.7086  0.333333       3.370549   -0.021667             NaN           1.421843    -0.000676      2.333333       98.181818
oos_pooled        20        20     125.289031        0.250578          0.082741          0.470549      0.9996  0.650000      10.780848    0.099999       47.312356           0.370175    -0.005839     43.300000       59.259259
```

### grad_momentum — cost stress (OOS pools only, last pick)
```
           label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
grad_momentum@1x        20        20     177.382134        0.354764          0.114877          0.673652      1.0000      0.65      16.869391    0.120260       56.406176           0.391510    -0.004085         42.25       59.259259
grad_momentum@2x        20        20     156.798954        0.313598          0.083001          0.624921      0.9994      0.60      11.127878    0.093983       45.014545           0.431632    -0.005059         42.25       59.259259
grad_momentum@3x        20        20     136.489796        0.272980          0.050245          0.578465      0.9960      0.55       7.683181    0.067999       28.769670           0.483097    -0.006054         42.25       59.259259
```

### grad_momentum — VERDICT: NOT VALIDATED
- only 20 OOS trades (<30)
- does not beat placebo upper CI (0.5102)

## dip_reclaim — full grid (every config tried)
```
 p_min_dip  p_min_run  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
      0.25        0.5           0.2        50     128.650752        0.094594         -0.034668      0.9170  0.380000       2.000773    -0.026582
      0.25        0.5           0.3        50     146.070233        0.108529         -0.034699      0.9202  0.380000       1.984430    -0.030637
      0.25        1.0           0.2        43      95.835514        0.079467         -0.059238      0.8374  0.348837       1.837995    -0.039431
      0.25        1.0           0.3        43     115.217316        0.097496         -0.063330      0.8628  0.348837       1.871342    -0.045486
      0.35        0.5           0.2        36     140.877168        0.144965         -0.024096      0.9486  0.472222       2.653443    -0.018723
      0.35        0.5           0.3        36     159.695619        0.165874         -0.026031      0.9528  0.444444       2.646118    -0.015967
      0.35        1.0           0.2        32     125.252814        0.143555         -0.043105      0.9314  0.468750       2.619068    -0.018047
      0.35        1.0           0.3        32     144.071265        0.167078         -0.042527      0.9374  0.437500       2.615652    -0.020246
      0.50        0.5           0.2        23      10.480647        0.000125         -0.152272      0.4922  0.391304       1.155628    -0.029945
      0.50        0.5           0.3        23       9.638601       -0.001339         -0.164003      0.4764  0.304348       1.129692    -0.025765
      0.50        1.0           0.2        22      15.871923        0.009933         -0.147411      0.5504  0.409091       1.256193    -0.029945
      0.50        1.0           0.3        22      15.029877        0.008402         -0.161827      0.5306  0.318182       1.218052    -0.022549
```

### dip_reclaim — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_2         7         7      87.570153        0.440923         -0.260424          1.250132      0.8718  0.714286       6.110734    0.114603       -13.27345           0.725529    -0.014323      4.285714       66.315789
oos_pooled         7         7      87.570153        0.440923         -0.260424          1.250132      0.8718  0.714286       6.110734    0.114603       -13.27345           0.725529    -0.014323      4.285714       66.315789
```

### dip_reclaim — cost stress (OOS pools only, last pick)
```
         label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
dip_reclaim@1x         7         7      90.221654        0.456074         -0.375814          1.702515      0.7314  0.571429       5.239649    0.039841      -20.284425           1.084483    -0.020284           4.0       66.315789
dip_reclaim@2x         7         7      81.896728        0.407678         -0.399468          1.627288      0.6974  0.571429       4.354408    0.012398      -24.104705           1.158843    -0.024105           4.0       66.315789
dip_reclaim@3x         7         7      73.738909        0.360237         -0.442400          1.559711      0.6752  0.428571       3.648405   -0.014666      -27.842766           1.248045    -0.027843           4.0       66.315789
```

### dip_reclaim — VERDICT: NOT VALIDATED
- only 7 OOS trades (<30)
- only 7 OOS tokens (<20)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.5102)
- pooled OOS P&L carried entirely by top-3 trades

## trending_follow — full grid (every config tried)
```
 p_min_liq  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
     15000          0.25        62     116.067414        0.074882         -0.005124      0.9642  0.419355       2.127284    -0.034937
     30000          0.25        57     128.997739        0.090525          0.002498      0.9792  0.438596       2.428885    -0.031063
```

### trending_follow — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_2        16        16     -15.984979       -0.039962         -0.095405          0.016255      0.0838    0.1875       0.356386   -0.024334      -24.836265                NaN    -0.020864        2.6875      110.769231
oos_pooled        16        16     -15.984979       -0.039962         -0.095405          0.016255      0.0838    0.1875       0.356386   -0.024334      -24.836265                NaN    -0.020864        2.6875      110.769231
```

### trending_follow — cost stress (OOS pools only, last pick)
```
             label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
trending_follow@1x        16        16     -21.268680       -0.053172         -0.091897         -0.013657      0.0026    0.1250       0.158294   -0.026454      -24.836650                NaN    -0.021296        2.2500      110.769231
trending_follow@2x        16        16     -32.184738       -0.080462         -0.120319         -0.040730      0.0000    0.0625       0.077388   -0.051310      -33.798158                NaN    -0.032185        2.2500      110.769231
trending_follow@3x        16        16     -42.950975       -0.107377         -0.151433         -0.066873      0.0000    0.0625       0.044046   -0.075869      -42.633536                NaN    -0.042951        2.1875      110.769231
```

### trending_follow — VERDICT: NOT VALIDATED
- only 16 OOS trades (<30)
- only 16 OOS tokens (<20)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.5102)
- dies at 2x costs (OOS)
- pooled OOS P&L carried entirely by top-3 trades

## regime_gated — full grid (every config tried)
```
 p_min_cohort_mom  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
             0.00           0.2       150     419.994530        0.111999          0.052906      1.0000  0.546667       3.458876    -0.015671
             0.00           0.3       144     338.476686        0.094021          0.034045      1.0000  0.520833       2.836356    -0.020247
             0.02           0.2       125     302.514967        0.096805          0.039959      0.9996  0.552000       3.117918    -0.013151
             0.02           0.3       123     211.515418        0.068786          0.017270      0.9960  0.536585       2.265959    -0.022040
             0.05           0.2       128     363.571602        0.113616          0.042482      1.0000  0.562500       3.542291    -0.014816
             0.05           0.3       127     311.097156        0.097983          0.031216      0.9996  0.543307       2.991556    -0.022603
```

### regime_gated — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        34        32     122.495182        0.144112          0.038441          0.275696      0.9970  0.500000       4.294034    0.011784       45.500974           0.497949    -0.013708     38.852941      112.551724
oos_fold_2        49        49     103.768091        0.084709         -0.006718          0.222306      0.9578  0.489796       2.817142   -0.002471       12.156476           0.882850    -0.023705      5.020408      342.524272
oos_pooled        83        81     226.263272        0.109043          0.034091          0.200643      0.9994  0.493976       3.399600   -0.002471       99.915639           0.698177    -0.021429     18.879518      186.458658
```

### regime_gated — cost stress (OOS pools only, last pick)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
regime_gated@1x        82        81     245.413036        0.119714          0.026075          0.250273      0.9982  0.512195       3.874117    0.003276       78.256330           0.824051    -0.017638     19.463415      184.212168
regime_gated@2x        83        81     165.903111        0.079953         -0.009941          0.207960      0.9458  0.457831       2.401735   -0.023140        4.159427           1.172970    -0.030087     19.216867      186.458658
regime_gated@3x        83        81      82.338889        0.039681         -0.048858          0.165222      0.7482  0.325301       1.497572   -0.066647      -74.093022           2.272421    -0.054814     19.168675      186.458658
```

### regime_gated — VERDICT: NOT VALIDATED
- does not beat placebo upper CI (0.5102)

## boost_follow — full grid (every config tried)
```
 p_min_liq  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
     15000          0.25        11     -13.388402       -0.048685          -0.14574        0.18  0.272727       0.529028    -0.020141
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
     0.12        0.08            0.02          0.15        43     183.856468        0.171029          0.094505      1.0000  0.744186       8.344295    -0.012500
     0.12        0.08            0.02          0.20        42     151.053584        0.143861          0.071174      1.0000  0.738095       5.957881    -0.013921
     0.12        0.08            0.08          0.15        31     126.027866        0.162617          0.071550      0.9992  0.709677       7.007605    -0.012500
     0.12        0.08            0.08          0.20        31     118.307624        0.152655          0.061137      0.9992  0.709677       5.704107    -0.013921
     0.12       99.00            0.02          0.15        62     272.443998        0.175770          0.098287      1.0000  0.677419       5.666687    -0.016403
     0.12       99.00            0.02          0.20        60     247.802728        0.165202          0.095164      1.0000  0.700000       4.920538    -0.011631
     0.12       99.00            0.08          0.15        50     218.534349        0.174827          0.089543      1.0000  0.640000       5.022741    -0.016403
     0.12       99.00            0.08          0.20        50     226.345717        0.181077          0.098098      1.0000  0.680000       4.910009    -0.011631
     0.25        0.08            0.02          0.15        43     187.039420        0.173990          0.098142      1.0000  0.744186       9.559778    -0.012500
     0.25        0.08            0.02          0.20        42     154.049561        0.146714          0.075939      1.0000  0.738095       6.607636    -0.013921
     0.25        0.08            0.08          0.15        32     125.472449        0.156841          0.064177      0.9996  0.687500       6.826857    -0.012500
     0.25        0.08            0.08          0.20        32     116.303589        0.145379          0.053006      0.9992  0.687500       5.283127    -0.013921
     0.25       99.00            0.02          0.15        64     258.293885        0.161434          0.086452      1.0000  0.640625       4.864341    -0.019794
     0.25       99.00            0.02          0.20        61     251.351796        0.164821          0.092417      1.0000  0.704918       5.196600    -0.011626
     0.25       99.00            0.08          0.15        53     200.645867        0.151431          0.064626      1.0000  0.584906       4.016194    -0.019794
     0.25       99.00            0.08          0.20        52     224.894772        0.172996          0.089684      1.0000  0.673077       4.774881    -0.011626
```

### composite_v2 — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_2        10        10      19.767799        0.079071         -0.019239          0.218679      0.9028       0.5       5.446735   -0.000623       -3.647189           0.790494    -0.003063           3.8      116.129032
oos_pooled        10        10      19.767799        0.079071         -0.019239          0.218679      0.9028       0.5       5.446735   -0.000623       -3.647189           0.790494    -0.003063           3.8      116.129032
```

### composite_v2 — cost stress (OOS pools only, last pick)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
composite_v2@1x        10        10      22.310858        0.089243         -0.019239          0.248901      0.9028       0.5       6.018793   -0.000623       -3.647189           0.814374    -0.003056           3.8      116.129032
composite_v2@2x        10        10      15.393064        0.061572         -0.043798          0.216541      0.7794       0.4       2.910551   -0.024943       -7.941904           1.102947    -0.006327           3.8      116.129032
composite_v2@3x        10        10       8.567657        0.034271         -0.068033          0.184630      0.6632       0.3       1.702989   -0.049001      -12.187461           1.845358    -0.011130           3.8      116.129032
```

### composite_v2 — VERDICT: NOT VALIDATED
- only 10 OOS trades (<30)
- only 10 OOS tokens (<20)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.5102)
- pooled OOS P&L carried entirely by top-3 trades

## Summary

- **grad_momentum**: NOT validated (only 20 OOS trades (<30); does not beat placebo upper CI (0.5102))
- **dip_reclaim**: NOT validated (only 7 OOS trades (<30); only 7 OOS tokens (<20); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.5102); pooled OOS P&L carried entirely by top-3 trades)
- **trending_follow**: NOT validated (only 16 OOS trades (<30); only 16 OOS tokens (<20); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.5102); dies at 2x costs (OOS); pooled OOS P&L carried entirely by top-3 trades)
- **regime_gated**: NOT validated (does not beat placebo upper CI (0.5102))
- **boost_follow**: NOT validated (no pooled out-of-sample trades)
- **composite_v2**: NOT validated (only 10 OOS trades (<30); only 10 OOS tokens (<20); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.5102); pooled OOS P&L carried entirely by top-3 trades)

> A strategy not marked VALIDATED must not be run live.
> Paper-trade validated strategies first; live only with
> throwaway funds and the risk caps in config/default.yaml.
# Strategy validation report

generated: 2026-08-28T15:54:56.298925+00:00
panel: 1016 pools (>= $2k max reserve, >= 5 minute-bars), 490 trending events
snapshot-covered collection windows (UTC): 08-27 14:37..08-27 17:27; 08-28 00:05..08-28 12:15; 08-28 15:28..08-28 15:47

> Entries are only permitted on bars with fresh snapshot
> coverage (liquidity/FDV/volume verified), i.e. inside the
> collection windows above. Verdicts tighten or flip as the
> collector accumulates more windows — re-run this script to
> regenerate. NOT VALIDATED on a thin panel means 'not enough
> evidence yet', never 'edge confirmed'.

## Defaults vs placebo (1x costs)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
  grad_momentum       113       113     801.164397        0.283598          0.147907          0.452561      1.0000  0.566372       7.893400    0.026747      472.182108           0.597335    -0.007242     21.876106      112.375691
    dip_reclaim        34        29     129.910231        0.140590         -0.069498          0.452917      0.8680  0.411765       2.721739   -0.057324      -29.229328           1.046229    -0.028105      4.588235       32.859060
 attention_cont         8         7      62.497263        0.312486          0.067031          0.613613      0.9938  0.625000      13.124672    0.148061        2.248512           0.335275    -0.002883    123.375000       13.457944
trending_follow        62        61     224.664785        0.144945          0.005643          0.322375      0.9808  0.370968       3.509190   -0.020300       29.297345           0.961517    -0.033198     28.145161       60.734694
   regime_gated       143       140     600.568042        0.167991          0.065277          0.299317      0.9998  0.496503       4.792622   -0.002471      267.005944           0.836408    -0.019087     19.727273      145.939050
   boost_follow        12        12      -3.859608       -0.012865         -0.089521          0.072016      0.3648  0.333333       0.814925   -0.048767      -18.825440                NaN    -0.012080      6.166667       11.755102
   composite_v2        42        42     334.947033        0.318997          0.117365          0.648585      1.0000  0.761905      26.157988    0.068099      133.797315           0.600542    -0.003460     23.285714       53.006135
    knife_catch       140       137    2187.599718        0.625028          0.217728          1.339562      1.0000  0.564286      11.463302    0.032432      862.262383           0.732055    -0.021578      2.807143      134.131737
  placebo_seed0        37        36     289.429017        0.312896          0.160176          0.492125      1.0000  0.648649       9.947657    0.183988      177.225218           0.305369    -0.007127     39.729730       36.719504
  placebo_seed1        34        34     260.206604        0.306125          0.066553          0.593597      0.9964  0.500000       6.930572   -0.001786       71.183878           0.500991    -0.014583     41.117647       40.396040
  placebo_seed2        27        27     162.091810        0.240136          0.087504          0.414902      0.9998  0.592593       7.806785    0.115664       72.528820           0.420116    -0.008188     30.000000       33.174061
```

placebo mean expectancy: 0.2864; upper-CI bar to beat: 0.5002

## grad_momentum — full grid (every config tried)
```
 p_min_age_min  p_min_liq  p_min_vol5  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
            15      15000        1000           0.2       127     518.961019        0.163452          0.096511         1.0  0.598425       5.202096    -0.011536
            15      15000        1000           0.3       126     470.454882        0.149351          0.084753         1.0  0.571429       4.293066    -0.013984
            15      15000        3000           0.2       112     490.603084        0.175215          0.100000         1.0  0.598214       4.670773    -0.011240
            15      15000        3000           0.3       112     433.498615        0.154821          0.080856         1.0  0.553571       3.905300    -0.014320
            15      30000        1000           0.2       120     410.722919        0.136908          0.072699         1.0  0.591667       4.427627    -0.011536
            15      30000        1000           0.3       120     368.676759        0.122892          0.059361         1.0  0.558333       3.638519    -0.012874
            15      30000        3000           0.2       105     383.023658        0.145914          0.073007         1.0  0.580952       4.005583    -0.013178
            15      30000        3000           0.3       105     333.445446        0.127027          0.055451         1.0  0.542857       3.309962    -0.013659
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
oos_fold_1        14        14      74.190286        0.211972          0.057961          0.391567      0.9986  0.785714      10.816047    0.104362       16.381718           0.340962    -0.005474     29.071429       85.063291
oos_fold_2         1         1       4.103426        0.164137          0.164137          0.164137      1.0000  1.000000            inf    0.164137             NaN           1.000000     0.000000      3.000000      480.000000
oos_pooled        15        15      78.293712        0.208783          0.062737          0.374142      0.9994  0.800000      11.358967    0.112468       20.485144           0.323092    -0.005474     27.333333       58.695652
```

### grad_momentum — cost stress (OOS pools only, last pick)
```
           label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
grad_momentum@1x        11        11      34.790533        0.126511          0.016322          0.259502      0.9902  0.818182       7.014366    0.096257        6.179067           0.463791    -0.004000     30.181818       43.043478
grad_momentum@2x        11        11      21.557211        0.078390         -0.033295          0.215613      0.9002  0.636364       2.869980    0.070446       -4.682771           0.707909    -0.006899     30.181818       43.043478
grad_momentum@3x        11        11       8.502999        0.030920         -0.092051          0.176130      0.6570  0.545455       1.424916    0.044920      -15.396140           1.693109    -0.014864     30.181818       43.043478
```

### grad_momentum — VERDICT: NOT VALIDATED
- only 15 OOS trades (<30)
- only 15 OOS tokens (<20)
- does not beat placebo upper CI (0.5002)

## dip_reclaim — full grid (every config tried)
```
 p_min_dip  p_min_run  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
      0.25        0.5           0.2        53     126.222687        0.087407         -0.031831      0.9110  0.377358       1.939038    -0.026582
      0.25        0.5           0.3        53     143.642168        0.100554         -0.032159      0.9138  0.377358       1.931253    -0.030637
      0.25        1.0           0.2        45      89.969908        0.070721         -0.062101      0.8214  0.333333       1.748324    -0.039431
      0.25        1.0           0.3        45     109.351710        0.087949         -0.063608      0.8450  0.333333       1.791857    -0.045486
      0.35        0.5           0.2        39     138.449103        0.131324         -0.024831      0.9452  0.461538       2.520284    -0.018723
      0.35        0.5           0.3        39     157.267554        0.150624         -0.023412      0.9522  0.435897       2.528664    -0.015967
      0.35        1.0           0.2        34     119.387207        0.128210         -0.045183      0.9124  0.441176       2.434482    -0.018047
      0.35        1.0           0.3        34     138.205658        0.150349         -0.045946      0.9250  0.411765       2.454217    -0.020246
      0.50        0.5           0.2        25       4.615040       -0.009270         -0.149383      0.4452  0.360000       1.063039    -0.030398
      0.50        0.5           0.3        25       3.772995       -0.010617         -0.157928      0.4388  0.280000       1.047054    -0.031242
      0.50        1.0           0.2        24      10.006316       -0.000671         -0.143709      0.4942  0.375000       1.147545    -0.029945
      0.50        1.0           0.3        24       9.164271       -0.002074         -0.156816      0.4806  0.291667       1.122528    -0.026039
```

### dip_reclaim — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        13        12      34.183246        0.105179         -0.076840          0.338145      0.8468  0.307692       2.404911   -0.025913      -16.729357           0.779418    -0.012535      6.615385       65.000000
oos_fold_2         8         8      60.864692        0.252280         -0.310901          0.985496      0.7500  0.625000       3.961755    0.077222      -16.689108           1.043868    -0.014620      2.750000       30.638298
oos_pooled        21        20      95.047938        0.161218         -0.081557          0.488310      0.8766  0.428571       3.117755   -0.012060      -10.390977           0.948760    -0.014139      5.142857       41.595598
```

### dip_reclaim — cost stress (OOS pools only, last pick)
```
         label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
dip_reclaim@1x        15        14     150.598572        0.373840         -0.070123          1.003158      0.9416  0.600000       6.755682    0.114603       -1.361566           0.649700    -0.014938           3.4       30.594901
dip_reclaim@2x        15        14     137.760206        0.339219         -0.095221          0.953931      0.9186  0.600000       5.744382    0.084705       -8.837524           0.688918    -0.017540           3.4       30.594901
dip_reclaim@3x        15        14     125.118629        0.305123         -0.119791          0.904875      0.8894  0.533333       4.879561    0.055046      -16.219687           0.735538    -0.020135           3.4       30.594901
```

### dip_reclaim — VERDICT: NOT VALIDATED
- only 21 OOS trades (<30)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.5002)
- pooled OOS P&L carried entirely by top-3 trades

## trending_follow — full grid (every config tried)
```
 p_min_liq  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
     15000          0.25        66     115.660797        0.070097         -0.007510      0.9576  0.439394       2.067450    -0.035101
     30000          0.25        58     131.807832        0.090902          0.003688      0.9808  0.448276       2.460011    -0.031063
```

### trending_follow — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        20        20      47.052913        0.094106         -0.012680          0.216994      0.9524  0.550000       2.868386    0.010913        3.420862           0.362380    -0.012857     22.000000       80.672269
oos_fold_2        15        15     -10.057307       -0.026819         -0.086799          0.034894      0.1936  0.266667       0.536928   -0.020696      -21.149408                NaN    -0.017746      2.533333       58.378378
oos_pooled        35        35      36.995606        0.042281         -0.025621          0.115692      0.8710  0.428571       1.788778   -0.019294       -6.636446           0.861687    -0.029588     13.657143       66.843501
```

### trending_follow — cost stress (OOS pools only, last pick)
```
             label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
trending_follow@1x        35        35      43.498631        0.049713         -0.023300          0.132537      0.8932  0.400000       1.997205   -0.019781       -8.206027           0.918572    -0.028543     13.457143       66.843501
trending_follow@2x        35        35      18.459602        0.021097         -0.049014          0.102767      0.6780  0.314286       1.331908   -0.043743      -30.491274           2.063116    -0.040040     13.457143       66.843501
trending_follow@3x        35        35      -6.133347       -0.007010         -0.075719          0.073304      0.4024  0.257143       0.912972   -0.069743      -52.367273                NaN    -0.051563     13.428571       66.843501
```

### trending_follow — VERDICT: NOT VALIDATED
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.5002)
- pooled OOS P&L carried entirely by top-3 trades

## regime_gated — full grid (every config tried)
```
 p_min_cohort_mom  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
             0.00           0.2       160     429.272153        0.107318          0.050137      1.0000  0.543750       3.283924    -0.015671
             0.00           0.3       154     344.573274        0.089500          0.033217      1.0000  0.512987       2.733672    -0.020266
             0.02           0.2       141     338.630134        0.096065          0.038724      1.0000  0.531915       3.013431    -0.019401
             0.02           0.3       139     261.869071        0.075358          0.023200      0.9992  0.517986       2.405960    -0.021685
             0.05           0.2       132     383.217320        0.116126          0.047861      1.0000  0.553030       3.541713    -0.014816
             0.05           0.3       131     335.203091        0.102352          0.038977      0.9998  0.534351       3.117669    -0.022684
```

### regime_gated — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        48        46      35.045720        0.029205         -0.022154          0.087869      0.8628  0.479167       1.551504   -0.001522       -5.236926           1.149431    -0.024092     18.895833      225.146580
oos_fold_2        49        49     164.261857        0.134091          0.035998          0.270081      0.9996  0.551020       4.759728    0.027517       60.660098           0.630711    -0.009287      4.836735      170.847458
oos_pooled        97        95     199.307577        0.082189          0.025057          0.156694      0.9990  0.515464       2.858596    0.011023       95.705818           0.659807    -0.024092     11.793814      186.737968
```

### regime_gated — cost stress (OOS pools only, last pick)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
regime_gated@1x       101        99     267.709291        0.106023          0.034732          0.206074      1.0000  0.544554       3.871355    0.020011      114.138028           0.782889    -0.018358     11.069307      194.438503
regime_gated@2x       102       100     180.236205        0.070681          0.000376          0.170516      0.9764  0.460784       2.360236   -0.011787       32.273914           1.113960    -0.033418     10.931373      196.363636
regime_gated@3x       102       100      86.726484        0.034010         -0.035855          0.132557      0.7610  0.323529       1.469579   -0.049001      -55.740939           2.215400    -0.073363     10.892157      196.363636
```

### regime_gated — VERDICT: NOT VALIDATED
- does not beat placebo upper CI (0.5002)

## boost_follow — full grid (every config tried)
```
 p_min_liq  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
     15000          0.25        12     -16.471655       -0.054906         -0.143801       0.136      0.25       0.477263    -0.020141
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
     0.12        0.08            0.02          0.15        43     183.951259        0.171117          0.094595      1.0000  0.744186       8.348081    -0.012500
     0.12        0.08            0.02          0.20        42     151.148375        0.143951          0.071175      1.0000  0.738095       5.960992    -0.013921
     0.12        0.08            0.08          0.15        31     126.027866        0.162617          0.071550      0.9992  0.709677       7.007605    -0.012500
     0.12        0.08            0.08          0.20        31     118.307624        0.152655          0.061137      0.9992  0.709677       5.704107    -0.013921
     0.12       99.00            0.02          0.15        64     286.221898        0.178889          0.103969      1.0000  0.687500       5.902688    -0.016403
     0.12       99.00            0.02          0.20        62     258.682973        0.166892          0.095162      1.0000  0.709677       5.092677    -0.011631
     0.12       99.00            0.08          0.15        52     232.217458        0.178629          0.096974      1.0000  0.653846       5.274617    -0.016403
     0.12       99.00            0.08          0.20        52     237.131170        0.182409          0.102890      1.0000  0.692308       5.096322    -0.011631
     0.25        0.08            0.02          0.15        43     187.134212        0.174078          0.098158      1.0000  0.744186       9.564116    -0.012500
     0.25        0.08            0.02          0.20        42     154.144352        0.146804          0.076108      1.0000  0.738095       6.611087    -0.013921
     0.25        0.08            0.08          0.15        32     125.472449        0.156841          0.064177      0.9996  0.687500       6.826857    -0.012500
     0.25        0.08            0.08          0.20        32     116.303589        0.145379          0.053006      0.9992  0.687500       5.283127    -0.013921
     0.25       99.00            0.02          0.15        66     272.071785        0.164892          0.091487      1.0000  0.651515       5.070472    -0.019794
     0.25       99.00            0.02          0.20        63     262.232040        0.166497          0.098641      1.0000  0.714286       5.378258    -0.011626
     0.25       99.00            0.08          0.15        55     214.328976        0.155876          0.072585      0.9998  0.600000       4.221885    -0.019794
     0.25       99.00            0.08          0.20        54     235.680225        0.174578          0.094756      1.0000  0.685185       4.955916    -0.011626
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
- does not beat placebo upper CI (0.5002)
- pooled OOS P&L carried entirely by top-3 trades

## knife_catch — full grid (every config tried)
```
 p_min_dip  p_use_regime  x_max_hold_min  x_stop_frac  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
      0.30             0              60         0.90           0.9       140    1491.036249        0.426010          0.137517      1.0000  0.578571       3.177677    -0.097435
      0.30             0              60         0.35           0.9       152    1814.628624        0.477534          0.218409      1.0000  0.552632       5.078261    -0.050935
      0.30             0             120         0.90           0.9       127    1553.039531        0.489146          0.168370      1.0000  0.582677       3.524782    -0.076065
      0.30             0             120         0.35           0.9       151    1840.855922        0.487644          0.225605      1.0000  0.549669       5.216243    -0.033446
      0.30             1              60         0.90           0.9       104    1258.485708        0.484033          0.103944      0.9986  0.557692       3.297567    -0.042454
      0.30             1              60         0.35           0.9       112    1515.604463        0.541287          0.204295      1.0000  0.544643       5.379159    -0.036387
      0.30             1             120         0.90           0.9        98    1260.804371        0.514614          0.121311      0.9994  0.551020       3.440330    -0.051363
      0.30             1             120         0.35           0.9       112    1531.638520        0.547014          0.209256      1.0000  0.544643       5.425487    -0.036387
      0.35             0              60         0.90           0.9       133    1523.551190        0.458211          0.152181      1.0000  0.593985       3.434619    -0.091049
      0.35             0              60         0.35           0.9       138    1787.322891        0.518065          0.235082      1.0000  0.565217       5.746837    -0.031860
      0.35             0             120         0.90           0.9       116    1397.376655        0.481854          0.135850      0.9996  0.577586       3.354596    -0.073800
      0.35             0             120         0.35           0.9       138    1791.150478        0.519174          0.231989      1.0000  0.557971       5.644925    -0.030685
      0.35             1              60         0.90           0.9       100    1275.352942        0.510141          0.123489      0.9996  0.570000       3.744806    -0.063226
      0.35             1              60         0.35           0.9       102    1460.513407        0.572750          0.211677      1.0000  0.558824       6.169115    -0.036106
      0.35             1             120         0.90           0.9        93    1224.970932        0.526869          0.116342      0.9998  0.569892       3.749251    -0.038049
      0.35             1             120         0.35           0.9       102    1470.198239        0.576548          0.214387      1.0000  0.558824       6.203392    -0.035798
      0.45             0              60         0.90           0.9       101    1125.692947        0.444815          0.066761      0.9966  0.534653       3.113546    -0.083118
      0.45             0              60         0.35           0.9       102    1289.852477        0.505825          0.135328      1.0000  0.490196       4.742956    -0.044741
      0.45             0             120         0.90           0.9        90    1150.803276        0.510341          0.078076      0.9962  0.533333       3.360082    -0.085231
      0.45             0             120         0.35           0.9       102    1298.848482        0.509352          0.136519      1.0000  0.480392       4.760644    -0.032328
      0.45             1              60         0.90           0.9        70     917.532887        0.522856          0.017221      0.9840  0.542857       3.469055    -0.071100
      0.45             1              60         0.35           0.9        70    1039.710232        0.594120          0.102596      0.9990  0.514286       5.263773    -0.053728
      0.45             1             120         0.90           0.9        68     913.579211        0.535908          0.009821      0.9804  0.529412       3.457554    -0.046847
      0.45             1             120         0.35           0.9        70    1034.506690        0.591147          0.099579      0.9990  0.500000       5.229057    -0.053728
```

### knife_catch — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        44        43     444.671237        0.404247          0.204872          0.621264      1.0000  0.681818       5.137974    0.332396      276.292952           0.378658    -0.035922      9.068182      216.986301
oos_fold_2        35        35     866.655611        0.990464          0.085191          2.612132      0.9976  0.600000       8.625558    0.331863      111.492978           0.837393    -0.015504      5.200000      128.244275
oos_pooled        79        78    1311.326848        0.663963          0.220452          1.421931      1.0000  0.645570       6.930586    0.331863      518.741461           0.644171    -0.035922      7.354430      146.409266
```

### knife_catch — cost stress (OOS pools only, last pick)
```
         label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
knife_catch@1x        80        79    1944.654616        0.972327          0.280990          2.170026         1.0    0.6500       8.262849    0.254906      668.280154           0.696923    -0.034972        7.1875      148.262548
knife_catch@2x        80        79    1802.028854        0.901014          0.248521          2.025656         1.0    0.6375       7.410624    0.222613      602.078676           0.708350    -0.037276        7.1875      148.262548
knife_catch@3x        80        79    1665.607725        0.832804          0.217645          1.887218         1.0    0.6125       6.689312    0.190810      539.683610           0.720522    -0.038561        7.0875      148.262548
```

### knife_catch — VERDICT: VALIDATED

## Summary

- **grad_momentum**: NOT validated (only 15 OOS trades (<30); only 15 OOS tokens (<20); does not beat placebo upper CI (0.5002))
- **dip_reclaim**: NOT validated (only 21 OOS trades (<30); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.5002); pooled OOS P&L carried entirely by top-3 trades)
- **trending_follow**: NOT validated (pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.5002); pooled OOS P&L carried entirely by top-3 trades)
- **regime_gated**: NOT validated (does not beat placebo upper CI (0.5002))
- **boost_follow**: NOT validated (no pooled out-of-sample trades)
- **composite_v2**: NOT validated (only 10 OOS trades (<30); only 10 OOS tokens (<20); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.5002); pooled OOS P&L carried entirely by top-3 trades)
- **knife_catch**: VALIDATED

> A strategy not marked VALIDATED must not be run live.
> Paper-trade validated strategies first; live only with
> throwaway funds and the risk caps in config/default.yaml.
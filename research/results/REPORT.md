# Strategy validation report

generated: 2026-08-29T23:49:55.050038+00:00
panel: 3683 pools (>= $2k max reserve, >= 5 minute-bars), 1140 trending events
snapshot-covered collection windows (UTC): 08-27 14:37..08-27 17:27; 08-28 00:05..08-28 12:15; 08-28 15:28..08-29 23:45

> Entries are only permitted on bars with fresh snapshot
> coverage (liquidity/FDV/volume verified), i.e. inside the
> collection windows above. Verdicts tighten or flip as the
> collector accumulates more windows — re-run this script to
> regenerate. NOT VALIDATED on a thin panel means 'not enough
> evidence yet', never 'edge confirmed'.

## Defaults vs placebo (1x costs)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
  grad_momentum       331       331    1420.274065        0.171634          0.108677          0.243444      1.0000  0.552870       5.364503    0.013685     1064.822333           0.707480    -0.009879     10.250755      139.654263
    dip_reclaim        74        68     434.329413        0.229146          0.060357          0.453028      0.9992  0.513514       4.610723    0.005840      151.463008           0.738929    -0.028105      3.391892       32.868600
 attention_cont         8         7      62.497263        0.312486          0.067031          0.613613      0.9938  0.625000      13.124672    0.148061        2.248512           0.335275    -0.002883    123.375000       13.457944
trending_follow       146       143     291.083962        0.079749          0.016227          0.162639      0.9970  0.397260       2.642342   -0.015157       94.382529           1.015769    -0.041972     14.294521       61.908127
   regime_gated       375       368    1203.278438        0.128350          0.075397          0.191116      1.0000  0.514667       4.083704    0.003160      834.846060           0.813822    -0.017007      9.954667      162.016202
   boost_follow        22        22       3.575678        0.006501         -0.069966          0.097421      0.5348  0.363636       1.086681   -0.069764      -28.254715           6.816681    -0.014948      4.000000        9.468022
   composite_v2        97        97     700.481689        0.288858          0.135980          0.491577      1.0000  0.731959      14.662369    0.047627      341.857051           0.598027    -0.005621     13.608247       42.009023
    knife_catch       358       355    3283.719203        0.366736          0.190449          0.652106      1.0000  0.522346       6.428324    0.012782     1958.381868           0.697196    -0.023726      2.466480      151.712772
  placebo_seed0        68        67     371.665682        0.218627          0.121837          0.334334      1.0000  0.602941       7.323624    0.040956      249.825346           0.391916    -0.009958     23.102941       29.056380
  placebo_seed1        67        67     281.400372        0.168000          0.035938          0.330534      0.9962  0.492537       4.216449   -0.002634       92.377646           0.854120    -0.021084     22.238806       28.629080
  placebo_seed2        52        51     211.833237        0.162949          0.059122          0.285557      1.0000  0.500000       5.394656   -0.000181       97.094738           0.541645    -0.011989     17.826923       22.773723
```

placebo mean expectancy: 0.1832; upper-CI bar to beat: 0.3168

## grad_momentum — full grid (every config tried)
```
 p_min_age_min  p_min_liq  p_min_vol5  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
            15      15000        1000           0.2       365     972.336504        0.106557          0.071201      1.0000  0.580822       3.625107    -0.013142
            15      15000        1000           0.3       363     869.634213        0.095827          0.061260      1.0000  0.570248       3.118758    -0.014684
            15      15000        3000           0.2       330     938.024668        0.113700          0.075164      1.0000  0.569697       3.531918    -0.014451
            15      15000        3000           0.3       329     841.016280        0.102251          0.063860      1.0000  0.559271       3.086626    -0.014945
            15      30000        1000           0.2       314     639.341613        0.081445          0.049528      1.0000  0.579618       3.174026    -0.016928
            15      30000        1000           0.3       314     569.356121        0.072529          0.040892      1.0000  0.566879       2.731272    -0.022946
            15      30000        3000           0.2       282     609.675128        0.086479          0.050274      1.0000  0.563830       3.055091    -0.017928
            15      30000        3000           0.3       282     533.218677        0.075634          0.040480      1.0000  0.549645       2.628642    -0.024233
            30      15000        1000           0.2        65     278.464508        0.171363          0.074255      1.0000  0.523077       8.105315    -0.006831
            30      15000        1000           0.3        65     244.874187        0.150692          0.055605      1.0000  0.461538       5.366056    -0.008730
            30      15000        3000           0.2        61     275.906414        0.180922          0.076689      0.9998  0.524590       9.059196    -0.006843
            30      15000        3000           0.3        61     243.305885        0.159545          0.056088      0.9998  0.459016       5.852524    -0.007595
            30      30000        1000           0.2        61     271.515539        0.178043          0.075387      0.9998  0.524590      10.240286    -0.007004
            30      30000        1000           0.3        61     241.731099        0.158512          0.058658      0.9998  0.459016       6.337526    -0.008748
            30      30000        3000           0.2        59     269.168584        0.182487          0.080950      1.0000  0.525424      10.330516    -0.006591
            30      30000        3000           0.3        59     239.384143        0.162294          0.061533      1.0000  0.457627       6.348973    -0.008331
```

### grad_momentum — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        12        12      -3.182756       -0.010609         -0.018688         -0.001230      0.0146  0.250000       0.246786   -0.015981       -4.225569                NaN    -0.003525      0.333333       22.012739
oos_fold_2        16        16      26.385526        0.065964         -0.018862          0.181846      0.9050  0.375000       4.453846   -0.006408       -6.416663           0.659608    -0.003592      2.000000       33.055954
oos_pooled        28        28      23.202770        0.033147         -0.015335          0.100386      0.8678  0.321429       2.955559   -0.011992       -9.599418           1.274028    -0.003603      1.285714       22.883087
```

### grad_momentum — cost stress (OOS pools only, last pick)
```
           label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
grad_momentum@1x        28        28      27.205315        0.038865         -0.015335          0.116481      0.8706  0.321429       3.292899   -0.011992       -9.599418           1.233712    -0.003589      1.285714       22.883087
grad_momentum@2x        28        28       9.235247        0.013193         -0.039821          0.088965      0.6092  0.178571       1.370169   -0.036167      -24.840821           3.413956    -0.011172      1.285714       22.883087
grad_momentum@3x        28        28      -8.522922       -0.012176         -0.063872          0.061628      0.3170  0.107143       0.786459   -0.060081      -39.912289                NaN    -0.018986      1.285714       22.883087
```

### grad_momentum — VERDICT: NOT VALIDATED
- only 28 OOS trades (<30)
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.3168)
- pooled OOS P&L carried entirely by top-3 trades

## dip_reclaim — full grid (every config tried)
```
 p_min_dip  p_min_run  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
      0.25        0.5           0.2       119     500.451124        0.164720          0.057311      0.9998  0.487395       3.128461    -0.026582
      0.25        0.5           0.3       119     498.494019        0.164062          0.051663      0.9998  0.436975       2.727883    -0.030637
      0.25        1.0           0.2        98     321.530994        0.126989          0.028978      0.9960  0.448980       2.547559    -0.039431
      0.25        1.0           0.3        98     334.800936        0.132405          0.024774      0.9934  0.408163       2.328165    -0.045486
      0.35        0.5           0.2        85     489.732313        0.225564          0.089351      1.0000  0.541176       4.155587    -0.018723
      0.35        0.5           0.3        85     479.604037        0.220798          0.080281      1.0000  0.529412       3.656263    -0.018763
      0.35        1.0           0.2        74     354.148903        0.185806          0.061807      0.9992  0.527027       3.525048    -0.019058
      0.35        1.0           0.3        74     348.246376        0.182615          0.053087      0.9984  0.513514       3.140660    -0.024681
      0.50        0.5           0.2        43     246.613544        0.219725         -0.009823      0.9682  0.441860       3.356956    -0.030398
      0.50        0.5           0.3        43     242.483578        0.215884         -0.017413      0.9600  0.395349       3.110476    -0.031242
      0.50        1.0           0.2        40     153.371650        0.142963         -0.031885      0.9346  0.450000       2.634043    -0.029945
      0.50        1.0           0.3        40     149.241683        0.138833         -0.044120      0.9192  0.400000       2.433318    -0.026039
```

### dip_reclaim — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        30        30     133.904878        0.164662         -0.018336          0.390402      0.9560  0.566667       3.202777    0.080514       26.587942           0.687401    -0.016632      1.800000       36.424958
oos_fold_2        30        29     235.808151        0.314411          0.008379          0.713218      0.9792  0.533333       5.091663    0.001188       11.141937           0.808792    -0.022381      3.833333       55.102041
oos_pooled        60        59     369.713029        0.239536          0.055230          0.467109      0.9970  0.550000       4.122036    0.018782      115.458651           0.687707    -0.020238      2.816667       41.084165
```

### dip_reclaim — cost stress (OOS pools only, last pick)
```
         label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
dip_reclaim@1x        49        48     535.732364        0.428836          0.102790          0.854141      0.9990  0.612245       8.048465    0.066498      136.678173           0.744876    -0.014634      3.204082       33.632031
dip_reclaim@2x        49        48     491.341055        0.392480          0.073764          0.807300      0.9982  0.530612       6.678073    0.023320      104.290019           0.787744    -0.018749      3.142857       33.632031
dip_reclaim@3x        49        48     435.384430        0.346683          0.033800          0.750191      0.9884  0.469388       5.187507   -0.029332       60.065984           0.862039    -0.023604      3.040816       33.632031
```

### dip_reclaim — VERDICT: NOT VALIDATED
- does not beat placebo upper CI (0.3168)

## trending_follow — full grid (every config tried)
```
 p_min_liq  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
     15000          0.25       161     155.268033        0.038576         -0.001445      0.9704  0.440994       1.646745    -0.052228
     30000          0.25       142     180.407354        0.050819          0.007855      0.9886  0.436620       1.922630    -0.041450
```

### trending_follow — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        52        51     -29.745723       -0.022881         -0.058733          0.013925      0.1018  0.365385       0.599673   -0.018522      -46.570325                NaN    -0.041097      6.211538       50.731707
oos_fold_2        56        55      31.383571        0.022417         -0.018730          0.067969      0.8432  0.410714       1.447320   -0.007777       -1.107663           1.035294    -0.014069      4.214286       82.877698
oos_pooled       108       106       1.637849        0.000607         -0.027094          0.030214      0.5214  0.388889       1.011338   -0.015629      -30.853386          34.318871    -0.041097      5.175926       69.027963
```

### trending_follow — cost stress (OOS pools only, last pick)
```
             label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
trending_follow@1x        95        93      47.626048        0.020053         -0.014703          0.056362      0.8638  0.389474       1.442176   -0.015370       -0.603304           1.379939    -0.025994      3.947368       60.477454
trending_follow@2x        95        93     -12.167020       -0.005123         -0.038724          0.030441      0.3692  0.336842       0.915085   -0.039578      -57.455953                NaN    -0.046094      3.852632       60.477454
trending_follow@3x        95        93     -68.628203       -0.028896         -0.061514          0.005910      0.0532  0.284211       0.615033   -0.063522     -111.022664                NaN    -0.086685      3.842105       60.477454
```

### trending_follow — VERDICT: NOT VALIDATED
- pooled OOS cluster-bootstrap CI includes <= 0
- does not beat placebo upper CI (0.3168)
- dies at 2x costs (OOS)
- pooled OOS P&L carried entirely by top-3 trades

## regime_gated — full grid (every config tried)
```
 p_min_cohort_mom  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
             0.00           0.2       479     898.216828        0.075008          0.046477         1.0  0.517745       2.661817    -0.015671
             0.00           0.3       470     756.406534        0.064375          0.035172         1.0  0.495745       2.261791    -0.022394
             0.02           0.2       374     787.975615        0.084275          0.049672         1.0  0.526738       2.806582    -0.018087
             0.02           0.3       370     669.688427        0.072399          0.040781         1.0  0.505405       2.368714    -0.024306
             0.05           0.2       354     793.641381        0.089677          0.052485         1.0  0.525424       2.975167    -0.014740
             0.05           0.3       352     718.827034        0.081685          0.046702         1.0  0.502841       2.639061    -0.017902
```

### regime_gated — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        73        73     125.765628        0.068913         -0.000931          0.158352      0.9728  0.383562       2.849213   -0.018206        8.880752           1.037837    -0.018747      3.643836       89.160305
oos_fold_2       177       174     360.968056        0.081575          0.031356          0.141556      0.9998  0.548023       2.893808    0.007555      186.225184           0.782530    -0.014866      4.350282      257.714863
oos_pooled       250       247     486.733685        0.077877          0.036151          0.125045      1.0000  0.500000       2.882080   -0.000138      293.090396           0.849432    -0.018747      4.144000      158.870256
```

### regime_gated — cost stress (OOS pools only, last pick)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
regime_gated@1x       247       244     536.395666        0.086866          0.034726          0.150745      1.0000  0.481781       3.075348   -0.007554      284.687071           0.944957    -0.017372      4.028340      156.963813
regime_gated@2x       247       244     367.228076        0.059470          0.008870          0.121630      0.9922  0.360324       2.069662   -0.031743      124.468345           1.322656    -0.042671      4.024291      156.963813
regime_gated@3x       247       244     196.511745        0.031824         -0.017326          0.091946      0.8704  0.267206       1.440982   -0.055672      -37.511220           2.366510    -0.092231      3.995951      156.963813
```

### regime_gated — VERDICT: NOT VALIDATED
- does not beat placebo upper CI (0.3168)

## boost_follow — full grid (every config tried)
```
 p_min_liq  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
     15000          0.25        22     -15.302955       -0.027824          -0.10894      0.2626  0.272727        0.72075    -0.020141
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
     0.12        0.08            0.02          0.15        97     459.258020        0.189385          0.111022         1.0  0.731959       8.972488    -0.012499
     0.12        0.08            0.02          0.20        96     425.053095        0.177105          0.099020         1.0  0.729167       7.156457    -0.013921
     0.12        0.08            0.08          0.15        75     399.866742        0.213262          0.115665         1.0  0.720000       9.025300    -0.012499
     0.12        0.08            0.08          0.20        75     392.048316        0.209092          0.110916         1.0  0.720000       7.679218    -0.013921
     0.12       99.00            0.02          0.15       139     658.816823        0.189588          0.123066         1.0  0.661871       6.210744    -0.016403
     0.12       99.00            0.02          0.20       139     614.955495        0.176966          0.113080         1.0  0.676259       5.133131    -0.011631
     0.12       99.00            0.08          0.15       119     607.114225        0.204072          0.129744         1.0  0.647059       6.116646    -0.016403
     0.12       99.00            0.08          0.20       119     594.180974        0.199725          0.124664         1.0  0.663866       5.291920    -0.011631
     0.25        0.08            0.02          0.15        98     462.195614        0.188651          0.112160         1.0  0.724490       9.454628    -0.012499
     0.25        0.08            0.02          0.20        97     426.339040        0.175810          0.099032         1.0  0.721649       7.292280    -0.013921
     0.25        0.08            0.08          0.15        77     399.065966        0.207307          0.113694         1.0  0.701299       8.882544    -0.012499
     0.25        0.08            0.08          0.20        77     388.334249        0.201732          0.107524         1.0  0.701299       7.222227    -0.013921
     0.25       99.00            0.02          0.15       144     646.013084        0.179448          0.113155         1.0  0.638889       5.686625    -0.019794
     0.25       99.00            0.02          0.20       143     615.638661        0.172207          0.109075         1.0  0.664336       5.017549    -0.011626
     0.25       99.00            0.08          0.15       125     590.572116        0.188983          0.113995         1.0  0.616000       5.413821    -0.019794
     0.25       99.00            0.08          0.20       124     589.864128        0.190279          0.116807         1.0  0.645161       4.988471    -0.011626
```

### composite_v2 — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1        21        21      55.176875        0.105099         -0.023385          0.278026      0.9256  0.571429       3.414795    0.014024       -4.666771           1.002297    -0.008460      3.619048       25.692438
oos_fold_2        54        54     284.257278        0.210561          0.086167          0.371875      1.0000  0.666667       7.004816    0.036444      130.315264           0.541559    -0.008312      5.481481       79.427988
oos_pooled        75        75     339.434152        0.181032          0.079609          0.306323      1.0000  0.640000       5.836090    0.026747      176.459880           0.553158    -0.008460      4.960000       47.829938
```

### composite_v2 — cost stress (OOS pools only, last pick)
```
          label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
composite_v2@1x        78        78     448.266231        0.229880          0.094283          0.410564      1.0000  0.641026       7.737337    0.025983      201.042728           0.626149    -0.007437      5.025641       49.743136
composite_v2@2x        78        78     387.411248        0.198672          0.066573          0.374356      1.0000  0.500000       5.510094    0.000552      149.054812           0.698155    -0.014722      5.025641       49.743136
composite_v2@3x        78        78     327.549827        0.167974          0.039398          0.338573      0.9986  0.423077       3.962494   -0.024551       97.848355           0.795301    -0.024989      5.025641       49.743136
```

### composite_v2 — VERDICT: NOT VALIDATED
- does not beat placebo upper CI (0.3168)

## knife_catch — full grid (every config tried)
```
 p_min_dip  p_use_regime  x_max_hold_min  x_stop_frac  x_trail_frac  n_trades  total_pnl_usd  expectancy_ret  expectancy_ci_lo  p_positive  win_rate  profit_factor  max_dd_frac
      0.30             0              60         0.90           0.9       380    2810.769732        0.295590          0.166032      1.0000  0.586842       2.765856    -0.080839
      0.30             0              60         0.35           0.9       397    3257.506962        0.327952          0.210231      1.0000  0.546599       3.904379    -0.040359
      0.30             0             120         0.90           0.9       363    2811.869168        0.309554          0.176009      1.0000  0.589532       2.833963    -0.076065
      0.30             0             120         0.35           0.9       392    3289.537251        0.335403          0.214942      1.0000  0.545918       3.958110    -0.038966
      0.30             1              60         0.90           0.9       217    1928.463243        0.354963          0.155870      1.0000  0.585253       3.124465    -0.048481
      0.30             1              60         0.35           0.9       228    2211.047661        0.387428          0.206677      1.0000  0.543860       4.485013    -0.036387
      0.30             1             120         0.90           0.9       209    1873.361509        0.358004          0.150954      1.0000  0.578947       3.099735    -0.057297
      0.30             1             120         0.35           0.9       226    2257.430976        0.399066          0.215610      1.0000  0.548673       4.613379    -0.036387
      0.35             0              60         0.90           0.9       341    2412.192510        0.282642          0.140204      1.0000  0.568915       2.550903    -0.089919
      0.35             0              60         0.35           0.9       354    2889.716337        0.326230          0.192087      1.0000  0.525424       3.714627    -0.039097
      0.35             0             120         0.90           0.9       314    2412.811519        0.307025          0.152107      1.0000  0.570064       2.680610    -0.073800
      0.35             0             120         0.35           0.9       351    2928.063184        0.333388          0.197672      1.0000  0.524217       3.774451    -0.038576
      0.35             1              60         0.90           0.9       194    1678.539390        0.345515          0.124261      1.0000  0.561856       2.975495    -0.063581
      0.35             1              60         0.35           0.9       199    1968.081744        0.395050          0.188607      1.0000  0.532663       4.483187    -0.035320
      0.35             1             120         0.90           0.9       180    1707.910392        0.378915          0.146287      1.0000  0.566667       3.189126    -0.056772
      0.35             1             120         0.35           0.9       199    2003.418768        0.402153          0.194442      1.0000  0.532663       4.545728    -0.035026
      0.45             0              60         0.90           0.9       266    1736.213912        0.260214          0.088136      0.9992  0.500000       2.315742    -0.072400
      0.45             0              60         0.35           0.9       270    2087.748101        0.308826          0.139470      1.0000  0.455556       3.281934    -0.065613
      0.45             0             120         0.90           0.9       246    1787.623437        0.290141          0.100749      1.0000  0.508130       2.446085    -0.085231
      0.45             0             120         0.35           0.9       269    2045.671137        0.303717          0.134365      1.0000  0.449814       3.234060    -0.066783
      0.45             1              60         0.90           0.9       141    1174.644288        0.331721          0.045049      0.9948  0.496454       2.634258    -0.069584
      0.45             1              60         0.35           0.9       143    1453.793579        0.405898          0.133976      1.0000  0.482517       3.965412    -0.037183
      0.45             1             120         0.90           0.9       132    1198.238576        0.362257          0.057673      0.9964  0.500000       2.727521    -0.047696
      0.45             1             120         0.35           0.9       143    1449.650726        0.404739          0.133080      1.0000  0.475524       3.952316    -0.037183
```

### knife_catch — walk-forward OOS (per fold + pooled)
```
     label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
oos_fold_1       107       107     524.138359        0.195986          0.064160          0.346792      0.9990  0.532710       2.368694    0.026102      290.086432           0.714026    -0.089677      4.626168       130.35533
oos_fold_2        80        80     365.656102        0.181735          0.068043          0.299273      0.9998  0.525000       2.841330    0.045945      245.535166           0.417194    -0.035768      6.762500       116.59919
oos_pooled       187       187     889.794461        0.189890          0.100493          0.289456      1.0000  0.529412       2.530091    0.031873      655.742534           0.592045    -0.089677      5.540107       119.68000
```

### knife_catch — cost stress (OOS pools only, last pick)
```
         label  n_trades  n_tokens  total_pnl_usd  expectancy_ret  expectancy_ci_lo  expectancy_ci_hi  p_positive  win_rate  profit_factor  median_ret  pnl_minus_top3  top5pct_pnl_share  max_dd_frac  avg_hold_min  trades_per_day
knife_catch@1x       121       121     885.573232        0.292029          0.136929          0.463879      1.0000  0.520661       3.143499    0.047601      555.898513           0.622860    -0.042089      6.586777       77.302573
knife_catch@2x       121       121     771.655000        0.254331          0.103241          0.421638      1.0000  0.504132       2.712610    0.016562      453.290437           0.687174    -0.048167      6.586777       77.302573
knife_catch@3x       121       121     661.304253        0.217813          0.070531          0.379497      0.9984  0.462810       2.352850   -0.010776      353.980473           0.770407    -0.052617      6.586777       77.302573
```

### knife_catch — VERDICT: NOT VALIDATED
- does not beat placebo upper CI (0.3168)

## Summary

- **grad_momentum**: NOT validated (only 28 OOS trades (<30); pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.3168); pooled OOS P&L carried entirely by top-3 trades)
- **dip_reclaim**: NOT validated (does not beat placebo upper CI (0.3168))
- **trending_follow**: NOT validated (pooled OOS cluster-bootstrap CI includes <= 0; does not beat placebo upper CI (0.3168); dies at 2x costs (OOS); pooled OOS P&L carried entirely by top-3 trades)
- **regime_gated**: NOT validated (does not beat placebo upper CI (0.3168))
- **boost_follow**: NOT validated (no pooled out-of-sample trades)
- **composite_v2**: NOT validated (does not beat placebo upper CI (0.3168))
- **knife_catch**: NOT validated (does not beat placebo upper CI (0.3168))

> A strategy not marked VALIDATED must not be run live.
> Paper-trade validated strategies first; live only with
> throwaway funds and the risk caps in config/default.yaml.
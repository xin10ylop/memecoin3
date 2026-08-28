# Panel base rates

pools: 20  (indexed by GT with >= $2k max reserve, >=30 bars)

## Unconditional (from first indexed bar)
- gross fwd 5m: n=20 mean=1.920 p25=0.997 med=1.006 p75=1.346 p95=3.638 frac>1: 70.0%
- gross fwd 15m: n=20 mean=1.663 p25=0.992 med=1.000 p75=1.534 p95=4.953 frac>1: 50.0%
- gross fwd 30m: n=20 mean=1.735 p25=0.987 med=1.005 p75=1.734 p95=7.111 frac>1: 60.0%
- gross fwd 60m: n=16 mean=0.993 p25=0.808 med=0.998 p75=1.197 p95=1.936 frac>1: 50.0%
- gross fwd 120m: n=12 mean=0.894 p25=0.792 med=0.985 p75=1.004 p95=1.572 frac>1: 33.3%
- gross fwd 240m: n=7 mean=0.999 p25=0.993 med=1.006 p75=1.010 p95=1.014 frac>1: 57.1%
- gross fwd 480m: n=7 mean=1.016 p25=0.967 med=1.013 p75=1.045 p95=1.106 frac>1: 57.1%
- peak multiple: n=20 mean=3.268 p25=1.155 med=1.391 p75=2.348 p95=8.881 frac>1: 95.0%
- minutes to peak: n=20 mean=1026.900 p25=13.250 med=45.000 p75=1956.750 p95=4229.700 frac>1: 95.0%

## Conditional on crossing tradable gate ($15k liq & $10k/h vol)
- gross fwd 5m: n=13 mean=0.867 p25=0.966 med=1.001 p75=1.009 p95=1.047 frac>1: 53.8%
- gross fwd 15m: n=13 mean=0.887 p25=0.940 med=0.999 p75=1.045 p95=1.191 frac>1: 46.2%
- gross fwd 30m: n=13 mean=0.906 p25=0.997 med=1.003 p75=1.043 p95=1.382 frac>1: 61.5%
- gross fwd 60m: n=10 mean=0.880 p25=0.987 med=1.000 p75=1.039 p95=1.220 frac>1: 50.0%
- gross fwd 120m: n=10 mean=0.892 p25=0.982 med=1.015 p75=1.065 p95=1.300 frac>1: 70.0%
- gross fwd 240m: n=7 mean=1.006 p25=1.003 med=1.013 p75=1.016 p95=1.017 frac>1: 71.4%
- gross fwd 480m: n=5 mean=1.014 p25=1.006 med=1.019 p75=1.021 p95=1.021 frac>1: 100.0%
- peak multiple after gate: n=13 mean=1.170 p25=1.029 med=1.073 p75=1.124 p95=1.575 frac>1: 92.3%
- minutes to peak after gate: n=13 mean=138.846 p25=25.000 med=40.000 p75=127.000 p95=460.200 frac>1: 92.3%
- age at gate (min): n=13 mean=1435.308 p25=9.000 med=1458.000 p75=1938.000 p95=4285.800 frac>1: 100.0%

## By dex (final/first, unconditional)
- fluxbeam fwd 8h: n=0
- meteora fwd 8h: n=3 mean=0.975 p25=0.956 med=0.966 p75=0.989 p95=1.008 frac>1: 33.3%
- pump-fun fwd 8h: n=0
- pumpswap fwd 8h: n=1 mean=0.968 p25=0.968 med=0.968 p75=0.968 p95=0.968 frac>1: 0.0%
- raydium fwd 8h: n=2 mean=1.089 p25=1.067 med=1.089 p75=1.110 p95=1.127 frac>1: 100.0%
- raydium-clmm fwd 8h: n=1 mean=1.045 p25=1.045 med=1.045 p75=1.045 p95=1.045 frac>1: 100.0%
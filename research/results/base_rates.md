# Panel base rates

pools: 349  (indexed by GT with >= $2k max reserve, >=30 bars)

## Unconditional (from first indexed bar)
- gross fwd 5m: n=349 mean=1.442 p25=1.000 med=1.036 p75=1.348 p95=2.313 frac>1: 73.4%
- gross fwd 15m: n=349 mean=2.269 p25=1.000 med=1.087 p75=1.809 p95=5.225 frac>1: 74.5%
- gross fwd 30m: n=349 mean=3.380 p25=1.002 med=1.158 p75=2.234 p95=9.254 frac>1: 77.7%
- gross fwd 60m: n=349 mean=3.941 p25=1.000 med=1.235 p75=2.329 p95=10.857 frac>1: 75.1%
- gross fwd 120m: n=349 mean=4.479 p25=1.002 med=1.282 p75=2.807 p95=10.412 frac>1: 77.4%
- gross fwd 240m: n=349 mean=4.996 p25=1.001 med=1.245 p75=3.134 p95=12.130 frac>1: 76.2%
- gross fwd 480m: n=349 mean=4.518 p25=0.996 med=1.247 p75=3.197 p95=11.671 frac>1: 73.9%
- peak multiple: n=349 mean=21.273 p25=1.282 med=2.081 p75=5.844 p95=25.984 frac>1: 99.1%
- minutes to peak: n=349 mean=1591.570 p25=38.000 med=136.000 p75=1515.000 p95=10200.200 frac>1: 98.9%

## Conditional on crossing tradable gate ($15k liq & $10k/h vol)
- gross fwd 5m: n=258 mean=1.148 p25=0.999 med=1.020 p75=1.095 p95=2.092 frac>1: 72.5%
- gross fwd 15m: n=258 mean=1.372 p25=0.999 med=1.055 p75=1.260 p95=3.086 frac>1: 72.1%
- gross fwd 30m: n=258 mean=1.509 p25=0.998 med=1.097 p75=1.463 p95=4.382 frac>1: 73.3%
- gross fwd 60m: n=258 mean=1.605 p25=0.993 med=1.123 p75=1.647 p95=4.672 frac>1: 70.2%
- gross fwd 120m: n=258 mean=1.677 p25=0.996 med=1.128 p75=1.873 p95=4.784 frac>1: 72.1%
- gross fwd 240m: n=258 mean=1.737 p25=0.988 med=1.112 p75=1.859 p95=4.882 frac>1: 69.0%
- gross fwd 480m: n=258 mean=2.963 p25=0.981 med=1.124 p75=1.916 p95=5.056 frac>1: 70.2%
- peak multiple after gate: n=258 mean=3.840 p25=1.074 med=1.452 p75=2.572 p95=8.461 frac>1: 96.9%
- minutes to peak after gate: n=258 mean=139.922 p25=21.000 med=46.000 p75=153.000 p95=624.150 frac>1: 96.5%
- age at gate (min): n=258 mean=1116.054 p25=9.000 med=9.500 p75=1193.500 p95=4468.500 frac>1: 100.0%

## By dex (final/first, unconditional)
- byreal fwd 8h: n=4 mean=1.005 p25=0.993 med=1.000 p75=1.011 p95=1.038 frac>1: 50.0%
- fluxbeam fwd 8h: n=14 mean=9.259 p25=8.614 med=9.682 p75=9.899 p95=10.041 frac>1: 100.0%
- meteora fwd 8h: n=19 mean=1.278 p25=0.975 med=0.996 p75=1.048 p95=3.312 frac>1: 47.4%
- meteora-damm-v2 fwd 8h: n=3 mean=1.102 p25=1.062 med=1.078 p75=1.130 p95=1.171 frac>1: 100.0%
- orca fwd 8h: n=10 mean=1.018 p25=0.997 med=1.014 p75=1.033 p95=1.062 frac>1: 70.0%
- pancakeswap-v3-solana fwd 8h: n=3 mean=1.034 p25=1.022 med=1.049 p75=1.053 p95=1.056 frac>1: 66.7%
- pump-fun fwd 8h: n=5 mean=1.296 p25=0.616 med=1.745 p75=1.832 p95=2.010 frac>1: 60.0%
- pumpswap fwd 8h: n=249 mean=5.437 p25=1.017 med=1.700 p75=3.823 p95=15.640 frac>1: 76.7%
- raydium fwd 8h: n=28 mean=0.996 p25=0.980 med=1.001 p75=1.031 p95=1.119 frac>1: 57.1%
- raydium-clmm fwd 8h: n=11 mean=1.026 p25=1.003 med=1.042 p75=1.047 p95=1.053 frac>1: 81.8%
- zerofi fwd 8h: n=3 mean=1.013 p25=0.997 med=1.001 p75=1.023 p95=1.041 frac>1: 66.7%
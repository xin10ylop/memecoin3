All analyses complete. Final report:

---

# NARRATIVE LAUNCH-WAVES — name-cluster analysis (data/panel.db, 2026-08-27 14:37 → 08-29 01:21 UTC; window A ts<1787860000 ≈ first 5.2h, window B ≈ next 29.6h)

**Method**: launch universe = 18,780 tokens (earliest pool per `base_token_address`, created within panel span, 1.56d). Names+symbols lowercased, `[a-z0-9]+` tokenized (len≥2); stopwords = top-50 by frequency (the, coin, cat, ape, on, is, solana, this, fone, in, of, dog, to, monkey, pump, …) ∪ explicit generic list (68 total). Wave = ≥4 launches sharing a distinctive word, chained at ≤3h gaps with ≥4 inside some 3h sub-window; waves merged at Jaccard≥0.6; each token assigned to its earliest wave. Entry = first bar strictly after first `reserve_usd≥10k` snapshot (combined OHLCV-minute + snapshot price series, next-bar convention, terminal extension for dead series, end-of-panel-censored entries excluded per horizon). Means winsorized at pooled [p1,p99] (r60 cap +1,608%, r240 cap +1,846% — raw series contain 1e6×+ bonding-curve/decimals glitch prints, concentrated in pumpswap/meteora pools); medians and hit-rates reported alongside; 2,000-draw bootstrap over tokens (1 event/token = cluster unit).

## (1) Wave inventory
- **1,549 waves** (starting in A: 132, B: 1,417), **990.6 waves/day**; sizes: median 7, mean 10.0, max 72, 724 waves ≥8 members. 15,417 member-slots = **82.1% of all launches** are wave-covered — at ~12k launches/day, copycatting is the norm, not the exception.
- Largest waves (word | n | span | actual names): **lara** 72 in 27min ('Lara', 'LITECOIN CONFIRMED LARA CHECK!!' ×dozens); **vampy** 56/6h ('Evil Vampy', 'HE TWEETED VAMPY GENNY'); **social** 54/4.4h ('Truth Social Memecoin Index (TSMI)', 'NEW GOV TRUTH SOCIAL MEME ETF??!'); **fomo** 52/9.2h ('Frog On Mobile', 'frogonfomo'); **elonish** 49 in 4min; **real** 48 ('hello? THE REAL GIRLCOIN'); **first** 47 ('The First Meme (MEME1921)').
- Qualification (ever cross 10k reserve) is **flat across positions**: 1st 9.3% (85/915), 2nd–3rd 8.1% (155/1,924), 4th+ 9.7% (732/7,585), non-wave 9.2% (767/8,356) — launch order does not predict reaching liquidity.

## (2) Wave-position outcomes (per window; n = tokens)
**Window A** (154 qualified events total): 1st launched n=12 **INSUFFICIENT** (med240 −60.4%, mean240 −39.5% [−70.6,−7.2] — directionally awful); 2nd–3rd n=18: fwd60 +144.9% [−7.0,+363.8], med +10.9%; 4th+ n=50: +76.8% [+0.6,+182.9], med +1.6%; 1st-to-cross n=40: +134.6% [+25.4,+261.1] vs later-crosser n=40: +51.6% [−10.4,+142.1]; non-wave n=74: +67.1% [+13.0,+140.5].
**Window B** (1,506 events): 1st launched n=71: fwd60 **+9.8%** [−10.8,+34.0], med +0.2%; 2nd–3rd n=130: +28.9% [−5.1,+76.4], med +0.9%; 4th+ n=653: **+48.4%** [+34.1,+63.6], med +6.1%; fwd240 same ordering (1st +19.1 / 2nd–3rd +29.3 / 4th+ +47.0). Cross-order: 1st-to-cross n=352 +20.2% [+5.1,+37.0], med +0.0% vs later-crosser n=502 **+57.7%** [+39.1,+78.1], med +10.1%. Non-wave n=652: +57.2% [+40.6,+75.5], med +5.0%.
**Leader-premium test (1st minus 4th+, fwd60, W-B): −38.6% [−63.0,−14.1]** — significantly NEGATIVE. Cross-order flips sign between windows (A: 1st-to-cross better; B: later-crossers better) — not robust.

## (3) Wave-heat regime
Binary ACTIVE (≥1 wave-member 10k-cross in prior 60min, excl. self) covers 74% (A) / 78% (B) of minutes → QUIET arm n=4 (A) / n=12 (B) = **INSUFFICIENT; binary regime untestable at this launch density**. Graded (within-window heat terciles, heat = # wave-member crossings in prior hour): W-B HIGH(>49) vs LOW(≤32): fwd60 +62.0 vs +35.7, **diff +26.3% [+1.1,+52.6]** (n=514 vs 536); fwd240 **diff +33.5% [+2.7,+66.3]**; medians favor LOW at 60m (+6.6 vs +4.4) — mean-driven, tail-carried. W-A: diff −43.5% [−161.4,+70.5] (n=46 vs 53) — opposite sign, ns. **Positive in B only; not window-robust.**

## (4) Avoid-filter: 4th+ vs non-wave
W-A: 4th+ n=50 vs non-wave n=74 — diff60 +9.6% [−98.4,+123.0], %neg60 28 vs 27, %240≤−50% 20 vs 20. W-B: n=653 vs 652 — **diff60 −8.8% [−31.2,+13.2]**, med 6.1 vs 5.0, %neg60 27 vs 28, rug-rate 19 vs 18. **No separation on any statistic in either window — '4th+ wave member' is NOT a negative filter** once the token has already reached 10k liquidity.

## Caveats
Single collection episode (~1.5 days); window A is only 5.2h/154 events; wave taxonomy captures 82% of launches so "non-wave" is a residual class; all groups show positive winsorized-mean drift post-10k-cross (survivor/selection structure of the panel) — comparisons are cross-sectional only; price feed contains extreme glitch prints (winsorization mandatory; medians are the trustworthy statistic).

## VERDICT
- **(a) Wave-leader entry: DEAD END.** Leaders (1st launched) are the *worst* position tier in the powered window (diff vs 4th+ −38.6% [−63.0,−14.1] at 60m; window A leaders med240 −60%, n=12 insufficient but concordant). Leaders also cross 10k no more often (9.3% vs 9.7%). First-to-cross advantage flips sign across windows. No exploitable leader premium at 10k-liquidity entry.
- **(b) Copycat avoid-filter: DEAD END.** 4th+ membership carries zero incremental information vs non-wave baseline in both windows (all CIs straddle 0; identical rug rates). The 10k-liquidity gate already absorbs whatever selection the copycat label would provide; late copycats that *do* reach liquidity perform like everything else (if anything, med +6.1% vs +5.0% better in B).
- **(c) Wave-onset regime input: WEAK CANDIDATE, needs more data.** Binary active/quiet is untestable (market is "active" 74–78% of minutes). Graded heat shows a mean-return gradient in window B only (+26%/+34% HIGH−LOW at 60/240m, CIs excluding 0 but barely, medians disagree, window A opposite-signed). Worth re-testing as a continuous feature on a longer panel with day-level clustering before any deployment.

Script: `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/waves.py`; full tables: `/tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/out.txt`.
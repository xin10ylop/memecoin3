# Organic-Flow Filters — Entry-Eligible Screen Analysis

## Methodology
Loaded full panel via `memebot.data.store.load_panel` (872 pools pass min_max_reserve=2000), added causal features; entry-eligible bars = reserve_usd≥15k, fdv∈[1e5,3e7], vol_h1_snap≥1e4 → 3,869 bar-observations, 116 tokens (Window A ts<1787860000: 1,566 bars/45 tokens; Window B: 2,303 bars/81 tokens). Forward return = close[t+1]→close[t+61] (next-bar entry, 60m hold), validated against the continuous minute grid. All CIs are 95% cluster bootstrap by base_mint (4,000 draws; 20,000 for p-values); tier "effect" = mean(tier) − mean(complement), same clustering; winsorized column clips fwd60 at +300% to check moonshot-tail sensitivity.

**Baseline (ALL eligible):** W A mean fwd60 +3.53% CI[−11.4%, +18.9%] (45 tok, n.s.); W B +13.65% CI[+3.4%, +23.7%] (81 tok, significant). Tape regime dwarfs any screen; screens below are judged vs their complement. fwd60 is heavy-tailed (p99 ≈ +270–340%, max +881%), hence the winsorized robustness column.

## (a) Buyers-per-trade: buyers_m5/max(buys_m5,1)

| tier | W | bars | tokens | mean | 95% CI (tier mean) | median | %>0 | effect vs rest [CI] |
|---|---|---|---|---|---|---|---|---|
| <0.5 | A | 553 | 24 | −2.13% | [−25.9, +17.5] | +11.7% | 69% | −8.7pp [−38.3, +17.7] |
| <0.5 | B | 680 | 32 | +25.83% | [+10.2, +39.3] | +21.4% | 81% | +17.3pp [−2.6, +36.0] |
| 0.5–0.8 | A | 485 | 29 | +3.02% | [−23.0, +32.2] | −6.2% | 42% | −0.7pp [−26.8, +26.9] |
| 0.5–0.8 | B | 704 | 36 | +14.76% | [−0.9, +30.2] | +3.4% | 58% | +1.6pp [−13.1, +17.4] |
| >0.8 | A | 528 | 26 | +9.91% | [−5.9, +29.2] | +2.1% | 60% | +9.6pp [−10.9, +32.1] |
| >0.8 | B | 919 | 48 | +3.79% | [−11.0, +17.6] | +0.5% | 51% | **−16.4pp [−32.4, −1.6]** |

Sign FLIPS between windows in every tier: >0.8 ("organic crowd") is +9.6pp in A but significantly −16.4pp in B; <0.5 ("bots") −8.7pp in A, +17.3pp in B. Equal-weight token means in B are flat (+9.8/+12.2/+11.7%), so B's bar-weighted effect is concentration-driven. The crowd-good hypothesis is contradicted in the hot tape. **Dead end.**

## (b) Turnover: vol_h1_snap/reserve_usd

| tier | W | bars | tokens | mean | 95% CI (tier mean) | median | %>0 | effect vs rest [CI] | wins@300% effect |
|---|---|---|---|---|---|---|---|---|---|
| <2 | A | 787 | 28 | +11.04% | [−3.6, +32.7] | +2.1% | 61% | +15.1pp [−12.6, +46.5] | +17.6pp |
| <2 | B | 1038 | 48 | +11.02% | [+1.0, +23.9] | +1.5% | 58% | −4.8pp [−23.5, +16.7] | −3.9pp |
| 2–10 | A | 226 | **14 (!)** | +22.05% | [−26.1, +91.9] | −5.9% | 45% | +21.6pp [−27.8, +93.8] | +8.6pp |
| 2–10 | B | 429 | 31 | +28.09% | [+7.4, +52.6] | +18.9% | 59% | +17.7pp [−5.9, +44.9], 1-sided p=0.080 | +15.2pp |
| >10 | A | 553 | 18 | −14.73% | [−41.5, +6.4] | +13.0% | 57% | **−28.2pp [−61.9, +0.6], 1-sided p=0.025** | −23.9pp |
| >10 | B | 836 | 29 | +9.50% | [−12.7, +30.6] | +19.7% | 70% | −6.5pp [−30.7, +17.0], 1-sided p=0.298 | −5.8pp |

turn>10 underperforms its complement in BOTH windows (−28.2pp / −6.5pp; equal-weight token means −22.8% vs +23.7/+33.2% in A, +6.0% vs +11.0/+26.2% in B); one-sided p=0.025 in A, though the two-sided 95% CI grazes zero (+0.6pp upper). Robust to winsorization. 2–10 tier is the best tier in both windows but has 14 tokens in A (insufficient) and CI includes zero in B. turn<2 sign-flips.

## (c) Early retention: dd from first-30min high at age 60m
Pools observed from creation, entry-eligible at the age-60 bar: **9 tokens total (A: 2, B: 7) — INSUFFICIENT DATA (<15/window), no verdict.** Raw pairs (window, ret_dd, fwd60): A(−0.99, −0.12), A(+0.42, +0.26); B(−0.23, −0.90), B(+0.16, +0.36), B(−0.99, −0.01), B(+0.02, 0.00), B(+0.38, +0.43), B(+0.33, +1.04), B(−0.87, +1.08). Directionally the age-60 winners (ret_dd>0) did well in B, but n forbids any claim.

## (d) Net buyer dominance: buy_frac

| tier | W | bars | tokens | mean | 95% CI (tier mean) | median | %>0 | effect vs rest [CI] | wins@300% effect |
|---|---|---|---|---|---|---|---|---|---|
| <0.45 | A | 344 | 17 | +3.40% | [−11.5, +22.6] | −0.4% | 49% | −0.2pp [−22.0, +22.8], p=0.485 | **+3.4pp (sign flips)** |
| <0.45 | B | 286 | 20 | −5.03% | [−25.6, +10.9] | −1.3% | 41% | **−21.3pp [−42.2, −3.0], p=0.011** | −20.8pp |
| 0.45–0.6 | A | 768 | 30 | −1.84% | [−23.3, +17.4] | +7.7% | 58% | −10.5pp [−36.5, +13.6] | −14.3pp |
| 0.45–0.6 | B | 925 | 42 | +9.32% | [−4.5, +21.2] | +8.4% | 59% | −7.2pp [−23.8, +7.7] | −7.5pp |
| >0.6 | A | 454 | 28 | +12.70% | [−15.2, +43.1] | +2.1% | 62% | +12.9pp [−19.3, +46.6], p=0.224 | +14.4pp |
| >0.6 | B | 1092 | 59 | +22.21% | [+7.7, +36.5] | +24.0% | 71% | +16.3pp [−0.5, +34.5], **1-sided p=0.033** | +16.3pp |

buy_frac>0.6 is positive vs complement in both windows (+12.9pp / +16.3pp), monotone tier ordering in B (−5.0 → +9.3 → +22.2% means; 41→59→71% hit rate), one-sided p=0.033 in B (two-sided CI grazes zero at −0.5pp). buy_frac<0.45 is strongly bad in B only (−21.3pp, CI excludes zero) but ~0pp in A and flips sign under winsorization.

## VERDICT

**Composite-strategy candidates (sign-consistent both windows; significance caveats stated):**
1. **EXCLUDE turnover>10 (wash/churn screen)** — strongest screen. Effect −28.2pp (A) / −6.5pp (B), same sign both windows, one-sided p=0.025 in A, robust to winsorization and to equal-weighting tokens. Two-sided 95% CI in A grazes zero (+0.6pp), so it meets the candidacy bar only via the one-sided test — label it a candidate with that caveat. 18/29 tokens.
2. **REQUIRE buy_frac>0.6 (buyer-dominance screen)** — +12.9pp (A) / +16.3pp (B), monotone tiers and CI-significant tier mean in B (one-sided effect p=0.033; two-sided CI touches −0.5pp). 28/59 tokens. Borderline but sign-consistent and winsorization-stable; sensible as a composite AND-condition, not standalone.

**Weak / B-only (passes the letter of the rule, fails its spirit):**
- **EXCLUDE buy_frac<0.45** — B effect −21.3pp with CI excluding zero; but A effect is −0.2pp (p=0.49) and flips to +3.4pp winsorized. Treat as subsumed by the >0.6 requirement, not an independent screen.

**Dead ends:**
- **(a) buyers-per-trade ratio** — sign flips across windows in all three tiers; the "crowd" tier (>0.8) is significantly negative in B (−16.4pp, CI [−32.4, −1.6]). Do not use.
- **turnover<2** — sign flips (+15.1pp A / −4.8pp B).

**Insufficient data:**
- **(c) early retention at age 60m** — 2 tokens (A) / 7 tokens (B).
- **turnover 2–10 as a positive tier** — best tier in both windows (+21.6/+17.7pp) but only 14 tokens in A; re-test when the panel grows.

Caveat: window A's all-eligible baseline is statistically zero, so every A-window effect rides on 14–30 tokens with heavy tails; the two candidate screens should enter the composite as gates and be re-validated on the next collection window before weighting capital.

Scripts/data: /tmp/claude-0/-home-user-memecoin3/1ab0d9cd-b817-53eb-8ea2-90d8142a7979/scratchpad/{extract_obs.py, stats.py, effects.py, obs.pkl, cobs.pkl}
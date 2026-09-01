# Autopsy: the migration scalper is dead

**Verdict: no exploitable edge.** Called 2026-09-02 on the live system's own
measurements (`research/live_journal_test.py`), not on a backtest.

## The evidence that killed it

Walk-forward OOS on the live journal — the bot's own recorded features, its
own executable outcomes, its own candidates. 445 range-qualifying rows.

| rule | TEST | 95% CI | placebo p |
|---|---|---|---|
| range only | +8.4% | [−1.7%, +20.0%] | — |
| + clean chart ≤10% | −3.8% | [−14.2%, +7.4%] | 0.94 |
| + clean chart ≤20% | +0.1% | [−11.9%, +15.4%] | 0.91 |
| + accel 1–10 | −7.7% | [−21.7%, +3.9%] | 0.81 |
| + accel & clean10 | −8.7% | [−25.6%, +4.8%] | 0.79 |

Every CI spans zero. Every filter is **worse than random selection**
(placebo 0.79–0.94). Live paper P&L over 31 trades: **−$61 on a $100 stake.**

Coverage was 63%, and the missing rows are pools the aggregator dropped —
disproportionately dead. So the table above reads **optimistic** and the
truth is worse. That is why the call is safe at 63%: more data can only
lower these numbers.

## Cause of death: every positive number measured something unreachable

The same error twice, in two costumes.

1. **Bar-high scoring.** Exits were scored against intra-minute peaks a live
   bot cannot sell into. On this population that inflated returns by ~47pp.
   A flat pool with one $10 wick to 5x scored +348%; a real seller got −2%.
   Every ranking built on it — trail widths, which filters to keep — was
   ranked on prices that did not exist.

2. **Panel population.** After fixing (1), an honest re-score of the panel
   said range+clean-chart on migrations was +66%, walk-forward, placebo
   p=0.000, robust in both time-halves and to dropping the top 3 winners.
   The live journal said −1.8% on the same nominal rule and population. The
   filter-definition hypothesis (bar highs vs sparse polls) was tested and
   **falsified** — close-based still gave +50%. Best remaining explanation:
   the panel can only contain pools GeckoTerminal chose to index, a quality
   filter the bot cannot replicate at entry time. Unproven, and now moot.

The through-line: **a backtest is only worth what the live system can
actually observe and act on.** Both failures were measurement reaching
somewhere execution could not follow.

## What was real and is worth keeping

- **Executable scoring** (`peak_reality.py`, `wick_census.py`): arm the stop
  only on closed bars, fill from the next bar. Non-negotiable for anything
  that follows.
- **Fate-aware sampling**: death from the collector's record, censored rows
  dropped, never inferred from bar count. Requiring long history discarded
  46% of the panel and turned −? into +73%.
- **Placebo controls**: the single cheapest lie-detector here. Every filter
  that looked good in-sample died against a random same-size subset.
- **Config-drift instrumentation**: preflight reading the *service* env,
  epoch-stamped ledgers, paired scoring, coverage warnings. Roughly half of
  the lost days were config drift, not strategy error.

## Where the graveyard points next

The bonding-curve phase (`pump-fun`, 37,091 pools in the panel) is entirely
unexplored — every population traded here was **post**-migration, after the
first big move. It is also where ~99% of tokens die and where the
competition is fiercest. It is a from-scratch effort, not a tweak, and it
must be judged by executable scoring and placebo from day one.

**Nothing goes live on real capital from this project as it stands.**

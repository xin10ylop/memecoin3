# Narrative History and What It Changes About This System

**Canonical synthesis of four research reports (compiled 2026-08-29).** Sources are cited as
(R1) giant case files 2023–26, (R2) twin/control-group study, (R3) 12-coin quantitative
lifecycle study (DefiLlama daily closes, conservative lower bounds on drawdowns), and
(R4) early-detectability memo. Claims flagged **[folklore]** in the source reports stay flagged here.

**Context this document serves:** the repo's validated strategy is `knife_catch` — buy the first
-35%-from-high break after a ≥2x pump, 60-min timed hold, 35% disaster stop, no trail/TP
(`config/knife.yaml`, `research/results/REPORT.md`). The question answered here: does narrative
history (the giants and their dead twins) change anything about that design, and if so, what,
concretely and testably.

---

## 1. Narrative taxonomy and the hit-rate reality

Base rates first (R2, R4): ~1.4% of pump.fun launches ever graduated the bonding curve (~$69–100K
cap), falling to <1% after Feb 2025 and ~0.2–0.63% by 2025–26; 98.6% of launches classified as
pump-and-dumps or rugs (Solidus Labs); ~89% of memecoins sit below $1,000 cap and ~5% ever exceed
$10M; $1B+ outcomes are ~1 in 10⁵–10⁶ launches. Every per-category number below sits on top of that
denominator.

| Category | Giants (peak) | Documented twin hit-rate | Lifecycle signature |
|---|---|---|---|
| **Internet-native cult** (frog/satire/"culture coin") | PEPE ($10–11B), MOG ($1.5B), SPX6900 ($2.1B), USELESS ($440M, under the $500M bar), TROLL ($283M) | No census; niche consolidates into one cult coin per meme; Murad's endorsement concentrated flow but 9/10 of his picks went -90%+ (R4) | Slowest ascents (17–24 mo), biggest multiples (186x–626x from first price), deepest pre-ATH shakeouts (-84% to -95%); only category to make ATHs *after* the Feb 2025 purge (SPX Jul 2025) (R1, R3) |
| **Animal meta** (dogs, cats, news animals) | BONK ($4.4B), WIF ($4.8B), POPCAT ($2B), PNUT ($2.4B), MOODENG ($614–670M) | Largest rival squirrel token capped at $50M (48x below PNUT); owner's own JUSTICE coin ~$144M **[single-outlet]** then collapsed; ETH "MOODENG" stalled at ~$60M vs Solana's $336M+ (venue twin); "hundreds of clones" is **[folklore]** but consistent with 20K+/day launch rates (R2) | News-driven ones are vertical (PNUT $0→$1B+ in ~12 days, no second act); dog/cat metas mix vertical (WIF 4.3 mo) and staircase (BONK 23 mo, POPCAT 11 mo) (R1, R3) |
| **AI meta** | GOAT ($1.35B), FARTCOIN ($2.48B) | 300+ tokens spammed at Truth Terminal's wallet, none replicated GOAT; ~14,000 Virtuals agent tokens, flagship ai16z peaked $2.39B then -99.9% and declared dead by its founder; forged-provenance twin (IB, hacked account) = $25M cap dumped in 45 min (R2) | Meta ignition wins; the meta itself rotates and kills its own flagship (GOAT -98.9% as capital rotated to Fartcoin/ai16z) (R1) |
| **Political / celebrity** | TRUMP ($14.75B), MELANIA (>$2B) | FT census: 700+ copycats within 3 weeks (167 family-themed), majority -95% within hours; best twin (fake BARRON) $460M then -95%; single-digit big ones out of 700+ ≈ <1–2% (R2) | Shortest lifecycles on record (TRUMP 2 days, MELANIA hours); catalyst-path bets — BODEN -60% in 2h on Biden's withdrawal, CAR -95% in 48h; even the "winner" was extractive: ~810K wallets lost ~$2B while issuers took ~$100M fees (R2) |
| **Celebrity-launch extraction class** | none — HAWK ($490M→$60M in 20 min), YZY (-74/-81%, 73.8% of wallets lost), LIBRA ($4.5B→-95% same day), WOLF (-99% in 2 days) | This *is* the control group: correct narrative + bundled supply + pre-positioned snipers = harvesting machine, not a failed memecoin (R2) | Minutes-to-hours; serial extractors recur (Davis: MELANIA→LIBRA→WOLF→YZY; sniper "Naseem" on TRUMP and YZY) (R2) |
| **NFT-brand / platform** | PENGU ($2.7–4.3B debut, second leg ~$3B on ETF filing) | Pre-launch name-squatting fakes went to ~zero on launch day — cheapest, fastest-dying copycat class (R2) | Airdrop dump (-50% in hours, -94% to ATL), then TradFi catalysts (SEC ETF acknowledgment +30%) — a new catalyst class (R1) |
| **CTO revival** | none ≥$500M (TROLL $283M; GIGA ~$830M peak in R4's account) | ">99% of CTO attempts fail" per the CTO literature itself; no published denominator (R4) | Dead 11 months then +174,948% (TROLL); real precondition of several giants but base rate as predictor undocumented (R1, R4) |

Era break (R1, R2, R4): **after MELANIA (Jan 2025), no new memecoin reached $1B.** LIBRA
(Feb 14, 2025) ended the boom — pump.fun users -36% in 5 days, launches -⅔ in a month, global
memecoin cap $93B→$36.5B Jan 2025→Jan 2026, sector cap peak ~$150B Dec 2024 then capitulation.
2025–26 "giants" were mostly 2023–24 survivors making second legs. Hit rates and copycat lifespans
are regime-dependent: post-LIBRA copycat cohorts died *faster* because there was less exit
liquidity for twins.

---

## 2. Anatomy of a giant's ascent

From R3's 12-coin daily-close reconstruction (drawdown counts are **lower bounds** — intraday
wicks invisible):

**Speed medians:** $10M→$100M = 3.5 days; $100M→$1B = 40 days; first-tracked-price→ATH = 167 days.

**Two archetypes, not one:**
- **Cluster A "Vertical"** (ascent ≤ ~3 mo): PNUT, GOAT, TRUMP, MOODENG, FARTCOIN, WIF.
  Narrative-event coins. Few shakeouts (0–4), shallow-to-moderate (-38% to -68%), recovering in
  **days** (median 2–23d). Produced the *smaller* multiples (1.5x–961x, mostly ≤56x).
- **Cluster B "Staircase"** (ascent 7–24 mo): PEPE, BONK, POPCAT, MOG, SPX6900, PENGU.
  Delivered the 100x+ outcomes (160x–961x) but **all** passed through at least one -84% to -95%
  drawdown lasting 2–10.5 months before ATH (BONK -95%/315d under prior high; SPX -95%/260d;
  PEPE -84%/295d; PENGU -91%/182d).

**Shakeout counts (the number that matters for knife_catch):** 39 pre-ATH ≥-35% breaks across 12
coins — median 2.5, mean 3.25 per coin; 27 ≥-50% breaks (median 2); median deepest pre-ATH
shakeout **-80.5%**. 10 of 12 giants triggered at least one -35% break before ATH (exceptions:
the two ultra-verticals, TRUMP's 2-day ascent and PENGU's day-0 tick top). R3's rule of thumb:
**every run >30 days offered ≥1 such entry; every run >90 days offered ≥2.**

**What happened after a -35% trigger (n=39 pooled):** median 28 days to a new high; 36% resolved
within 14 days, 51% within 30 days — **but 23% took >100 days (max 317d)**, and depth routinely
continued to -60%/-90% *after* triggering. Positive-expectancy entry conditional on ex-post giant
status, with a fat left tail. R3's explicit survivorship warning: the same -35% signal fired on
thousands of coins that went to zero.

**The universal post-peak law (12/12):** the ATH was terminal. Median 33 days to fall below half
of peak; **90.5% of all post-ATH days spent below half of ATH**; median coin today at ~6% of
close-basis ATH; **0 of 12 ever reclaimed its ATH** across up to 880 days. All 12 are currently
77–99% below ATH.

### What this means for dip-buying
- The -35% break is not a one-shot event on a runner — it *recurs* (median 2.5 close-basis, more
  intraday). Dip-buying an eventual giant worked 39 times in this cohort.
- But the entry alone was not safe: staircase episodes bottomed at a median -80% peak-to-trough
  and 23% of episodes took >100 days to resolve. Surviving the tail required either wide stops or
  a **time-stop** — which is exactly what the validated 60-min hold is. The lifecycle data
  *endorses* the timed exit rather than arguing for holding through the dip.

### What this means for moonbag / tail-riding exit design
- **Patience paid only before the ATH.** R3: a system that holds through -80% pre-ATH but exits
  within ~30 days of a suspected top (before the median 33-day break of the 50%-of-ATH level)
  captures essentially the whole documented value. After the ATH, holding meant a median 90% of
  days below half of peak and zero recoveries in the entire sample.
- Therefore any moonbag/tail position **must have a kill condition**; "hold forever in case it's
  the next PEPE" is quantified as a median ~-94% outcome with 0/12 chance of ATH reclaim.
  A tail-rider needs either a trail or a time-under-level rule (e.g. exit after N days below 50%
  of the position's local high), because the top is never announced — it was ended by cycle
  rollovers, cannibal launches (MELANIA halving TRUMP within an hour), listing sell-the-news
  (MOG), meta rotation (GOAT), and catalyst exhaustion (PNUT: no catalyst class above "Musk
  posting about you") (R1).
- Cluster asymmetry: on verticals, dips recover in days and the run dies in weeks — tight trails
  and short time-boxes fit. On staircases, tails are months long and -60%+ deep — a moonbag wide
  enough to ride SPX or PEPE must tolerate -80% interim and multi-month underwater stretches,
  which only makes sense at negligible size (house-money residue), never as held risk capital.

---

## 3. Winner-vs-twin separators: observable early vs survivorship myths

### Documented separators (R2's synthesis table, settled within ~24–72h of a narrative igniting)
1. **First-mover within hours of the catalyst.** PNUT vs squirrel variants capped at $50M; Trump
   copycats began 30 minutes after the real launch and mostly died -95% in hours. Liquidity
   consolidates into whichever contract is focal *before* CEX listing.
2. **Verifiable provenance.** TRUMP posted from the principal's real account vs fake BARRON -95%
   on failed verification; PENGU's official CA vs name-squatting fakes; forged provenance (IB via
   hacked account) = instant extraction.
3. **Clean float** — no bundled insider block. Strongest single discriminator *between a winner
   and its same-week extraction twins* in R2's record (HAWK 80–97% insider, WOLF 82% one entity,
   LIBRA self-sniped, MELANIA sniped $2.4M at launch). **But see the R4 caveat below — this does
   not survive as an ex-ante giant filter.**
4. **CEX listing consolidation.** Binance/Coinbase listed exactly one twin per narrative; the
   ETH MOODENG, unlisted, stalled at 1/10th the Solana original's cap. Listings are the ratchet
   that makes the winner permanent — for a coin *already running*.
5. **Dev/principal behavior post-launch.** MOTHER, the only surviving 2024 celeb coin, kept its
   principal engaged; CHILLGUY -54% in hours on creator copyright hostility; CAR died on a
   vanished website.
6. **Venue.** Solana/pump.fun vs Ethereum for 2023–25 metas (moderate-strong per R2).
7. **Timing within the meta cycle.** Early-meta launches (MOODENG Sep, GOAT Oct, PNUT Nov 2024)
   won; after the flagship peaks, copycats are exit liquidity by construction.

### The reconciliation R2 vs R4 (important)
R2 finds "clean distribution" the strongest discriminator; R4 documents that **the giants
themselves flunked clean-distribution filters**: PEPE had ~30% of genesis supply in one bundled
cluster dumping day one and 10 wallets holding ~41%; TRUMP had 80% insider supply; WIF's "pure
fair launch" story is contradicted by a documented 29-participant presale taking 18% — the
contradiction itself evidence that clean-launch narratives are retrofitted marketing. Resolution:
clean float separates a narrative's winner from its *instant-extraction* twins (the
minutes-to-hours rug class), but it is **not** a reliable positive screen for gianthood. It works
as a rug filter, not a winner-picker.

### Survivorship myths (flagged in the reports)
- **Holder-curve rules** ("holders leading price = healthy", "top-10 <15% = safe"): correlational
  garnish; no out-of-sample lead time demonstrated; PEPE and TRUMP violate the concentration rule
  while being top performers (R4).
- **KOL calls as signal:** anti-signal on average — 86% of influencer-promoted coins -90% within
  3 months, only 1% ever 10x; KOL wallet-tracking (1.6M trades) shows they scalp their own flow
  (R4).
- **CEX listing as validation:** every 2024 Binance listing finished negative; 2025: 24 of 27
  negative, avg -44%. Spot listings repeatedly marked or missed tops (MOG's Coinbase listing was
  the top; MOODENG's and POPCAT's spot adds came *after* their price ATHs; perp listings fueled
  the 2024 runs instead) (R1, R4).
- **"Diamond hands always win":** false post-ATH — 0/12 reclaims, median at ~6% of peak (R3).
- **"Giants go straight up":** true only for Cluster A, which produced the smaller multiples (R3).
- **"You can't buy dips on runners":** false except for the two fastest verticals (R3).
- POPCAT whale-cornering and "hundreds of squirrel coins": **[folklore]**, uncensused (R1, R2).

---

## 4. The honest detectability verdict

R4's decomposition of a $1M→$2B ascent (~3.3 log-decades):

| Entry stage | Share of log ascent | Verdict |
|---|---|---|
| Pick at $1–5M | 100% | **Survivorship fantasy.** Real early signals exist (socials-at-launch = 8.9–17.4x graduation lift, n=832,941 survival analysis; 34 "elite deployers" with 71% bonding rates) but they predict *graduation to ~$70K* — a 10⁻² event — while gianthood is 10⁻⁵–10⁻⁶; no published model bridges the gap, and the giants themselves flunked the clean filters. Documented $1–5M winners either had structural access (MELANIA insiders buying 2.5 min pre-announcement; 1,012-wallet sniper rings) or are single anecdotes (Sigil Fund at $2M Fartcoin) with no disclosed repetition. |
| $10M–$100M momentum on survivors | ~70% | The capturable band — every documented giant offered months inside it — but conditional odds still ~1:200+, demanding strict trailing exits and 1:20–1:50 hit-rate sizing. |
| $100M+ post-listing trend | ~40% | Exists (WIF +158% post-Binance-ATH; SPX 20x from $100M) but 2025–26 outcomes show the exit rule, not the entry, determined whether anything was kept. |

The only public forward test of curated narrative picking — Murad's 10-pick list, published
Oct 2024 by a genuinely early, high-conviction, skin-in-the-game curator in the best macro window
memecoins ever had — went **~0/10 on a buy-and-hold basis** (9 of 10 down 90%+; even flagship SPX
below call-day price two years later) and **~10/10 as a 3-month momentum trade**. His personal
fortune came from a pre-thesis $10M-cap SPX entry, and the "never sell" doctrine converted his own
book to losses. That is a statement about **timing and exits, not narrative selection** (R4).

The best-informed cohort ever measured — Fartcoin's top-1,000 addresses — averaged $0.48 entry /
$0.53 exit: even whales captured a sliver (R4). And the extraction overlay is real and
professionalized: the same snipers and deployers recur across winners and rugs; retail copying
visible traces (KOL wallets) is documented to lose (R2, R4).

**Verdict: the ascent was partly capturable; the pick was not.** Edge in this market is
microstructure and exits, not selection at the $1M stage. This validates the repo's existing
positioning — a minute-scale microstructure strategy — and forecloses the tempting pivot to
"narrative sniping."

---

## 5. Concrete, testable implications for this system (ranked)

Ranked by (evidence strength × relevance to the validated knife_catch spec: -35% break after ≥2x
pump, 60-min hold, 35% stop, no trail, fresh graduates, $10k liq floor).

**1. Knife entries recur on runners — build re-entry, don't one-shot.**
Giants produced a median 2.5 (mean 3.25) close-basis -35% breaks pre-ATH — more intraday — and
every run >30 days offered ≥1, every run >90 days ≥2 (R3). A token that already paid a knife
trade is *more* interesting the next time it breaks -35% off a fresh high, not used up.
*Test:* in the panel, condition knife expectancy on "token had a prior knife event that resolved
to a new high" — if expectancy holds or improves, allow unlimited re-arms per token (re-arm on
each new post-trade high ≥2x). This is the cheapest extension: same signal, same exits, more
trades on the best population.

**2. Keep the 60-min timed exit; do not "upgrade" knife_catch into a hold-through-the-dip
strategy.** 23% of -35% episodes took >100 days to resolve (max 317d) and depth routinely ran to
-60%/-90% *after* triggering; staircase episodes bottomed at a median -80% (R3). The timed hold
is precisely what makes the fat left tail survivable, and those daily-close figures are lower
bounds. Any longer-hold variant must be a separate strategy with its own validation, wide stops,
and a time-stop — never a parameter tweak to the validated spec.

**3. If a moonbag/tail-rider is added, it must be time-boxed and trailed — never open-ended.**
Post-peak law: 12/12 ATHs terminal, median 33 days to below half of peak, 90.5% of post-ATH days
spent there, 0/12 reclaims in up to 880 days (R3). *Concrete design:* moonbag only from realized
profits (house money), a trail (e.g. exit on close below 50% of the position's local high held
N days, N≈30 per the 33-day median), and a hard calendar stop. *Test:* replay the 12-giant daily
series with "hold X% past first exit under rule R" vs the validated timed exit; any rule without a
kill condition will show the median ~-94% giveback.

**4. Do NOT build a $1M-stage narrative picker.** Published early signals predict graduation
(~$70K), a 10⁻² event, not gianthood (10⁻⁵–10⁻⁶); the giants flunked the clean-distribution
filters retail would use; the only forward test of curated picking went 0/10 on a hold basis
(R4). Engineering time spent here has negative expected value versus extending validated
microstructure edges.

**5. Treat CEX-listing and KOL pumps as distribution events — as knife context, hostile.**
2025 Binance listings: 24/27 negative, avg -44%; KOL-promoted coins 86% down 90% within 3 months
(R4); spot listings repeatedly marked tops (MOG, MOODENG, POPCAT) (R1). For this system the
actionable form: a -35% break whose preceding 2x pump was a listing/KOL announcement pump is a
break of *distributed* supply, not a shaken-out runner. *Test:* if listing/announcement timestamps
can be joined (even coarsely via volume-spike + trending-source metadata), split knife expectancy
by pump provenance; expect the announcement-pump subset to underperform.

**6. Hard-skip the celebrity/political insta-launch class.** Its lifecycle (HAWK -88% in 20 min,
LIBRA -95% same-day, YZY -74/-81% in hours, CAR -95% in 48h, 700+ Trump clones dead in hours)
is faster than a 60-min hold can survive, and the class is a documented harvesting machine with
80%+ bundled supply and pre-funded snipers (R2). The existing on-chain safety checks
(concentration, authorities, sellability) are the right defense — this evidence says keep them
strict even though they'd have excluded PEPE (R4): at minute scale on fresh launches, the
concentration filter's job is dodging LIBRA-class extraction, and the cost of missing a PEPE at
minute-scale is one foregone knife trade, not a foregone 350x.

**7. Twin/copycat awareness: later same-narrative launches are exit liquidity.** The twin question
settles in 24–72h; non-focal twins cap out 10–48x below the winner and die -95% in hours (R2).
*Test:* tag panel tokens by name/symbol similarity to an earlier, larger token in the same window;
measure knife expectancy on "derivative" vs "focal" tokens. If the derivative subset drags,
add a cheap name-dedup filter to safety.

**8. Regime dependence is structural — keep hot-window gating and re-validation cadence.**
The entire narrative economy broke at LIBRA (Feb 2025): launches -80%, graduation <1%, zero new
$1B coins after Jan 2025, memecoin cap -61% YoY (R2, R4). Base rates under this system's feet
drift by an order of magnitude between regimes. The walk-forward re-validation loop
(`research/run_validation.py`) and regime-aware sizing are not optional hygiene; the historical
record shows the same signal population can change character in weeks.

**9. Category as a conditioning feature — second-order, ex-post-labelling caveat.** Vertical-class
coins (news/political/AI-event) showed shallow fast dips (recover 2–23d) and short lives;
staircase-class (cult) showed -84/-95% multi-month shakeouts (R3). At 60-min holds this mostly
doesn't bind, but for any tail-rider variant: wider trails are justified *only* for cult-category
coins, and category is cleanly knowable only ex post — so test it as a label on the moonbag rule
(#3), not as an entry filter.

---

*Cross-references: `research/mining/failure-autopsy.md` (knife origin), `research/results/REPORT.md`
(validation), `config/knife.yaml` (live spec). Source data for the R3 lifecycle numbers:
DefiLlama daily series, listed in Report 3's source block.*

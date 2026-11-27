# Does the Price Tag Tell? Video Game Discount Speed as an Early Signal for Publishers

**Pilot study: Capcom, Square Enix and Ubisoft, PC games launched 2016–2024 (holdout 2025–2026)**

## Summary

When a big game sells badly, publishers often cut its price early. Those cuts are public on the day they happen, while the sales figures only reach investors weeks or months later in earnings reports. This project tests whether unusually early or deep discounting is an early warning about a publisher's earnings that the stock market misses.

Every test was pre-registered (`docs/preregistration.md`, committed before any data was collected), and every later change is logged with its reason in `docs/deviations.md`.

The pilot finds **no support for the hypothesis**:

- **Q1:** abnormal discount depth by day 90 does not predict a worse stock reaction at the next earnings announcement. The estimated relation is positive (+0.082, p = 0.16) and positive in every robustness variant.
- **Q2:** stocks drift down by about 3% in the two weeks after a game's first discount, but games with no early cut fall almost as much (-2.7% vs -3.1% for early-cut tentpoles; other early cuts fall only -0.5%), and partly coincides with Steam's seasonal sales. It is not specific to the signal.
- **Q3:** the pre-registered trading rule (short early-cut tentpoles from the discount until after earnings) loses 5.5% per trade after costs, worse than 99.7% of random-date placebo runs.

The results suggest, as an **exploratory hypothesis only**, that markets may briefly overreact to early discounts on major games, which then recover by the earnings report. It was found by looking at these data and needs to be tested on new data.

## 1. Question and hypotheses

- **H1 (Q1):** a game discounted more deeply than its publisher's norm by day 90 is followed by a negative abnormal stock return at the publisher's next earnings announcement.
- **H2 (Q2):** the market underreacts: little reaction when the discount appears, a negative reaction at earnings.
- **Q3:** shorting the publisher after an early cut on a major game, until after the next earnings, is profitable after costs and beats random-date placebos.

## 2. Data

| Source | What | Notes |
|---|---|---|
| Steam store API | App IDs, release dates, publishers | Current publisher names differ from launch publishers for games sold to Embracer (Eidos, Crystal Dynamics); launch publisher used |
| IsThereAnyDeal (ITAD) API | Full price history for each game's reference store | Steam for most games; Ubisoft Store or Epic for 15 games not on Steam at launch |
| Yahoo Finance | Daily adjusted closes, 2015–2026 | 9697.T, 9684.T, UBI.PA; Nikkei 225 and CAC 40 |
| Company investor relations | Earnings announcement dates, key titles | 44 scheduled announcements per publisher, 2016–2026 |
| Steam reviews (GetAppReviews) | Reviews in the first 30 and 90 days | Size (tentpole rule) and share positive (quality control) |

**Sample:** 74 eligible games (base games, launch price at least $39.99, PC launch within 30 days of the first release on any platform; remasters and collections excluded). 66 games launched 2016–2024 form the main sample (Capcom 13, Square Enix 25, Ubisoft 28); 8 games launched 2025–2026 form the holdout.

**Data problems found and fixed** (details in `docs/data_log.md`):

- **Wrong edition in the price history:** ITAD tracked Resident Evil Village's Deluxe Edition ($79.99) as the base game from the day its pre-orders opened. The launch price was corrected to $59.99 from contemporaneous sources, which also confirmed that no discount was missed. A similar six-day episode affects Assassin's Creed Odyssey and is documented.
- **Invalid price entries:** a $0.00 entry logged at the same second as a real discount (Exoprimal) is dropped; a standalone $0.00 entry, where ITAD stopped tracking a game (Marvel's Avengers), marks the price as unknown rather than carrying the last price forward.
- **Padded stock data:** Yahoo filled Japanese holidays and Ubisoft's November 2025 trading suspension with repeated prices at zero volume, which would have shown up as fake 0% returns. Zero-volume rows are dropped, so the return across a closure is recorded when trading resumes.
- **Retired endpoint:** Steam switched off its public reviews endpoint on 22 October 2026; reviews were collected from its documented replacement and validated against known totals.

## 3. Method

**Discount measure (D5, as revised).** For each game, `max_depth_k` is the deepest discount offered between day 15 and day k after launch, relative to the launch price. The pre-registered single-day depth was replaced before any stock data was collected, because it mostly measured whether day k happened to fall inside a temporary sale; it is kept as a robustness check.

**Publisher norm (D6).** `norm_k` is the median `max_depth_k` of the same publisher's earlier games (at least 5, otherwise all publishers' earlier games). `abn_90 = max_depth_90 - norm_90`. The norm matters: Square Enix and Ubisoft routinely discount by day 90, Capcom almost never does.

**Early cut (D15).** `early_cut_rt` flags a first cut of at least 20% by day 90 that is deeper than the norm on that day; every input is known on the cut date.

**Tentpole (D4).** Top quartile of 30-day Steam reviews among the publisher's games of the previous three years, or named as a key title in earnings materials before launch. The second criterion was applied with a written rule; it was not used for Square Enix, whose materials label nearly every release "major."

**Event study (D7–D9).** Abnormal returns from a market model (stock on local index) estimated over trading days [-250, -30]. `CAR_E` covers [-1, +1] around the first trading day after the earnings release, so pre-open, intraday and after-close releases are all captured. `CAR_D` covers [0, +2] and [0, +10] after the first discount, with day 0 the next trading day in the home market.

**Inference.** With three publishers, clustered inference is unreliable, so all p-values are descriptive. The publisher-block bootstrap was computed exactly over its 27 possible resamples. 32 specifications were run in total, all recorded in `docs/trial_log.csv`.

## 4. Results

### Q1: discount depth and the earnings reaction

Regression of `CAR_E` on `abn_90` with review share, log review count (with a missing-value indicator), the 60-day pre-event return and publisher fixed effects. 65 games, 45 announcements.

| Specification | abn_90 coefficient | SE | p | n |
|---|---|---|---|---|
| **Primary (HC1)** | **+0.082** | 0.059 | 0.16 | 65 |
| Clustered by announcement | +0.082 | 0.058 | 0.16 | 65 |
| No controls | +0.079 | 0.054 | 0.14 | 65 |
| Single-day depth (original D5) | +0.097 | 0.051 | 0.06 | 65 |
| Norm built on at least 5 games | +0.094 | 0.061 | 0.12 | 61 |
| Excluding games not on Steam at launch | +0.084 | 0.061 | 0.17 | 50 |
| One observation per announcement | +0.074 | 0.073 | 0.31 | 45 |
| Leave out Capcom / Square Enix / Ubisoft | +0.039 / +0.179 / +0.106 | | | 53 / 40 / 37 |

All 27 bootstrap resamples give a positive coefficient. The predicted sign was negative. A coefficient of +0.08 means a game discounted 10 points deeper than its publisher's norm is followed by an earnings reaction about 0.8 percentage points *higher*; with an SE of about 0.06, the pilot could only have detected effects of roughly ±0.12 or larger.

### Q2: the reaction at the discount

| Group | n | CAR_D [0, +10] | p | CAR_E | p |
|---|---|---|---|---|---|
| A: early-cut tentpole | 22 | -3.1% | 0.05 | +3.3% | 0.09 |
| B: early cut, not tentpole | 21 | -0.5% | 0.68 | +1.9% | 0.25 |
| C: no early cut | 23 | -2.7% | 0.03 | -1.7% | 0.29 |

Group A falls after the discount and rises at earnings, which is not the underreaction pattern of H2. But group C, which had no early cut, falls almost as much, and how far a cut exceeded its norm has no relation to the decline (coefficient -0.02, p = 0.86). The decline is gradual (most of it between days 5 and 12), and 48–68% of first discounts fall in June, November or December, against 25% if spread evenly, consistent with a seasonal component around Steam's major sales. Collapsing events that share a publisher and date changes little (A: -2.8%, p = 0.08), since such overlaps are rare.

### Q3: the trading rule

Short the stock against its index from the close of the discount day to the close of the first trading day after the next earnings release; 20 bp per side.

| Variant | Trades | Mean net per trade | t | Hit rate |
|---|---|---|---|---|
| **Primary** | **22** | **-5.5%** | -2.15 | 23% |
| Costs 10 / 40 bp | 22 | -5.3% / -5.9% | | |
| Stricter early-cut flag | 18 | -7.2% | -2.97 | 22% |
| Tentpole by review count only | 9 | -11.3% | -5.07 | 0% |

**Placebo (pre-registered):** the same trades on random dates at least 60 days from any real event, 1,000 times, average **+3.0%** (these stocks underperformed their indices over the period, so shorting them paid on most dates). The real rule is below 99.7% of placebo runs: after an early cut, tentpole stocks tended to *outperform* their index until the next earnings.

A second placebo restricted to the same calendar month was added after Q2 and turned out to be uninformative: its eligible dates are concentrated in a few years (for 12 of 14 Ubisoft trades, only November–December 2022 and 2025, just before Ubisoft's two largest crashes). It is reported but not used.

### Holdout (D13, run once)

8 games launched 2025–2026, analyzed once with the main-sample rules unchanged (`docs/holdout_run.txt`). There are **no early-cut tentpoles**, so Q3 cannot be tested out of sample. The simple Q1 slope is positive (+0.20), the same sign as the main sample, but it is not informative: Capcom's three games all have zero abnormal depth, pairs of games share announcements, and with no room for publisher fixed effects the slope mostly reflects the +18.9% abnormal reaction to Capcom's July 2026 results. One holdout game shows the cost of unscheduled news: Anno 117's 10-day discount window contains Ubisoft's -40% restructuring day (22 January 2026), giving a CAR_D of -31.7% unrelated to the discount.

## 5. What the pilot shows and does not show

**Shows:** in these three publishers, early discounting, as defined here, is not followed by worse earnings reactions, and a short strategy built on it loses money relative to random timing. The data pipeline and the pre-registered tests behave as intended, and the data problems that could have produced false results were caught.

**Does not show:** that discount signals carry no information in general. Three publishers cannot support reliable clustered inference, the holdout is too small, and the early-cut tentpole group has 22 games.

**Exploratory hypothesis (not a finding):** early cuts on major games are followed by a short dip and a stronger recovery into earnings, consistent with an initial overreaction. Because this pattern was found in the same data, it can only be tested on new data.

## 6. Limitations

- **Inference:** three publishers; p-values are descriptive.
- **Tentpole definition:** Steam review counts understate launches for publishers with their own stores (Ubisoft), while company labels are too generous for Ubisoft and uninformative for Square Enix.
- **Price data:** one game verified against independent sources; others screened with automated consistency checks.
- **Market model:** a broad national index does not remove sector or seasonal effects specific to games companies.
- **Contamination:** unscheduled company announcements (profit warnings, restructurings) can fall inside event windows; only scheduled earnings were flagged.
- **Trading rule:** borrow costs and short availability are not modeled.
- **Secondary outcome not analyzed:** the guidance-cut indicator (D7, D11) was not tested, because guidance changes were only recorded for some announcements. With two confirmed cuts in the sample, it could not have been tested meaningfully in the pilot.

## 7. Next steps for a full-sample version

1. Extend to the full publisher list from the roadmap, which is the only way to get enough publishers for proper inference and enough early-cut tentpoles to test the exploratory hypothesis.
2. Flag discount windows that overlap any company announcement, not only scheduled earnings.
3. Add a games-sector index, or a seasonal benchmark built from non-event years, to separate Steam-sale seasonality from discount effects.
4. Redesign the same-month placebo so its date pools are not concentrated in a few years.
5. Pre-register the overreaction hypothesis before looking at the new data.

## 8. Reproducing the results

From the repository root, with an ITAD API key in `.env`:

```
python -m src.fetch_steam search|details <publisher>
python -m src.fetch_itad <publisher>
python -m src.build_prices
python -m src.fetch_stocks
python -m src.fetch_reviews
python -m src.build_events
python -m src.event_study
python -m src.q1_regression
python -m src.q2_discount_reaction
python -m src.q3_trading_rule
```

Manual inputs are in `data/manual/` (game lists, exclusions, price overrides, earnings dates, key titles). Raw downloaded data is not redistributed.

# Deviations from pre-registration

## 2026-11-26: Clarification of D2(b), before any data collection
- Original: D2(b) excludes "DLC, expansion, bundle, remaster pack, or soundtrack" but does not address single-game remasters or remakes.
- New: Remakes rebuilt as new games (e.g., Resident Evil 2 (2019), Resident Evil 4 (2023)) count as base games. Remasters, ports, and collections of previously released games are excluded.
- Reason: Ambiguity found while compiling the Capcom candidate list. Decided before any price or stock data was collected.

## 2026-11-26: D5 primary discount measure changed, before any stock or earnings data was collected
- Original: depth_k = discount on calendar day k after launch; primary measure abn_90 uses depth_90.
- New: max_depth_k = deepest discount on any day from day 15 to day k. Primary measure abn_90 uses max_depth_90; publisher norms (D6) use max_depth_k. The original single-day depth_k is kept and reported as a robustness check.
- Reason: In the Capcom pilot price data, single-day depth mostly reflects whether day k falls inside a temporary Steam sale (e.g., Resident Evil 3: 34% at day 90, 0% at day 180; Resident Evil 7: first cut on day 59 but 0% on day 90). Decided from price data alone; no returns, earnings, or outcome data had been collected.

## 2026-11-27: D3 clarification: fallback store, before any stock or earnings data was collected
- Original: games not on Steam at launch use the publisher's primary PC store as recorded by ITAD.
- New: if that store's ITAD history starts more than 7 days after PC launch, use the Epic Game Store history instead, provided it starts within 7 days of launch. If neither does, the game is excluded for missing launch-period data.
- Reason: The Crew Motorfest's Ubisoft Store history starts 51 days after launch, missing most of the day 15-90 window; its Epic history starts on launch day. Ubisoft priced its games the same on both stores. Applied to: The Crew Motorfest.

## 2026-11-27: Robustness checks added after building the event table, before any abnormal returns were computed
Primary specifications unchanged. Added:
- early_cut_strict: first_cut_depth exceeds norm_at_first_cut by at least 0.10. Reason: early_cut_rt (D15) flags 17 of 25 Square Enix and 21 of 28 Ubisoft main-sample games, because early cuts are compared with norms at early days, when few earlier games had discounted.
- Event-level aggregation: games sharing the same earnings announcement are averaged into one observation (abn_90 averaged; one CAR_E per announcement).
- Norm-depth filter: drop games with n_norm_90 < 5.
- Pilot note: with 3 publishers, publisher-clustered inference (D10) is not reliable; pilot results are reported as descriptive.

## 2026-11-27: D4 and D10 for games not on Steam at launch, before any abnormal returns were computed
- Issue: 16 games (15 Ubisoft, Stranger of Paradise) launched on the Ubisoft Store or Epic, so no Steam reviews exist for their first 30/90 days after PC launch.
- reviews_pos (D10): use share positive in the first 90 days after Steam release (reviews_pos_steam), flagged; robustness check drops these games.
- size / tentpole (D4): D4(a) not applied to these games; tentpole status from D4(b) (named as a key title in the publisher's earnings materials) only. D4(a) quartiles computed among Steam-launch games.
- log(size) control (D10): missing-value indicator for these games.
- Also noted: Anno 1800 was pulled from Steam sale before launch; its launch-window reviews come only from Steam pre-orders, so its size understates launch demand (flagged).
- Correction (2026-11-27): the entry above should read 15 games (14 Ubisoft, Stranger of Paradise), not 16. Anno 1800 is not late to Steam (its Steam page existed at launch); it is flagged separately.

## 2026-11-27: Operational rule for D4(b), set before any abnormal returns were computed
- D4(b) applied to all games, as D4 is written ("either" criterion), not only to late-to-Steam games.
- Rule: a game is a key title if a results release published before its PC launch labels it AAA, or lists it in the top tier ("big brands", "major releases", "large game") of the fiscal year's line-up. A mention in a full release schedule or a lower tier (e.g. "long-lasting Live games") does not count. Renamed projects count (e.g. Gods & Monsters = Immortals Fenyx Rising).
- Ubisoft result: 19 of 28 games qualify, so tentpole (a or b) covers about two-thirds of Ubisoft games. Robustness check added: tentpole by D4(a) only.

## 2026-11-27: D4(b) by publisher, set before any abnormal returns were computed
- Square Enix: D4(b) not applied. Its results materials label nearly every new HD release a "major" title (slide headings "HD Games: Major New titles in FY..."; the FY2017/3 "major titles" list includes small releases), so the criterion does not discriminate. Square Enix tentpoles use D4(a) only. Known consequence: Shadow of the Tomb Raider, singled out as a major title in May 2018, is not a tentpole under D4(a). Stranger of Paradise (late to Steam) has no tentpole status and is excluded from tentpole splits.
- Capcom: D4(b) source is the annual "Sales Plan for Major Consumer Titles" (2-3 titles per year with unit targets). Applied to Street Fighter V (first game in the sample, no earlier games for D4(a)): yes. Other Capcom games use D4(a); D4(b) to be completed as a confirmation.

## 2026-11-27: Q1 script fixes after the first run (no change to the primary specification)
- event_level robustness row now uses the same sample as the primary model (Street Fighter V, which has no norm, was included before averaging: 46 vs 45 announcements). Bug fix.
- Controls that are constant within a subsample (size_missing in drop_late_to_steam) are dropped automatically, removing a rank-deficiency warning. Does not affect the abn_90 coefficient.
- First-run primary result (unchanged by these fixes): abn_90 coefficient +0.082 (HC1 SE 0.059, p = 0.16, n = 65), opposite in sign to the prediction.
- Clarification: the event_level estimate was unchanged by the fix (0.0736); statsmodels had already dropped the game with missing abn_90, so only the reported n_events count was wrong (46 -> 45).

## 2026-11-27: Q2 robustness check added after the first Q2 run
- date_clustered: events sharing a publisher and discount day 0 are averaged into one observation per group, and the number of distinct publisher-dates and the share of first discounts in June, November and December are reported.
- Reason: the first Q2 run showed similar post-discount declines in groups A and C, with a slow drift over days 5-12, consistent with many first discounts falling on the same Steam seasonal-sale days. Cross-sectional t-tests treat those events as independent. Added after seeing results, so reported as a robustness check, not a primary test.
- Result of the date_clustered check: little same-publisher same-day overlap (group A: 22 events on 21 publisher-dates; C: 23 on 22); estimates barely change (A: CAR_D_0_10 -2.8%, p = 0.079; C: -2.9%, p = 0.020). First discounts concentrate in June, November and December (48-68% vs 25% if uniform). Remaining explanation to test: a seasonal effect common to gaming stocks after Steam sales, addressed by the Q3 placebo test (D12).

## 2026-11-27: Q3 implementation details and placebos added after Q2, before Q3 was run
- "Next earnings announcement" (D12) = first scheduled announcement on or after the discount day 0; exit at the close of the first trading day after it (releases are after the close). Trade return = index return - stock return over the holding period, minus COST_BPS on the stock leg at entry and exit.
- Added placebo same_month: random entries restricted to the real entry's calendar month (tests the seasonal explanation from Q2).
- Added q2_month_placebo: mean market-model abnormal return over days 0..+10 after all first discounts vs random same-month dates, using each event's alpha and beta.
- The pre-registered random-date placebo (D12) is unchanged and remains the primary placebo test.
- Result: the same_month placebo is uninformative and is reported as such, not redesigned. Requiring the real entry's calendar month plus a 60-day gap from every real event leaves very small pools: 12 of 14 Ubisoft trades can only draw November-December dates from 2022 and 2025, which run into Ubisoft's January 2023 and January 2026 crashes (placebo mean +15.4% per trade). The q2_month_placebo uses the same pools, so the seasonal decomposition of the Q2 drift is inconclusive. The pre-registered random-date placebo (D12) remains the primary test.
- Q3 primary result: mean net -5.5% per trade (22 trades, t = -2.15, hit rate 23%); random-date placebo mean +3.0%, real result below 99.7% of placebo runs.

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

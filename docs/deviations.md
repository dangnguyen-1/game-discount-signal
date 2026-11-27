# Deviations from pre-registration

## 2026-11-26: Clarification of D2(b), before any data collection
- Original: D2(b) excludes "DLC, expansion, bundle, remaster pack, or soundtrack" but does not address single-game remasters or remakes.
- New: Remakes rebuilt as new games (e.g., Resident Evil 2 (2019), Resident Evil 4 (2023)) count as base games. Remasters, ports, and collections of previously released games are excluded.
- Reason: Ambiguity found while compiling the Capcom candidate list. Decided before any price or stock data was collected.

## 2026-11-26: D5 primary discount measure changed, before any stock or earnings data was collected
- Original: depth_k = discount on calendar day k after launch; primary measure abn_90 uses depth_90.
- New: max_depth_k = deepest discount on any day from day 15 to day k. Primary measure abn_90 uses max_depth_90; publisher norms (D6) use max_depth_k. The original single-day depth_k is kept and reported as a robustness check.
- Reason: In the Capcom pilot price data, single-day depth mostly reflects whether day k falls inside a temporary Steam sale (e.g., Resident Evil 3: 34% at day 90, 0% at day 180; Resident Evil 7: first cut on day 59 but 0% on day 90). Decided from price data alone; no returns, earnings, or outcome data had been collected.

# Pre-registration

Project: Does the Price Tag Tell? Video Game Discount Speed as an Early Signal for Publishers

These decisions are fixed before any data is collected or analyzed. The commit timestamp of this file is the record. Any later change goes in `docs/deviations.md` (date, original decision, new decision, reason); this file is not edited after the first commit.

Differences from roadmap v1.0, made before this commit:

- **D4** uses only games launched before game g, so the tentpole flag contains no future information.
- **D9** sets day 0 for US-listed publishers to the calendar day the discount appeared, because Steam sales start during US trading hours.
- **D12** and a new **real-time early-cut flag (D15)**: the trading rule enters on a signal that is fully known on the entry date, instead of one that depends on day-90 depth.

## Decisions

**D1: Sample period.** Games launched on PC from 1 January 2016 to the data collection date minus 180 days, so every game has at least 180 days of price history. Games launched from 1 January 2025 onward form the holdout (D13).

**D2: Game eligibility.** A game is included if: (a) it is published by a company on the publisher list while that company is listed; (b) it is a base game (not DLC, expansion, bundle, remaster pack, or soundtrack); (c) its US Steam regular price at launch is at least $39.99; (d) it launched on PC within 30 days of its first release on any platform; (e) it is sold on Steam at launch, or on another store covered by IsThereAnyDeal (ITAD) if it was not on Steam initially (record which store). Free-to-play games are excluded.

**D3: Reference store and region.** Prices are US-dollar prices on the US Steam store. For games not on Steam at launch, use the publisher's primary PC store as recorded by ITAD, and flag the game.

**D4: Tentpole definition.** A game is a tentpole if either:
(a) its `size` (first-30-day Steam reviews) is in the top quartile among that publisher's eligible games launched in the three years before game g's launch date, using only games launched before g; or
(b) the publisher's own earnings materials, published before game g's launch, name it as a key title for the fiscal year.
If fewer than 4 earlier games are available for (a), use all publishers' eligible games launched in the same three-year window, and flag the game. Record which criterion applies.

**D5: Discount measurement.** Use the lowest price available on the reference store each day. Ignore launch discounts in the first 14 days. Depth on day k is measured on calendar day k after launch, with k = 45, 90, 180. The primary measure is `abn_90`.

**D6: Publisher norm.** `norm_p,k` is the median `depth_k` over that publisher's eligible games launched before game g, requiring at least 5 earlier games. Before 5 are available, use the median over all publishers' earlier games, and flag the game. The same rule defines `norm_p,d` for any day d (used in D15).

**D7: Primary outcome for Q1.** `CAR_E` over trading days [-1, +1] around the first earnings announcement after day 90 of the game's launch. Secondary: a guidance-cut indicator at that announcement (D11).

**D8: Market model.** Abnormal returns use a market model estimated over trading days [-250, -30] before each event, with the publisher's local benchmark index. All returns in local currency.

**D9: Event-day timing.** Day 0 for a discount depends on the publisher's home market:
- US-listed publishers: the calendar date the discount first appeared, if it is a US trading day; otherwise the next US trading day. Steam sales typically start in the US Pacific morning, during the US trading session.
- All other publishers: the first trading day in the home market strictly after the calendar date the discount first appeared, since the discount starts after the close in Asia and Europe.
Robustness: apply the strictly-after rule to US publishers as well.

**D10: Controls.** All Q1 regressions include `reviews_pos` measured on day 90, `log(size)`, and the publisher's pre-event 60-day return. Publisher fixed effects are included. Standard errors are clustered by publisher, with a publisher-block bootstrap as the main inference.

**D11: Guidance cuts.** A guidance cut is recorded when the publisher lowers its full-year revenue, bookings, or profit forecast at the announcement, based on its press release. Record "no guidance given" separately.

**D12: Trading rule (Q3).** For each tentpole game with `early_cut_rt = 1` (D15): short the publisher's stock against its local index from the close of discount day 0 (D9) to the close of the trading day after the next earnings announcement. Equal weight per event. Transaction cost: 20 basis points per side on the stock leg (robustness: 10 and 40). Borrow costs are noted as a limitation.

**D13: Holdout.** Games launched from 1 January 2025 onward are analyzed once, after all other decisions and robustness checks are final, and reported separately.

**D14: Trial log.** Every variant tested is logged in `docs/trial_log.csv`; the total count is reported in the write-up.

**D15: Real-time early-cut flag.** Let d be `first_cut_day`, the first day after day 14 with a discount of at least 20%, and `first_cut_depth` the depth on that day. Then:

    early_cut_rt = 1 if d <= 90 and first_cut_depth >= 0.20 and first_cut_depth > norm_p,d, else 0

Every input is known on the first-cut date. `early_cut_rt` is used for the Q2 group comparisons and the Q3 trading rule. The original `early_cut` (based on `abn_90`) is kept for Q1 descriptive tables only.

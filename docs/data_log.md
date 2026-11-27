
## ITAD price histories
- Downloaded 2026-11-26 21:36 UTC (DATA_COLLECTION_DATE = 2026-11-26).
- Endpoints: GET /games/lookup/v1 (by Steam appid), GET /games/history/v2 (id, country=US, shops=61, since=2010-01-01).
- Steam shop ID on ITAD: 61.
- Capcom pilot: 16 games, all matched, all histories start before PC launch (pre-order tracking).

## Sources and choices
- ITAD API terms read 2026-11-26 (docs.isthereanydeal.com). Raw responses not redistributed; derived measures only.
- Benchmark indices: Nikkei 225 (^N225) for all Japanese publishers; CAC 40 (^FCHI) for French publishers. TOPIX not used because its free Yahoo Finance data is unreliable.
- Steam publisher strings for Capcom: "CAPCOM Co., Ltd.", "Capcom", "Capcom U.S.A, Inc." (stored without commas in publishers.csv; matching ignores punctuation).

## Price history cleaning rules (applied in build_prices.py; raw ITAD files are never modified)
1. Drop entries with a regular price of 0 or less. Found in Exoprimal (2023-11-02): a $0.00 entry with the same timestamp as a real 35% discount. Applied before the same-day lowest-price rule (Section 8.4), which would otherwise record a 100% discount.
2. Corrections from external sources go in data/manual/price_overrides.csv, with the source and date checked. Found in Resident Evil Village: ITAD shows a $79.99 regular price from 2021-01-22 to 2021-10-20, 43 minutes after a $59.99 listing, and later returns to $59.99 with no recorded change.
- Square Enix pilot: downloaded 2026-11-27 02:56 UTC; 27 games, all matched, all histories start before PC launch. DATA_COLLECTION_DATE kept at 2026-11-26 for all publishers so every series ends on the same day.
- Cleaning rule 1 refined (2026-11-27): a zero-regular entry sharing a timestamp with a real entry is dropped (Exoprimal). A standalone zero-regular entry marks the price as unknown until the next real entry, instead of carrying the previous price forward (Marvel's Avengers, 2021-07-31: ITAD appears to stop tracking the base game after ~2021-03; first 180 days unaffected).
- Babylon's Fall: retired from sale in 2022 after day 180; removal not recorded by ITAD; measures to day 180 unaffected.
- Ubisoft pilot: downloaded 2026-11-27 UTC; 30 games. Reference stores: 15 Steam (ITAD shop 61), 14 Ubisoft Store (shop 62), 1 Epic (shop 16; The Crew Motorfest, D3 fallback). Stranger of Paradise (Square Enix) uses Epic under D2(e), PC launch 2022-03-18. Shop IDs from /service/shops/v1 on 2026-11-27.
- The Division 2 (Ubisoft Store): history starts 4 days after launch (within the 7-day tolerance); days 0-3 have no price.
- Bug fixed in fetch_itad.py summarize(): launch price fell back to the last history entry instead of the first when no pre-launch entry existed (Steep, The Division 2 showed $29.99). Coverage summary only; build_prices.py was not affected.
- Price above P0 (likely edition mix-up, as with Resident Evil Village): Far Cry 5 days 305-306 ($69.99), outside all measurement windows, no effect. Assassin's Creed Odyssey days 32-37 (2018-11-06 to 11-11, $79.99), inside the window: a sale on those days would be missed, which could affect max_depth_45 and first_cut_day (47); max_depth_90 (0.50) cannot be affected. Kept as is; added to spot-check list.

## Stock prices (Yahoo Finance via yfinance)
- Downloaded 2026-11-27: 9697.T, 9684.T, UBI.PA, ^N225, ^FCHI, adjusted closes, 2015-01-01 to DATA_COLLECTION_DATE. Raw files not committed.
- Zero-volume rows dropped: Yahoo pads exchange holidays (Tokyo: 24 rows, mostly 2017-2018 Japanese holidays; Paris: 2019-12-25) and the Ubisoft trading suspension (2025-11-14 to 11-20) with a repeated price at zero volume. The return across a closure is recorded on the day trading resumes (Ubisoft: 2025-11-21).
- Index returns are computed over the stock's own trading days, so both returns always cover the same interval.
- Largest moves checked against news: Ubisoft 2026-01-22 (-40%, restructuring and six cancellations), 2024-10-04 (+34%, buyout reports); Capcom 2024-08-05/06 (global market crash and rebound, Nikkei -12%/+10%).

## Earnings announcement dates
- Capcom: 44 announcements (2016-01-28 to 2026-10-27), collected from Capcom IR calendar archive pages and press releases (capcom.co.jp blocks scripts, so dates were gathered via web search of those pages). Releases came after the Tokyo close (15:20 JST observed) before 2024-11-05; the 8 later releases need their time checked against the 15:30 close. Consistent with returns: the three largest Capcom up-days (2019-08-02, 2023-07-27, 2026-07-29) each follow a Q1 release by one trading day.
- Square Enix: 44 announcements (2016-02-04 to 2026-11-11), from the IR calendar page (hd.square-enix.com/eng/ir/calendar.html) plus the 2016-02-04 press release. Fiscal years labeled by start year, as for Capcom. Large next-day moves after releases (2020-08-07, 2020-11-09, 2023-08-07, 2024-05-14) are consistent with after-close timing. Largest move, +16.1% on 2025-04-30, is not an earnings date.
- Ubisoft: 44 scheduled announcements (2016-02-11 to 2026-11-19) plus 4 unscheduled (2017-12-07, 2023-01-11, 2024-09-25, 2026-01-21), marked in event_type. Sources: GlobeNewswire press releases, AMF filings (echanges.dila.gouv.fr), Euronext company news, MarketScreener calendar. Releases at 17:40 Paris time, after the 17:30 close, from 2017; 2016 release times unconfirmed. 2025-11-21 results followed a trading suspension (2025-11-14 to 11-20): check release time vs reopening.

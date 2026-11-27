
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

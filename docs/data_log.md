
## ITAD price histories
- Downloaded 2026-11-26 21:36 UTC (DATA_COLLECTION_DATE = 2026-11-26).
- Endpoints: GET /games/lookup/v1 (by Steam appid), GET /games/history/v2 (id, country=US, shops=61, since=2010-01-01).
- Steam shop ID on ITAD: 61.
- Capcom pilot: 16 games, all matched, all histories start before PC launch (pre-order tracking).

## Sources and choices
- ITAD API terms read 2026-11-26 (docs.isthereanydeal.com). Raw responses not redistributed; derived measures only.
- Benchmark indices: Nikkei 225 (^N225) for all Japanese publishers; CAC 40 (^FCHI) for French publishers. TOPIX not used because its free Yahoo Finance data is unreliable.
- Steam publisher strings for Capcom: "CAPCOM Co., Ltd.", "Capcom", "Capcom U.S.A, Inc." (stored without commas in publishers.csv; matching ignores punctuation).

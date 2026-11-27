# Does the Price Tag Tell?

**Video game discount speed as an early signal for publisher stocks: a pre-registered event study**

When a big game sells badly, its publisher often cuts the price early. Those cuts are public the day they happen, while sales figures only reach investors weeks later in earnings reports. This project tests whether unusually early discounting predicts the stock reaction at the next earnings announcement, and whether a trading rule built on it makes money.

Pilot: **Capcom, Square Enix and Ubisoft**, 66 PC games launched 2016–2024, plus 8 games from 2025–2026 held out and analyzed once.

## Headline results

| Question | Prediction | Result |
|---|---|---|
| Does abnormal discount depth by day 90 predict the earnings reaction? | Negative | Positive and not significant (+0.08, p = 0.16), positive in every robustness variant |
| Does the market react at the discount or only at earnings? | Underreaction | A ~3% decline after first discounts for early-cut major games, but a similar one for games with no early cut; partly seasonal |
| Is shorting after an early cut on a major game profitable? | Yes | -5.5% per trade after costs, worse than 99.7% of random-date placebo runs |

The hypothesis is not supported. The results hint, as an exploratory idea for future testing, that markets may briefly overreact to early discounts on major games, which then recover by the earnings report.

Full write-up: **[docs/report.md](docs/report.md)**

## How it was done

- **Pre-registered.** All tests were fixed in [docs/preregistration.md](docs/preregistration.md) before any data was collected. Every later change, with its date and reason, is in [docs/deviations.md](docs/deviations.md), and every specification run is in [docs/trial_log.csv](docs/trial_log.csv).
- **Discount data:** full price histories from the IsThereAnyDeal API (Steam, Ubisoft Store and Epic), cleaned for tracking errors, measured against each publisher's own discounting norm.
- **Event study:** market-model abnormal returns around earnings announcements and first discounts, with placebo tests on random dates.
- **Data checks:** problems found and fixed are documented in [docs/data_log.md](docs/data_log.md), including a wrong-edition price history, a stock trading suspension padded with fake prices, and a retired Steam API.

## Repository layout

```
src/            data collection, cleaning, event study and analysis scripts
data/manual/    hand-built inputs: game lists, exclusions, earnings dates, key titles, price overrides
data/processed/ derived per-game measures (raw downloads are not committed)
output/         result tables and figures
docs/           pre-registration, deviations, data log, trial log, report
config.py       all parameters, matching the pre-registration
run_all.py      reruns the analysis in order
```

## Reproducing

Requires Python 3.11+ and an IsThereAnyDeal API key in `.env` (`ITAD_API_KEY=...`).

Data collection, per publisher (`capcom`, `square_enix`, `ubisoft`), then once for all:

```
pip install -r requirements.txt
python -m src.fetch_steam search <publisher>    # suggests app IDs; verified IDs go in data/manual/candidates_<publisher>.csv
python -m src.fetch_steam details <publisher>
python -m src.fetch_itad <publisher>
python -m src.build_prices
python -m src.fetch_stocks
python -m src.fetch_reviews
```

Earnings dates (`data/manual/earnings_<publisher>.csv`) and tentpole key titles were compiled by hand from investor relations materials; sources are in the files and in `docs/data_log.md`.

Analysis, from the collected data:

```
python run_all.py
```

This runs `build_prices`, `fetch_stocks` (from the cached prices), `build_events`, `event_study`, `q1_regression`, `q2_discount_reaction` and `q3_trading_rule` in order. The holdout analysis (`src.holdout`) is not included: it was run once, as the pre-registration requires (`docs/holdout_run.txt`).

Raw data from IsThereAnyDeal, Steam and Yahoo Finance is downloaded locally and not redistributed.

## Limitations

Three publishers cannot support reliable clustered inference, so the pilot's p-values are descriptive, and the holdout contains no trades. See the report for the full list and the next steps for a full-sample version.

## License

The code is released under the MIT License (see `LICENSE`). Data obtained from IsThereAnyDeal, Steam and Yahoo Finance remains subject to those services' terms.

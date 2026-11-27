"""
Phase 6: event table, one row per game.

Usage, from the repo root:
    python -m src.build_events

Inputs:  data/processed/game_prices.csv, data/processed/daily_prices.csv,
         data/manual/earnings_<publisher>.csv, data/interim/returns.csv
Output:  data/processed/events.csv

Rules (docs/preregistration.md, with logged deviations):
  D5/D6   max_depth_k vs publisher norm: median max_depth_k of the publisher's games launched
          before this one; at least MIN_NORM_GAMES earlier games, otherwise all publishers' earlier games.
  D15     early_cut_rt: first cut (>= 20%) by day 90 that is deeper than the norm at that day.
  D7      earnings event: first scheduled announcement more than 90 days after PC launch.
  D9      day 0 for non-US publishers: first trading day strictly after the calendar date.
          Earnings released after the close: first trading day strictly after the release date.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

import config

US_TICKERS = set()   # no US-listed publishers in the pilot; D9 same-day rule would apply to these


def load_inputs():
    games = pd.read_csv(config.PROCESSED / "game_prices.csv", parse_dates=["pc_launch_date"])
    daily = pd.read_csv(config.PROCESSED / "daily_prices.csv")
    returns = pd.read_csv(config.INTERIM / "returns.csv", parse_dates=["date"])
    earnings = pd.concat([pd.read_csv(p, parse_dates=["announcement_date"])
                          for p in sorted(config.MANUAL.glob("earnings_*.csv"))], ignore_index=True)
    if "event_type" not in earnings.columns:
        earnings["event_type"] = "scheduled"
    earnings["event_type"] = earnings["event_type"].fillna("scheduled")
    return games, daily, returns, earnings


def cumulative_max_depth(daily):
    """For each game: deepest discount from day 15 up to each day (index = day)."""
    out = {}
    for appid, g in daily.groupby("steam_appid"):
        g = g.sort_values("day")
        depth = g["depth"].where(g["day"] > config.LAUNCH_DISCOUNT_DAYS, 0.0)
        out[appid] = depth.fillna(0.0).cummax().to_numpy()
    return out


def norm_pool(games, g):
    """Earlier games used for g's norm, and whether they are the publisher's own or pooled."""
    earlier = games[games["pc_launch_date"] < g["pc_launch_date"]]
    own = earlier[earlier["publisher"] == g["publisher"]]
    if len(own) >= config.MIN_NORM_GAMES:
        return own, "own"
    return earlier, "pooled"


def norm_at(pool, col):
    vals = pool[col].dropna()
    return (vals.median(), len(vals)) if len(vals) else (np.nan, 0)


def norm_at_day(pool, cummax, d):
    vals = [cummax[a][d] for a in pool["steam_appid"] if a in cummax and len(cummax[a]) > d]
    return (float(np.median(vals)), len(vals)) if vals else (np.nan, 0)


def next_trading_day(trading_days, date, strictly_after=True):
    """First trading day after (or on) a calendar date; NaT if beyond the data."""
    idx = trading_days.searchsorted(date, side="right" if strictly_after else "left")
    return trading_days[idx] if idx < len(trading_days) else pd.NaT


def trading_gap(trading_days, a, b):
    """Number of trading days from a to b (b - a), or NaN."""
    if pd.isna(a) or pd.isna(b):
        return np.nan
    return int(trading_days.searchsorted(b) - trading_days.searchsorted(a))


def main():
    games, daily, returns, earnings = load_inputs()
    cummax = cumulative_max_depth(daily)
    tickers = earnings.groupby("publisher")["ticker"].first().to_dict()
    calendars = {t: pd.DatetimeIndex(sorted(r["date"].unique())) for t, r in returns.groupby("ticker")}

    rows = []
    for _, g in games.iterrows():
        pub, launch = g["publisher"], g["pc_launch_date"]
        ticker = tickers.get(pub)
        days = calendars.get(ticker)
        flags = [f for f in str(g.get("flags", "")).split("; ") if f and f != "nan"]
        pool, norm_source = norm_pool(games, g)

        row = {"publisher": pub, "ticker": ticker, "game_title": g["game_title"],
               "steam_appid": g["steam_appid"], "pc_launch_date": launch.date(),
               "holdout": g["holdout"], "norm_source": norm_source}

        # D5/D6: abnormal depth (primary: max depth; robustness: single-day depth)
        for k in config.DEPTH_DAYS:
            norm, n = norm_at(pool, f"max_depth_{k}")
            row[f"max_depth_{k}"] = g[f"max_depth_{k}"]
            row[f"norm_{k}"] = norm
            row[f"abn_{k}"] = g[f"max_depth_{k}"] - norm
            row[f"n_norm_{k}"] = n
            single_norm, _ = norm_at(pool, f"depth_{k}")
            row[f"abn_single_{k}"] = g[f"depth_{k}"] - single_norm
        if row["n_norm_90"] == 0:
            flags.append("no_earlier_games_for_norm")

        # D15: real-time early-cut flag, plus the original abn_90-based flag (descriptive only)
        d, depth_d = g["first_cut_day"], g["first_cut_depth"]
        row["first_cut_day"], row["first_cut_depth"] = d, depth_d
        if pd.notna(d) and d <= config.EARLY_CUT_MAX_DAY:
            norm_d, _ = norm_at_day(pool, cummax, int(d))
            row["norm_at_first_cut"] = norm_d
            row["early_cut_rt"] = bool(depth_d >= config.FIRST_CUT_THRESHOLD and depth_d > norm_d)
        else:
            row["norm_at_first_cut"] = np.nan
            row["early_cut_rt"] = False
        row["early_cut"] = bool(pd.notna(d) and d <= config.EARLY_CUT_MAX_DAY and row["abn_90"] > 0)

        # D9: discount event day 0 (first-cut date)
        if pd.notna(d) and days is not None:
            cut_date = launch + timedelta(days=int(d))
            row["first_cut_date"] = cut_date.date()
            row["day0_discount"] = next_trading_day(days, cut_date, strictly_after=ticker not in US_TICKERS)
        else:
            row["first_cut_date"], row["day0_discount"] = None, pd.NaT

        # D7: first scheduled earnings announcement more than 90 days after launch
        e = earnings[(earnings["publisher"] == pub) & (earnings["event_type"] == "scheduled") &
                     (earnings["announcement_date"] > launch + timedelta(days=config.PRIMARY_DEPTH_DAY))]
        e = e.sort_values("announcement_date")
        if len(e) and days is not None:
            ann = e.iloc[0]
            same_day = ann["timing"] in ("before_open", "during_session")
            if ann["timing"] == "check":
                flags.append("earnings_timing_unchecked")
            row.update({"earnings_date": ann["announcement_date"].date(), "earnings_period": ann["period"],
                        "earnings_timing": ann["timing"], "guidance_change": ann.get("guidance_change"),
                        "day0_earnings": next_trading_day(days, ann["announcement_date"], strictly_after=not same_day)})
            unsched = earnings[(earnings["publisher"] == pub) & (earnings["event_type"] == "unscheduled") &
                               (earnings["announcement_date"] > launch) &
                               (earnings["announcement_date"] < ann["announcement_date"])]
            if len(unsched):
                flags.append("unscheduled_update_before_earnings:" +
                             ",".join(unsched["announcement_date"].dt.strftime("%Y-%m-%d")))
        else:
            row.update({"earnings_date": None, "earnings_period": None, "earnings_timing": None,
                        "guidance_change": None, "day0_earnings": pd.NaT})
            flags.append("no_earnings_event_in_data")

        # windows that overlap would mix the two events
        gap = trading_gap(days, row["day0_discount"], row["day0_earnings"]) if days is not None else np.nan
        row["discount_to_earnings_tdays"] = gap
        if pd.notna(gap) and abs(gap) <= 10:
            flags.append("discount_within_10_tdays_of_earnings")

        row["tentpole"] = None     # D4: filled once first-30-day Steam reviews are collected
        row["flags"] = "; ".join(flags)
        rows.append(row)

    events = pd.DataFrame(rows)
    for c in ["day0_discount", "day0_earnings"]:
        events[c] = pd.to_datetime(events[c]).dt.date
    out = config.PROCESSED / "events.csv"
    events.to_csv(out, index=False)

    main_sample = events[~events["holdout"]]
    print(f"Saved {out}: {len(events)} games ({len(main_sample)} main sample, {events['holdout'].sum()} holdout)\n")
    print(main_sample.groupby("publisher").agg(
        games=("game_title", "size"), own_norm=("norm_source", lambda s: (s == "own").sum()),
        early_cut_rt=("early_cut_rt", "sum"), early_cut=("early_cut", "sum"),
        median_abn_90=("abn_90", "median")).round(3).to_string())
    show = events[["publisher", "game_title", "max_depth_90", "norm_90", "abn_90", "first_cut_day",
                   "early_cut_rt", "day0_discount", "earnings_date", "day0_earnings", "flags"]].copy()
    print("\n" + show.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
